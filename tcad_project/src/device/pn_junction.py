"""1D abrupt Si PN equilibrium; cm/V/C units, complete ionization.

simulate(): Poisson-Boltzmann equilibrium, SG consistency diagnostics.
simulate_bias_branch(): coupled DC drift-diffusion, optional bulk SRH.
Optional SRH and impact-ionization coupling; no BTBT.
Uses DEVSIM's Apache-2.0 simple_physics potential/contact API (DEVSIM LLC);
all physical parameters are explicitly supplied rather than library defaults.
"""
import math
import uuid


def validate(config):
    positive = (
        'temperature_K', 'p_length_nm', 'n_length_nm', 'acceptors_cm3',
        'donors_cm3', 'intrinsic_density_cm3', 'relative_permittivity',
        'epsilon0_F_per_cm', 'electron_charge_C', 'boltzmann_J_per_K',
        'electron_mobility_cm2_per_Vs', 'hole_mobility_cm2_per_Vs',
        'solver_absolute_error', 'solver_relative_error', 'vbi_rtol',
        'depletion_width_rtol', 'mass_action_rtol',
        'equilibrium_current_atol_A_per_cm2', 'gauss_atol_C_per_cm2',
        'mesh_metric_rtol', 'domain_metric_rtol', 'domain_check_scale',
    )
    for key in positive:
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'{key}: positive finite number required')
    if config['model'] != 'equilibrium_poisson_boltzmann':
        raise ValueError('Only equilibrium_poisson_boltzmann is implemented')
    if config['material'] != 'Silicon':
        raise ValueError('This baseline is Silicon only')
    for key in ('left_bias_V', 'right_bias_V'):
        if isinstance(config[key], bool) or not isinstance(config[key], (int, float)) or config[key] != 0:
            raise ValueError('Equilibrium runner requires both applied biases to be zero')
    if min(config['acceptors_cm3'], config['donors_cm3']) < 100*config['intrinsic_density_cm3']:
        raise ValueError('Depletion approximation baseline requires doping >= 100 ni')
    counts = config['mesh_intervals']
    if not isinstance(counts, list) or len(counts) < 3 or any(type(n) is not int or n < 20 for n in counts):
        raise ValueError('Use at least three integer meshes >=20 intervals')
    if counts != sorted(set(counts)):
        raise ValueError('Meshes must be unique and increasing')
    fraction = config['p_length_nm']/(config['p_length_nm']+config['n_length_nm'])
    if any(not math.isclose(n*fraction, round(n*fraction), abs_tol=1e-10, rel_tol=0) for n in counts):
        raise ValueError('Junction must align with a mesh node')
    if type(config['solver_maximum_iterations']) is not int or config['solver_maximum_iterations'] < 1:
        raise ValueError('Positive integer iteration limit required')
    scale = config['domain_check_scale']
    if scale <= 1 or not math.isclose(scale*counts[-1], round(scale*counts[-1]), abs_tol=1e-10):
        raise ValueError('Domain scale >1 must preserve the finest mesh spacing')
    if not math.isclose(scale*counts[-1]*fraction, round(scale*counts[-1]*fraction), abs_tol=1e-10):
        raise ValueError('Expanded domain junction must align with mesh')


def reference(config):
    validate(config)
    vt = config['boltzmann_J_per_K']*config['temperature_K']/config['electron_charge_C']
    ni, na, nd = config['intrinsic_density_cm3'], config['acceptors_cm3'], config['donors_cm3']
    eps = config['relative_permittivity']*config['epsilon0_F_per_cm']
    vbi = vt*math.log(na*nd/ni**2)
    width = math.sqrt(2*eps*vbi/config['electron_charge_C']*(1/na+1/nd))
    return dict(thermal_voltage_V=vt, epsilon_F_per_cm=eps, Vbi_V=vbi,
                xp_cm=width*nd/(na+nd), xn_cm=width*na/(na+nd), W_cm=width,
                E_peak_V_per_cm=-2*vbi/width,
                left_potential_V=-vt*math.asinh(na/(2*ni)),
                right_potential_V=vt*math.asinh(nd/(2*ni)))


def bernoulli(x):
    if abs(x) < 1e-5:
        return 1-x/2+x*x/12-x**4/720
    if x > 50:
        return x*math.exp(-x)/(1-math.exp(-x))
    return x/math.expm1(x)


