"""Read-only analysis of saved PN states; no DEVSIM solve or gate changes.

Half-majority recovery is a diagnostic definition, not a replacement width.
10/50/90% are fixed in advance to expose boundary-definition sensitivity.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from src.device.pn_junction import interface_side_charges, bias_reference, reference


def crossing(distance, recovery, fraction):
    """Unique outward crossing with linear interpolation; reject ambiguity."""
    if not 0 < fraction < 1 or len(distance) != len(recovery) or len(distance) < 2:
        raise ValueError('Invalid recovery threshold or arrays')
    if any(not math.isfinite(v) for v in [*distance, *recovery]):
        raise ValueError('Nonfinite profile')
    if any(b <= a for a, b in zip(distance, distance[1:])):
        raise ValueError('Distance must increase from junction')
    if recovery[0] >= fraction or recovery[-1] <= fraction:
        raise ValueError('Threshold not bracketed by junction and outer contact')
    hits = []
    for i, (a, b) in enumerate(zip(recovery, recovery[1:])):
        if a < fraction <= b:
            hits.append(distance[i] + (distance[i+1]-distance[i])*(fraction-a)/(b-a))
        elif a >= fraction > b:
            raise ValueError('Nonmonotonic crossing')
    if len(hits) != 1:
        raise ValueError('Ambiguous recovery edge')
    return hits[0]


def interpolate(x, y, point):
    if not x[0] <= point <= x[-1]:
        raise ValueError('Interpolation outside domain')
    for i in range(len(x)-1):
        if x[i] <= point <= x[i+1]:
            t = (point-x[i])/(x[i+1]-x[i])
            return y[i]*(1-t)+y[i+1]*t
    return y[-1]


def integrate(x, y, start, stop):
    grid = [start] + [v for v in x if start < v < stop] + [stop]
    vals = [interpolate(x, y, v) for v in grid]
    return math.fsum((b-a)*(u+v)/2 for a,b,u,v in zip(grid,grid[1:],vals,vals[1:]))


def extract(config, state, saved):
    nodes, edges = state['nodes'], state['edges']
    x, n, p, psi = (nodes[k] for k in ('x_cm','Electrons_cm3','Holes_cm3','Potential_V'))
    junction = state['junction_cm']
    j = min(range(len(x)), key=lambda i: abs(x[i]-junction))
    if abs(x[j]-junction) > 1e-15:
        raise ValueError('Junction node missing')
    na, nd, q = (config[k] for k in ('acceptors_cm3','donors_cm3','electron_charge_C'))
    left_d = [junction-v for v in reversed(x[:j+1])]
    right_d = [v-junction for v in x[j:]]
    left_recovery = [v/na for v in reversed(p[:j+1])]
    right_recovery = [v/nd for v in n[j:]]
    qleft, qright = interface_side_charges(config,state)
    wq = abs(qleft)/(q*na)+abs(qright)/(q*nd)
    wref = bias_reference(config,state['applied_V'])['W_cm']
    if not math.isclose(wq,float(saved['charge_equivalent_W_cm']),rel_tol=1e-12):
        raise AssertionError('Re-extracted W differs from saved result')
    row = dict(applied_V=state['applied_V'],intervals=state['intervals'],
               refinement=int(saved['refinement']),state_file=saved['state_file'],
               W_Q_nm=wq*1e7,W_reference_nm=wref*1e7,
               W_Q_difference_pct=100*(wq/wref-1),
               junction_n_cm3=n[j],junction_p_cm3=p[j],
               potential_drop_V=psi[-1]-psi[0],
               expected_drop_V=reference(config)['Vbi_V']-state['applied_V'],
               peak_abs_E_V_per_cm=max(abs(v) for v in edges['ElectricField_V_per_cm']))
    for fraction in (0.1,0.5,0.9):
        label = str(round(fraction*100))
        xp = crossing(left_d,left_recovery,fraction)
        xn = crossing(right_d,right_recovery,fraction)
        row.update({f'xp_{label}_nm':xp*1e7,f'xn_{label}_nm':xn*1e7,
                    f'W_{label}_nm':(xp+xn)*1e7,
                    f'W_{label}_difference_pct':100*((xp+xn)/wref-1)})
    # Account for the area difference from a full-depletion rectangle.
    # Same sided rho as the official integral, but keep signed charge fractions.
    fl = [1+(a-b)/na for a,b in zip(n[:j+1],p[:j+1])]
    fr = [1+(a-b)/nd for a,b in zip(p[j:],n[j:])]
    a = junction-wref*nd/(na+nd)
    b = junction+wref*na/(na+nd)
    inner = integrate(x[:j+1],fl,a,junction)+integrate(x[j:],fr,junction,b)
    tail = integrate(x[:j+1],fl,x[0],a)+integrate(x[j:],fr,b,x[-1])
    row['inside_rectangle_deficit_nm'] = (wref-inner)*1e7
    row['outside_rectangle_tail_nm'] = tail*1e7
    row['area_accounting_residual_nm'] = (wq-(inner+tail))*1e7
    if abs(row['area_accounting_residual_nm']) > 1e-7:
        raise AssertionError('Charge signs/area decomposition inconsistent')
    offset = 500e-7  # fixed 500 nm away from junction, within both domains
    row['n_at_P_500nm_cm3'] = interpolate(x,n,junction-offset)
    row['p_at_N_500nm_cm3'] = interpolate(x,p,junction+offset)
    row['outer_500nm_potential_drop_V'] = (
        interpolate(x,psi,junction-offset)-psi[0]
        +psi[-1]-interpolate(x,psi,junction+offset))
    return row


def figures(states, rows, config, profiles_path, widths_path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3,2,figsize=(12,12))
    for state in states:
        nodes,edges=state['nodes'],state['edges']
        x=[(v-state['junction_cm'])*1e7 for v in nodes['x_cm']]
        ex=[(v-state['junction_cm'])*1e7 for v in edges['x_cm']]
        n,p,psi=(nodes[k] for k in ('Electrons_cm3','Holes_cm3','Potential_V'))
        j=min(range(len(x)),key=lambda i:abs(x[i]))
        label=f"{state['applied_V']:+.2f} V"
        line,=axes[0,0].semilogy(x,n,label=label)
        color=line.get_color()
        axes[0,1].semilogy(x,p,color=color,label=label)
        q=config['electron_charge_C']; na=config['acceptors_cm3']; nd=config['donors_cm3']
        rho_l=[q*(h-e-na) for h,e in zip(p[:j+1],n[:j+1])]
        rho_r=[q*(h-e+nd) for h,e in zip(p[j:],n[j:])]
        axes[1,0].plot(x[:j+1],rho_l,color=color,label=label)
        axes[1,0].plot(x[j:],rho_r,color=color)
        axes[1,1].plot(x,[v-psi[0] for v in psi],color=color,label=label)
        axes[2,0].plot(ex,[v/1e3 for v in edges['ElectricField_V_per_cm']],color=color,label=label)
        axes[2,1].plot(x[:j+1],[v/na for v in p[:j+1]],color=color,label=label)
        axes[2,1].plot(x[j:],[v/nd for v in n[j:]],color=color)
    for ax,title,ylabel in zip(axes.flat,
        ('Electron density','Hole density','Space charge (sided junction values)',
         'Potential relative to left contact','Signed electric field','Majority-carrier recovery'),
        ('n [cm$^{-3}$]','p [cm$^{-3}$]',r'$\rho$ [C/cm$^3$]',
         r'$\psi(x)-\psi(left)$ [V]','E (+x) [kV/cm]','p / NA (P side), n / ND (N side)')):
        ax.set(title=title,xlabel='x - junction [nm]',ylabel=ylabel,xlim=(-400,400))
        ax.axvline(0,color='gray',lw=0.7,ls=':')
        ax.grid(True,alpha=0.4); ax.legend(fontsize=8)
    for f in (0.1,0.5,0.9):
        axes[2,1].axhline(f,color='gray',ls='--',lw=0.7)
        axes[2,1].text(300,f+0.015,f'{f:.0%}',fontsize=8)
    axes[2,1].set_ylim(-0.03,1.08)
    fig.suptitle('Saved extension: 800 intervals, 0.0025 V step — no new simulation')
    fig.tight_layout()
    fig.savefig(profiles_path,dpi=160); plt.close(fig)
    fine=[r for r in rows if r['intervals']==800 and r['refinement']==2]
    v=[r['applied_V'] for r in fine]
    fig,ax=plt.subplots(1,2,figsize=(12,5))
    styles=[('W_reference_nm','Depletion approximation','k--'),('W_Q_nm','Charge integral','o-'),
            ('W_10_nm','10% majority recovery',':'),('W_50_nm','50% majority recovery','s-'),
            ('W_90_nm','90% majority recovery',':')]
    for key,label,style in styles:
        ax[0].plot(v,[r[key] for r in fine],style,label=label)
        if key!='W_reference_nm':
            ax[1].plot(v,[100*(r[key]/r['W_reference_nm']-1) for r in fine],style,label=label)
    for y in (-5,0,5):
        ax[1].axhline(y,color='gray',ls='--',lw=0.7)
    for a in ax:
        a.set_xlabel('V_P - V_N [V]'); a.grid(True,alpha=0.4); a.legend(fontsize=8)
    ax[0].set_ylabel('Width [nm]')
    ax[1].set_ylabel('Signed difference from depletion approximation [%]')
    fig.suptitle('Width-definition comparison — diagnostic thresholds, not new PASS gates')
    fig.tight_layout(); fig.savefig(widths_path,dpi=160); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    args=parser.parse_args()
    raw=Path(args.run).resolve()
    out=Path('data/processed'); figdir=Path('figures')
    paths=[out/'pn_extension_depletion.csv',out/'pn_extension_depletion_summary.json',
           figdir/'pn_extension_profiles.png',figdir/'pn_extension_width_comparison.png']
    if any(p.exists() for p in paths):
        raise FileExistsError('Refusing to overwrite analysis outputs')
    original={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.rglob('*') if p.is_file()}
    config=json.loads((raw/'config.json').read_text())['base_model']
    with (raw/'iv.csv').open(newline='') as h:
        selected=[r for r in csv.DictReader(h) if r['branch']=='forward'
                  and float(r['applied_V']) in (0.0,0.1,0.2,0.3)]
    rows=[]; states=[]
    for saved in selected:
        state=json.loads((raw/saved['state_file']).read_text())
        rows.append(extract(config,state,saved))
        if state['intervals']==800 and int(saved['refinement'])==2:
            states.append(state)
    assert len(rows)==24 and len(states)==4
    assert all(r['W_10_nm']<r['W_50_nm']<r['W_90_nm'] for r in rows)
    out.mkdir(exist_ok=True); figdir.mkdir(exist_ok=True)
    with paths[0].open('x',newline='',encoding='utf-8') as h:
        writer=csv.DictWriter(h,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    figures(states,rows,config,paths[2],paths[3])
    fine=[r for r in rows if r['intervals']==800 and r['refinement']==2]
    differences={}
    for key in ('W_Q_nm','W_50_nm'):
        pairs=[]
        for r in fine:
            medium=next(s for s in rows if s['intervals']==400 and s['refinement']==2 and s['applied_V']==r['applied_V'])
            pairs.append(abs(r[key]-medium[key])/r[key]*100)
        differences[key]=max(pairs)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in original.items())
    summary=dict(source=str(raw),source_sha256=original,original_files_unchanged=len(original),
                 solver_rerun=False,original_pass_gates_modified=False,
                 recovery_fractions=[0.1,0.5,0.9],nominal_diagnostic_fraction=0.5,
                 interpolation='linear in majority carrier / fixed doping, outward unique crossing',
                 max_medium_fine_difference_pct=differences,fine_results=fine,
                 limitations=['No domain enlargement test; no claim of impossibility to reach 5%.',
                              'Recovery widths are diagnostic definitions, not calibrated true boundaries.',
                              'Original charge-equivalent width and acceptance gates are unchanged.'])
    paths[1].write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':
    main()
