"""Static dielectric capacitor voltage sweep. Run as a module from the project root."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import traceback

import numpy as np
from src.device.capacitor import analytic_profile, layer_mesh, reference, simulate
from src.extraction.capacitance import extract_qv


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def validate_qv(c):
    reference(c['model'])
    if len(c['model']['mesh_intervals']) != 1:
        raise ValueError('Q-V experiment fixes one mesh; use one mesh_intervals entry')
    layer_mesh(c['model'], c['model']['mesh_intervals'][0])
    for key in ('delta_v_min_V', 'delta_v_max_V', 'field_atol_V_per_cm',
                'charge_atol_C_per_cm2', 'charge_rtol', 'step_capacitance_rtol'):
        val = c[key]
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
            raise ValueError(f'{key}: finite number required')
        if key not in ('delta_v_min_V', 'delta_v_max_V') and val <= 0:
            raise ValueError(f'{key}: positive tolerance required')
    if c['delta_v_min_V'] >= 0 or c['delta_v_max_V'] != -c['delta_v_min_V']:
        raise ValueError('Use symmetric negative/positive endpoints around zero')
    counts = c['point_counts']
    if (not isinstance(counts, list) or len(counts) != 2 or
        any(type(n) is not int or n < 3 or n % 2 == 0 for n in counts) or
        counts[1] != 2*counts[0]-1):
        raise ValueError('Two odd point counts with second=2*first-1 required')


def make_plot(out, runs, expected):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    thickness_cm = json.loads((out/'config.json').read_text(encoding='utf-8'))['model']['thickness_nm']*1e-7
    for n, rows, extracted in runs:
        v = np.array([r['delta_V'] for r in rows])
        qr = np.array([r['Qright_C_per_cm2'] for r in rows])
        ql = np.array([r['Qleft_C_per_cm2'] for r in rows])
        label = f"step={v[1]-v[0]:g} V"
        potential_deltas, mean_fields = [], []
        for row in rows:
            state = json.loads((out/f'points_{n}'/f'state_{int(row["index"]):03d}.json').read_text(encoding='utf-8'))
            nodes, edges = state['nodes'], state['edges']
            order = np.argsort(nodes['x_cm'])
            potential_deltas.append(nodes['potential_V'][int(order[-1])]-nodes['potential_V'][int(order[0])])
            dx = np.array(edges['x1_cm'])-np.array(edges['x0_cm'])
            field = np.array(edges['E_edge_V_per_cm'])*np.sign(dx)
            mean_fields.append(float(np.average(field, weights=np.abs(dx))))
        axes[0, 0].plot(v, potential_deltas, '.-', label=label)
        axes[1, 0].plot(v, qr*1e6, '.-', label='right, '+label)
        axes[1, 0].plot(v, ql*1e6, '.--', label='left, '+label)
        axes[0, 1].plot(v, np.array(extracted['local_F_per_cm2'])*1e7, '.-', label=label)
        axes[1, 1].plot(v, np.array(mean_fields)/1e6, '.-', label=label)
        axes[2, 0].plot(v, (qr-expected*v)*1e21, '.-', label=label)
        axes[2, 1].plot(v, (ql+qr)*1e21, '.-', label=label)
    v = np.array([r['delta_V'] for r in runs[-1][1]])
    axes[0, 0].plot(v, v, 'k:', label='Applied voltage')
    axes[1, 0].plot(v, expected*v*1e6, 'k:', label='analytic right')
    axes[1, 1].plot(v, -v/thickness_cm/1e6, 'k:', label='analytic')
    axes[0, 1].axhline(expected*1e7, color='k', linestyle='--', label='analytic')
    axes[0, 1].set_ylim(expected*1e7*0.98, expected*1e7*1.02)
    axes[0, 0].set_ylabel('Solved potential difference [V]')
    axes[0, 1].set_ylabel('d(Qright/A)/dV [fF/um^2]')
    axes[1, 0].set_ylabel('Surface charge density Q/A [uC/cm^2]')
    axes[1, 1].set_ylabel('Mean signed E_x [MV/cm]')
    axes[2, 0].set_ylabel('Qright/A - analytic [10^-21 C/cm^2]')
    axes[2, 1].set_ylabel('(Qleft + Qright)/A [10^-21 C/cm^2]')
    for ax in axes.flat:
        ax.set_xlabel('Vright - Vleft [V]')
        ax.ticklabel_format(axis='y', style='plain', useOffset=False)
        ax.grid(True)
        ax.legend(fontsize=8)
    model = json.loads((out/'config.json').read_text(encoding='utf-8'))['model']
    title = 'Multi-Layer SiO2/HfO2' if 'layer_relative_permittivities' in model else 'SiO2'
    fig.suptitle(title + ' voltage sweep: Q-V and capacitance validation')
    fig.tight_layout()
    fig.savefig(out/'qv.png', dpi=160)
    plt.close(fig)


def run(c, out):
    expected = reference(c['model'])['C_per_area_F_per_cm2']
    count = c['model']['mesh_intervals'][0]
    runs, checks = [], []

    def check(name, error, limit, points):
        checks.append(dict(points=points, check=name, error=float(error), limit=float(limit),
                           passed=bool(math.isfinite(error) and error < limit)))

    fields = ['points', 'index', 'delta_V', 'left_V', 'right_V', 'Qleft_C_per_cm2',
              'Qright_C_per_cm2', 'Qright_expected_C_per_cm2', 'charge_balance_C_per_cm2',
              'potential_max_error_V', 'field_max_error_V_per_cm', 'converged', 'iterations']
    with (out/'qv.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for n in c['point_counts']:
            rows = []
            folder = out/f'points_{n}'
            folder.mkdir()
            voltages = np.linspace(c['delta_v_min_V'], c['delta_v_max_V'], n)
            voltages[n//2] = 0.0
            for i, voltage in enumerate(voltages):
                model = dict(c['model'], right_V=c['model']['left_V']+float(voltage))
                state = simulate(model, count)
                write_json(folder/f'state_{i:03d}.json', dict(delta_V=float(voltage), **state))
                ref, nodes, edges = state['reference'], state['nodes'], state['edges']
                pe = max(abs(p-model['left_V']-voltage*x/ref['thickness_cm']) for x,p in zip(nodes['x_cm'], nodes['potential_V']))
                ee = max(abs(e*(1 if b>a else -1)-ref['E_V_per_cm']) for a,b,e in
                         zip(edges['x0_cm'], edges['x1_cm'], edges['E_edge_V_per_cm']))
                if 'layer_relative_permittivities' in model:
                    pe = max(abs(p-analytic_profile(model,x)[0])
                             for x,p in zip(nodes['x_cm'],nodes['potential_V']))
                    ee = max(abs(e*(1 if b>a else -1)-analytic_profile(model,(a+b)/2)[1])
                             for a,b,e in zip(edges['x0_cm'],edges['x1_cm'],edges['E_edge_V_per_cm']))
                    # Test every edge against its own layer field; valid also at zero bias.
                    for j,(a,b,e) in enumerate(zip(edges['x0_cm'],edges['x1_cm'],edges['E_edge_V_per_cm'])):
                        target = analytic_profile(model,(a+b)/2)[1]
                        check(f'layer_field_{i}_{j}', abs(e*(1 if b>a else -1)-target),
                              c['field_atol_V_per_cm']+model['field_rtol']*abs(target), n)
                    for j,(lr,rr) in enumerate(zip(state.get('regions',[]),state.get('regions',[])[1:])):
                        def endpoint(region, right):
                            nd, ed = region['nodes'], region['edges']
                            select = max if right else min
                            ni = select(range(len(nd['x_cm'])), key=nd['x_cm'].__getitem__)
                            ei = select(range(len(ed['x0_cm'])), key=lambda k: (ed['x0_cm'][k]+ed['x1_cm'][k])/2)
                            return nd['potential_V'][ni], ed['D_edge_C_per_cm2'][ei]*(1 if ed['x1_cm'][ei]>ed['x0_cm'][ei] else -1)
                        lp,ld = endpoint(lr, True)
                        rp,rd = endpoint(rr, False)
                        check(f'interface_potential_{i}_{j}', abs(lp-rp), model['potential_atol_V'], n)
                        check(f'interface_displacement_{i}_{j}', abs(ld-rd), model['charge_balance_atol_C_per_cm2'], n)
                ql, qr = state['charges']['left'], state['charges']['right']
                row = dict(points=n, index=i, delta_V=float(voltage), left_V=model['left_V'], right_V=model['right_V'],
                           Qleft_C_per_cm2=ql, Qright_C_per_cm2=qr, Qright_expected_C_per_cm2=expected*float(voltage),
                           charge_balance_C_per_cm2=ql+qr, potential_max_error_V=pe,
                           field_max_error_V_per_cm=ee, converged=state['solver_info']['converged'],
                           iterations=len(state['solver_info']['iterations']))
                if not all(math.isfinite(v) for v in row.values()):
                    raise ValueError(f'Non-finite data at points={n}, index={i}')
                writer.writerow(row)
                f.flush()
                rows.append(row)
                check(f'potential_{i}', pe, model['potential_atol_V'], n)
                check(f'field_{i}', ee, c['field_atol_V_per_cm']+model['field_rtol']*abs(ref['E_V_per_cm']), n)
                check(f'charge_balance_{i}', abs(ql+qr), model['charge_balance_atol_C_per_cm2'], n)
                for terminal, value, analytic in [('left', ql, -expected*voltage), ('right', qr, expected*voltage)]:
                    check(f'{terminal}_charge_{i}', abs(value-analytic), c['charge_atol_C_per_cm2']+c['charge_rtol']*abs(analytic), n)
            ext = extract_qv([r['delta_V'] for r in rows], [r['Qright_C_per_cm2'] for r in rows])
            check('fit_capacitance', abs(ext['slope_F_per_cm2']/expected-1), c['model']['capacitance_rtol'], n)
            check('local_capacitance', max(abs(v/expected-1) for v in ext['local_F_per_cm2']), c['model']['capacitance_rtol'], n)
            check('intercept', abs(ext['intercept_C_per_cm2']), c['charge_atol_C_per_cm2'], n)
            write_json(folder/'extraction.json', ext)
            runs.append((n, rows, ext))
    check('step_slope_change', abs(runs[1][2]['slope_F_per_cm2']-runs[0][2]['slope_F_per_cm2'])/expected,
          c['step_capacitance_rtol'], 'coarse_vs_fine')
    coarse_c = np.array(runs[0][2]['local_F_per_cm2'])
    fine_c = np.array(runs[1][2]['local_F_per_cm2'])[::2]
    check('step_local_capacitance_change', float(np.max(np.abs(coarse_c-fine_c)))/expected,
          c['step_capacitance_rtol'], 'coarse_vs_fine')
    with (out/'validation.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['points', 'check', 'error', 'limit', 'passed'], lineterminator='\n')
        w.writeheader()
        w.writerows(checks)
    summary = {'expected_C_per_area_F_per_cm2': expected,
               'sweeps': [{'points': n, 'step_V': (c['delta_v_max_V']-c['delta_v_min_V'])/(n-1),
                           'fit_C_per_area_F_per_cm2': ext['slope_F_per_cm2']} for n, rows, ext in runs],
               'checks': len(checks), 'failed': sum(not r['passed'] for r in checks)}
    write_json(out/'summary.json', summary)
    make_plot(out, runs, expected)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/phase1/capacitor_voltage.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    c = json.loads(Path(args.config).read_text(encoding='utf-8'))
    validate_qv(c)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'config.json', c)
    metadata = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'RUNNING',
                'python': platform.python_version(), 'command': sys.argv,
                'versions': {p: importlib.metadata.version(p) for p in ('devsim', 'numpy', 'matplotlib')},
                'config_sha256': hashlib.sha256(Path(args.config).read_bytes()).hexdigest()}
    for key, command in [('commit', ['git','rev-parse','HEAD']), ('dirty_status', ['git','status','--porcelain'])]:
        try:
            metadata[key] = subprocess.check_output(command, text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            metadata[key] = 'unavailable'
    metadata['source_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               (Path(__file__), Path('src/device/capacitor.py'), Path('src/extraction/capacitance.py'))}
    write_json(out/'metadata.json', metadata)
    try:
        summary = run(c, out)
        metadata['status'] = 'PASS' if not summary['failed'] else 'FAIL'
        print(f"{metadata['status']}: {summary['checks']} checks, output={out}")
        return 0 if metadata['status']=='PASS' else 1
    except Exception:
        metadata['status'] = 'ERROR'
        (out/'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise
    finally:
        write_json(out/'metadata.json', metadata)


if __name__ == '__main__':
    raise SystemExit(main())
