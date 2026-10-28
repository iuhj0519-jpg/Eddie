"""PN DC voltage sweep preparation. No simulations occur on import.

Use --stage pilot first. All branches restart from equilibrium, not from a
different direction. Failed attempts and partial outputs remain auditable.
"""
import argparse
from contextlib import closing
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
from validation.analytic.pn_junction.run_pn_junction import write_csv, write_json
from validation.analytic.pn_junction.export_vtm import export_vtm


def compare_rows(a,b,sweep,label):
    result=[]
    for key in ('J_A_per_cm2','charge_equivalent_W_cm','peak_abs_E_V_per_cm'):
        atol=sweep['current_atol_A_per_cm2'] if key=='J_A_per_cm2' else 0.0
        error=abs(a[key]-b[key])
        limit=atol+sweep['comparison_rtol']*max(abs(a[key]),abs(b[key]))
        result.append(dict(case=label,intervals=a['intervals'],refinement=a['refinement'],
                           applied_V=a['applied_V'],check=key,error=error,limit=limit,
                           passed=math.isfinite(error) and error<=limit))
    return result


def plot_voltage(out,rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,2,figsize=(12,12))
    groups=sorted({(r['intervals'],r['refinement']) for r in rows})
    for count,refinement in groups:
        # The two zero-bias branch solves are separately checked; show one.
        points={r['applied_V']:r for r in rows if (r['intervals'],r['refinement'])==(count,refinement)}
        ordered=[points[v] for v in sorted(points)]
        v=[r['applied_V'] for r in ordered]
        label=f'{count} intervals, step / {refinement}'
        axes[0,0].plot(v,[r['J_A_per_cm2'] for r in ordered],label=label)
        resolved=[r for r in ordered if r['current_resolved']]
        axes[0,1].semilogy([r['applied_V'] for r in resolved],
                          [abs(r['J_A_per_cm2']) for r in resolved],label=label)
        axes[1,0].plot(v,[r['charge_equivalent_W_cm']*1e7 for r in ordered],label=label)
        axes[1,1].plot(v,[r['peak_abs_E_V_per_cm'] for r in ordered],label=label)
        axes[2,0].plot(v,[r['terminal_balance_A_per_cm2'] for r in ordered],label=label)
        axes[2,1].plot(v,[r['width_relative_difference']*100 for r in ordered],label=label)
    unique={r['applied_V']:r['depletion_reference_W_cm'] for r in rows}
    axes[1,0].plot(sorted(unique),[unique[v]*1e7 for v in sorted(unique)],'k--',label='Depletion approximation')
    labels=['Signed J (+x) [A/cm²]','Resolved |J| only [A/cm²]',
            'Charge-equivalent W [nm]','Peak |E| [V/cm]',
            '|Ileft + Iright| / unit area [A/cm²]','|W / Wdepletion - 1| [%]']
    for ax,label in zip(axes.flat,labels):
        ax.set(xlabel='V_P - V_N [V]',ylabel=label)
        ax.grid(True)
        ax.legend(fontsize=6)
    fig.suptitle('PN DC drift-diffusion: no SRH / BTBT / avalanche; unresolved log points omitted')
    fig.tight_layout()
    fig.savefig(out/'voltage.png',dpi=160)
    plt.close(fig)


