"""Prepared SRH OFF/ON/lifetime experiment. No solve or output on import.

Run pilot first; extension requires a reviewed, matching PASS SRH pilot.
Existing voltage runs are read-only references. Never automatically retry run_002.
"""
import argparse
from contextlib import closing
from copy import deepcopy
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import traceback

from src.device.pn_junction import validate_bias, bias_grid, assess_bias, simulate_bias_branch
from src.physics.srh import validate_srh
from validation.analytic.pn_junction.run_voltage import compare_rows
from validation.analytic.pn_junction.run_pn_junction import write_json, write_csv
from validation.analytic.pn_junction.export_vtm import export_vtm

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ('src/device/pn_junction.py', 'src/physics/srh.py',
           'validation/analytic/pn_junction/run_srh.py',
           'validation/analytic/pn_junction/run_voltage.py',
           'validation/analytic/pn_junction/run_pn_junction.py',
           'validation/analytic/pn_junction/export_vtm.py')


def load_config(path):
    path = Path(path).resolve()
    experiment = json.loads(path.read_text(encoding='utf-8'))
    base_path = path.parent / experiment['base_config']
    config = json.loads(base_path.read_text(encoding='utf-8'))
    sweep = deepcopy(experiment['transport'])
    if experiment['model'] != 'drift_diffusion_srh' or sweep['extended_precision'] is not True:
        raise ValueError('SRH experiment requires extended precision')
    names = [case['name'] for case in experiment['cases']]
    if len(names) != len(set(names)) or not names or names[0] != 'off':
        raise ValueError('Unique cases beginning with off required')
    if experiment['cases'][0]['enabled'] or not any(c['enabled'] for c in experiment['cases']):
        raise ValueError('OFF and ON cases required')
    for case in experiment['cases']:
        if not case['name'].isascii() or not case['name'].replace('_','').isalnum():
            raise ValueError('Case names must be safe ASCII identifiers')
        validate_srh(case)
        for stage in ('pilot', 'extension'):
            validate_bias(config, case_sweep(sweep, case), stage)
    tolerance = experiment['equilibrium_mass_action_rtol']
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int,float)) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Positive finite equilibrium tolerance required')
    hashes = {str(p.name): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (path, base_path)}
    return config, sweep, experiment, hashes


def case_sweep(sweep, case):
    result = deepcopy(sweep)
    result.update(model='drift_diffusion_srh', srh=deepcopy(case))
    return result


def continuity_metrics(config, state):
    """Interior control volumes: dJn/dx=qU, dJp/dx=-qU.

    Exclude contact half-cells to match first-to-last edge current differences.
    """
    nodes, edges = state['nodes'], state['edges']
    rates, volumes = nodes['SRHNetRate_cm3_per_s'], nodes['ControlVolume_cm']
    source = [config['electron_charge_C']*r*v for r,v in zip(rates[1:-1],volumes[1:-1])]
    integral = math.fsum(source)
    jn,jp = edges['ElectronCurrent_A_per_cm2'],edges['HoleCurrent_A_per_cm2']
    return dict(
        q_integral_U_A_per_cm2=integral,
        q_integral_abs_U_A_per_cm2=math.fsum(abs(v) for v in source),
        electron_integral_residual_A_per_cm2=abs(jn[-1]-jn[0]-integral),
        hole_integral_residual_A_per_cm2=abs(jp[-1]-jp[0]+integral),
        electron_local_residual_A_per_cm2=max(abs(b-a-u) for a,b,u in zip(jn,jn[1:],source)),
        hole_local_residual_A_per_cm2=max(abs(b-a+u) for a,b,u in zip(jp,jp[1:],source)),
        source_current_scale_A_per_cm2=max(abs(v) for v in jn+jp)+abs(integral),
        max_abs_U_cm3_per_s=max(abs(v) for v in rates),
    )


