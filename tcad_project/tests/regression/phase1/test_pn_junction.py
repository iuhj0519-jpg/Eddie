"""Actual DEVSIM equilibrium checks. Prepared, not executed during scaffolding."""
import json
from pathlib import Path
import tempfile
import unittest

from src.device.pn_junction import assess, assess_interface, simulate
from validation.analytic.pn_junction.run_pn_junction import run, write_json

CONFIG = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/pn_junction.json').read_text())


class PNRegressionTests(unittest.TestCase):
    def test_equilibrium(self):
        state = simulate(CONFIG,CONFIG['mesh_intervals'][0])
        legacy_metrics,legacy_checks = assess(CONFIG,state)
        self.assertFalse(next(r['passed'] for r in legacy_checks if r['check']=='charge_equivalent_W_relative_error'))
        metrics,checks = assess_interface(CONFIG,state)
        self.assertAlmostEqual(legacy_metrics['charge_equivalent_W_cm']*1e7,404.013393,places=3)
        self.assertTrue(metrics['converged'])
        self.assertTrue(all(row['passed'] for row in checks),checks)
        self.assertEqual(len(state['nodes']['x_cm']),CONFIG['mesh_intervals'][0]+1)
        self.assertTrue(all(v>0 for v in state['nodes']['Electrons_cm3']))
        self.assertTrue(all(v>0 for v in state['nodes']['Holes_cm3']))

    def test_full_equilibrium_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            write_json(out/'config.json',CONFIG)
            summary = run(CONFIG,out,assessment='interface_sided')
            self.assertEqual(summary['failed'],0,summary)
            self.assertEqual(summary['solves'],4)
            for name in ('profiles.csv','edges.csv','metrics.csv','validation.csv',
                         'domain_check.json','summary.json','pn_junction.png','pn_junction.vtm','pn_junction.vtu'):
                self.assertTrue((out/name).is_file(),name)
