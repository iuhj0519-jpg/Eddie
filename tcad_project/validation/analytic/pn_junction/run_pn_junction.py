"""PN equilibrium validation and six-panel Python plot; no bias sweep."""
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

from src.device.pn_junction import assess, assess_interface, reference, simulate, validate
from validation.analytic.pn_junction.export_vtm import export_vtm


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def write_csv(path, rows):
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(out, states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3,2,figsize=(12,12))
    for state in states:
        n,e = state['nodes'],state['edges']
        x,xe = [v*1e4 for v in n['x_cm']],[v*1e4 for v in e['x_cm']]
        label = f"{state['intervals']} intervals"
        axes[0,1].semilogy(x,n['Electrons_cm3'],label='n, '+label)
        axes[0,1].semilogy(x,n['Holes_cm3'],'--',label='p, '+label)
        axes[1,0].plot(x,n['Potential_V'],label=label)
        axes[1,1].plot(xe,e['ElectricField_V_per_cm'],label=label)
        axes[2,0].plot(x,n['ChargeDensity_C_per_cm3'],label=label)
        axes[2,1].plot(xe,e['TotalCurrent_A_per_cm2'],label='total, '+label)
    fine = states[-1]
    n,e,ref,junction = fine['nodes'],fine['edges'],fine['reference'],fine['junction_cm']
    x,xe = [v*1e4 for v in n['x_cm']],[v*1e4 for v in e['x_cm']]
    axes[0,0].plot(x,n['Acceptors_cm3'],label='Acceptors')
    axes[0,0].plot(x,n['Donors_cm3'],label='Donors')
    axes[1,1].plot([(junction-ref['xp_cm'])*1e4,junction*1e4,(junction+ref['xn_cm'])*1e4],
                   [0,ref['E_peak_V_per_cm'],0],'k--',label='Depletion approximation')
    axes[2,1].plot(xe,e['ElectronCurrent_A_per_cm2'],'--',label='Jn, finest')
    axes[2,1].plot(xe,e['HoleCurrent_A_per_cm2'],':',label='Jp, finest')
    labels = ['Doping [cm^-3]','Carrier density [cm^-3]','Potential [V]',
              'Signed E_x [V/cm]','Space charge [C/cm^3]','Equilibrium SG diagnostic J [A/cm^2]']
    for ax,label in zip(axes.flat,labels):
        ax.set(xlabel='x [um]',ylabel=label)
        ax.axvline(junction*1e4,color='gray',linestyle=':',linewidth=0.7)
        ax.grid(True)
        ax.legend(fontsize=7)
    fig.suptitle('1D PN equilibrium: Poisson-Boltzmann (no continuity/SRH solve)')
    fig.tight_layout()
    fig.savefig(out/'pn_junction.png',dpi=160)
    plt.close(fig)


