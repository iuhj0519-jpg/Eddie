"""Prepared pure tests; not executed during voltage-sweep preparation."""
import json
from pathlib import Path
import unittest

from src.device.pn_junction import bias_grid, bias_reference, reference, validate_bias

ROOT=Path(__file__).resolve().parents[3]
CONFIG=json.loads((ROOT/'configs/phase1/pn_junction.json').read_text())
SWEEP=json.loads((ROOT/'configs/phase1/pn_junction_voltage.json').read_text())


class PNVoltageUnitTests(unittest.TestCase):
    def test_stage_grids(self):
        for stage in ('pilot','extension'):
            validate_bias(CONFIG,SWEEP,stage)
            for branch in ('reverse','forward'):
                segments=SWEEP['stages'][stage][branch+'_segments']
                coarse=bias_grid(segments)
                fine=bias_grid(segments,2)
                self.assertGreaterEqual(len(coarse),11)
                self.assertEqual(len(coarse),len(set(coarse)))
                self.assertTrue(set(coarse)<=set(fine))
        extension=SWEEP['stages']['extension']
        for refinement,expected in ((1,101),(2,201)):
            reverse=bias_grid(extension['reverse_segments'],refinement)
            forward=bias_grid(extension['forward_segments'],refinement)
            self.assertEqual(len(reverse),40*refinement+1)
            self.assertEqual(len(forward),60*refinement+1)
            self.assertEqual(len(set(reverse+forward)),expected)
            for branch in (reverse,forward):
                for a,b in zip(branch,branch[1:]):
                    self.assertAlmostEqual(abs(b-a),0.005/refinement,places=12)

    def test_bias_width_reference(self):
        eq=reference(CONFIG)['W_cm']
        self.assertEqual(bias_reference(CONFIG,0)['W_cm'],eq)
        self.assertGreater(bias_reference(CONFIG,-0.1)['W_cm'],eq)
        self.assertLess(bias_reference(CONFIG,0.1)['W_cm'],eq)
        with self.assertRaises(ValueError):
            bias_reference(CONFIG,reference(CONFIG)['Vbi_V'])

    def test_invalid_grids(self):
        for segments in ([],[[0,0.1,0]],[[0,0.1,-0.01]],[[0,0.1,0.03]],
                         [[0,0.1,0.01],[0.2,0.3,0.01]]):
            with self.subTest(segments=segments),self.assertRaises(ValueError):
                bias_grid(segments)