def equilibrium_currents(config, x, potential, electrons, holes):
    """Scharfetter-Gummel edge currents in +x; not a solved I-V result."""
    vt = config['boltzmann_J_per_K']*config['temperature_K']/config['electron_charge_C']
    jn, jp = [], []
    for i in range(len(x)-1):
        delta = (potential[i+1]-potential[i])/vt
        bp, bm = bernoulli(delta), bernoulli(-delta)
        factor = config['electron_charge_C']*vt/(x[i+1]-x[i])
        jn.append(factor*config['electron_mobility_cm2_per_Vs']*(electrons[i+1]*bp-electrons[i]*bm))
        jp.append(factor*config['hole_mobility_cm2_per_Vs']*(holes[i]*bp-holes[i+1]*bm))
    return jn, jp


def simulate(config, intervals):
    import devsim as ds
    from devsim.python_packages.simple_physics import (
        CreateSiliconPotentialOnly, CreateSiliconPotentialOnlyContact,
    )
    ref = reference(config)
    if type(intervals) is not int or intervals < 20:
        raise ValueError('Integer intervals >=20 required')
    total = (config['p_length_nm']+config['n_length_nm'])*1e-7
    junction = config['p_length_nm']*1e-7
    if not math.isclose(intervals*junction/total, round(intervals*junction/total), abs_tol=1e-10):
        raise ValueError('Junction must align with mesh')
    name, region = 'pn_'+uuid.uuid4().hex, 'silicon'
    ds.create_1d_mesh(mesh=name)
    created = False
    try:
        for i in range(intervals+1):
            tag = 'left' if i == 0 else 'right' if i == intervals else f'x{i}'
            ds.add_1d_mesh_line(mesh=name, pos=total*i/intervals, ps=total/intervals, tag=tag)
        ds.add_1d_region(mesh=name, material='Silicon', region=region, tag1='left', tag2='right')
        for contact in ('left', 'right'):
            ds.add_1d_contact(mesh=name, name=contact, tag=contact, material='metal')
        ds.finalize_mesh(mesh=name)
        ds.create_device(mesh=name, device=name)
        created = True
        args = dict(device=name, region=region)
        parameters = dict(Permittivity=ref['epsilon_F_per_cm'], ElectronCharge=config['electron_charge_C'],
                          n_i=config['intrinsic_density_cm3'], V_t=ref['thermal_voltage_V'])
        for key,value in parameters.items():
            ds.set_parameter(**args, name=key, value=value)
        x = list(ds.get_node_model_values(**args, name='x'))
        # Cell-volume average at the abrupt junction node; no artificial intrinsic slab.
        tolerance = total*1e-12
        na = [config['acceptors_cm3']*(1 if v<junction-tolerance else 0 if v>junction+tolerance else 0.5) for v in x]
        nd = [config['donors_cm3']*(0 if v<junction-tolerance else 1 if v>junction+tolerance else 0.5) for v in x]
        ds.node_solution(**args, name='NetDoping')
        ds.set_node_values(**args, name='NetDoping', values=[d-a for d,a in zip(nd,na)])
        CreateSiliconPotentialOnly(name, region)
        # Gauge shift avoids a near-zero unknown in DEVSIM's relative-update norm.
        # Shift BOTH Boltzmann reference and contacts: fields/carriers/bias unchanged.
        gauge = ref['Vbi_V']+ref['thermal_voltage_V']
        ds.set_parameter(**args, name='PotentialGauge', value=gauge)
        for model, expression, derivative in (
            ('IntrinsicElectrons','n_i*exp((Potential-PotentialGauge)/V_t)','IntrinsicElectrons/V_t'),
            ('IntrinsicHoles','n_i^2/IntrinsicElectrons','-IntrinsicHoles/V_t'),
            ('IntrinsicCharge','kahan3(IntrinsicHoles, -IntrinsicElectrons, NetDoping)','-(IntrinsicHoles+IntrinsicElectrons)/V_t'),
            ('PotentialIntrinsicCharge','-ElectronCharge*IntrinsicCharge','ElectronCharge*(IntrinsicHoles+IntrinsicElectrons)/V_t'),
        ):
            ds.node_model(**args,name=model,equation=expression)
            ds.node_model(**args,name=model+':Potential',equation=derivative)
        # Smooth linear initial guess; no analytic depletion profile imposed on the solve.
        ds.set_node_values(**args, name='Potential', values=[
            gauge+ref['left_potential_V']+(ref['right_potential_V']-ref['left_potential_V'])*v/total for v in x])
        for contact in ('left', 'right'):
            ds.set_parameter(device=name, name=contact+'_bias', value=gauge)
            CreateSiliconPotentialOnlyContact(name, region, contact)
        info = ds.solve(type='dc', absolute_error=config['solver_absolute_error'],
                        relative_error=config['solver_relative_error'],
                        maximum_iterations=config['solver_maximum_iterations'], info=True)
        if not info.get('converged', False):
            raise RuntimeError('PN equilibrium solve did not converge')
        potential = [v-gauge for v in ds.get_node_model_values(**args, name='Potential')]
        n = list(ds.get_node_model_values(**args, name='IntrinsicElectrons'))
        p = list(ds.get_node_model_values(**args, name='IntrinsicHoles'))
        order = sorted(range(len(x)), key=x.__getitem__)
        x, potential, n, p, na, nd = [[v[i] for i in order] for v in (x,potential,n,p,na,nd)]
        vt, ni, q = ref['thermal_voltage_V'], config['intrinsic_density_cm3'], config['electron_charge_C']
        field = [-(b-a)/(xr-xl) for a,b,xl,xr in zip(potential,potential[1:],x,x[1:])]
        jn,jp = equilibrium_currents(config,x,potential,n,p)
        nodes = dict(x_cm=x, Potential_V=potential, Electrons_cm3=n, Holes_cm3=p,
                     Acceptors_cm3=na, Donors_cm3=nd, NetDoping_cm3=[d-a for d,a in zip(nd,na)],
                     ChargeDensity_C_per_cm3=[q*(h-e+d-a) for h,e,d,a in zip(p,n,nd,na)],
                     ElectronQuasiFermi_V=[v-vt*math.log(e/ni) for v,e in zip(potential,n)],
                     HoleQuasiFermi_V=[v+vt*math.log(h/ni) for v,h in zip(potential,p)])
        edges = dict(x_cm=[(a+b)/2 for a,b in zip(x,x[1:])], ElectricField_V_per_cm=field,
                     ElectronCurrent_A_per_cm2=jn, HoleCurrent_A_per_cm2=jp,
                     TotalCurrent_A_per_cm2=[a+b for a,b in zip(jn,jp)])
        if not all(math.isfinite(v) for table in (nodes,edges) for values in table.values() for v in values):
            raise ValueError('Non-finite output')
        return dict(model=config['model'], potential_gauge_offset_V=gauge, intervals=intervals, junction_cm=junction, nodes=nodes, edges=edges,
                    reference=ref, solver_info=info,
                    diagnostic_note='Carriers obey equilibrium Boltzmann relations; SG currents and quasi-Fermi levels are consistency checks, not independent continuity solves.')
    finally:
        if created:
            ds.delete_device(device=name)
        ds.delete_mesh(mesh=name)


