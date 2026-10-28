"""Prepared DEVSIM smoke/regression checks; not run during preparation."""
from contextlib import closing
from pathlib import Path
import unittest

from src.device.pn_junction import simulate_bias_branch
from validation.analytic.pn_junction.run_srh import load_config, case_sweep, assess_srh

ROOT=Path(__file__).resolve().parents[3]


class PNSRHRegressionTests(unittest.TestCase):
    def test_off_equivalence_and_on_continuity(self):
        config,sweep,experiment,_=load_config(ROOT/'configs/phase1/pn_junction_srh.json')
        count=config['mesh_intervals'][0]
        def solve(settings,voltages):
            with closing(simulate_bias_branch(config,settings,count,voltages,lambda record:None)) as states:
                return list(states)
        for end in (-0.01,0.01):
            baseline=solve(sweep,[0,end])
            for case in experiment['cases']:
                settings=case_sweep(sweep,case)
                states=solve(settings,[0,end])
                for state in states:
                    old_metric,checks=assess_srh(config,settings,experiment,state)
                    self.assertTrue(all(r['passed'] for r in checks),checks)
                    new_metric,new_checks=assess_srh(config,settings,experiment,state,'junction_linear_v1')
                    self.assertTrue(all(r['passed'] for r in new_checks),new_checks)
                    for key,value in old_metric.items():
                        if key != 'peak_abs_E_V_per_cm':
                            self.assertEqual(value,new_metric[key])
                    self.assertGreaterEqual(new_metric['peak_abs_E_V_per_cm'],old_metric['peak_abs_E_V_per_cm'])
                    self.assertEqual(new_metric['edge_peak_abs_E_V_per_cm'],old_metric['peak_abs_E_V_per_cm'])
                if not case['enabled']:
                    for old,new in zip(baseline,states):
                        for a,b in zip(old['edges']['TotalCurrent_A_per_cm2'],new['edges']['TotalCurrent_A_per_cm2']):
                            self.assertLessEqual(abs(a-b),sweep['current_atol_A_per_cm2'])
                        for a,b in zip(old['nodes']['Potential_V'],new['nodes']['Potential_V']):
                            self.assertLessEqual(abs(a-b),sweep['potential_atol_V'])
                else:
                    rates=states[-1]['nodes']['SRHNetRate_cm3_per_s']
                    self.assertTrue(any(abs(r)>0 for r in rates))
