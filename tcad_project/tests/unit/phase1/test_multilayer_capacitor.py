import copy
import json
from pathlib import Path
import unittest
from src.device.capacitor import layer_mesh, reference

CONFIG = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/multilayer_capacitor.json').read_text(encoding='utf-8'))


class MultilayerInputTests(unittest.TestCase):
    def test_mesh_and_reference(self):
        for count in (10, 20, 40):
            self.assertEqual(layer_mesh(CONFIG, count), [0, count//2, count])
        self.assertAlmostEqual(reference(CONFIG)['C_per_area_F_per_cm2']/3.453133246992e-7, 1)

    def test_invalid_layers(self):
        for layers in ([], [5, 4], [0, 10], [-5, 15], [True, 9], [float('nan'), 5]):
            c = copy.deepcopy(CONFIG)
            c['layer_thicknesses_nm'] = layers
            with self.subTest(layers=layers), self.assertRaises(ValueError):
                reference(c)
        with self.assertRaises(ValueError):
            layer_mesh(CONFIG, 11)
