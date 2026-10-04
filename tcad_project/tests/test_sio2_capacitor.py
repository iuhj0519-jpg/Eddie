import copy
import json
from pathlib import Path
import unittest

from src.device.sio2_capacitor import assess, reference, simulate

CONFIG = json.loads((Path(__file__).resolve().parents[1]/'configs/phase1/capacitor.json').read_text(encoding='utf-8'))


class ReferenceTests(unittest.TestCase):
    def test_known_values(self):
        r = reference(CONFIG)
        self.assertAlmostEqual(r['thickness_cm'], 1e-6)
        self.assertAlmostEqual(r['C_per_area_F_per_cm2']/3.453133246992e-7, 1)
        self.assertAlmostEqual(r['E_V_per_cm'], -1e6)

    def test_invalid_input(self):
        for key, value in [('thickness_nm', 0), ('relative_permittivity', -1),
                           ('left_V', float('nan')), ('right_V', 0), ('mesh_intervals', [2.5]),
                           ('mesh_intervals', [10, 5]), ('field_rtol', True)]:
            with self.subTest(key=key, value=value):
                c = copy.deepcopy(CONFIG)
                c[key] = value
                with self.assertRaises(ValueError):
                    reference(c)


class SolverTests(unittest.TestCase):
    def test_polarity_offset_and_scaling(self):
        for thickness, left, right in [(10,0,1), (20,0,1), (10,1,0), (10,2,3)]:
            with self.subTest(thickness=thickness,left=left,right=right):
                c = dict(CONFIG, thickness_nm=thickness, left_V=left, right_V=right)
                result = simulate(c, 10)
                _, checks = assess(c, result)
                self.assertTrue(all(x['pass'] for x in checks), checks)
                result['charges']['right'] *= 1.2
                _, checks = assess(c, result)
                self.assertFalse(all(x['pass'] for x in checks))


if __name__ == '__main__':
    unittest.main()
