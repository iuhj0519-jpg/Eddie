"""Prepared DD solve checks. Explicit future execution only, not yet verified."""
from contextlib import closing
import json
from pathlib import Path
import unittest

from src.device.pn_junction import simulate_bias_branch, assess_bias, assess_interface, simulate

ROOT=Path(__file__).resolve().parents[3]
CONFIG=json.loads((ROOT/'configs/phase1/pn_junction.json').read_text())
SWEEP=json.loads((ROOT/'configs/phase1/pn_junction_voltage.json').read_text())


class PNVoltageRegressionTests(unittest.TestCase):
    def test_zero_bias_and_small_forward_reverse(self):
        count=CONFIG['mesh_intervals'][0]
        equilibrium=simulate(CONFIG,count)
        metric,_=assess_interface(CONFIG,equilibrium)
        for end in (-0.01,0.01):
            attempts=[]
            with closing(simulate_bias_branch(CONFIG,SWEEP,count,[0,end],attempts.append)) as states:
                for state in states:
                    result,checks=assess_bias(CONFIG,SWEEP,state)
                    self.assertTrue(all(r['passed'] for r in checks),checks)
                    if state['applied_V']==0:
                        self.assertLess(abs(result['charge_equivalent_W_cm']/metric['charge_equivalent_W_cm']-1),0.001)
            self.assertTrue(attempts)
