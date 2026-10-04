"""Charge-free 1D SiO2 slab, cm/V/F units, ideal Dirichlet electrodes.

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
    if config['left_V'] == config['right_V']:
        raise ValueError('Nonzero voltage difference required for Q/dV validation')
    counts = config['mesh_intervals']
    if not isinstance(counts, list) or not counts or any(type(n) is not int or n < 2 for n in counts):
        raise ValueError('mesh_intervals must contain integers >= 2')
    if counts != sorted(set(counts)):
        raise ValueError('mesh_intervals must be unique and increasing')


def reference(config):
    validate(config)
    thickness = config['thickness_nm'] * 1e-7
    epsilon = config['relative_permittivity'] * config['epsilon0_F_per_cm']
    delta = config['right_V'] - config['left_V']
    return {'thickness_cm': thickness, 'C_per_area_F_per_cm2': epsilon / thickness,
            'E_V_per_cm': -delta / thickness, 'D_C_per_cm2': -epsilon * delta / thickness}


def simulate(config, intervals):
    import devsim as ds
    ref = reference(config)
    if type(intervals) is not int or intervals < 2:
        raise ValueError('intervals must be integer >= 2')
    name = 'cap_' + uuid.uuid4().hex
    region = 'oxide'
    ds.create_1d_mesh(mesh=name)
    created = False
    try:
        for i in range(intervals + 1):
            tag = 'left' if i == 0 else ('right' if i == intervals else f'p{i}')
            ds.add_1d_mesh_line(mesh=name, pos=ref['thickness_cm'] * i / intervals,
                                ps=ref['thickness_cm'] / intervals, tag=tag)
        ds.add_1d_region(mesh=name, material='SiO2', region=region, tag1='left', tag2='right')
        for contact in ('left', 'right'):
            ds.add_1d_contact(mesh=name, name=contact, tag=contact, material='metal')
        ds.finalize_mesh(mesh=name)
        ds.create_device(mesh=name, device=name)
        created = True
        args = {'device': name, 'region': region}
        ds.set_parameter(**args, name='eps', value=config['relative_permittivity'] * config['epsilon0_F_per_cm'])
        ds.node_solution(**args, name='Potential')
        ds.edge_from_node_model(**args, node_model='Potential')
        models = {'ElectricField': '(Potential@n0-Potential@n1)*EdgeInverseLength',
                  'ElectricField:Potential@n0': 'EdgeInverseLength',
                  'ElectricField:Potential@n1': '-EdgeInverseLength',
                  'Displacement': 'eps*ElectricField',
                  'Displacement:Potential@n0': 'eps*EdgeInverseLength',
                  'Displacement:Potential@n1': '-eps*EdgeInverseLength'}
        for model, expression in models.items():
            ds.edge_model(**args, name=model, equation=expression)
        ds.equation(**args, name='PotentialEquation', variable_name='Potential', edge_model='Displacement')
        for contact in ('left', 'right'):
            model = contact + '_bc'
            ds.node_model(**args, name=model, equation=f"Potential-({config[contact + '_V']!r})")
            ds.node_model(**args, name=model + ':Potential', equation='1')
            ds.contact_equation(device=name, contact=contact, name='PotentialEquation',
                                node_model=model, edge_charge_model='Displacement')
        solver_info = ds.solve(type='dc', absolute_error=1e-12, relative_error=1e-10,
                               maximum_iterations=30, info=True)
        if not solver_info.get('converged', False):
            raise RuntimeError(f'DC solver failed: {solver_info}')
        nodes = {key: list(ds.get_node_model_values(**args, name=model))
                 for key, model in [('x_cm', 'x'), ('potential_V', 'Potential')]}
        # Explicit endpoint coordinates avoid assuming edge ordering/orientation.
        ds.edge_from_node_model(**args, node_model='x')
        edges = {key: list(ds.get_edge_model_values(**args, name=model))
                 for key, model in [('x0_cm', 'x@n0'), ('x1_cm', 'x@n1'),
                                    ('E_edge_V_per_cm', 'ElectricField'), ('D_edge_C_per_cm2', 'Displacement')]}
        charges = {c: ds.get_contact_charge(device=name, contact=c, equation='PotentialEquation')
                   for c in ('left', 'right')}
        return {'nodes': nodes, 'edges': edges, 'charges': charges,
                'reference': ref, 'solver_info': solver_info}
    finally:
        if created:
            ds.delete_device(device=name)
        ds.delete_mesh(mesh=name)


def assess(config, result):
    ref = reference(config)
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
    checks = [('potential_max_error_V', p_error, config['potential_atol_V']),
              ('field_max_relative_error', e_error, config['field_rtol']),
              ('capacitance_relative_error', abs(numeric_c/ref['C_per_area_F_per_cm2']-1), config['capacitance_rtol']),
              ('charge_balance_C_per_cm2', abs(charges['left']+charges['right']), config['charge_balance_atol_C_per_cm2'])]
    return numeric_c, [{'check': key, 'error': value, 'limit': limit, 'pass': value < limit}
                       for key, value, limit in checks]