def assess_srh(config, sweep, experiment, state, peak_field_method='edge'):
    metric, checks = assess_bias(config, sweep, state)
    extra = continuity_metrics(config, state)
    metric.update(extra)
    limit = sweep['current_atol_A_per_cm2'] + sweep['current_conservation_rtol']*extra['source_current_scale_A_per_cm2']
    def check(name, error, bound):
        checks.append(dict(check=name, error=error, limit=bound,
                           passed=math.isfinite(error) and error <= bound))
    for name in ('electron_integral_residual_A_per_cm2', 'hole_integral_residual_A_per_cm2',
                 'electron_local_residual_A_per_cm2', 'hole_local_residual_A_per_cm2'):
        check(name, extra[name], limit)
    if state['applied_V'] == 0:
        check('equilibrium_integrated_abs_SRH', extra['q_integral_abs_U_A_per_cm2'], sweep['current_atol_A_per_cm2'])
        nodes = state['nodes']
        error = max(abs(n*p/config['intrinsic_density_cm3']**2-1)
                    for n,p in zip(nodes['Electrons_cm3'], nodes['Holes_cm3']))
        check('equilibrium_mass_action', error, experiment['equilibrium_mass_action_rtol'])
    if peak_field_method == 'junction_linear_v1':
        field = junction_peak_field(state)
        metric.update(field)
        check('junction_left_right_consistency',
              abs(field['junction_left_E_V_per_cm']-field['junction_right_E_V_per_cm']),
              sweep['comparison_rtol']*field['peak_abs_E_V_per_cm'])
    elif peak_field_method != 'edge':
        raise ValueError('Unknown peak-field extraction method')
    return metric, checks


def transport_physics(sweep):
    """Compare every solver/assessment setting, excluding grids and provenance."""
    return {k:v for k,v in sweep.items() if k not in ('stages', 'base_config', 'note')}


def pilot_compatibility(snapshot, config, sweep, experiment):
    """Only extension grids, labels and config packaging may change."""
    def physics_cases(cases):
        return [{k:v for k,v in c.items() if k != 'display_name'} for c in cases]
    return (snapshot['base_model'] == config
            and transport_physics(snapshot['transport']) == transport_physics(sweep)
            and snapshot['transport']['stages']['pilot'] == sweep['stages']['pilot']
            and snapshot['experiment']['model'] == experiment['model']
            and snapshot['experiment']['equilibrium_mass_action_rtol'] == experiment['equilibrium_mass_action_rtol']
            and physics_cases(snapshot['experiment']['cases']) == physics_cases(experiment['cases']))


def resolved_magnitudes(rows, key='J_A_per_cm2'):
    """Preserve positions with NaN so missing/zero-bias points are not bridged."""
    return [abs(r[key]) if r['current_resolved'] and r['applied_V'] != 0 else math.nan for r in rows]


def junction_peak_field(state):
    """Postprocess a continuous-field Si junction; never modify the DD state.

    Extrapolate independently on each side, not across the doping discontinuity.
    On a uniform mesh E(j) = (3*E_nearest - E_next)/2 + O(h**2).
    Keep both estimates so agreement can be checked rather than hidden by averaging.
    This estimator is not intended for dielectric interfaces or sheet charges.
    """
    x = state['edges']['x_cm']
    field = state['edges']['ElectricField_V_per_cm']
    junction = state['junction_cm']
    if (len(x) != len(field) or len(x) < 4
            or not all(math.isfinite(v) for v in [junction, *x, *field])
            or any(b <= a for a, b in zip(x, x[1:]))):
        raise ValueError('Finite ordered edge coordinates and fields required')
    left = [i for i, value in enumerate(x) if value < junction]
    right = [i for i, value in enumerate(x) if value > junction]
    if len(left) < 2 or len(right) < 2 or any(value == junction for value in x):
        raise ValueError('Junction must be bracketed by two edges on each side')
    def extrapolate(a, b):
        return field[a] + (junction-x[a])*(field[b]-field[a])/(x[b]-x[a])
    a = extrapolate(left[-1], left[-2])
    b = extrapolate(right[0], right[1])
    raw = max(map(abs, field))
    return dict(edge_peak_abs_E_V_per_cm=raw,
                junction_left_E_V_per_cm=a, junction_right_E_V_per_cm=b,
                peak_abs_E_V_per_cm=max(raw, abs(a), abs(b)))


