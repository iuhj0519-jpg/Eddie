"""Run from project root: python -m validation.analytic.capacitor.run_capacitor."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import traceback

from src.device.capacitor import analytic_profile, assess, layer_mesh, reference, simulate


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/phase1/capacitor.json')
    parser.add_argument('--output', required=True, help='New output directory; existing paths are rejected')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    expected = reference(config)
    for count in config['mesh_intervals']:
        layer_mesh(config, count)
    if config['left_V'] == config['right_V']:
        parser.error('Single-bias Q/dV validation requires nonzero bias; use run_voltage instead')
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'config.json', config)
    metadata = {'utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
                'command': sys.argv, 'cwd': str(Path.cwd()), 'status': 'running',
                'config_sha256': hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
                'versions': {p: importlib.metadata.version(p) for p in ('devsim', 'matplotlib')}}
    try:
        metadata.update(git_commit=git('rev-parse', 'HEAD'), git_status=git('status', '--porcelain'))
    except (subprocess.CalledProcessError, FileNotFoundError):
        metadata['git_commit'] = 'unavailable'
    metadata['source_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               (Path(__file__), Path('src/device/capacitor.py'))}
    write_json(out/'metadata.json', metadata)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        different_k = len(set(config.get('layer_relative_permittivities', [config['relative_permittivity']]))) > 1
        fig, axes = plt.subplots(2 if different_k else 1, 2, figsize=(11, 8 if different_k else 4))
        axes = axes.flatten()
        all_pass = True
        with (out/'validation.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=['intervals', 'nodes', 'C_per_area_F_per_cm2', 'check', 'error', 'limit', 'pass'])
            writer.writeheader()
            for count in config['mesh_intervals']:
                result = simulate(config, count)
                write_json(out/f'mesh_{count}.json', result)
                c_value, checks = assess(config, result)
                for check in checks:
                    writer.writerow(dict(intervals=count, nodes=len(result['nodes']['x_cm']), C_per_area_F_per_cm2=c_value, **check))
                    all_pass &= check['pass']
                handle.flush()
                n, e = result['nodes'], result['edges']
                axes[0].plot([x*1e7 for x in n['x_cm']], n['potential_V'], '.-', label=f'{count} intervals')
                axes[1].plot([(a+b)*0.5e7 for a,b in zip(e['x0_cm'], e['x1_cm'])],
                             [v*(1 if b>a else -1) for a,b,v in zip(e['x0_cm'],e['x1_cm'],e['E_edge_V_per_cm'])], '.-')
                if different_k:
                    # Do not interpolate across a discontinuous dielectric interface.
                    line = axes[1].lines[-1]
                    color = line.get_color()
                    line.remove()
                    for region in result['regions']:
                        re = region['edges']
                        axes[1].plot([(a+b)*0.5e7 for a,b in zip(re['x0_cm'], re['x1_cm'])],
                                     [v*(1 if b>a else -1) for a,b,v in zip(re['x0_cm'],re['x1_cm'],re['E_edge_V_per_cm'])],
                                     '.-', color=color)
                    axes[2].plot(count, c_value*1e7, 'o', label=f'{count} intervals')
                    axes[3].plot([0, config['thickness_nm']],
                                 [result['charges']['left']*1e6, result['charges']['right']*1e6],
                                 'o', label=f'{count} intervals')
        axes[0].plot([0,config['thickness_nm']], [config['left_V'],config['right_V']], 'k--', label='Analytic')
        axes[1].axhline(expected['E_V_per_cm'], color='k', linestyle='--')
        axes[0].set_ylabel('Potential [V]')
        axes[1].set_ylabel('Electric field, +x [V/cm]')
        for ax in axes[:2]:
            ax.set_xlabel('x [nm]')
            ax.grid(True)
        axes[1].ticklabel_format(axis='y', style='sci', scilimits=(0, 0), useOffset=False)
        field_margin = 0.05*abs(expected['E_V_per_cm'])
        axes[1].set_ylim(expected['E_V_per_cm']-field_margin, expected['E_V_per_cm']+field_margin)
        if different_k:
            # Replace the homogeneous reference lines with a piecewise stack reference.
            axes[0].lines[-1].remove()
            axes[1].lines[-1].remove()
            bounds = [0.0]
            for t in config['layer_thicknesses_nm']:
                bounds.append(bounds[-1]+t)
            axes[0].plot(bounds, [analytic_profile(config, x*1e-7)[0] for x in bounds],
                         'k--', label='Analytic')
            fields = [analytic_profile(config, (a+b)*0.5e-7)[1] for a,b in zip(bounds, bounds[1:])]
            axes[1].step(bounds, fields+[fields[-1]], where='post', color='k', linestyle='--', label='Analytic')
            margin = 0.1*max(abs(v) for v in fields)
            axes[1].set_ylim(min(fields)-margin, max(fields)+margin)
            axes[1].legend()
            axes[2].axhline(expected['C_per_area_F_per_cm2']*1e7, color='k', linestyle='--', label='Analytic')
            axes[2].set(xlabel='Total mesh intervals', ylabel='C/A [fF/um^2]')
            c_plot = expected['C_per_area_F_per_cm2']*1e7
            axes[2].set_ylim(0.95*c_plot, 1.05*c_plot)
            axes[2].ticklabel_format(axis='y', style='plain', useOffset=False)
            q = expected['C_per_area_F_per_cm2']*(config['right_V']-config['left_V'])*1e6
            axes[3].plot([0,config['thickness_nm']], [-q,q], 'kx', markersize=10, label='Analytic')
            axes[3].set(xlabel='Electrode position x [nm]', ylabel='Electrode Q/A [uC/cm^2]')
            for ax in axes[2:]:
                ax.grid(True)
                ax.legend()
            fig.suptitle('Multi-Layer Capacitor: SiO2 / HfO2 (assumed k)')
        axes[0].legend()
        fig.tight_layout()
        fig.savefig(out/'capacitor.png', dpi=160)
        plt.close(fig)
        metadata['status'] = 'PASS' if all_pass else 'FAIL'
        print(f"{metadata['status']}: C/A analytic = {expected['C_per_area_F_per_cm2']:.12g} F/cm^2; output={out}")
        return 0 if all_pass else 1
    except Exception:
        metadata['status'] = 'ERROR'
        (out/'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise
    finally:
        write_json(out/'metadata.json', metadata)


if __name__ == '__main__':
    raise SystemExit(main())
