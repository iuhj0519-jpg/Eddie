"""Pure input/formula/finite-volume tests; no DEVSIM solve."""
from copy import deepcopy
import math
from pathlib import Path
import unittest

from src.physics.avalanche import coefficient, generation, interior_generation_integrals, validate_avalanche
from src.device.pn_junction import validate_bias
from validation.analytic.pn_junction.run_avalanche import load_config, preflight, guard_domain

ROOT=Path(__file__).resolve().parents[3]


class PNAvalancheUnitTests(unittest.TestCase):
    def setUp(self):
        self.base,self.config,self.sweep,self.experiment=load_config(ROOT/'configs/phase1/pn_junction_avalanche.json')

    def test_coefficient_scale_symmetry_and_zero(self):
        # Independent hand expression at E=300 kV/cm.
        expected=0.426*300000*math.exp(-(481000/300000)**2)
        self.assertAlmostEqual(coefficient(300000,0.426,481000),expected)
        self.assertEqual(coefficient(-300000,0.426,481000),expected)
        self.assertEqual(coefficient(0,0.426,481000),0)
        self.assertLess(coefficient(200000,0.426,481000),expected)

    def test_generation_units_and_off(self):
        parameters=deepcopy(self.experiment['avalanche'])
        q=1.602176634e-19
        expected=coefficient(300000,0.426,481000)*0.001/q
        self.assertAlmostEqual(generation(300000,-0.001,0,q,parameters)/expected,1)
        self.assertEqual(generation(300000,0,0,q,parameters),0)
        parameters['enabled']=False
        self.assertEqual(generation(300000,-0.001,0,q,parameters),0)

    def test_half_edge_control_volumes_nonuniform(self):
        state={'nodes':{'x_cm':[0,1,3,6]},'edges':{'ImpactGeneration_cm3_per_s':[2,4,8]}}
        # Interior: 2*1/2+4*2/2=5; 4*2/2+8*3/2=16.
        self.assertEqual(interior_generation_integrals(state),[5,16])
        # The remaining contact half-volumes are 1 and 12: full integral=34.
        self.assertEqual(sum(interior_generation_integrals(state))+1+12,34)

    def test_domain_and_mesh_screening(self):
        report=preflight(self.config,self.sweep,self.experiment)
        self.assertEqual(report['spacing_nm'],[10,5,2.5])
        self.assertEqual(report['stages']['pilot']['points_per_mesh_case'],[21,41])
        self.assertEqual(report['stages']['extension']['points_per_mesh_case'],[161,321])
        with self.assertRaises(ValueError):
            guard_domain(self.base,self.experiment,-80)
        self.assertEqual(self.base['p_length_nm'],1000)
        self.assertEqual(self.config['p_length_nm'],5000)

    def test_reverse_only_is_avalanche_specific(self):
        validate_bias(self.config,self.sweep,'pilot')
        bad=deepcopy(self.sweep)
        bad['model']='drift_diffusion_srh'
        with self.assertRaises((KeyError,ValueError)):
            validate_bias(self.config,bad,'pilot')

    def test_invalid_parameters(self):
        for key,value in [('enabled',1),('a_n_per_V',float('nan')),('b_p_V_per_cm',-1),
                          ('field_regularization_V_per_cm',1)]:
            p=deepcopy(self.experiment['avalanche']); p[key]=value
            with self.assertRaises(ValueError):
                validate_avalanche(p)
        with self.assertRaises(ValueError):
            validate_avalanche(self.experiment['avalanche'],350)


if __name__=='__main__':
    unittest.main()