def assess(config, state):
    """Legacy averaged-node assessment, retained for run_001 reproducibility."""
    ref = reference(config)
    n, e = state['nodes'], state['edges']
    x, rho, junction = n['x_cm'], n['ChargeDensity_C_per_cm3'], state['junction_cm']
    # Charge-equivalent depletion width: integrate signed charge on each side.
    # This is not a threshold-defined carrier-depletion boundary.
    left = right = 0.0
    for a,b,ra,rb in zip(x,x[1:],rho,rho[1:]):
        area = (b-a)*(ra+rb)/2
        if (a+b)/2 < junction:
            left += area
        else:
            right += area
    q = config['electron_charge_C']
    xp, xn = abs(left)/(q*config['acceptors_cm3']), abs(right)/(q*config['donors_cm3'])
    vbi = n['Potential_V'][-1]-n['Potential_V'][0]
    width = xp+xn
    peak = max(abs(v) for v in e['ElectricField_V_per_cm'])
    # Interior control volumes correspond to first/last edge displacement difference.
    charge = sum(rho[i]*(x[i+1]-x[i-1])/2 for i in range(1,len(x)-1))
    gauss = abs(ref['epsilon_F_per_cm']*(e['ElectricField_V_per_cm'][-1]-e['ElectricField_V_per_cm'][0])-charge)
    items = [
        ('Vbi_relative_error',abs(vbi/ref['Vbi_V']-1),config['vbi_rtol']),
        ('charge_equivalent_W_relative_error',abs(width/ref['W_cm']-1),config['depletion_width_rtol']),
        ('mass_action_relative_error',max(abs(a*b/config['intrinsic_density_cm3']**2-1) for a,b in zip(n['Electrons_cm3'],n['Holes_cm3'])),config['mass_action_rtol']),
        ('electron_current_max_A_per_cm2',max(abs(v) for v in e['ElectronCurrent_A_per_cm2']),config['equilibrium_current_atol_A_per_cm2']),
        ('hole_current_max_A_per_cm2',max(abs(v) for v in e['HoleCurrent_A_per_cm2']),config['equilibrium_current_atol_A_per_cm2']),
        ('total_current_max_A_per_cm2',max(abs(v) for v in e['TotalCurrent_A_per_cm2']),config['equilibrium_current_atol_A_per_cm2']),
        ('gauss_residual_C_per_cm2',gauss,config['gauss_atol_C_per_cm2']),
    ]
    metrics = dict(intervals=state['intervals'], Vbi_V=vbi, charge_equivalent_xp_cm=xp,
                   charge_equivalent_xn_cm=xn, charge_equivalent_W_cm=width,
                   peak_abs_E_V_per_cm=peak, converged=state['solver_info']['converged'])
    return metrics, [dict(check=key,error=value,limit=limit,passed=math.isfinite(value) and value<limit)
                     for key,value,limit in items]