def run(config,sweep,stage,out):
    validate_bias(config,sweep,stage)
    rows,checks=[],[]
    condition=sweep['stages'][stage]
    def flush():
        if rows:
            write_csv(out/'iv.csv',rows)
        if checks:
            write_csv(out/'validation.csv',checks)
    try:
        for count in config['mesh_intervals']:
            for refinement in sweep['step_refinements']:
                for direction in ('reverse','forward'):
                    grid=bias_grid(condition[direction+'_segments'],refinement)
                    def attempt(record):
                        record.update(intervals=count,refinement=refinement,branch=direction)
                        with (out/'convergence.jsonl').open('a',encoding='utf-8') as handle:
                            handle.write(json.dumps(record,allow_nan=False)+'\n')
                    with closing(simulate_bias_branch(config,sweep,count,grid,attempt)) as states:
                        for index,state in enumerate(states):
                            prefix=f'mesh_{count}_step_{refinement}_{direction}_{index:03d}'
                            write_json(out/(prefix+'.json'),state)
                            metric,tests=assess_bias(config,sweep,state)
                            metric.update(refinement=refinement,branch=direction,state_file=prefix+'.json')
                            rows.append(metric)
                            checks.extend(dict(case=direction,intervals=count,refinement=refinement,
                                               applied_V=state['applied_V'],**r) for r in tests)
                            flush()
                            if count==config['mesh_intervals'][-1] and refinement==2 and state['applied_V'] in condition['vtk_biases_V']:
                                export_vtm(state,out/prefix)
                            if not all(r['passed'] for r in tests):
                                raise RuntimeError(f'Validation gate failed: {prefix}; inspect validation.csv')
        indexed={(r['intervals'],r['refinement'],r['branch'],r['applied_V']):r for r in rows}
        for row in rows:
            count,refinement,branch,v=row['intervals'],row['refinement'],row['branch'],row['applied_V']
            if refinement==1:
                checks.extend(compare_rows(row,indexed[count,2,branch,v],sweep,'half_step'))
            position=config['mesh_intervals'].index(count)
            if position<len(config['mesh_intervals'])-1:
                next_count=config['mesh_intervals'][position+1]
                checks.extend(compare_rows(row,indexed[next_count,refinement,branch,v],sweep,'mesh'))
            if branch=='reverse' and v==0:
                checks.extend(compare_rows(row,indexed[count,refinement,'forward',0],sweep,'zero_branch_restart'))
        flush()
        plot_voltage(out,rows)
        summary=dict(status='PASS' if all(r['passed'] for r in checks) else 'FAIL',stage=stage,
                     requested_points_completed=len(rows),checks=len(checks),failed=sum(not r['passed'] for r in checks),
                     extraction='interface_sided_v1',model=sweep['model'],
                     limitations=['No domain enlargement test in this sweep; equilibrium domain check is not sufficient for biased transport.',
                                  'Small reverse currents below configured noise floor are unresolved, not physical zero.',
                                  'Width at forward bias above gate is reported, not forced to match depletion approximation.',
                                  'No recombination: short-base/contact-driven injection; not a calibrated leakage or breakdown model.'])
        write_json(out/'summary.json',summary)
        return summary
    except Exception:
        flush()
        write_json(out/'summary.json',dict(status='INCOMPLETE',stage=stage,
                   requested_points_completed=len(rows),failed=sum(not r['passed'] for r in checks),
                   note='Stopped at first exhausted solve or failed point gate; no success claim.'))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='configs/phase1/pn_junction_voltage.json')
    parser.add_argument('--stage',choices=('pilot','extension'),default='pilot')
    parser.add_argument('--pilot-run',help='Required PASS pilot directory for extension; manual review still required')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    config_path=Path(args.config).resolve()
    sweep=json.loads(config_path.read_text(encoding='utf-8'))
    base_path=(config_path.parent/sweep['base_config']).resolve()
    config=json.loads(base_path.read_text(encoding='utf-8'))
    validate_bias(config,sweep,args.stage)
    sources=[Path('src/device/pn_junction.py'),Path(__file__),
             Path('validation/analytic/pn_junction/export_vtm.py'),
             Path('validation/analytic/pn_junction/run_pn_junction.py')]
    source_hashes={str(p.resolve().relative_to(Path.cwd().resolve())):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    snapshot=dict(sweep=sweep,base_model=config)
    if args.stage=='extension':
        if not args.pilot_run:
            parser.error('Extension requires reviewed --pilot-run')
        pilot=Path(args.pilot_run)
        previous=json.loads((pilot/'metadata.json').read_text())
        if previous['status']!='PASS' or previous['stage']!='pilot' or previous['source_sha256']!=source_hashes:
            parser.error('A PASS pilot with the same source hashes is required')
        if json.loads((pilot/'config.json').read_text())!=snapshot:
            parser.error('Pilot configuration differs; rerun pilot first')
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'config.json',snapshot)
    metadata=dict(status='RUNNING',stage=args.stage,utc=datetime.now(timezone.utc).isoformat(),
                  python=platform.python_version(),source_sha256=source_hashes,
                  assessment='interface_sided_v1',config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
                  base_config_sha256=hashlib.sha256(base_path.read_bytes()).hexdigest(),
                  command=vars(args),cwd=str(Path.cwd()),pilot_run=args.pilot_run)
    try:
        import devsim.python_packages.simple_physics as physics
        import devsim.python_packages.simple_dd as dd
        metadata['versions']={p:importlib.metadata.version(p) for p in ('devsim','matplotlib')}
        metadata['helper_sha256']={p.__name__:hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest() for p in (physics,dd)}
        for key,command in [('commit',['rev-parse','HEAD']),('dirty_status',['status','--porcelain'])]:
            try:
                metadata[key]=subprocess.check_output(['git',*command],text=True).strip()
            except (OSError,subprocess.CalledProcessError):
                metadata[key]='unavailable'
        write_json(out/'metadata.json',metadata)
        summary=run(config,sweep,args.stage,out)
        metadata['status']=summary['status']
        print(f"{summary['status']}: {out}")
        return int(summary['status']!='PASS')
    except Exception:
        metadata['status']='ERROR'
        (out/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise
    finally:
        write_json(out/'metadata.json',metadata)


if __name__=='__main__':
    raise SystemExit(main())
