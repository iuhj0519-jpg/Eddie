import copy
import json
from pathlib import Path
import unittest
from validation.analytic.capacitor.run_thickness import thickness_model, validate_thickness

CONFIG = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/capacitor_thickness.json').read_text(encoding='utf-8'))


class ThicknessConfigTests(unittest.TestCase):
    def test_multilayer_scaling(self):
        c = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/multilayer_sio2_hfo2_capacitor_thickness.json').read_text())
        original = copy.deepcopy(c)
        validate_thickness(c)
        for t in c['thicknesses_nm']:
            model = thickness_model(c['model'], t)
            self.assertEqual(model['layer_thicknesses_nm'], [t/2, t/2])
            self.assertEqual(model['layer_relative_permittivities'], [3.9,20.0])
        self.assertEqual(c, original)
        self.assertNotIn('layer_thicknesses_nm', thickness_model(CONFIG['model'], 5))

    def test_default(self):
        validate_thickness(CONFIG)

    def test_invalid_thicknesses(self):
        for ts in ([5, 10], [5]*10, list(range(10)), list(range(20, 10, -1)),
                   [float('nan')]+list(range(1, 10)), [True]+list(range(1, 10))):
            c = copy.deepcopy(CONFIG)
            c['thicknesses_nm'] = ts
            with self.subTest(ts=ts), self.assertRaises(ValueError):
                validate_thickness(c)

    def test_invalid_controls(self):
        for key, value in [('right_V', 0), ('mesh_intervals', [40])]:
            c = copy.deepcopy(CONFIG)
            c['model'][key] = value
            with self.assertRaises(ValueError):
                validate_thickness(c)
        for value in (0, True, float('inf')):
            c = copy.deepcopy(CONFIG)
            c['mesh_capacitance_rtol'] = value
            with self.assertRaises(ValueError):
                validate_thickness(c)
