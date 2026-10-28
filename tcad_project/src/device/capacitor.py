"""Charge-free 1D dielectric stack, cm/V/F units, ideal Dirichlet electrodes.

API pattern: DEVSIM 2.11 testing/cap2.py (Apache-2.0, DEVSIM LLC).
This project implementation excludes transport, leakage and interface charge.
"""
import math
import uuid


def validate(config):
    positive = ('thickness_nm', 'relative_permittivity', 'epsilon0_F_per_cm',
                'capacitance_rtol', 'field_rtol', 'potential_atol_V',
                'charge_balance_atol_C_per_cm2')
    for key in (*positive, 'left_V', 'right_V'):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{key} must be finite numeric data')
        if key in positive and value <= 0:
            raise ValueError(f'{key} must be positive')
    counts = config['mesh_intervals']
    if not isinstance(counts, list) or not counts or any(type(n) is not int or n < 2 for n in counts):
        raise ValueError('mesh_intervals must contain integers >= 2')
    if counts != sorted(set(counts)):
        raise ValueError('mesh_intervals must be unique and increasing')
    layers = config.get('layer_thicknesses_nm', [config['thickness_nm']])
    if not isinstance(layers, list) or not layers or any(
        isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or t <= 0
        for t in layers
    ):
        raise ValueError('layer_thicknesses_nm must contain positive finite numbers')
    if not math.isclose(sum(layers), config['thickness_nm'], rel_tol=1e-12, abs_tol=0):
        raise ValueError('Layer thickness sum must equal total thickness_nm')
    ks = config.get('layer_relative_permittivities', [config['relative_permittivity']]*len(layers))
    if not isinstance(ks, list) or len(ks) != len(layers) or any(
        isinstance(k, bool) or not isinstance(k, (int, float)) or not math.isfinite(k) or k <= 0 for k in ks
    ):
        raise ValueError('One positive finite relative permittivity per layer is required')
    materials = config.get('layer_materials', ['SiO2']*len(layers))
    if not isinstance(materials, list) or len(materials) != len(layers) or any(
        not isinstance(m, str) or not m.strip() for m in materials
    ):
        raise ValueError('One material label per layer is required')


def layer_mesh(config, intervals):
    """One uniform global mesh; every SiO2 interface must be a mesh node."""
    validate(config)
    if type(intervals) is not int or intervals < 2:
        raise ValueError('intervals must be integer >= 2')
    layers = config.get('layer_thicknesses_nm', [config['thickness_nm']])
    counts = [intervals*t/config['thickness_nm'] for t in layers]
    if any(round(n) < 1 or not math.isclose(n, round(n), abs_tol=1e-10, rel_tol=0) for n in counts):
        raise ValueError('Each interface must align with the total uniform mesh')
    bounds = [0]
    for n in counts:
        bounds.append(bounds[-1]+round(n))
    return bounds


def reference(config):
    validate(config)
    thickness = config['thickness_nm'] * 1e-7
    epsilon = config['relative_permittivity'] * config['epsilon0_F_per_cm']
    delta = config['right_V'] - config['left_V']
    layers = config.get('layer_thicknesses_nm', [config['thickness_nm']])
    ks = config.get('layer_relative_permittivities', [config['relative_permittivity']]*len(layers))
    cap = epsilon / thickness if 'layer_relative_permittivities' not in config else 1 / sum(
        t*1e-7/(k*config['epsilon0_F_per_cm']) for t,k in zip(layers, ks))
    return {'thickness_cm': thickness, 'C_per_area_F_per_cm2': cap,
            'E_V_per_cm': -delta / thickness, 'D_C_per_cm2': -cap*delta}


def analytic_profile(config, x_cm):
    """Piecewise potential and signed field; interface E uses its right side."""
    ref = reference(config)
    layers = config.get('layer_thicknesses_nm', [config['thickness_nm']])
    ks = config.get('layer_relative_permittivities', [config['relative_permittivity']]*len(layers))
    x0, potential = 0.0, config['left_V']
    for i, (t, k) in enumerate(zip(layers, ks)):
        width = t*1e-7
        field = ref['D_C_per_cm2']/(k*config['epsilon0_F_per_cm'])
        if x_cm < x0+width or i == len(layers)-1:
            return potential-field*(x_cm-x0), field
        potential -= field*width
        x0 += width


