"""Fixed-bias thickness sweep using the shared SiO2 device implementation."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import traceback

from src.device.capacitor import assess, layer_mesh, reference, simulate
from validation.analytic.capacitor.run_capacitor import git, write_json


def thickness_model(base, thickness):
    model = dict(base, thickness_nm=thickness)
    if 'layer_thicknesses_nm' in base:
        model['layer_thicknesses_nm'] = [t*thickness/base['thickness_nm']
                                       for t in base['layer_thicknesses_nm']]
    return model


def validate_thickness(c):
    reference(c['model'])
    if c['model']['left_V'] == c['model']['right_V']:
        raise ValueError('Nonzero fixed bias required for Q/dV')
    ts = c['thicknesses_nm']
    if not isinstance(ts, list) or len(ts) < 10:
        raise ValueError('Use at least 10 thickness samples')
    if any(isinstance(t, bool) or not isinstance(t, (int, float)) or
           not math.isfinite(t) or t <= 0 for t in ts):
        raise ValueError('Thicknesses must be positive finite numbers')
    if ts != sorted(set(ts)):
        raise ValueError('Thicknesses must be unique and increasing')
    if len(c['model']['mesh_intervals']) < 3:
        raise ValueError('Use at least three increasing meshes')
    tol = c['mesh_capacitance_rtol']
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or tol <= 0:
        raise ValueError('Positive finite mesh tolerance required')
    for thickness in ts:
        for count in c['model']['mesh_intervals']:
            layer_mesh(thickness_model(c['model'], thickness), count)


def plot(out, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    model = json.loads((out/'config.json').read_text(encoding='utf-8'))['model']
    multilayer = 'layer_thicknesses_nm' in model
    for count in sorted({r['intervals'] for r in rows}):
        rr = [r for r in rows if r['intervals'] == count]
        t = [r['thickness_nm'] for r in rr]
        label = f'{count} intervals'
        axs[0, 0].plot(t, [r['C_per_area_F_per_cm2']*1e7 for r in rr], '.-', label=label)
        axs[0, 1].plot(t, [r['Qright_C_per_cm2']*1e6 for r in rr], '.-', label=label)
        axs[1, 0].plot(t, [r['E_mean_V_per_cm']/1e6 for r in rr], '.-', label=label)
        axs[1, 1].plot(t, [r['C_relative_error'] for r in rr], '.-', label=label)
    fine = [r for r in rows if r['intervals'] == max(r['intervals'] for r in rows)]
    # Dense analytic reference, not additional simulation samples.
    t = np.linspace(fine[0]['thickness_nm'], fine[-1]['thickness_nm'], 300)
    first = fine[0]
    axs[0, 0].plot(t, first['C_expected_F_per_cm2']*first['thickness_nm']/t*1e7, 'k--', label='Analytic')
    axs[0, 1].plot(t, first['Qright_expected_C_per_cm2']*first['thickness_nm']/t*1e6, 'k--', label='Analytic')
    axs[1, 0].plot(t, first['E_expected_V_per_cm']*first['thickness_nm']/t/1e6, 'k--', label='Analytic')
    axs[1, 1].axhline(0, color='k', linestyle='--')
    for ax, label in zip(axs.flat, ['C/A [fF/um^2]', 'Qright/A [uC/cm^2]', 'Signed E_x [MV/cm]', '|C/C_analytic - 1|']):
        ax.set(xlabel='Total stack thickness [nm]' if multilayer else 'SiO2 thickness [nm]', ylabel=label)
        ax.ticklabel_format(axis='y', style='sci', scilimits=(-3, 3), useOffset=False)
        ax.grid(True)
        ax.legend()
    if multilayer:
        axs[1, 0].set_ylabel('Mean signed E_x [MV/cm]')
    fig.suptitle(('Multi-Layer capacitor' if multilayer else 'SiO2') +
                 ' thickness sweep: fixed voltage and permittivity')
    fig.tight_layout()
    fig.savefig(out/'thickness.png', dpi=160)
    plt.close(fig)


def run(c, out):
    validate_thickness(c)
    rows, checks = [], []
    with (out/'thickness.csv').open('w', newline='', encoding='utf-8') as f:
        writer = None
        for i, thickness in enumerate(c['thicknesses_nm']):
            model = thickness_model(c['model'], thickness)
            ref = reference(model)
            delta = model['right_V']-model['left_V']
            values = []
            for count in model['mesh_intervals']:
                result = simulate(model, count)
                write_json(out/f'state_{i:03d}_mesh_{count}.json', dict(thickness_nm=thickness, **result))
                cap, tests = assess(model, result)
                values.append(cap)
                edges = result['edges']
                lengths = [abs(b-a) for a,b in zip(edges['x0_cm'], edges['x1_cm'])]
                signed = [e*(1 if b>a else -1) for a,b,e in zip(edges['x0_cm'], edges['x1_cm'], edges['E_edge_V_per_cm'])]
                row = dict(thickness_nm=thickness, intervals=count, nodes=len(result['nodes']['x_cm']),
                           delta_V=delta, C_per_area_F_per_cm2=cap, C_expected_F_per_cm2=ref['C_per_area_F_per_cm2'],
                           C_relative_error=abs(cap/ref['C_per_area_F_per_cm2']-1),
                           Qleft_C_per_cm2=result['charges']['left'], Qright_C_per_cm2=result['charges']['right'],
                           Qright_expected_C_per_cm2=ref['C_per_area_F_per_cm2']*delta,
                           E_mean_V_per_cm=sum(e*h for e,h in zip(signed,lengths))/sum(lengths),
                           E_expected_V_per_cm=ref['E_V_per_cm'], converged=result['solver_info']['converged'])
                if not all(math.isfinite(v) for v in row.values()):
                    raise ValueError('Non-finite sweep result')
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=list(row), lineterminator='\n')
                    writer.writeheader()
                writer.writerow(row)
                f.flush()
                rows.append(row)
                checks.extend(dict(thickness_nm=thickness, intervals=count, **test) for test in tests)
            for j in range(1, len(values)):
                error = abs(values[j]-values[j-1])/ref['C_per_area_F_per_cm2']
                checks.append(dict(thickness_nm=thickness, intervals=f'{model["mesh_intervals"][j-1]}_vs_{model["mesh_intervals"][j]}',
                                   check='mesh_C_relative_change', error=error, limit=c['mesh_capacitance_rtol'],
                                   **{'pass': math.isfinite(error) and error < c['mesh_capacitance_rtol']}))
    with (out/'validation.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(checks[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(checks)
    summary = dict(solves=len(rows), checks=len(checks), failed=sum(not r['pass'] for r in checks),
                   max_C_relative_error=max(r['C_relative_error'] for r in rows))
    write_json(out/'summary.json', summary)
    plot(out, rows)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/phase1/capacitor_thickness.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    c = json.loads(Path(args.config).read_text(encoding='utf-8'))
    validate_thickness(c)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'config.json', c)
    meta = dict(status='RUNNING', utc=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                cwd=str(Path.cwd()), python=platform.python_version(),
                versions={p: importlib.metadata.version(p) for p in ('devsim', 'numpy', 'matplotlib')},
                config_sha256=hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
                source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                    (Path(__file__), Path('src/device/capacitor.py'), Path('validation/analytic/capacitor/run_capacitor.py'))})
    try:
        meta.update(commit=git('rev-parse','HEAD'), dirty_status=git('status','--porcelain'))
    except Exception:
        meta['commit'] = 'unavailable'
    write_json(out/'metadata.json', meta)
    try:
        summary = run(c, out)
        meta['status'] = 'FAIL' if summary['failed'] else 'PASS'
        print(f"{meta['status']}: {summary['solves']} solves, {summary['checks']} checks; output={out}")
        return 1 if summary['failed'] else 0
    except Exception:
        meta['status'] = 'ERROR'
        (out/'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise
    finally:
        write_json(out/'metadata.json', meta)


if __name__ == '__main__':
    raise SystemExit(main())