def recheck_failed_fields(source, out, config, sweep, experiment):
    """Targeted fresh solves only; not a full extension PASS or figure run."""
    source, out = Path(source).resolve(), Path(out).resolve()
    if out.exists() or out.is_relative_to(source):
        raise FileExistsError('Use a new targeted output, never the original run')
    before = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in source.rglob('*') if p.is_file()}
    snapshot = json.loads((source/'config.json').read_text(encoding='utf-8'))
    if (snapshot['base_model'] != config or snapshot['transport'] != sweep
            or snapshot['experiment'] != experiment):
        raise ValueError('Targeted recheck requires identical original configuration')
    original_summary = json.loads((source/'summary.json').read_text(encoding='utf-8'))
    if original_summary['status'] != 'FAIL':
        raise ValueError('Expected a saved FAIL run')
    with (source/'validation.csv').open(newline='', encoding='utf-8') as handle:
        failed = [(line, row) for line, row in enumerate(csv.DictReader(handle), 2)
                  if row['passed'].lower() == 'false']
    if not failed or any(row['case'] != 'mesh' or row['check'] != 'peak_abs_E_V_per_cm'
                         for _, row in failed):
        raise ValueError('This recheck handles only mesh peak-field failures')
    with (source/'iv.csv').open(newline='', encoding='utf-8') as handle:
        original = {(r['case_name'], int(r['intervals']), float(r['applied_V'])): r
                    for r in csv.DictReader(handle)
                    if r['branch'] == 'forward' and int(r['refinement']) == 2}
    meshes = config['mesh_intervals']
    targets = {}
    for _, row in failed:
        coarse = int(row['intervals'])
        fine = meshes[meshes.index(coarse)+1]
        for count in (coarse, fine):
            targets.setdefault((row['case_name'], count), set()).add(float(row['applied_V']))
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'config.json', snapshot)
    metadata = dict(status='RUNNING', scope='targeted_peak_field_recheck_only',
                    source_run=str(source), utc=datetime.now(timezone.utc).isoformat(),
                    source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
                    estimator='one_sided_linear_junction_extrapolation_v1',
                    physics_and_tolerances_unchanged=True,
                    refinements='Original duplicate mesh checks reuse the same fresh DC state; no full step sweep',
                    protected_source_sha256=before)
    write_json(out/'metadata.json', metadata)
    metrics, fields, checks = [], {}, []
    attempts = []
    def check(case, count, voltage, name, error, limit, source_line=0):
        checks.append(dict(case_name=case, intervals=count, applied_V=voltage,
                           check=name, error=error, limit=limit,
                           source_csv_line=source_line,
                           passed=math.isfinite(error) and error <= limit))
    def solve(case, count, voltages, anchor=False):
        # Only approach states are added, not a full low-voltage/negative sweep.
        start = min(voltages)
        warmup = [round(i*.1, 10) for i in range(math.ceil(start/.1))]
        requested = sorted(set(warmup) | set(voltages) | {0.0})
        settings = case_sweep(sweep, case)
        def log(record):
            attempts.append(dict(case_name=case['name'], intervals=count, **record))
        with closing(simulate_bias_branch(config, settings, count, requested, log)) as states:
            for state in states:
                voltage = state['applied_V']
                metric, state_checks = assess_srh(config, settings, experiment, state)
                for item in state_checks:
                    check(case['name'], count, voltage, item['check'], item['error'], item['limit'])
                if voltage not in voltages:
                    continue
                key = (case['name'], count, voltage)
                field = junction_peak_field(state)
                fields[key] = field
                check(case['name'], count, voltage, 'junction_left_right_consistency',
                      abs(field['junction_left_E_V_per_cm']-field['junction_right_E_V_per_cm']),
                      sweep['comparison_rtol']*field['peak_abs_E_V_per_cm'])
                if not anchor:
                    old = json.loads((source/original[key]['state_file']).read_text(encoding='utf-8'))
                    # Extraction is separate; verify the solved physical profiles did not change.
                    for table, name, atol, rtol in (
                        ('nodes','Potential_V',1e-12,0),
                        ('nodes','Electrons_cm3',0,1e-10), ('nodes','Holes_cm3',0,1e-10),
                        ('edges','ElectricField_V_per_cm',1e-8,1e-10),
                        ('edges','TotalCurrent_A_per_cm2',1e-15,1e-10)):
                        a, b = state[table][name], old[table][name]
                        if len(a) != len(b):
                            raise ValueError('Profile mesh changed')
                        ratio = max(abs(u-v)/(atol+rtol*max(abs(u),abs(v),1e-300))
                                    for u,v in zip(a,b))
                        check(case['name'], count, voltage, 'unchanged_'+name, ratio, 1.0)
                metric.update(field)
                filename = f"{case['name']}_mesh_{count}_V_{voltage:.4f}.json"
                metric.update(case_name=case['name'], state_file=filename, anchor=anchor)
                metrics.append(metric)
                write_json(out/filename, state)
                if len(metrics) % 50 == 0:
                    print(f'Targeted states saved: {len(metrics)}', flush=True)
    status = 'ERROR'
    try:
        for case in experiment['cases']:
            for count in meshes:
                values = targets.get((case['name'], count), set())
                if values:
                    solve(case, count, values)
        for line, row in failed:
            count, voltage = int(row['intervals']), float(row['applied_V'])
            fine = meshes[meshes.index(count)+1]
            a = fields[row['case_name'], count, voltage]['peak_abs_E_V_per_cm']
            b = fields[row['case_name'], fine, voltage]['peak_abs_E_V_per_cm']
            check(row['case_name'], count, voltage, 'rechecked_peak_field_mesh', abs(a-b),
                  sweep['comparison_rtol']*max(a,b), line)
        # Independent finer meshes at the worst-bias endpoints, OFF and shortest lifetime.
        anchor_cases = [experiment['cases'][0], min(
            (c for c in experiment['cases'] if c['enabled']), key=lambda c:c['tau_n_s'])]
        endpoint = max(float(row['applied_V']) for _,row in failed)
        for case in anchor_cases:
            for count in (meshes[-1]*2, meshes[-1]*4):
                solve(case, count, {endpoint}, anchor=True)
            reference = fields[case['name'], meshes[-1]*4, endpoint]['peak_abs_E_V_per_cm']
            for count in (*meshes, meshes[-1]*2):
                value = fields[case['name'], count, endpoint]['peak_abs_E_V_per_cm']
                check(case['name'], count, endpoint, 'fine_mesh_anchor_peak', abs(value-reference),
                      sweep['comparison_rtol']*max(value,reference))
        status = 'TARGETED_PASS' if all(c['passed'] for c in checks) else 'TARGETED_FAIL'
    finally:
        after = {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in source.rglob('*') if p.is_file()}
        if after != before:
            status = 'ERROR_SOURCE_CHANGED'
        if metrics:
            write_csv(out/'iv.csv', metrics)
        if checks:
            write_csv(out/'validation.csv', checks)
        write_json(out/'convergence.json', attempts)
        metadata['status'] = status
        metadata['source_run_unchanged'] = after == before
        write_json(out/'metadata.json', metadata)
        write_json(out/'summary.json', dict(status=status, scope=metadata['scope'],
            full_extension_validated=False, original_failed_checks=len(failed),
            saved_target_and_anchor_states=len(metrics), solve_attempts=len(attempts),
            checks=len(checks), failed=sum(not c['passed'] for c in checks),
            source_run_unchanged=after == before, figures_generated=False))
    return int(status != 'TARGETED_PASS')


