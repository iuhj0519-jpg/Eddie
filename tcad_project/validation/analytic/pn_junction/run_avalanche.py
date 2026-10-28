"""Prepare/check inputs by default; --execute explicitly runs DEVSIM.

Order: domain-pilot -> pilot -> domain-extension -> extension.
Never overwrite output or automatically retry a failed experiment as run_002.
"""
import argparse
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import traceback

from src.device.pn_junction import (validate_bias, bias_grid, bias_reference, reference,
                                    simulate_bias_branch, assess_bias)
from src.physics.avalanche import validate_avalanche, interior_generation_integrals
from validation.analytic.pn_junction.run_srh import junction_peak_field
from validation.analytic.pn_junction.run_voltage import compare_rows
from validation.analytic.pn_junction.run_pn_junction import write_json, write_csv
from validation.analytic.pn_junction.export_vtm import export_vtm

ROOT = Path(__file__).resolve().parents[3]


def load_config(path):
    path = Path(path).resolve()
    experiment = json.loads(path.read_text(encoding='utf-8'))
    base_path = (path.parent/experiment['base_config']).resolve()
    base = json.loads(base_path.read_text(encoding='utf-8'))
    config = deepcopy(base)
    allowed = {'p_length_nm', 'n_length_nm', 'mesh_intervals'}
    if set(experiment['geometry_overrides']) - allowed:
        raise ValueError('Only geometry/mesh overrides supported')
    config.update(experiment['geometry_overrides'])
    sweep = deepcopy(experiment['transport'])
    sweep['avalanche'] = deepcopy(experiment['avalanche'])
    validate_avalanche(sweep['avalanche'], config['temperature_K'])
    if sweep['extended_precision'] is not True or not sweep['srh']['enabled']:
        raise ValueError('Extended precision and fixed SRH baseline required')
    domain = experiment['domain_check']
    if type(domain['scale']) is not int or domain['scale'] < 2:
        raise ValueError('Integer domain enlargement >=2 required')
    if not 0 < domain['maximum_depletion_fraction'] < 1:
        raise ValueError('Depletion/contact guard must be between 0 and 1')
    limits = experiment['limits']
    for key, value in limits.items():
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'Positive finite experiment limit required: {key}')
    if limits['breakdown_criterion_A_per_cm2'] >= limits['maximum_abs_current_A_per_cm2']:
        raise ValueError('Current stop must exceed the reporting criterion')
    for stage in ('pilot', 'extension'):
        validate_bias(config, sweep, stage)
        grid = bias_grid(sweep['stages'][stage]['reverse_segments'])
        if not set(domain[stage+'_biases_V']).issubset(grid) or domain[stage+'_biases_V'][0] != 0:
            raise ValueError('Domain probes must start at zero and belong to the grid')
        if domain[stage+'_biases_V'] != sorted(set(domain[stage+'_biases_V']), reverse=True):
            raise ValueError('Domain probes must be unique and descending')
        if domain[stage+'_biases_V'][-1] != grid[-1]:
            raise ValueError('Domain probes must include the maximum reverse bias')
        guard_domain(config, experiment, grid[-1])
    if not set(bias_grid(sweep['stages']['pilot']['reverse_segments'])).issubset(
            bias_grid(sweep['stages']['extension']['reverse_segments'])):
        raise ValueError('Extension must cover pilot points')
    return base, config, sweep, experiment


def guard_domain(config, experiment, voltage):
    ref = reference(config)
    width = bias_reference(config, voltage)['W_cm']
    fractions = {side: width*ref['x'+side+'_cm']/ref['W_cm']/(config[side+'_length_nm']*1e-7)
                 for side in ('p', 'n')}
    if max(fractions.values()) >= experiment['domain_check']['maximum_depletion_fraction']:
        raise ValueError('Estimated depletion consumes too much of a contact-side domain')
    return fractions


def preflight(config, sweep, experiment):
    """Analytical screening only; not a mesh/domain convergence PASS."""
    result = dict(status='PREPARED_NOT_SIMULATED', Vbi_V=reference(config)['Vbi_V'],
                  spacing_nm=[(config['p_length_nm']+config['n_length_nm'])/n for n in config['mesh_intervals']],
                  model=experiment['avalanche']['model'], stages={})
    for stage in ('pilot', 'extension'):
        condition = sweep['stages'][stage]
        grids = [bias_grid(condition['reverse_segments'], r) for r in sweep['step_refinements']]
        result['stages'][stage] = dict(points_per_mesh_case=list(map(len, grids)),
            planned_states=2*len(config['mesh_intervals'])*sum(map(len, grids)),
            depletion_fraction=guard_domain(config, experiment, grids[0][-1]),
            depletion_peak_E_V_per_cm=abs(bias_reference(config, grids[0][-1])['E_peak_V_per_cm']))
    return result


