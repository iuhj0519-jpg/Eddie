import copy
import json
from pathlib import Path
import unittest

import numpy as np
from src.extraction.capacitance import extract_qv
from validation.analytic.capacitor.run_voltage import validate_qv


class QVTests(unittest.TestCase):
    def test_multilayer_config(self):
        c = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/multilayer_sio2_hfo2_capacitor_voltage.json').read_text())
        validate_qv(c)
        bad = copy.deepcopy(c)
        bad['model']['layer_thicknesses_nm'] = [5.1, 4.9]
        with self.assertRaises(ValueError):
            validate_qv(bad)

    def test_linear_with_offset(self):
        v = np.linspace(-1, 1, 21)
        result = extract_qv(v, 3e-7*v+2e-9)
        self.assertAlmostEqual(result['slope_F_per_cm2']/3e-7, 1)
        self.assertAlmostEqual(result['intercept_C_per_cm2']/2e-9, 1)
        np.testing.assert_allclose(result['local_F_per_cm2'], 3e-7, rtol=1e-12, atol=0)

    def test_quadratic_derivative_including_endpoints(self):
        v = np.linspace(-1, 1, 21)
        result = extract_qv(v, v*v)
        np.testing.assert_allclose(result['local_F_per_cm2'], 2*v, atol=1e-13)

    def test_reject_bad_arrays(self):
        for v, q in [([0,1],[0,1]), ([0,0,1],[0,0,1]), ([1,0,-1],[1,0,-1]),
                     ([0,1,2],[0,float('nan'),2]), ([0,1,2],[0,1])]:
            with self.assertRaises(ValueError):
                extract_qv(v, q)

    def test_config(self):
        c = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/capacitor_voltage.json').read_text())
        validate_qv(c)
        for key, value in [('point_counts',[21,40]), ('point_counts',[21,31]),
                           ('charge_atol_C_per_cm2',0), ('delta_v_min_V',float('nan'))]:
            bad = copy.deepcopy(c)
            bad[key] = value
            with self.assertRaises(ValueError):
                validate_qv(bad)
