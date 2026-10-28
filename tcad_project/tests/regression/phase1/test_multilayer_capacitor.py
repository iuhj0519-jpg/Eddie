import copy
import json
from pathlib import Path
import unittest
import tempfile
from src.device.capacitor import assess, simulate

CONFIG = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/multilayer_capacitor.json').read_text(encoding='utf-8'))


class MultilayerSolverTests(unittest.TestCase):
    def test_voltage_sweep(self):
        from validation.analytic.capacitor.run_voltage import run, validate_qv, write_json
        root = Path(__file__).resolve().parents[3]
        c = json.loads((root/'configs/phase1/multilayer_sio2_hfo2_capacitor_voltage.json').read_text())
        validate_qv(c)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            write_json(out/'config.json', c)
            summary = run(c, out)
            self.assertEqual(summary['failed'], 0)
            self.assertEqual(len(summary['sweeps']), 2)
            for sweep in summary['sweeps']:
                self.assertLess(abs(sweep['fit_C_per_area_F_per_cm2']/5.77930250542594e-7-1), 1e-10)
            self.assertEqual({p.name for p in out.iterdir()},
                             {'config.json','summary.json','validation.csv','qv.csv','qv.png','points_21','points_41'})

    def test_different_permittivities(self):
        c = dict(CONFIG, layer_relative_permittivities=[3.9, 20.0], layer_materials=['SiO2', 'HfO2'])
        expected_c = 1/(5e-7/(3.9*CONFIG['epsilon0_F_per_cm'])+5e-7/(20*CONFIG['epsilon0_F_per_cm']))
        for voltage in (1.0, -1.0):
            for count in CONFIG['mesh_intervals']:
                model = dict(c, right_V=voltage)
                result = simulate(model, count)
                cap, checks = assess(model, result)
                self.assertTrue(all(r['pass'] for r in checks), checks)
                self.assertLess(abs(cap/expected_c-1), 1e-10)
                for i, k in enumerate([3.9, 20.0]):
                    e = result['regions'][i]['edges']
                    for a,b,v in zip(e['x0_cm'],e['x1_cm'],e['E_edge_V_per_cm']):
                        expected_e = -expected_c*voltage/(k*CONFIG['epsilon0_F_per_cm'])
                        self.assertLess(abs(v*(1 if b>a else -1)/expected_e-1), 1e-10)

    def test_matches_single_region(self):
        single = dict(CONFIG)
        single.pop('layer_thicknesses_nm')
        for count in CONFIG['mesh_intervals']:
            split = simulate(CONFIG, count)
            base = simulate(single, count)
            cap, checks = assess(CONFIG, split)
            base_cap, _ = assess(single, base)
            self.assertTrue(all(c['pass'] for c in checks), checks)
            self.assertEqual(len(checks), 6)
            self.assertEqual(split['unique_nodes'], count+1)
            self.assertEqual(len(split['nodes']['x_cm']), count+2)
            self.assertLess(abs(cap/base_cap-1), 1e-10)
            for region in split['regions']:
                for x, p in zip(region['nodes']['x_cm'], region['nodes']['potential_V']):
                    nearest = min(range(len(base['nodes']['x_cm'])), key=lambda i: abs(base['nodes']['x_cm'][i]-x))
                    self.assertLess(abs(p-base['nodes']['potential_V'][nearest]), 1e-9)
            broken = copy.deepcopy(split)
            broken['regions'][1]['nodes']['potential_V'][0] += 0.01
            _, bad = assess(CONFIG, broken)
            self.assertFalse(next(c['pass'] for c in bad if c['check']=='interface_0_potential_jump_V'))

    def test_reversed_bias(self):
        c = dict(CONFIG, left_V=1.0, right_V=0.0)
        _, checks = assess(c, simulate(c, 10))
        self.assertTrue(all(r['pass'] for r in checks))