def reference_rows(path, config, sweep, stage, peak_field_method='edge'):
    """Require reviewed R=0 reference; do not pretend old source hashes match."""
    path = Path(path)
    metadata = json.loads((path/'metadata.json').read_text(encoding='utf-8'))
    snapshot = json.loads((path/'config.json').read_text(encoding='utf-8'))
    if metadata['status'] != 'PASS' or metadata['stage'] != stage:
        raise ValueError('Matching PASS voltage reference required')
    if snapshot['base_model'] != config or transport_physics(snapshot['sweep']) != transport_physics(sweep):
        raise ValueError('Reference physics/solver parameters differ from SRH transport/base settings')
    with (path/'iv.csv').open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    result = {(int(r['intervals']),int(r['refinement']),r['branch'],float(r['applied_V'])):
            {k:float(r[k]) for k in ('J_A_per_cm2','charge_equivalent_W_cm','peak_abs_E_V_per_cm')}
            for r in rows}
    if peak_field_method == 'junction_linear_v1':
        # Compare like with like, without rewriting archived baseline metrics.
        for row in rows:
            state = json.loads((path/row['state_file']).read_text(encoding='utf-8'))
            key = (int(row['intervals']), int(row['refinement']), row['branch'], float(row['applied_V']))
            result[key]['peak_abs_E_V_per_cm'] = junction_peak_field(state)['peak_abs_E_V_per_cm']
    elif peak_field_method != 'edge':
        raise ValueError('Unknown peak-field extraction method')
    # Require the complete old grid to be covered; never extrapolate its values.
    for count in config['mesh_intervals']:
        for refinement in sweep['step_refinements']:
            for branch in ('reverse', 'forward'):
                expected = bias_grid(snapshot['sweep']['stages'][stage][branch+'_segments'], refinement)
                actual = bias_grid(sweep['stages'][stage][branch+'_segments'], refinement)
                if not set(expected).issubset(actual):
                    raise ValueError('SRH grid must include the saved reference grid')
                if any((count,refinement,branch,v) not in result for v in expected):
                    raise ValueError('Incomplete saved reference grid')
    return result