def simulate(config, intervals):
    import devsim as ds
    ref = reference(config)
    bounds = layer_mesh(config, intervals)
    name = 'cap_' + uuid.uuid4().hex
    regions = ['oxide'] if len(bounds) == 2 else [f'oxide_{i}' for i in range(len(bounds)-1)]
    def tag(i):
        return 'left' if i == 0 else ('right' if i == intervals else f'p{i}')
    ds.create_1d_mesh(mesh=name)
    created = False
    try:
        for i in range(intervals + 1):
            ds.add_1d_mesh_line(mesh=name, pos=ref['thickness_cm'] * i / intervals,
                                ps=ref['thickness_cm'] / intervals, tag=tag(i))
        materials = config.get('layer_materials', ['SiO2']*len(regions))
        ks = config.get('layer_relative_permittivities', [config['relative_permittivity']]*len(regions))
        for region, start, stop, material in zip(regions, bounds[:-1], bounds[1:], materials):
            ds.add_1d_region(mesh=name, material=material, region=region, tag1=tag(start), tag2=tag(stop))
        for j, boundary in enumerate(bounds[1:-1]):
            ds.add_1d_interface(mesh=name, name=f'interface_{j}', tag=tag(boundary))
        for contact in ('left', 'right'):
            ds.add_1d_contact(mesh=name, name=contact, tag=contact, material='metal')
        ds.finalize_mesh(mesh=name)
        ds.create_device(mesh=name, device=name)
        created = True
        models = {'ElectricField': '(Potential@n0-Potential@n1)*EdgeInverseLength',
                  'ElectricField:Potential@n0': 'EdgeInverseLength',
                  'ElectricField:Potential@n1': '-EdgeInverseLength',
                  'Displacement': 'eps*ElectricField',
                  'Displacement:Potential@n0': 'eps*EdgeInverseLength',
                  'Displacement:Potential@n1': '-eps*EdgeInverseLength'}
        for region, k in zip(regions, ks):
            args = {'device': name, 'region': region}
            ds.set_parameter(**args, name='eps', value=k * config['epsilon0_F_per_cm'])
            ds.node_solution(**args, name='Potential')
            ds.edge_from_node_model(**args, node_model='Potential')
            for model, expression in models.items():
                ds.edge_model(**args, name=model, equation=expression)
            ds.equation(**args, name='PotentialEquation', variable_name='Potential', edge_model='Displacement')
        for j in range(len(regions)-1):
            interface = f'interface_{j}'
            for model, expression in [('continuousPotential', 'Potential@r0-Potential@r1'),
                                      ('continuousPotential:Potential@r0', '1'),
                                      ('continuousPotential:Potential@r1', '-1')]:
                ds.interface_model(device=name, interface=interface, name=model, equation=expression)
            ds.interface_equation(device=name, interface=interface, name='PotentialEquation',
                                  interface_model='continuousPotential', type='continuous')
        for contact in ('left', 'right'):
            args = {'device': name, 'region': regions[0] if contact == 'left' else regions[-1]}
            model = contact + '_bc'
            ds.node_model(**args, name=model, equation=f"Potential-({config[contact + '_V']!r})")
            ds.node_model(**args, name=model + ':Potential', equation='1')
            ds.contact_equation(device=name, contact=contact, name='PotentialEquation',
                                node_model=model, edge_charge_model='Displacement')
        solver_info = ds.solve(type='dc', absolute_error=1e-12, relative_error=1e-10,
                               maximum_iterations=30, info=True)
        if not solver_info.get('converged', False):
            raise RuntimeError(f'DC solver failed: {solver_info}')
        regional = []
        for region in regions:
            args = {'device': name, 'region': region}
            nodes = {key: list(ds.get_node_model_values(**args, name=model))
                     for key, model in [('x_cm', 'x'), ('potential_V', 'Potential')]}
            ds.edge_from_node_model(**args, node_model='x')
            edges = {key: list(ds.get_edge_model_values(**args, name=model))
                     for key, model in [('x0_cm', 'x@n0'), ('x1_cm', 'x@n1'),
                                        ('E_edge_V_per_cm', 'ElectricField'), ('D_edge_C_per_cm2', 'Displacement')]}
            regional.append(dict(region=region, nodes=nodes, edges=edges))
        # Keep both interface-side nodes: never hide a discontinuity by averaging.
        nodes = {key: [v for r in regional for v in r['nodes'][key]] for key in regional[0]['nodes']}
        edges = {key: [v for r in regional for v in r['edges'][key]] for key in regional[0]['edges']}
        charges = {c: ds.get_contact_charge(device=name, contact=c, equation='PotentialEquation')
                   for c in ('left', 'right')}
        output = {'nodes': nodes, 'edges': edges, 'charges': charges,
                  'reference': ref, 'solver_info': solver_info}
        if len(regions) > 1:
            output['regions'] = regional
            output['unique_nodes'] = len(set(nodes['x_cm']))
        return output
    finally:
        if created:
            ds.delete_device(device=name)
        ds.delete_mesh(mesh=name)


