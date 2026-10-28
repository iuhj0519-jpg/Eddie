"""Single-level bulk SRH, positive U = recombination, negative U = generation.

Constant lifetimes, nondegenerate statistics; no trap charge, tunneling or II.
DEVSIM source sign convention follows its Apache-2.0 simple_physics.CreateSRH.
"""
import math


def validate_srh(parameters):
    if type(parameters['enabled']) is not bool:
        raise ValueError('SRH enabled must be boolean')
    for key in ('tau_n_s', 'tau_p_s'):
        value = parameters[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'{key} must be finite and positive')
    energy = parameters['trap_energy_minus_intrinsic_eV']
    if isinstance(energy, bool) or not isinstance(energy, (int, float)) or not math.isfinite(energy):
        raise ValueError('Finite trap energy relative to intrinsic level required')
    if energy != 0:
        raise ValueError('This first experiment fixes Et = Ei; energy sweep is not configured')


def srh_rate(n, p, ni, parameters):
    """Pure reference calculation [cm^-3 s^-1]; not a substitute for DD solve."""
    validate_srh(parameters)
    if any(not math.isfinite(v) or v <= 0 for v in (n, p, ni)):
        raise ValueError('Positive finite carrier densities required')
    if not parameters['enabled']:
        return 0.0
    return (n*p-ni*ni)/(parameters['tau_p_s']*(n+ni)+parameters['tau_n_s']*(p+ni))


def create_srh(device, region, parameters):
    """Install SRH sources AND analytic Jacobians before continuity equations."""
    import devsim as ds
    from devsim.python_packages.model_create import CreateNodeModelDerivative
    validate_srh(parameters)
    args = dict(device=device, region=region)
    for key, value in (('srh_tau_n', parameters['tau_n_s']), ('srh_tau_p', parameters['tau_p_s'])):
        ds.set_parameter(**args, name=key, value=value)
    rate = '(Electrons*Holes-n_i^2)/(srh_tau_p*(Electrons+n_i)+srh_tau_n*(Holes+n_i))'
    if not parameters['enabled']:
        rate = '0'
    for name, expression in (('SRHNetRate', rate),
                             ('ElectronGeneration', '-ElectronCharge*SRHNetRate'),
                             ('HoleGeneration', 'ElectronCharge*SRHNetRate')):
        ds.node_model(**args, name=name, equation=expression)
        for variable in ('Electrons', 'Holes'):
            CreateNodeModelDerivative(device, region, name, expression, variable)
        ds.node_model(**args, name=name+':Potential', equation='0')

