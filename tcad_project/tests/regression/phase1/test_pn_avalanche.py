"""Actual DEVSIM checks for the next test phase; not run at preparation."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import unittest

from src.device.pn_junction import simulate_bias_branch
from validation.analytic.pn_junction.run_avalanche import load_config, assess

ROOT=Path(__file__).resolve().parents[3]


class PNAvalancheRegressionTests(unittest.TestCase):
    def setUp(self):
        self.base,self.config,self.sweep,self.experiment=load_config(ROOT/'configs/phase1/pn_junction_avalanche.json')

    def solve(self,config,settings,count,grid):
        with closing(simulate_bias_branch(config,settings,count,grid,lambda record:None)) as states:
            return list(states)

    def test_avalanche_off_reproduces_original_srh(self):
        baseline=deepcopy(self.sweep)
        del baseline['avalanche']
        baseline['model']='drift_diffusion_srh'
        off=deepcopy(self.sweep); off['avalanche']['enabled']=False
        # Original 1+1 um geometry isolates the optional-source change.
        grid=[0,-0.01,-0.1]
        old=self.solve(self.base,baseline,200,grid)
        new=self.solve(self.base,off,200,grid)
        for a,b in zip(old,new):
            self.assertTrue(all(v==0 for v in b['edges']['ImpactGeneration_cm3_per_s']))
            for x,y in zip(a['nodes']['Potential_V'],b['nodes']['Potential_V']):
                self.assertLessEqual(abs(x-y),off['potential_atol_V'])
            for x,y in zip(a['edges']['TotalCurrent_A_per_cm2'],b['edges']['TotalCurrent_A_per_cm2']):
                self.assertLessEqual(abs(x-y),off['current_atol_A_per_cm2']+off['comparison_rtol']*max(abs(x),abs(y)))
            _,checks=assess(self.base,off,b)
            self.assertTrue(all(t['passed'] for t in checks),checks)

    def test_on_equilibrium_and_reverse_source_balance(self):
        settings=deepcopy(self.sweep)
        grid=[0,-0.5,-1,-2,-3,-4,-5,-6,-7,-8,-9,-10]
        states=self.solve(self.config,settings,self.config['mesh_intervals'][0],grid)
        for state in states:
            metric,checks=assess(self.config,settings,state)
            self.assertTrue(all(t['passed'] for t in checks),checks)
        self.assertGreater(metric['q_integral_G_II_A_per_cm2'],0)
        self.assertGreater(metric['max_G_II_cm3_per_s'],0)
        # This checks coupling and conservation, not a calibrated breakdown voltage.


if __name__=='__main__':
    unittest.main()