def interface_side_charges(config, state):
    """Integrate each side with its own abrupt-junction limit; do not mutate state.

    Node doping at the interface is a control-volume average for the solver,
    not either material-side limit for piecewise trapezoidal integration.
    Carriers remain continuous and are taken from the solved interface node.
    """
    nodes = state['nodes']
    x, rho = nodes['x_cm'], nodes['ChargeDensity_C_per_cm3']
    junction = state['junction_cm']
    matches = [i for i,v in enumerate(x) if math.isclose(v,junction,rel_tol=0,abs_tol=(x[-1]-x[0])*1e-12)]
    if len(matches) != 1 or matches[0] in (0,len(x)-1):
        raise ValueError('An interior junction node is required for sided integration')
    if any(b <= a for a,b in zip(x,x[1:])):
        raise ValueError('Coordinates must be strictly increasing')
    index = matches[0]
    q = config['electron_charge_C']
    mobile = nodes['Holes_cm3'][index]-nodes['Electrons_cm3'][index]
    rho_left = q*(mobile-config['acceptors_cm3'])
    rho_right = q*(mobile+config['donors_cm3'])
    left = right = 0.0
    for i,(a,b) in enumerate(zip(x,x[1:])):
        ra, rb = rho[i], rho[i+1]
        if i < index:
            if i+1 == index:
                rb = rho_left
            left += (b-a)*(ra+rb)/2
        else:
            if i == index:
                ra = rho_right
            right += (b-a)*(ra+rb)/2
    return left, right


def assess_interface(config, state):
    """Interface-sided charge width; all other legacy checks and limits unchanged."""
    metrics, checks = assess(config,state)
    left, right = interface_side_charges(config,state)
    q = config['electron_charge_C']
    xp = abs(left)/(q*config['acceptors_cm3'])
    xn = abs(right)/(q*config['donors_cm3'])
    metrics.update(charge_equivalent_xp_cm=xp,charge_equivalent_xn_cm=xn,
                   charge_equivalent_W_cm=xp+xn)
    error = abs((xp+xn)/reference(config)['W_cm']-1)
    for row in checks:
        if row['check'] == 'charge_equivalent_W_relative_error':
            row.update(error=error,passed=math.isfinite(error) and error<row['limit'])
    return metrics, checks


def bias_reference(config, applied_V):
    """Depletion approximation only: applied_V = V_P - V_N."""
    ref = reference(config)
    barrier = ref['Vbi_V']-applied_V
    if not math.isfinite(applied_V) or barrier <= 0:
        raise ValueError('Depletion reference requires finite bias below Vbi')
    width = ref['W_cm']*math.sqrt(barrier/ref['Vbi_V'])
    return dict(barrier_V=barrier, W_cm=width, E_peak_V_per_cm=-2*barrier/width)