def plot_results(out, rows, status, count):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3,2,figsize=(12,12))
    # Derive display text from saved physical parameters, never parse case IDs.
    snapshot = json.loads((out/'config.json').read_text(encoding='utf-8'))
    labels_by_case = {}
    for case in snapshot['experiment']['cases']:
        if not case['enabled']:
            label = 'SRH OFF'
        elif case['tau_n_s'] == case['tau_p_s']:
            label = f"tau = {case['tau_n_s']*1e6:g} us"
        else:
            label = f"tau_n = {case['tau_n_s']*1e6:g} us, tau_p = {case['tau_p_s']*1e6:g} us"
        labels_by_case[case['name']] = label
    keys = ('J_A_per_cm2','J_A_per_cm2','q_integral_U_A_per_cm2',
            'max_abs_U_cm3_per_s','current_span_A_per_cm2','electron_integral_residual_A_per_cm2')
    labels = ('Signed J [A/cm²]','Resolved |J| [A/cm²]',
              'q integral U dx [A/cm²]','Maximum |U| [cm^-3 s^-1]',
              'Total current span [A/cm²]','Electron continuity residual [A/cm²]')
    for case in dict.fromkeys(r['case_name'] for r in rows):
        points = {r['applied_V']:r for r in rows
                  if r['case_name']==case and r['intervals']==count and r['refinement']==2}
        ordered = [points[v] for v in sorted(points)]
        for i,(ax,key) in enumerate(zip(axes.flat, keys)):
            selected = ordered
            if not selected:
                continue
            x = [r['applied_V'] for r in selected]
            y = resolved_magnitudes(selected,key) if i==1 else [r[key] for r in selected]
            (ax.semilogy if i==1 else ax.plot)(x,y,label=labels_by_case[case])
    for ax,label in zip(axes.flat, labels):
        ax.set(xlabel='V_P - V_N [V]',ylabel=label)
        ax.grid(True)
        if ax.lines:
            ax.legend(fontsize=8)
        else:
            ax.text(.5,.5,'No saved finest/half-step data',ha='center',transform=ax.transAxes)
    fig.suptitle(f'SRH: {status}; {len(rows)} saved states; {count} intervals, half step only')
    fig.tight_layout()
    fig.savefig(out/'srh.png',dpi=160)
    plt.close(fig)


