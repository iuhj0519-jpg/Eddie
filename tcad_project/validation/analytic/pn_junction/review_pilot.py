"""Postprocess saved failed/pass pilot data only. Never solve or overwrite inputs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read_rows(path):
    with path.open(newline='',encoding='utf-8') as handle:
        return [{k:(v=='True' if v in ('True','False') else v if k in ('branch','state_file') else float(v))
                 for k,v in row.items()} for row in csv.DictReader(handle)]


def key(row):
    return tuple(row[k] for k in ('intervals','refinement','branch','applied_V'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--failed',required=True)
    parser.add_argument('--passed',required=True)
    parser.add_argument('--figures',default='figures')
    args=parser.parse_args()
    failed,passed,figures=map(Path,(args.failed,args.passed,args.figures))
    outputs=[failed/'voltage.png',figures/'pn_pilot_current_uniformity.png',figures/'pn_pilot_comparison.json']
    if any(p.exists() for p in outputs):
        raise FileExistsError('Refusing to overwrite diagnostic output')
    tracked=[p for folder in (failed,passed) for p in folder.iterdir() if p.is_file()]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
    a,b=read_rows(failed/'iv.csv'),read_rows(passed/'iv.csv')
    lookup={key(row):row for row in b}
    pairs=[(row,lookup[key(row)]) for row in a]
    metrics=('J_A_per_cm2','charge_equivalent_W_cm','peak_abs_E_V_per_cm',
             'terminal_balance_A_per_cm2','current_span_A_per_cm2','width_relative_difference')
    report=dict(matched_points=len(pairs),failed_rows=len(a),passed_rows=len(b),
                max_absolute_differences={k:max(abs(x[k]-y[k]) for x,y in pairs) for k in metrics},
                provenance='Postprocessed saved data; no solve. Partial failed run is not a complete sweep.')
    with (failed/'validation.csv').open() as handle:
        failures=[dict(line=i,**r) for i,r in enumerate(csv.DictReader(handle),start=2) if r['passed']=='False']
    report['failed_checks']=failures
    f=failures[0]
    target=(float(f['intervals']),float(f['refinement']),f['case'],float(f['applied_V']))
    ar=next(row for row in a if key(row)==target)
    br=lookup[target]
    report['failed_point_comparison']={'run_001':ar,'run_002':br}
    fig,axs=plt.subplots(3,2,figsize=(12,12))
    for count,ref in sorted({(r['intervals'],r['refinement']) for r in a}):
        points={r['applied_V']:r for r in a if (r['intervals'],r['refinement'])==(count,ref)}
        rows=[points[v] for v in sorted(points)]
        label=f'{count:g} intervals, step/{ref:g} ({len(rows)} saved V)'
        v=[r['applied_V'] for r in rows]
        for ax,k,scale in [(axs[0,0],'J_A_per_cm2',1),(axs[1,0],'charge_equivalent_W_cm',1e7),
                           (axs[1,1],'peak_abs_E_V_per_cm',1),(axs[2,0],'terminal_balance_A_per_cm2',1),
                           (axs[2,1],'width_relative_difference',100)]:
            ax.plot(v,[r[k]*scale for r in rows],'.-',label=label,markersize=3)
        resolved=[r for r in rows if r['current_resolved']]
        axs[0,1].semilogy([r['applied_V'] for r in resolved],[abs(r['J_A_per_cm2']) for r in resolved],'.-',label=label)
    unique={r['applied_V']:r['depletion_reference_W_cm'] for r in a}
    axs[1,0].plot(sorted(unique),[unique[v]*1e7 for v in sorted(unique)],'k--',label='Depletion reference')
    labels=['Signed J [A/cm²]','Resolved |J| [A/cm²]','Charge-equivalent W [nm]',
            'Peak |E| [V/cm]','Terminal sum residual [A/cm²]','Width difference [%]']
    for ax,label in zip(axs.flat,labels):
        ax.set(xlabel='V_P - V_N [V]',ylabel=label)
        ax.grid(True)
        ax.legend(fontsize=6)
    fig.suptitle('run_001 PILOT: FAILED / PARTIAL — 65 saved states only',color='darkred')
    fig.text(0.5,0.005,'Failure: INTERNAL current span at 400 intervals, 0 V (not the terminal-sum panel). No 800-interval data.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,0.025,1,0.96))
    fig.savefig(outputs[0],dpi=160)
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4.8))
    for folder,row,ax,color in ((failed,ar,axs[0],'tab:red'),(passed,br,axs[1],'tab:blue')):
        state=json.loads((folder/row['state_file']).read_text())
        edges=state['edges']; currents=edges['TotalCurrent_A_per_cm2']
        span=max(currents)-min(currents)
        limit=1e-9+1e-4*max(abs(v) for v in currents)
        ax.plot([x*1e4 for x in edges['x_cm']],currents,color=color)
        ax.set(xlabel='x [µm]',ylabel='Jtotal (+x) [A/cm²]',title=folder.parent.name)
        ax.grid(True)
        ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0))
        ax.text(0.03,0.97,f'span = {span:.4e}\nlimit = {limit:.4e}\n'+('PASS' if span<=limit else 'FAIL'),
                transform=ax.transAxes,va='top',bbox=dict(facecolor='white',alpha=0.85))
    fig.suptitle('Same point: 400 intervals, step/1, reverse branch 0 V — axes have different scales')
    fig.tight_layout()
    figures.mkdir(parents=True,exist_ok=True)
    fig.savefig(outputs[1],dpi=160)
    plt.close(fig)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in hashes.items())
    report['existing_files_unchanged']=len(hashes)
    outputs[2].write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
