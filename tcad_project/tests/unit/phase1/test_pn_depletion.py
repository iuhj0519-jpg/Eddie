"""Pure saved-profile extraction tests; no solver invocation."""
import unittest
from validation.analytic.pn_junction.analyze_depletion import crossing, integrate


class RecoveryBoundaryTests(unittest.TestCase):
    def test_linear_interpolation(self):
        self.assertAlmostEqual(crossing([0,1,2],[0,0.4,1],0.5),1+1/6)

    def test_exact_node(self):
        self.assertEqual(crossing([0,1,2],[0,0.5,1],0.5),1)

    def test_no_crossing(self):
        with self.assertRaises(ValueError):
            crossing([0,1],[0,0.4],0.5)

    def test_nonmonotonic_crossing(self):
        with self.assertRaises(ValueError):
            crossing([0,1,2,3],[0,0.8,0.2,1],0.5)

    def test_integral_clipping(self):
        self.assertAlmostEqual(integrate([0,1,2],[0,1,2],0.5,1.5),1)


if __name__=='__main__':
    unittest.main()