def bias_grid(segments, refinement=1):
    """Inclusive contiguous segments from zero; no duplicate joining points."""
    if type(refinement) is not int or refinement < 1 or not segments:
        raise ValueError('Positive integer refinement and segments required')
    values = []
    direction = None
    for start,stop,step in segments:
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
               for v in (start,stop,step)) or step == 0 or (stop-start)*step <= 0:
            raise ValueError('Invalid bias segment')
        count = (stop-start)/step
        if not math.isclose(count,round(count),rel_tol=0,abs_tol=1e-9):
            raise ValueError('Step must exactly divide its segment')
        if (not values and start != 0) or (values and not math.isclose(start,values[-1],abs_tol=1e-12)):
            raise ValueError('Segments must start at zero and join continuously')
        sign = 1 if step > 0 else -1
        if direction is not None and sign != direction:
            raise ValueError('Each branch must be monotonic')
        direction = sign
        count = round(count)*refinement
        part = [round(start+(stop-start)*i/count,12) for i in range(count+1)]
        values.extend(part if not values else part[1:])
    return values


def validate_bias(config, sweep, stage):
    validate(config)  # unchanged equilibrium configuration is the initialization
    if sweep['model'] not in ('drift_diffusion_no_recombination', 'drift_diffusion_srh', 'drift_diffusion_avalanche') or sweep['assessment'] != 'interface_sided_v1':
        raise ValueError('Unsupported transport or extraction model')
    if sweep['model'] in ('drift_diffusion_srh', 'drift_diffusion_avalanche'):
        from src.physics.srh import validate_srh
        validate_srh(sweep['srh'])
    if sweep['model'] == 'drift_diffusion_avalanche':
        from src.physics.avalanche import validate_avalanche
        validate_avalanche(sweep['avalanche'], config['temperature_K'])
    elif sweep['model'] != 'drift_diffusion_srh' and sweep.get('srh', {}).get('enabled', False):
        raise ValueError('Enabled SRH requires drift_diffusion_srh model')
    if sweep['step_refinements'] != [1,2]:
        raise ValueError('Baseline and half-step comparison [1,2] required')
    for key in ('dd_absolute_error','dd_relative_error','minimum_continuation_step_V',
                'current_atol_A_per_cm2','current_conservation_rtol','comparison_rtol',
                'potential_atol_V','width_depletion_rtol','width_gate_max_forward_V'):
        value = sweep[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'{key} must be finite and positive')
    for key in ('dd_maximum_iterations','maximum_bisection_depth'):
        if type(sweep[key]) is not int or sweep[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    condition = sweep['stages'][stage]
    reverse = bias_grid(condition['reverse_segments'])
    avalanche = sweep['model'] == 'drift_diffusion_avalanche'
    forward = [] if avalanche else bias_grid(condition['forward_segments'])
    if len(reverse)<11 or reverse[-1]>=0 or (not avalanche and (len(forward)<11 or forward[-1]<=0)):
        raise ValueError('Each branch needs at least 11 points including zero')
    for voltage in reverse+forward:
        ref = bias_reference(config,voltage)
        # Contacts must remain outside estimated depletion boundaries.
        base = reference(config)
        for side in ('p','n'):
            fraction = base['x'+side+'_cm']/base['W_cm']
            if ref['W_cm']*fraction >= config[side+'_length_nm']*1e-7:
                raise ValueError('Estimated depletion region reaches a contact')
    if not set(condition['vtk_biases_V']).issubset(set(reverse+forward)):
        raise ValueError('VTK biases must be requested grid points')


def assess_bias(config, sweep, state):
    """No equilibrium np=ni^2 or J=0 assertion at nonzero bias."""
    voltage = state['applied_V']
    ref = bias_reference(config,voltage)
    left,right = interface_side_charges(config,state)
    q = config['electron_charge_C']
    width = abs(left)/(q*config['acceptors_cm3'])+abs(right)/(q*config['donors_cm3'])
    nodes,edges = state['nodes'],state['edges']
    currents = edges['TotalCurrent_A_per_cm2']
    mean = math.fsum(currents)/len(currents)
    terminal = state['terminal_current_raw_unit_area']
    total_left = sum(terminal['left'].values())
    total_right = sum(terminal['right'].values())
    atol,rtol = sweep['current_atol_A_per_cm2'],sweep['current_conservation_rtol']
    contact_residual = abs(total_left+total_right)
    current_scale = max(abs(v) for v in currents)
    variation = max(currents)-min(currents)
    expected = reference(config)['right_potential_V']-reference(config)['left_potential_V']-voltage
    boundary_error = abs(nodes['Potential_V'][-1]-nodes['Potential_V'][0]-expected)
    x,rho = nodes['x_cm'],nodes['ChargeDensity_C_per_cm3']
    gauss = abs(reference(config)['epsilon_F_per_cm']*(edges['ElectricField_V_per_cm'][-1]-edges['ElectricField_V_per_cm'][0])
                -math.fsum(rho[i]*(x[i+1]-x[i-1])/2 for i in range(1,len(x)-1)))
    width_error = abs(width/ref['W_cm']-1)
    checks = []
    def check(name,error,limit):
        checks.append(dict(check=name,error=error,limit=limit,passed=math.isfinite(error) and error<=limit))
    check('terminal_current_balance',contact_residual,atol+rtol*(abs(total_left)+abs(total_right)))
    check('edge_total_current_uniformity',variation,atol+rtol*current_scale)
    # Unit cross section: contact current magnitude must match 1D edge J.
    check('terminal_edge_magnitude',max(abs(abs(total_left)-abs(mean)),abs(abs(total_right)-abs(mean))),atol+rtol*current_scale)
    check('boundary_potential',boundary_error,sweep['potential_atol_V'])
    check('discrete_gauss',gauss,config['gauss_atol_C_per_cm2'])
    if voltage <= sweep['width_gate_max_forward_V']:
        check('depletion_width_approximation',width_error,sweep['width_depletion_rtol'])
    if voltage == 0:
        check('zero_bias_current',current_scale,atol)
    elif abs(mean)>atol:
        check('forward_reverse_current_sign',0 if mean*voltage>0 else 1,0)
    metric = dict(applied_V=voltage,intervals=state['intervals'],J_A_per_cm2=mean,
                  terminal_left_raw=total_left,terminal_right_raw=total_right,
                  terminal_balance_A_per_cm2=contact_residual,current_span_A_per_cm2=variation,
                  charge_equivalent_W_cm=width,depletion_reference_W_cm=ref['W_cm'],
                  width_relative_difference=width_error,
                  width_comparison_gated=voltage<=sweep['width_gate_max_forward_V'],
                  peak_abs_E_V_per_cm=max(abs(v) for v in edges['ElectricField_V_per_cm']),
                  current_resolved=abs(mean)>atol,converged=state['solver_info']['converged'])
    return metric,checks


def simulate_bias_branch(config, sweep, intervals, voltages, attempt_log):
    """Scope DEVSIM extended precision to this branch and restore caller settings."""
    import devsim as ds
    enabled=sweep.get('extended_precision',False)
    if type(enabled) is not bool:
        raise ValueError('extended_precision must be boolean')
    keys=('extended_solver','extended_model','extended_equation')
    saved={}
    for key in keys:
        try:
            saved[key]=ds.get_parameter(name=key)
        except ds.error:
            saved[key]=False  # DEVSIM's unset default is double precision.
    try:
        for key in keys:
            ds.set_parameter(name=key,value=enabled)
        yield from _simulate_bias_branch(config,sweep,intervals,voltages,attempt_log)
    finally:
        for key,value in saved.items():
            ds.set_parameter(name=key,value=value)


def _simulate_bias_branch(config, sweep, intervals, voltages, attempt_log):
    """Yield requested DC points. Restore converged state before bounded retries.

    Uses installed DEVSIM simple_physics/simple_dd (DEVSIM LLC, Apache-2.0).
    Avoids implicit SRH defaults in CreateSiliconDriftDiffusion; SRH is opt-in.
    One fresh zero-bias initialization per direction/mesh/step grid.
    Optional impact-ionization coupling is opt-in; prior SRH behavior is retained.
    """
    import devsim as ds
    from devsim.python_packages.model_create import CreateSolution
    from devsim.python_packages.simple_physics import (
        CreateSiliconPotentialOnly, CreateSiliconPotentialOnlyContact,
        CreatePE, CreateECE, CreateHCE, CreateSiliconDriftDiffusionAtContact,
    )
    if not voltages or voltages[0] != 0:
        raise ValueError('Each branch starts at zero')
    seed = simulate(config,intervals)
    ref = reference(config)
    gauge = seed['potential_gauge_offset_V']
    name,region = 'pn_dd_'+uuid.uuid4().hex,'silicon'
    args = dict(device=name,region=region)
    created = False
    ds.create_1d_mesh(mesh=name)
    try:
        xs = seed['nodes']['x_cm']
        for i,x in enumerate(xs):
            tag = 'left' if i==0 else 'right' if i==len(xs)-1 else f'x{i}'
            ds.add_1d_mesh_line(mesh=name,pos=x,ps=xs[1]-xs[0],tag=tag)
        ds.add_1d_region(mesh=name,region=region,material='Silicon',tag1='left',tag2='right')
        for contact in ('left','right'):
            ds.add_1d_contact(mesh=name,name=contact,material='metal',tag=contact)
        ds.finalize_mesh(mesh=name)
        ds.create_device(mesh=name,device=name)
        created = True
        for key,value in dict(Permittivity=ref['epsilon_F_per_cm'],ElectronCharge=config['electron_charge_C'],
                              n_i=config['intrinsic_density_cm3'],V_t=ref['thermal_voltage_V'],
                              mu_n=config['electron_mobility_cm2_per_Vs'],mu_p=config['hole_mobility_cm2_per_Vs']).items():
            ds.set_parameter(**args,name=key,value=value)
        # Map saved coordinates to the actual node order instead of assuming ordering.
        actual_x = list(ds.get_node_model_values(**args,name='x'))
        indices = [min(range(len(xs)),key=lambda i:abs(xs[i]-x)) for x in actual_x]
        if len(set(indices))!=len(xs) or any(abs(xs[i]-x)>1e-14 for i,x in zip(indices,actual_x)):
            raise ValueError('Seed and DD mesh differ')
        CreateSolution(name,region,'NetDoping')
        ds.set_node_values(**args,name='NetDoping',values=[seed['nodes']['NetDoping_cm3'][i] for i in indices])
        CreateSiliconPotentialOnly(name,region)  # field/flux only; replaced before solve
        for solution,values in (
            ('Potential',[v+gauge for v in seed['nodes']['Potential_V']]),
            ('Electrons',seed['nodes']['Electrons_cm3']),('Holes',seed['nodes']['Holes_cm3'])):
            if solution!='Potential':
                CreateSolution(name,region,solution)
            ds.set_node_values(**args,name=solution,values=[values[i] for i in indices])
        CreatePE(name,region)
        for model in ('ElectronGeneration','HoleGeneration'):
            ds.node_model(**args,name=model,equation='0')
            for variable in ('Potential','Electrons','Holes'):
                ds.node_model(**args,name=model+':'+variable,equation='0')
        if 'srh' in sweep:
            from src.physics.srh import create_srh
            create_srh(name, region, sweep['srh'])
        CreateECE(name,region,'mu_n')
        CreateHCE(name,region,'mu_p')
        if 'avalanche' in sweep:
            from src.physics.avalanche import create_avalanche
            create_avalanche(name, region, sweep['avalanche'], config['temperature_K'])
        for contact in ('left','right'):
            ds.set_parameter(device=name,name=contact+'_bias',value=gauge)
            CreateSiliconPotentialOnlyContact(name,region,contact)
            CreateSiliconDriftDiffusionAtContact(name,region,contact)
        def solve(voltage):
            ds.set_parameter(device=name,name='left_bias',value=gauge+voltage)
            info = ds.solve(type='dc',absolute_error=sweep['dd_absolute_error'],
                            relative_error=sweep['dd_relative_error'],
                            maximum_iterations=sweep['dd_maximum_iterations'],info=True)
            if not info.get('converged',False):
                raise RuntimeError('DD solve not converged')
            return info
        solutions = ('Potential','Electrons','Holes')
        def advance(previous,target,depth=0):
            saved = {s:list(ds.get_node_model_values(**args,name=s)) for s in solutions}
            try:
                info = solve(target)
                attempt_log(dict(from_V=previous,to_V=target,depth=depth,converged=True,solver_info=info))
                return info
            except (ds.error,RuntimeError) as exc:
                attempt_log(dict(from_V=previous,to_V=target,depth=depth,converged=False,error=str(exc)))
                for s,values in saved.items():
                    ds.set_node_values(**args,name=s,values=values)
                ds.set_parameter(device=name,name='left_bias',value=gauge+previous)
                if depth>=sweep['maximum_bisection_depth'] or abs(target-previous)/2<sweep['minimum_continuation_step_V']:
                    raise RuntimeError(f'Continuation exhausted at {target} V') from exc
                middle=(previous+target)/2
                advance(previous,middle,depth+1)
                return advance(middle,target,depth+1)
        ds.edge_from_node_model(**args,node_model='x')
        previous=0.0
        for voltage in voltages:
            info=advance(previous,voltage)
            order=sorted(range(len(actual_x)),key=actual_x.__getitem__)
            phi,n,p = [[ds.get_node_model_values(**args,name=s)[i] for i in order] for s in solutions]
            phi=[v-gauge for v in phi]
            if any(not math.isfinite(v) or v<=0 for v in n+p):
                raise ValueError('Nonpositive/nonfinite DD carrier density')
            nodes=dict(seed['nodes'])
            nodes.update(Potential_V=phi,Electrons_cm3=n,Holes_cm3=p,
                         ChargeDensity_C_per_cm3=[config['electron_charge_C']*(h-e+d-a) for h,e,d,a in zip(p,n,nodes['Donors_cm3'],nodes['Acceptors_cm3'])],
                         ElectronQuasiFermi_V=[v-ref['thermal_voltage_V']*math.log(e/config['intrinsic_density_cm3']) for v,e in zip(phi,n)],
                         HoleQuasiFermi_V=[v+ref['thermal_voltage_V']*math.log(h/config['intrinsic_density_cm3']) for v,h in zip(phi,p)])
            x0=list(ds.get_edge_model_values(**args,name='x@n0'))
            if 'srh' in sweep:
                nodes['SRHNetRate_cm3_per_s'] = [ds.get_node_model_values(**args,name='SRHNetRate')[i] for i in order]
                nodes['ControlVolume_cm'] = [ds.get_node_model_values(**args,name='NodeVolume')[i] for i in order]
            x1=list(ds.get_edge_model_values(**args,name='x@n1'))
            eo=sorted(range(len(x0)),key=lambda i:(x0[i]+x1[i])/2)
            fields=[]
            for model in ('ElectricField','ElectronCurrent','HoleCurrent'):
                values=ds.get_edge_model_values(**args,name=model)
                fields.append([values[i]*(1 if x1[i]>x0[i] else -1) for i in eo])
            field,jn,jp=fields
            edges=dict(x_cm=[(x0[i]+x1[i])/2 for i in eo],ElectricField_V_per_cm=field,
                       ElectronCurrent_A_per_cm2=jn,HoleCurrent_A_per_cm2=jp,
                       TotalCurrent_A_per_cm2=[a+b for a,b in zip(jn,jp)])
            if 'avalanche' in sweep:
                for model, key in (('ImpactGeneration','ImpactGeneration_cm3_per_s'),
                                   ('IIAlpha_n','IonizationAlphaN_per_cm'), ('IIAlpha_p','IonizationAlphaP_per_cm')):
                    values = ds.get_edge_model_values(**args, name=model)
                    edges[key] = [values[i] for i in eo]
            terminal={contact:{carrier:ds.get_contact_current(device=name,contact=contact,equation=carrier+'ContinuityEquation')
                               for carrier in ('Electron','Hole')} for contact in ('left','right')}
            if not all(math.isfinite(v) for table in (nodes,edges) for values in table.values() for v in values):
                raise ValueError('Nonfinite DD field output')
            yield dict(model=sweep['model'],applied_V=voltage,intervals=intervals,junction_cm=seed['junction_cm'],
                       nodes=nodes,edges=edges,solver_info=info,reference=bias_reference(config,voltage),
                       terminal_current_raw_unit_area=terminal,potential_gauge_offset_V=gauge,
                       diagnostic_note=('Coupled DC bulk SRH; positive U=recombination; unit cross section.'
                                        if sweep.get('srh', {}).get('enabled', False) else
                                        'Coupled DC continuity, R=G=0. Contact raw sign must be checked against +x edge J; unit cross section.'))
            previous=voltage
    finally:
        if created:
            ds.delete_device(device=name)
        ds.delete_mesh(mesh=name)