def assess(config, sweep, state):
    metric, checks = assess_bias(config, sweep, state)
    metric.update(junction_peak_field(state))
    nodes, edges = state['nodes'], state['edges']
    q = config['electron_charge_C']
    ii = interior_generation_integrals(state)
    srh = [r*v for r, v in zip(nodes['SRHNetRate_cm3_per_s'][1:-1], nodes['ControlVolume_cm'][1:-1])]
    net = [q*(u-g) for u, g in zip(srh, ii)]
    jn, jp = edges['ElectronCurrent_A_per_cm2'], edges['HoleCurrent_A_per_cm2']
    scale = max(map(abs, jn+jp))+math.fsum(map(abs, net))
    limit = sweep['current_atol_A_per_cm2']+sweep['current_conservation_rtol']*scale
    values = dict(
        electron_integral_residual_A_per_cm2=abs(jn[-1]-jn[0]-math.fsum(net)),
        hole_integral_residual_A_per_cm2=abs(jp[-1]-jp[0]+math.fsum(net)),
        electron_local_residual_A_per_cm2=max(abs(b-a-u) for a,b,u in zip(jn,jn[1:],net)),
        hole_local_residual_A_per_cm2=max(abs(b-a+u) for a,b,u in zip(jp,jp[1:],net)))
    metric.update(values, q_integral_G_II_A_per_cm2=q*math.fsum(ii),
                  q_integral_U_SRH_A_per_cm2=q*math.fsum(srh),
                  max_G_II_cm3_per_s=max(edges['ImpactGeneration_cm3_per_s']))
    for key, error in values.items():
        checks.append(dict(check=key, error=error, limit=limit, passed=math.isfinite(error) and error<=limit))
    mismatch = abs(metric['junction_left_E_V_per_cm']-metric['junction_right_E_V_per_cm'])
    bound = sweep['comparison_rtol']*metric['peak_abs_E_V_per_cm']
    checks.append(dict(check='junction_left_right_consistency', error=mismatch, limit=bound, passed=mismatch<=bound))
    generation_ok = all(math.isfinite(g) and g>=0 for g in edges['ImpactGeneration_cm3_per_s'])
    if not sweep['avalanche']['enabled']:
        generation_ok = generation_ok and all(g==0 for g in edges['ImpactGeneration_cm3_per_s'])
    checks.append(dict(check='nonnegative_generation_and_exact_OFF', error=0 if generation_ok else 1,
                       limit=0, passed=generation_ok))
    return metric, checks


