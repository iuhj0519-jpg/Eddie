"""Plot saved SRH data on linear/log axes without running DEVSIM."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def plot_log_current(source, output, config, summary, rows, current_atol):
    """One supplemental PNG; leave raw plots and saved currents untouched."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    count = max(int(r['intervals']) for r in rows)
    refinement = max(int(r['refinement']) for r in rows)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.7))
    styles = [('-', 'o'), ('--', 's'), ('-.', '^'), (':', 'D')]
    for i, case in enumerate(config['experiment']['cases']):
        points = {float(r['applied_V']):r for r in rows if r['case_name']==case['name']
                  and int(r['intervals'])==count and int(r['refinement'])==refinement}
        if not points:
            raise ValueError(f"Missing finest-grid data: {case['name']}")
        label = 'SRH OFF' if not case['enabled'] else f"tau = {case['tau_n_s']*1e6:g} us"
        if case['enabled'] and case['tau_n_s'] != case['tau_p_s']:
            label = f"tau_n = {case['tau_n_s']*1e6:g}, tau_p = {case['tau_p_s']*1e6:g} us"
        for ax, sign, ceiling in ((axes[0],1,math.inf),(axes[1],1,.15),(axes[2],-1,math.inf)):
            volts = sorted((v for v in points if sign*v>=0 and abs(v)<=ceiling), key=abs)
            current = [float(points[v]['J_A_per_cm2']) for v in volts]
            if not all(math.isfinite(j) for j in current):
                raise ValueError('Non-finite saved current')
            y = [abs(j) if v!=0 and points[v]['current_resolved'].lower()=='true'
                 else math.nan for v,j in zip(volts,current)]
            style,marker = styles[i%len(styles)]
            ax.semilogy([abs(v) for v in volts],y,color=f'C{i}',linestyle=style,
                        marker=marker,markevery=(i*2, max(8,len(volts)//15)),
                        markersize=4,markerfacecolor='none',linewidth=1.4,label=label)
    for ax,title,xlabel in zip(axes,
            ('Forward bias: full range','Forward bias: low-voltage detail','Reverse bias: magnitude'),
            ('Forward voltage [V]','Forward voltage [V]','Reverse voltage magnitude [V]')):
        ax.set(title=title,xlabel=xlabel,ylabel=r'Resolved $|J|$ [A/cm$^2$] - LOG')
        ax.set_ylim(bottom=current_atol*.8)
        ax.grid(True,which='both',alpha=.25)
        ax.legend(fontsize=8)
    axes[1].set_xlim(0,.15)
    fig.suptitle(f'SRH {source.name}: {summary["status"]} | {source.parent.name} | {count} intervals | refinement {refinement}')
    off_reverse = [r for r in rows if r['case_name']=='off' and float(r['applied_V'])<0
                   and int(r['intervals'])==count and int(r['refinement'])==refinement]
    note = ('SRH OFF reverse current is below the displayed resolution threshold.'
            if off_reverse and all(r['current_resolved'].lower()!='true' for r in off_reverse)
            else 'Unresolved gaps are not bridged.')
    fig.text(.5,.02,f'Same saved currents; no offsets or rescaling of values. Zero/unresolved points (|J| <= {current_atol:g} A/cm2) are omitted.\n'
             f'High-forward-bias curves can still overlap physically. {note}',
             ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.10,1,.94))
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,dpi=180)
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=root / 'data/raw/phase1/pn_junction_srh/run_001/pilot')
    parser.add_argument('--output', type=Path, default=root / 'figures/pn_srh_run_001_pilot_linear_log.png')
    parser.add_argument('--log-only', action='store_true', help='One log-current PNG with forward low-voltage detail; no companion plots')
    args = parser.parse_args()
    source = args.input.resolve()
    output = args.output.resolve()
    if output.is_relative_to(source):
        raise ValueError('Output must be outside the saved run directory')
    before = {p: hashlib.sha256(p.read_bytes()).digest() for p in source.rglob('*') if p.is_file()}
    config = json.loads((source / 'config.json').read_text(encoding='utf-8'))
    summary = json.loads((source / 'summary.json').read_text(encoding='utf-8'))
    current_atol = config['transport']['current_atol_A_per_cm2']
    with (source / 'iv.csv').open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if args.log_only:
        if output.exists():
            raise FileExistsError('Refusing to overwrite supplemental PNG')
        plot_log_current(source,output,config,summary,rows,current_atol)
        after = {p:hashlib.sha256(p.read_bytes()).digest() for p in source.rglob('*') if p.is_file()}
        if before != after:
            raise RuntimeError('Saved run files changed during postprocessing')
        print(f'Unchanged raw files: {len(before)}; output: {output}')
        return
    count = max(int(r['intervals']) for r in rows)
    refinement = max(int(r['refinement']) for r in rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import numpy as np
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.3))
    log_axes = [ax.twinx() for ax in axes]
    effect_fig, effect_axes = plt.subplots(1, 2, figsize=(13, 6))
    baseline = {float(r['applied_V']): float(r['J_A_per_cm2']) for r in rows
                if r['case_name'] == 'off' and int(r['intervals']) == count
                and int(r['refinement']) == refinement}
    for case in config['experiment']['cases']:
        selected = [r for r in rows if r['case_name'] == case['name']
                    and int(r['intervals']) == count and int(r['refinement']) == refinement]
        if not selected:
            raise ValueError(f"Missing finest-grid data: {case['name']}")
        # Each branch saves its own equilibrium point. Select one per voltage.
        points = {float(r['applied_V']): r for r in selected}
        volts = sorted(points)
        current = [float(points[v]['J_A_per_cm2']) for v in volts]
        if not all(math.isfinite(j) for j in current):
            raise ValueError('Non-finite saved current')
        label = 'SRH OFF' if not case['enabled'] else (
            f"tau = {case['tau_n_s'] * 1e6:g} us" if case['tau_n_s'] == case['tau_p_s'] else
            f"tau_n = {case['tau_n_s'] * 1e6:g}, tau_p = {case['tau_p_s'] * 1e6:g} us")
        # NaN keeps unresolved gaps: never join reverse and forward branches.
        resolved = [abs(j) if points[v]['current_resolved'].lower() == 'true' and v != 0
                    else math.nan for v, j in zip(volts, current)]
        color = f'C{config["experiment"]["cases"].index(case)}'
        for index, sign in enumerate((1, -1)):
            indices = [i for i, v in enumerate(volts) if sign*v >= 0]
            # Plot reverse magnitude against increasing reverse-bias magnitude.
            indices.sort(key=lambda i: abs(volts[i]))
            x = [abs(volts[i]) for i in indices]
            y = [abs(current[i]) for i in indices]
            axes[index].plot(x, y, '-', color=color, label=label, lw=1.8)
            log_axes[index].semilogy(x, [resolved[i] for i in indices], '--o',
                                    color=color, ms=3, lw=1.1)
        if case['enabled']:
            delta = [j-baseline[v] for v, j in zip(volts, current)]
            effect_axes[0].plot(volts, delta, color=color, label=label)
        # Interior central differences; no endpoint one-sided derivatives.
        v = np.asarray(volts)
        j = np.asarray(current)
        g = (j[2:]-j[:-2])/(v[2:]-v[:-2])
        effect_axes[1].semilogy(v[1:-1], np.where(g > 0, g, np.nan), color=color, label=label)
        for v in (-0.1, 0.1):
            if v in points:
                print(f"{label}, V={v:+g}, J={float(points[v]['J_A_per_cm2']):.12e} A/cm2")
    for index, (ax, log_ax) in enumerate(zip(axes, log_axes)):
        ax.set(title=('Forward bias', 'Reverse bias (magnitude)')[index],
               xlabel=('Forward voltage [V]', 'Reverse voltage magnitude [V]')[index],
               ylabel=r'$|J|$ [A/cm$^2$] - LINEAR (solid)')
        ax.set_ylim(bottom=0)
        log_ax.set_ylabel(r'Resolved $|J|$ [A/cm$^2$] - LOG (dashed + dots)')
        values = [float(r['J_A_per_cm2']) for r in rows if int(r['intervals'])==count
                  and int(r['refinement'])==refinement and
                  ((float(r['applied_V'])>0) if index==0 else (float(r['applied_V'])<0))]
        log_ax.set_ylim(current_atol*.8, max(current_atol*10,max(abs(j) for j in values)*2))
        ax.grid(True, alpha=0.3)
    axes[0].legend(loc='upper left', fontsize=9)
    axes[1].legend(handles=[Line2D([], [], color='black', label='Left axis: linear'),
                           Line2D([], [], color='black', linestyle='--', marker='o', ms=3,
                                  label='Right axis: log')], loc='upper left', fontsize=9)
    fig.suptitle(f'SRH {source.name}: {summary["status"]} | {source.parent.name} | {count} intervals | refinement {refinement}')
    fig.text(0.5, 0.02, 'Each case is drawn twice: SAME saved current, two different y-axis scales (not two models).\n'
             f'Log curves omit zero and unresolved points (|J| <= {current_atol:g} A/cm2); no gap bridging or extrapolation.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    effect_axes[0].set(title='SRH-induced change relative to OFF', xlabel=r'$V_P - V_N$ [V]',
                       ylabel=r'$\Delta J = J_{SRH}-J_{OFF}$ [A/cm$^2$]')
    effect_axes[0].axhline(0, color='grey', lw=0.6)
    effect_axes[1].set(title='Differential conductance density', xlabel=r'$V_P - V_N$ [V]',
                       ylabel=r'$g_J = dJ/dV$ [S/cm$^2$] - LOG')
    for ax in effect_axes:
        ax.grid(True, which='both', alpha=0.3)
        ax.legend(fontsize=9)
    effect_fig.suptitle(f'SRH {source.name}: {summary["status"]} | current diagnostics | {count} intervals | refinement {refinement}')
    effect_fig.text(0.5, 0.02, 'Delta J: difference of self-consistent solutions, NOT an isolated SRH terminal-current component.\n'
                    'g_J: central difference of saved signed J; endpoints omitted. Not the paper\'s fitted G_D.',
                    ha='center', fontsize=9)
    effect_fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    diagnostics = output.with_name(output.stem.replace('linear_log', 'current_diagnostics') + '.png')
    if diagnostics == output:
        diagnostics = output.with_name(output.stem + '_diagnostics.png')
    effect_fig.savefig(diagnostics, dpi=180)
    plt.close(effect_fig)
    after = {p: hashlib.sha256(p.read_bytes()).digest() for p in source.rglob('*') if p.is_file()}
    if before != after:
        raise RuntimeError('Saved run files changed during postprocessing')
    print(f'Unchanged raw files: {len(before)}; output: {output}')
    print(f'Diagnostics: {diagnostics}')


if __name__ == '__main__':
    main()