def plot_profiles(states, path, status):
    """Same six physical profile panels; both reverse and forward biases."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3,2,figsize=(12,12))
    for state in states:
        nodes,edges = state['nodes'],state['edges']
        x = [(v-state['junction_cm'])*1e7 for v in nodes['x_cm']]
        xe = [(v-state['junction_cm'])*1e7 for v in edges['x_cm']]
        label = f"{state['applied_V']:+.2f} V"
        axes[0,0].semilogy(x,nodes['Electrons_cm3'],label=label)
        axes[0,1].semilogy(x,nodes['Holes_cm3'],label=label)
        # Plot sided limits at abrupt doping interface, not its averaged node.
        junction_index=min(range(len(x)),key=lambda i:abs(x[i]))
        q=state['electron_charge_C']
        mobile=nodes['Holes_cm3'][junction_index]-nodes['Electrons_cm3'][junction_index]
        rho=list(nodes['ChargeDensity_C_per_cm3'])
        left_rho=q*(mobile-nodes['Acceptors_cm3'][0])
        right_rho=q*(mobile+nodes['Donors_cm3'][-1])
        axes[1,0].plot(x[:junction_index+1]+x[junction_index:],
                       rho[:junction_index]+[left_rho,right_rho]+rho[junction_index+1:],label=label)
        axes[1,1].plot(x,[v-nodes['Potential_V'][0] for v in nodes['Potential_V']],label=label)
        axes[2,0].plot(xe,[v/1e3 for v in edges['ElectricField_V_per_cm']],label=label)
        # Split sides to avoid dividing by the averaged interface-node doping.
        for side,carrier,dopant in ((-1,'Holes_cm3','Acceptors_cm3'),(1,'Electrons_cm3','Donors_cm3')):
            indices=[i for i,v in enumerate(x) if side*v>0]
            axes[2,1].plot([x[i] for i in indices],
                          [nodes[carrier][i]/nodes[dopant][i] for i in indices],
                          label=label if side==-1 else None,
                          color=axes[0,0].lines[-1].get_color())
    labels=('n [cm^-3]','p [cm^-3]','rho [C/cm³]','Potential relative to left [V]',
            'Signed E [kV/cm]','Majority / doping')
    for ax,label in zip(axes.flat,labels):
        ax.set(xlabel='Distance from junction [nm]',ylabel=label)
        ax.grid(True)
        if ax.lines:
            ax.legend(fontsize=8)
    fig.suptitle(f'SRH tau=1 us profiles: {status}; saved finest half-step states')
    fig.tight_layout()
    fig.savefig(path,dpi=160)
    plt.close(fig)


def run(config, sweep, experiment, stage, out, baseline, profile_path,
        peak_field_method='edge', checkpoint_states=1):
    rows, checks, profiles = [], [], []
    status = 'INCOMPLETE'
    condition = sweep['stages'][stage]
    def flush():
        if rows:
            write_csv(out/'iv.csv',rows)
        if checks:
            write_csv(out/'validation.csv',checks)
    try:
        for case in experiment['cases']:
            settings = case_sweep(sweep,case)
            for count in config['mesh_intervals']:
                for refinement in sweep['step_refinements']:
                    for branch in ('reverse','forward'):
                        grid = bias_grid(condition[branch+'_segments'],refinement)
                        def attempt(record):
                            record.update(case_name=case['name'],intervals=count,refinement=refinement,branch=branch)
                            with (out/'convergence.jsonl').open('a',encoding='utf-8') as h:
                                h.write(json.dumps(record,allow_nan=False)+'\n')
                        with closing(simulate_bias_branch(config,settings,count,grid,attempt)) as states:
                            for index,state in enumerate(states):
                                prefix=f"{case['name']}_mesh_{count}_step_{refinement}_{branch}_{index:03d}"
                                state['srh_parameters'] = case
                                state['electron_charge_C'] = config['electron_charge_C']
                                write_json(out/(prefix+'.json'),state)
                                metric,tests = assess_srh(config,settings,experiment,state,peak_field_method)
                                metric.update(case_name=case['name'],refinement=refinement,branch=branch,state_file=prefix+'.json')
                                rows.append(metric)
                                checks.extend(dict(case_name=case['name'],case=branch,intervals=count,refinement=refinement,
                                                   applied_V=state['applied_V'],**t) for t in tests)
                                if case['name']=='off':
                                    key=(count,refinement,branch,state['applied_V'])
                                    if key in baseline:
                                        checks.extend(dict(case_name='off',**t) for t in compare_rows(metric,baseline[key],sweep,'saved_R0_reference'))
                                if len(rows) % checkpoint_states == 0:
                                    flush()
                                    if checkpoint_states > 1:
                                        print(f'Saved {len(rows)} states: {prefix}', flush=True)
                                if not all(t['passed'] for t in tests) or any(not t['passed'] for t in checks[-3:]):
                                    status='FAIL'
                                    raise RuntimeError(f'Validation failed: {prefix}; preserved outputs; no automatic retry')
                                if count==config['mesh_intervals'][-1] and refinement==2 and state['applied_V'] in condition['vtk_biases_V']:
                                    export_vtm(state,out/prefix)
                                    if case['name']=='tau_1us' and not (branch=='reverse' and state['applied_V']==0):
                                        profiles.append(state)
        indexed={(r['case_name'],r['intervals'],r['refinement'],r['branch'],r['applied_V']):r for r in rows}
        for row in rows:
            name,count,refinement,branch,v=(row[k] for k in ('case_name','intervals','refinement','branch','applied_V'))
            targets=[]
            if refinement==1:
                targets.append(('half_step',indexed[name,count,2,branch,v]))
            position=config['mesh_intervals'].index(count)
            if position<len(config['mesh_intervals'])-1:
                targets.append(('mesh',indexed[name,config['mesh_intervals'][position+1],refinement,branch,v]))
            if branch=='reverse' and v==0:
                targets.append(('zero_restart',indexed[name,count,refinement,'forward',v]))
            for label,other in targets:
                checks.extend(dict(case_name=name,**t) for t in compare_rows(row,other,sweep,label))
                error=abs(row['q_integral_U_A_per_cm2']-other['q_integral_U_A_per_cm2'])
                limit=sweep['current_atol_A_per_cm2']+sweep['comparison_rtol']*max(abs(row['q_integral_U_A_per_cm2']),abs(other['q_integral_U_A_per_cm2']))
                checks.append(dict(case_name=name,case=label,intervals=count,refinement=refinement,applied_V=v,
                                   check='integrated_SRH_comparison',error=error,limit=limit,passed=math.isfinite(error) and error<=limit))
        status='PASS' if all(t['passed'] for t in checks) else 'FAIL'
        return status
    finally:
        flush()
        write_json(out/'summary.json',dict(status=status,stage=stage,saved_states=len(rows),
                   checks=len(checks),failed=sum(not t['passed'] for t in checks),
                   peak_field_method=peak_field_method,
                   saved_reference_voltage_range_V=[min(k[3] for k in baseline),max(k[3] for k in baseline)],
                   off_states_without_saved_reference=sum(r['case_name']=='off' and
                       (r['intervals'],r['refinement'],r['branch'],r['applied_V']) not in baseline for r in rows),
                   limitations=['Educational lifetimes, not calibrated leakage.',
                                'Forward width above +0.10 V remains diagnostic, not a 5% PASS claim.',
                                'No avalanche, BTBT, tunneling or reliability model.']))
        if rows:
            plot_results(out,rows,status,config['mesh_intervals'][-1])
        if profiles:
            plot_profiles(profiles,profile_path,status)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='configs/phase1/pn_junction_srh.json')
    parser.add_argument('--stage',choices=('pilot','extension'),default='pilot')
    parser.add_argument('--baseline-run',help='Read-only matching PASS no-SRH voltage run')
    parser.add_argument('--recheck-failed-run', help='Only re-solve saved mesh peak-field failures; no plots/full sweep')
    parser.add_argument('--pilot-run',help='Reviewed SRH PASS pilot required for extension')
    parser.add_argument('--output',required=True)
    parser.add_argument('--reviewed-runner-change', help='Explicit audit reason for runner-only changes since the PASS pilot')
    parser.add_argument('--peak-field-method', choices=('edge','junction_linear_v1'), default='edge')
    parser.add_argument('--checkpoint-states', type=int, default=1,
                        help='CSV checkpoint frequency only; all state JSONs and solver logs are saved immediately')
    args=parser.parse_args()
    if args.checkpoint_states < 1:
        parser.error('--checkpoint-states must be positive')
    config,sweep,experiment,config_hashes=load_config(args.config)
    if args.recheck_failed_run:
        out = Path(args.output).resolve()
        if (out.name != 'extension_field_recheck' or not out.parent.name.startswith('run_')
                or out.parent.parent.name != 'pn_junction_srh'):
            parser.error('Use pn_junction_srh/run_NNN/extension_field_recheck for targeted results')
        return recheck_failed_fields(args.recheck_failed_run, out, config, sweep, experiment)
    if not args.baseline_run:
        parser.error('--baseline-run required for a full sweep')
    baseline=reference_rows(args.baseline_run,config,sweep,args.stage,args.peak_field_method)
    source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    snapshot=dict(base_model=config,transport=sweep,experiment=experiment,
                  extraction=dict(peak_field_method=args.peak_field_method))
    if args.stage=='extension':
        if not args.pilot_run:
            parser.error('Review PASS SRH pilot before extension')
        pilot=Path(args.pilot_run)
        meta=json.loads((pilot/'metadata.json').read_text(encoding='utf-8'))
        changed_sources=[p for p in SOURCES if meta['source_sha256'].get(p)!=source_hashes[p]]
        runner='validation/analytic/pn_junction/run_srh.py'
        if meta['status']!='PASS' or meta['stage']!='pilot' or any(p!=runner for p in changed_sources):
            parser.error('Matching PASS SRH pilot source required')
        if changed_sources and not args.reviewed_runner_change:
            parser.error('Runner changed: explicit review reason required; physics sources must remain identical')
        if not pilot_compatibility(json.loads((pilot/'config.json').read_text(encoding='utf-8')), config, sweep, experiment):
            parser.error('SRH pilot physics/solver/pilot-grid configuration changed')
    out=Path(args.output).resolve()
    if out.name!=args.stage or not out.parent.name.startswith('run_') or out.parent.parent.name!='pn_junction_srh':
        parser.error('Use data/raw/phase1/pn_junction_srh/run_NNN/pilot or extension')
    profile_path=ROOT/'figures'/f'pn_srh_{out.parent.name}_{args.stage}_profiles.png'
    if out.exists() or profile_path.exists():
        raise FileExistsError('Refusing to overwrite run or profile')
    out.mkdir(parents=True,exist_ok=False)
    profile_path.parent.mkdir(parents=True,exist_ok=True)
    metadata=dict(status='RUNNING',stage=args.stage,utc=datetime.now(timezone.utc).isoformat(),
                  python=platform.python_version(),source_sha256=source_hashes,config_sha256=config_hashes,
                  command=vars(args),baseline_path=str(Path(args.baseline_run).resolve()),
                  peak_field_method=args.peak_field_method,
                  baseline_peak_field_reextracted_read_only=args.peak_field_method != 'edge',
                  baseline_iv_sha256=hashlib.sha256((Path(args.baseline_run)/'iv.csv').read_bytes()).hexdigest())
    if args.stage=='extension':
        metadata['pilot_compatibility_review']=dict(reason=args.reviewed_runner_change,
            changed_sources=changed_sources, old_source_sha256=meta['source_sha256'],
            pilot_metadata_sha256=hashlib.sha256((pilot/'metadata.json').read_bytes()).hexdigest(),
            physics_solver_and_pilot_grid_match=True,
            allowed_configuration_changes='Extension grid, display labels and SRH config packaging only')
    write_json(out/'config.json',snapshot)
    write_json(out/'metadata.json',metadata)
    try:
        import devsim.python_packages.simple_physics as physics
        import devsim.python_packages.simple_dd as dd
        metadata['versions']={p:importlib.metadata.version(p) for p in ('devsim','matplotlib')}
        metadata['helper_sha256']={p.__name__:hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest() for p in (physics,dd)}
        for key,command in (('commit',['rev-parse','HEAD']),('dirty_status',['status','--porcelain'])):
            try:
                metadata[key]=subprocess.check_output(['git',*command],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
            except (OSError,subprocess.CalledProcessError):
                metadata[key]='unavailable'
        metadata['status']=run(config,sweep,experiment,args.stage,out,baseline,profile_path,
                               args.peak_field_method,args.checkpoint_states)
        return int(metadata['status']!='PASS')
    except Exception:
        summary=out/'summary.json'
        metadata['status']=json.loads(summary.read_text())['status'] if summary.exists() else 'ERROR'
        (out/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise
    finally:
        write_json(out/'metadata.json',metadata)


if __name__=='__main__':
    raise SystemExit(main())