def run(c,out,assessment='legacy'):
    validate(c)
    assessor = {'legacy':assess,'interface_sided':assess_interface}[assessment]
    states, metrics, checks = [],[],[]
    for count in c['mesh_intervals']:
        state = simulate(c,count)
        write_json(out/f'mesh_{count}.json',state)
        metric, tests = assessor(c,state)
        states.append(state)
        metrics.append(dict(case='baseline',**metric))
        checks.extend(dict(case='baseline',intervals=count,**row) for row in tests)
    for a,b in zip(metrics,metrics[1:]):
        for key in ('charge_equivalent_W_cm','peak_abs_E_V_per_cm'):
            error = abs(a[key]/b[key]-1)
            checks.append(dict(case='mesh',intervals=f"{a['intervals']}_vs_{b['intervals']}",
                               check=key,error=error,limit=c['mesh_metric_rtol'],passed=error<c['mesh_metric_rtol']))
    # Enlarge both neutral regions at unchanged dx; not a geometry optimization.
    scale = c['domain_check_scale']
    count = round(scale*c['mesh_intervals'][-1])
    expanded = dict(c,p_length_nm=c['p_length_nm']*scale,n_length_nm=c['n_length_nm']*scale,
                    mesh_intervals=[round(scale*n) for n in c['mesh_intervals']])
    state = simulate(expanded,count)
    write_json(out/'domain_check.json',dict(config=expanded,**state))
    metric, tests = assessor(expanded,state)
    metrics.append(dict(case='expanded_domain',**metric))
    checks.extend(dict(case='expanded_domain',intervals=count,**row) for row in tests)
    for key in ('Vbi_V','charge_equivalent_W_cm','peak_abs_E_V_per_cm'):
        error = abs(metrics[-2][key]/metric[key]-1)
        checks.append(dict(case='domain',intervals=count,check=key,error=error,
                           limit=c['domain_metric_rtol'],passed=error<c['domain_metric_rtol']))
    write_csv(out/'metrics.csv',metrics)
    write_csv(out/'validation.csv',checks)
    fine = states[-1]
    write_csv(out/'profiles.csv',[dict(zip(fine['nodes'],values)) for values in zip(*fine['nodes'].values())])
    write_csv(out/'edges.csv',[dict(zip(fine['edges'],values)) for values in zip(*fine['edges'].values())])
    plot(out,states)
    vtk_files = export_vtm(fine,out/'pn_junction')
    summary = dict(assessment=assessment,solves=len(states)+1,checks=len(checks),failed=sum(not r['passed'] for r in checks),
                   reference=reference(c),vtk_files=vtk_files,
                   caveats=['Vbi uses contact boundary potentials; not an independent test of spatial profile.',
                            'np and quasi-Fermi consistency follow from the equilibrium carrier model.',
                            'Charge-equivalent width is compared with depletion approximation, not an exact analytic solution.',
                            'VTK XML and ParaView visual correctness require a separate first-run check.'])
    write_json(out/'summary.json',summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='configs/phase1/pn_junction.json')
    parser.add_argument('--output',required=True)
    parser.add_argument('--assessment',choices=('legacy','interface_sided'),default='legacy')
    args = parser.parse_args()
    c = json.loads(Path(args.config).read_text(encoding='utf-8'))
    validate(c)
    ref = reference(c)
    if c['p_length_nm']*1e-7 <= ref['xp_cm'] or c['n_length_nm']*1e-7 <= ref['xn_cm']:
        parser.error('Both contacts must lie outside estimated depletion region')
    out = Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'config.json',c)
    sources = [Path(__file__),Path('src/device/pn_junction.py'),
               Path('validation/analytic/pn_junction/export_vtm.py')]
    metadata = dict(assessment=args.assessment,status='RUNNING',utc=datetime.now(timezone.utc).isoformat(),command=sys.argv,
                    cwd=str(Path.cwd()),python=platform.python_version(),
                    versions={p:importlib.metadata.version(p) for p in ('devsim','matplotlib')},
                    config_sha256=hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
                    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    import devsim.python_packages.simple_physics as physics
    helper = Path(physics.__file__)
    metadata['physics_helper_sha256'] = hashlib.sha256(helper.read_bytes()).hexdigest()
    for key,arguments in [('commit',['rev-parse','HEAD']),('dirty_status',['status','--porcelain'])]:
        try:
            metadata[key] = subprocess.check_output(['git',*arguments],text=True).strip()
        except (OSError,subprocess.CalledProcessError):
            metadata[key] = 'unavailable'
    write_json(out/'metadata.json',metadata)
    try:
        summary = run(c,out,assessment=args.assessment)
        metadata['status'] = 'PASS' if summary['failed']==0 else 'FAIL'
        print(f"{metadata['status']}: {summary['solves']} solves, {summary['checks']} checks; {out}")
        return int(bool(summary['failed']))
    except Exception:
        metadata['status'] = 'ERROR'
        (out/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise
    finally:
        write_json(out/'metadata.json',metadata)


if __name__ == '__main__':
    raise SystemExit(main())