def assess(config, result):
    ref = reference(config)
    if config['left_V'] == config['right_V']:
        raise ValueError('Q/dV is undefined at zero bias; use Q-V slope extraction')
    nodes, edges, charges = result['nodes'], result['edges'], result['charges']
    values = [v for collection in (nodes, edges, charges) for value in collection.values()
              for v in (value if isinstance(value, list) else [value])]
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError('Empty or non-finite solver output')
    delta = config['right_V'] - config['left_V']
    numeric_c = charges['right'] / delta
    p_error = max(abs(p - (config['left_V'] + delta*x/ref['thickness_cm']))
                  for x, p in zip(nodes['x_cm'], nodes['potential_V']))
    e_error = max(abs(e - ref['E_V_per_cm'] * (1 if b > a else -1)) / abs(ref['E_V_per_cm'])
                  for a, b, e in zip(edges['x0_cm'], edges['x1_cm'], edges['E_edge_V_per_cm']))
    if 'layer_relative_permittivities' in config:
        p_error = max(abs(p-analytic_profile(config, x)[0])
                      for x,p in zip(nodes['x_cm'], nodes['potential_V']))
        e_error = max(abs(e*(1 if b>a else -1)/analytic_profile(config, (a+b)/2)[1]-1)
                      for a,b,e in zip(edges['x0_cm'], edges['x1_cm'], edges['E_edge_V_per_cm']))
    checks = [('potential_max_error_V', p_error, config['potential_atol_V']),
              ('field_max_relative_error', e_error, config['field_rtol']),
              ('capacitance_relative_error', abs(numeric_c/ref['C_per_area_F_per_cm2']-1), config['capacitance_rtol']),
              ('charge_balance_C_per_cm2', abs(charges['left']+charges['right']), config['charge_balance_atol_C_per_cm2'])]
    for i, (left, right) in enumerate(zip(result.get('regions', []), result.get('regions', [])[1:])):
        ln, rn = left['nodes'], right['nodes']
        li = max(range(len(ln['x_cm'])), key=ln['x_cm'].__getitem__)
        ri = min(range(len(rn['x_cm'])), key=rn['x_cm'].__getitem__)
        jump = abs(ln['potential_V'][li]-rn['potential_V'][ri])
        def boundary_d(region, at_right):
            e = region['edges']
            mids = [(a+b)/2 for a,b in zip(e['x0_cm'], e['x1_cm'])]
            k = (max if at_right else min)(range(len(mids)), key=mids.__getitem__)
            return e['D_edge_C_per_cm2'][k]*(1 if e['x1_cm'][k]>e['x0_cm'][k] else -1)
        d_jump = abs(boundary_d(left, True)-boundary_d(right, False))
        checks.extend([(f'interface_{i}_potential_jump_V', jump, config['potential_atol_V']),
                       (f'interface_{i}_D_jump_C_per_cm2', d_jump, config['charge_balance_atol_C_per_cm2'])])
    return numeric_c, [{'check': key, 'error': value, 'limit': limit, 'pass': value < limit}
                       for key, value, limit in checks]