def provenance(path):
    paths = [Path(path), Path(path).parent/json.loads(Path(path).read_text(encoding='utf-8'))['base_config']]
    paths += [ROOT/p for p in ('src/device/pn_junction.py', 'src/physics/srh.py', 'src/physics/avalanche.py',
              'validation/analytic/pn_junction/run_avalanche.py', 'validation/analytic/pn_junction/run_srh.py',
              'validation/analytic/pn_junction/run_voltage.py', 'validation/analytic/pn_junction/run_pn_junction.py',
              'validation/analytic/pn_junction/export_vtm.py')]
    return {str(p.resolve().relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def require_pass(path, stage, hashes):
    if path is None:
        raise ValueError(f'Reviewed {stage} output required')
    path = Path(path)
    result = json.loads((path/'summary.json').read_text(encoding='utf-8'))
    meta = json.loads((path/'metadata.json').read_text(encoding='utf-8'))
    if result['status'] != 'PASS' or result['stage'] != stage or meta['sha256'] != hashes:
        raise ValueError(f'Need PASS {stage} from identical configuration and implementation')


def plot(out, rows, status):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    specs = [('J_A_per_cm2','Signed J [A/cm2]'), ('J_A_per_cm2','Resolved |J| [A/cm2]'),
             ('q_integral_G_II_A_per_cm2','q integral G_II dx [A/cm2]'),
             ('peak_abs_E_V_per_cm','Junction peak |E| [V/cm]'),
             ('current_span_A_per_cm2','Total current span [A/cm2]'),
             ('electron_integral_residual_A_per_cm2','Electron continuity residual [A/cm2]')]
    # Actual saved groups are explicit: partial runs never masquerade as finest results.
    for group in sorted({(r['case_name'],r['intervals'],r['refinement']) for r in rows}):
        selected = sorted([r for r in rows if (r['case_name'],r['intervals'],r['refinement'])==group], key=lambda r: -r['applied_V'])
        for i, (ax, (key, label)) in enumerate(zip(axes.flat, specs)):
            y = [abs(r[key]) if r['current_resolved'] and r['applied_V']!=0 else math.nan for r in selected] if i==1 else [r[key] for r in selected]
            (ax.semilogy if i==1 else ax.plot)([-r['applied_V'] for r in selected],y,label=f'{group[0]}, N={group[1]}, step/{group[2]}')
            ax.set(xlabel='Reverse voltage magnitude [V]', ylabel=label)
            ax.grid(True)
    for ax in axes.flat:
        if ax.lines:
            ax.legend(fontsize=6)
    fig.suptitle(f'Avalanche {status}: {len(rows)} saved states; no BTBT / heating')
    fig.tight_layout()
    fig.savefig(out/'avalanche.png', dpi=160)
    plt.close(fig)


def run(config, sweep, experiment, stage, out):
    rows, checks = [], []
    status, reason = 'INCOMPLETE', None
    domain_run = stage.startswith('domain-')
    scope = stage.removeprefix('domain-')
    condition = sweep['stages'][scope]
    scale = experiment['domain_check']['scale']
    jobs = []
    for enabled in (False, True):
        settings = deepcopy(sweep)
        settings['avalanche']['enabled'] = enabled
        if domain_run:
            for factor in (1, scale):
                model = deepcopy(config)
                for side in ('p', 'n'):
                    model[side+'_length_nm'] *= factor
                model['mesh_intervals'] = [n*factor for n in config['mesh_intervals']]
                jobs.append((model, settings, model['mesh_intervals'][-1], 1,
                             experiment['domain_check'][scope+'_biases_V'], factor))
        else:
            for count in config['mesh_intervals']:
                for refinement in sweep['step_refinements']:
                    jobs.append((config, settings, count, refinement,
                                 bias_grid(condition['reverse_segments'], refinement), 1))
    def add_checks(metric, tests, category):
        for test in tests:
            # Uniform schema across state, mesh, step, and domain checks.
            checks.append(dict(case_name=metric['case_name'], category=category,
                intervals=metric['intervals'], refinement=metric['refinement'], applied_V=metric['applied_V'],
                check=test['check'], error=test['error'], limit=test['limit'], passed=test['passed']))
    try:
        for model, settings, count, refinement, grid, factor in jobs:
            case = 'avalanche_on' if settings['avalanche']['enabled'] else 'avalanche_off'
            def attempt(record):
                record.update(case_name=case, intervals=count, refinement=refinement, domain_scale=factor)
                with (out/'convergence.jsonl').open('a',encoding='utf-8') as handle:
                    handle.write(json.dumps(record,allow_nan=False)+'\n')
            with closing(simulate_bias_branch(model, settings, count, grid, attempt)) as states:
                for index, state in enumerate(states):
                    prefix=f'{case}_domain_{factor}_mesh_{count}_step_{refinement}_{index:04d}'
                    state['avalanche_parameters'] = settings['avalanche']
                    state['srh_parameters'] = settings['srh']
                    write_json(out/(prefix+'.json'), state)
                    metric, tests = assess(model, settings, state)
                    metric.update(case_name=case, refinement=refinement, domain_scale=factor, state_file=prefix+'.json')
                    rows.append(metric)
                    add_checks(metric, tests, 'state')
                    write_csv(out/'iv.csv', rows)
                    write_csv(out/'validation.csv', checks)
                    if not all(t['passed'] for t in tests):
                        raise RuntimeError(f'Validation failed at {prefix}; no automatic retry')
                    if state['applied_V'] in condition['vtk_biases_V']:
                        export_vtm(state,out/prefix)
                    if abs(metric['J_A_per_cm2']) >= experiment['limits']['maximum_abs_current_A_per_cm2']:
                        status='STOPPED_CURRENT_LIMIT'
                        raise RuntimeError(f'Current limit reached at {prefix}; not a breakdown PASS')
                    if metric['peak_abs_E_V_per_cm'] >= experiment['limits']['maximum_peak_field_V_per_cm']:
                        status='STOPPED_FIELD_LIMIT'
                        raise RuntimeError(f'Field limit reached at {prefix}; review model scope')
        lookup = {(r['case_name'],r['intervals'],r['refinement'],r['applied_V']):r for r in rows}
        for row in rows:
            case,n,step,v = (row[k] for k in ('case_name','intervals','refinement','applied_V'))
            if domain_run:
                if row['domain_scale']==1:
                    add_checks(row,compare_rows(row,lookup[(case,n*scale,step,v)],sweep,'domain'),'domain')
            else:
                meshes=config['mesh_intervals']
                if n != meshes[-1]:
                    add_checks(row,compare_rows(row,lookup[(case,meshes[meshes.index(n)+1],step,v)],sweep,'mesh'),'mesh')
                if step==1:
                    add_checks(row,compare_rows(row,lookup[(case,n,2,v)],sweep,'step'),'step')
        status='PASS' if all(t['passed'] for t in checks) else 'FAIL'
    except Exception as exc:
        if status=='INCOMPLETE':
            status='FAIL'
        reason=str(exc)
        (out/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        if rows:
            write_csv(out/'iv.csv',rows)
        if checks:
            write_csv(out/'validation.csv',checks)
        # Report per-grid criterion brackets; never infer a crossing from nonconvergence.
        brackets=[]
        criterion=experiment['limits']['breakdown_criterion_A_per_cm2']
        for group in sorted({(r['case_name'],r['intervals'],r['refinement']) for r in rows}):
            selected=sorted([r for r in rows if (r['case_name'],r['intervals'],r['refinement'])==group],key=lambda r:-r['applied_V'])
            for previous,current in zip(selected,selected[1:]):
                if abs(previous['J_A_per_cm2'])<criterion<=abs(current['J_A_per_cm2']):
                    brackets.append(dict(case_name=group[0],intervals=group[1],refinement=group[2],
                        reverse_voltage_bracket_V=[-previous['applied_V'],-current['applied_V']]))
                    break
        summary=dict(status=status,stage=stage,saved_states=len(rows),checks=len(checks),
            failed=sum(not t['passed'] for t in checks),reason=reason,
            current_criterion_A_per_cm2=criterion,criterion_brackets=brackets,
            limitations=['Local-field/constant-mobility 300 K experiment; not calibrated breakdown.',
                        'No BTBT/heating; criterion brackets require mesh/step/domain review.',
                        'Absence of crossing is not proof of absence of breakdown outside this range.'])
        if rows and not domain_run:
            try:
                plot(out,rows,status)
            except Exception:
                summary['status']='FAIL_OUTPUT'
                summary['reason']='Plot generation failed; numeric results preserved'
                (out/'plot_error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        write_json(out/'summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/phase1/pn_junction_avalanche.json')
    parser.add_argument('--stage',choices=('domain-pilot','pilot','domain-extension','extension'),default='domain-pilot')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--reviewed-domain-run',type=Path)
    parser.add_argument('--reviewed-pilot-run',type=Path)
    args=parser.parse_args()
    base,config,sweep,experiment=load_config(args.config)
    report=preflight(config,sweep,experiment)
    if not args.execute:
        print(json.dumps(report,indent=2,allow_nan=False))
        return
    hashes=provenance(args.config)
    if args.stage in ('pilot','extension'):
        require_pass(args.reviewed_domain_run,'domain-'+args.stage,hashes)
    if args.stage in ('domain-extension','extension'):
        require_pass(args.reviewed_pilot_run,'pilot',hashes)
    if args.output is None:
        parser.error('--execute requires a new --output directory')
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'config.json',dict(base_model=base,effective_model=config,experiment=experiment))
    import platform
    from importlib.metadata import version
    write_json(out/'metadata.json',dict(utc=datetime.now(timezone.utc).isoformat(),sha256=hashes,
        command={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        python=platform.python_version(),devsim=version('devsim')))
    result=run(config,sweep,experiment,args.stage,out)
    print(json.dumps(result,indent=2))
    if result['status']!='PASS':
        raise SystemExit(1)


if __name__=='__main__':
    main()
