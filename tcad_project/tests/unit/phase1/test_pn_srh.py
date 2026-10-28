"""Prepared pure SRH checks; execution is intentionally deferred."""
from copy import deepcopy
import math
import json
from pathlib import Path
import unittest

from src.physics.srh import validate_srh, srh_rate
from src.device.pn_junction import bias_grid
from validation.analytic.pn_junction.run_srh import (load_config, case_sweep, continuity_metrics,
    pilot_compatibility, resolved_magnitudes, junction_peak_field)

ROOT=Path(__file__).resolve().parents[3]
PARAMETERS=dict(enabled=True,tau_n_s=1e-6,tau_p_s=1e-6,trap_energy_minus_intrinsic_eV=0.0)


class PNSRHUnitTests(unittest.TestCase):
    def test_junction_field_piecewise_linear_and_no_mutation(self):
        state = dict(junction_cm=0, edges=dict(
            x_cm=[-1.5,-.5,.5,1.5], ElectricField_V_per_cm=[-7,-9,-8.5,-5.5]))
        before = deepcopy(state)
        result = junction_peak_field(state)
        self.assertEqual(result['peak_abs_E_V_per_cm'],10)
        self.assertEqual(result['edge_peak_abs_E_V_per_cm'],9)
        self.assertEqual(result['junction_left_E_V_per_cm'],-10)
        self.assertEqual(result['junction_right_E_V_per_cm'],-10)
        self.assertEqual(state,before)

    def test_junction_field_nonuniform_and_sign(self):
        state = dict(junction_cm=0, edges=dict(
            x_cm=[-3,-1,.5,2], ElectricField_V_per_cm=[4,8,8.5,4]))
        self.assertEqual(junction_peak_field(state)['peak_abs_E_V_per_cm'],10)

    def test_junction_field_second_order(self):
        errors = []
        for h in (.2,.1,.05):
            x = [-1.5*h,-.5*h,.5*h,1.5*h]
            state = dict(junction_cm=0, edges=dict(x_cm=x,
                ElectricField_V_per_cm=[-10+2*abs(v)+v*v for v in x]))
            errors.append(abs(junction_peak_field(state)['peak_abs_E_V_per_cm']-10))
        self.assertAlmostEqual(errors[0]/errors[1],4,places=9)
        self.assertAlmostEqual(errors[1]/errors[2],4,places=9)

    def test_junction_field_rejects_bad_geometry(self):
        for x in ([-1,.5,1.5],[-1.5,-.5,0,.5,1.5],[-1.5,.5,-.5,1.5]):
            with self.assertRaises(ValueError):
                junction_peak_field(dict(junction_cm=0,edges=dict(
                    x_cm=x,ElectricField_V_per_cm=[-1]*len(x))))

    def test_equilibrium_and_off(self):
        self.assertEqual(srh_rate(1e10,1e10,1e10,PARAMETERS),0)
        self.assertEqual(srh_rate(1e16,1e4,1e10,PARAMETERS),0)
        self.assertEqual(srh_rate(1e12,1e12,1e10,dict(PARAMETERS,enabled=False)),0)

    def test_sign_lifetime_and_generation_limit(self):
        rate=srh_rate(1e12,1e12,1e10,PARAMETERS)
        self.assertGreater(rate,0)
        self.assertLess(srh_rate(1,1,1e10,PARAMETERS),0)
        short=dict(PARAMETERS,tau_n_s=1e-7,tau_p_s=1e-7)
        self.assertTrue(math.isclose(srh_rate(1e12,1e12,1e10,short),10*rate,rel_tol=1e-12))
        limit=-1e10/(2e-6)
        self.assertTrue(math.isclose(srh_rate(1,1,1e10,PARAMETERS),limit,rel_tol=1e-9))
        long=dict(PARAMETERS,tau_n_s=1e9,tau_p_s=1e9)
        self.assertLess(abs(srh_rate(1e12,1e12,1e10,long)),abs(rate)*1e-12)

    def test_invalid_parameters(self):
        for key,value in (('enabled',1),('tau_n_s',0),('tau_p_s',-1),
                          ('tau_n_s',float('nan')),('trap_energy_minus_intrinsic_eV',0.1)):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                validate_srh(dict(PARAMETERS,**{key:value}))

    def test_continuity_sign_and_contact_exclusion(self):
        # q=1 synthetic units: one interior source U*volume=2.
        state=dict(nodes={'SRHNetRate_cm3_per_s':[999,4,999],'ControlVolume_cm':[.25,.5,.25]},
                   edges={'ElectronCurrent_A_per_cm2':[3,5],'HoleCurrent_A_per_cm2':[7,5]})
        result=continuity_metrics({'electron_charge_C':1},state)
        self.assertEqual(result['q_integral_U_A_per_cm2'],2)
        self.assertEqual(result['electron_integral_residual_A_per_cm2'],0)
        self.assertEqual(result['hole_integral_residual_A_per_cm2'],0)
        self.assertEqual(result['electron_local_residual_A_per_cm2'],0)
        bad=deepcopy(state)
        bad['edges']['HoleCurrent_A_per_cm2']=[7,9]
        self.assertEqual(continuity_metrics({'electron_charge_C':1},bad)['hole_integral_residual_A_per_cm2'],4)

    def test_inherited_config_and_no_mutation(self):
        config,sweep,experiment,_=load_config(ROOT/'configs/phase1/pn_junction_srh.json')
        original=deepcopy(sweep)
        for case in experiment['cases']:
            derived=case_sweep(sweep,case)
            self.assertEqual(derived['srh'],case)
            self.assertTrue(derived['extended_precision'])
        self.assertEqual(sweep,original)
        self.assertNotIn('srh',sweep)
        self.assertEqual(config['mesh_intervals'],[200,400,800])
        self.assertNotIn('transport_config',experiment)
        voltage=json.loads((ROOT/'configs/phase1/pn_junction_voltage.json').read_text(encoding='utf-8'))
        self.assertEqual(voltage['stages']['extension']['forward_segments'][0][1],0.30)
        for stage,expected in (('pilot',21),('extension',171)):
            condition=sweep['stages'][stage]
            values=bias_grid(condition['reverse_segments'])+bias_grid(condition['forward_segments'])
            self.assertEqual(len(set(values)),expected)

    def test_resolved_gaps(self):
        rows=[dict(applied_V=v,J_A_per_cm2=j,current_resolved=r)
              for v,j,r in [(-.1,-2e-9,True),(-.01,-1e-10,False),(0,1e-20,True),(.1,2e-9,True)]]
        result=resolved_magnitudes(rows)
        self.assertEqual(len(result),4)
        self.assertEqual(result[0],2e-9)
        self.assertTrue(math.isnan(result[1]))
        self.assertTrue(math.isnan(result[2]))
        self.assertEqual(result[3],2e-9)

    def test_pilot_compatibility_rejects_physics_changes(self):
        config,sweep,experiment,_=load_config(ROOT/'configs/phase1/pn_junction_srh.json')
        snapshot=deepcopy(dict(base_model=config,transport=sweep,experiment=experiment))
        snapshot['transport']['stages']['extension']['forward_segments']=[[0,.3,.005]]
        for case in snapshot['experiment']['cases']:
            case.pop('display_name',None)
        self.assertTrue(pilot_compatibility(snapshot,config,sweep,experiment))
        for section,key,value in [('base_model','acceptors_cm3',2e16),
                                  ('transport','current_atol_A_per_cm2',1e-6)]:
            bad=deepcopy(snapshot)
            bad[section][key]=value
            self.assertFalse(pilot_compatibility(bad,config,sweep,experiment))
        bad=deepcopy(snapshot)
        bad['experiment']['cases'][1]['tau_n_s']=1e-3
        self.assertFalse(pilot_compatibility(bad,config,sweep,experiment))
        bad=deepcopy(snapshot)
        bad['transport']['stages']['pilot']['forward_segments']=[[0,.2,.01]]
        self.assertFalse(pilot_compatibility(bad,config,sweep,experiment))
