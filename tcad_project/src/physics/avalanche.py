"""300 K local-field Okuto-Crowell impact ionization, cm/V/A units.

Coefficients: Allpix Squared manual 3.0.1, original Okuto parametrization.
This local |E| driving force is explicit; it is NOT DEVSIM's example's
quasi-Fermi-gradient variant. No temperature extrapolation or BTBT.
"""
import math


def validate_avalanche(parameters, temperature=300.0):
    if parameters['model'] != 'okuto_crowell_local_field_300K':
        raise ValueError('Unsupported impact ionization model')
    if type(parameters['enabled']) is not bool or temperature != 300.0:
        raise ValueError('Boolean enabled and fixed 300 K required')
    for key in ('a_n_per_V', 'a_p_per_V', 'b_n_V_per_cm', 'b_p_V_per_cm',
                'field_regularization_V_per_cm'):
        value = parameters[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'Positive finite {key} required')
    if parameters['field_regularization_V_per_cm'] > 1e-6:
        raise ValueError('Regularizer must not alter resolved physical fields')


def coefficient(field, a, b, regularizer=1e-30):
    """alpha [cm^-1]; zero at E=0, even in signed field."""
    if not all(math.isfinite(v) for v in (field, a, b, regularizer)) or min(a, b, regularizer) <= 0:
        raise ValueError('Finite field and positive parameters required')
    f = abs(field)
    return a*f*math.exp(-(b/(f+regularizer))**2)


def generation(field, jn, jp, charge, parameters):
    validate_avalanche(parameters)
    if not all(math.isfinite(v) for v in (field, jn, jp, charge)) or charge <= 0:
        raise ValueError('Finite inputs and positive charge required')
    if not parameters['enabled']:
        return 0.0
    r = parameters['field_regularization_V_per_cm']
    return (coefficient(field, parameters['a_n_per_V'], parameters['b_n_V_per_cm'], r)*abs(jn)
            + coefficient(field, parameters['a_p_per_V'], parameters['b_p_V_per_cm'], r)*abs(jp))/charge


def interior_generation_integrals(state):
    """Integral G dx in each interior control volume (unit area).

    Exactly the two half-edge volumes used by edge_volume_model; exclude
    contact half-cells to compare currents at first/last edge centers.
    """
    x = state['nodes']['x_cm']
    g = state['edges']['ImpactGeneration_cm3_per_s']
    if len(g) != len(x)-1 or any(b <= a for a, b in zip(x, x[1:])):
        raise ValueError('Ordered line mesh and one generation value per edge required')
    return [(g[i-1]*(x[i]-x[i-1])+g[i]*(x[i+1]-x[i]))/2 for i in range(1, len(x)-1)]


def create_avalanche(device, region, parameters, temperature):
    """Add edge-volume generation without replacing the SRH node source."""
    import devsim as ds
    from devsim.python_packages.model_create import CreateEdgeModelDerivatives
    validate_avalanche(parameters, temperature)
    args = dict(device=device, region=region)
    for key in ('a_n_per_V', 'a_p_per_V', 'b_n_V_per_cm', 'b_p_V_per_cm', 'field_regularization_V_per_cm'):
        ds.set_parameter(**args, name='ii_'+key, value=parameters[key])
    models = [('IIField', 'abs(ElectricField)')]
    for carrier in ('n', 'p'):
        expr = f'ii_a_{carrier}_per_V*IIField*exp(-(ii_b_{carrier}_V_per_cm/(IIField+ii_field_regularization_V_per_cm))^2)'
        models.append(('IIAlpha_'+carrier, expr if parameters['enabled'] else '0'))
    models.extend([
        ('ImpactGeneration', '(IIAlpha_n*abs(ElectronCurrent)+IIAlpha_p*abs(HoleCurrent))/ElectronCharge'),
        ('IIElectronSource', 'ElectronCharge*ImpactGeneration'),
        ('IIHoleSource', '-ElectronCharge*ImpactGeneration')])
    for name, expr in models:
        ds.edge_model(**args, name=name, equation=expr)
        for variable in ('Potential', 'Electrons', 'Holes'):
            CreateEdgeModelDerivatives(device, region, name, expr, variable)
    # Unit-area 1D finite volumes, scoped to this device region.
    ds.edge_model(**args, name='IIHalfEdgeVolume', equation='0.5*EdgeLength')
    for key in ('edge_node0_volume_model', 'edge_node1_volume_model'):
        ds.set_parameter(**args, name=key, value='IIHalfEdgeVolume')
    for carrier, variable, charge in (('Electron', 'Electrons', 'NCharge'), ('Hole', 'Holes', 'PCharge')):
        ds.equation(**args, name=carrier+'ContinuityEquation', variable_name=variable,
                    time_node_model=charge, edge_model=carrier+'Current',
                    node_model=carrier+'Generation', edge_volume_model='II'+carrier+'Source',
                    variable_update='positive')
