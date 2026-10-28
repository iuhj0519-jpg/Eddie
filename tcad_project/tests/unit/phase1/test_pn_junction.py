"""Pure logic and synthetic VTK tests; DEVSIM solve is not needed."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from src.device.pn_junction import bernoulli, equilibrium_currents, interface_side_charges, reference, validate
from validation.analytic.pn_junction.export_vtm import export_vtm

CONFIG = json.loads((Path(__file__).resolve().parents[3]/'configs/phase1/pn_junction.json').read_text())


class PNUnitTests(unittest.TestCase):
    def test_sided_integration_asymmetric_nonuniform(self):
        config = dict(CONFIG,acceptors_cm3=2e16,donors_cm3=3e16)
        q = config['electron_charge_C']
        state = dict(junction_cm=2e-6,nodes=dict(
            x_cm=[0,0.5e-6,2e-6,3e-6,5e-6],
            Electrons_cm3=[1e10]*5,Holes_cm3=[1e10]*5,
            ChargeDensity_C_per_cm3=[-q*2e16,-q*2e16,q*0.5e16,q*3e16,q*3e16]))
        before = copy.deepcopy(state)
        left,right = interface_side_charges(config,state)
        self.assertAlmostEqual(left/(-q*2e16*2e-6),1.0,places=14)
        self.assertAlmostEqual(right/(q*3e16*3e-6),1.0,places=14)
        self.assertEqual(state,before)

    def test_sided_integration_preserves_mobile_charge(self):
        q = CONFIG['electron_charge_C']
        mobile = 2e15
        state = dict(junction_cm=1e-6,nodes=dict(
            x_cm=[0,1e-6,2e-6],Electrons_cm3=[1e10]*3,
            Holes_cm3=[mobile+1e10]*3,
            ChargeDensity_C_per_cm3=[q*(mobile-1e16),q*mobile,q*(mobile+1e16)]))
        left,right = interface_side_charges(CONFIG,state)
        self.assertAlmostEqual(left/(q*(mobile-1e16)*1e-6),1.0,places=14)
        self.assertAlmostEqual(right/(q*(mobile+1e16)*1e-6),1.0,places=14)
        state['junction_cm']=0.7e-6
        with self.assertRaises(ValueError):
            interface_side_charges(CONFIG,state)

    def test_reference_and_symmetry(self):
        ref = reference(CONFIG)
        vt = CONFIG['boltzmann_J_per_K']*CONFIG['temperature_K']/CONFIG['electron_charge_C']
        self.assertAlmostEqual(ref['Vbi_V'],vt*math.log(1e12),places=12)
        self.assertAlmostEqual(ref['xp_cm']/ref['xn_cm'],1.0)
        self.assertLess(abs((ref['right_potential_V']-ref['left_potential_V'])/ref['Vbi_V']-1),1e-10)
        self.assertAlmostEqual(ref['E_peak_V_per_cm']*ref['W_cm'],-2*ref['Vbi_V'])

    def test_invalid_input(self):
        for key,value in [('right_bias_V',0.1),('temperature_K',0),
                          ('intrinsic_density_cm3',float('nan')),('mesh_intervals',[20,40]),
                          ('mesh_intervals',[200,201,800]),('domain_check_scale',1),
                          ('model','drift_diffusion'),('donors_cm3',True)]:
            c = copy.deepcopy(CONFIG)
            c[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(c)

    def test_bernoulli_identity(self):
        self.assertEqual(bernoulli(0),1)
        for x in (-10,-1,-1e-8,1e-8,1,10,80):
            self.assertAlmostEqual(bernoulli(-x)-bernoulli(x),x,places=12)

    def test_equilibrium_current_identity(self):
        vt = reference(CONFIG)['thermal_voltage_V']
        phi = [-0.02,0,0.02]
        ni = CONFIG['intrinsic_density_cm3']
        n = [ni*math.exp(v/vt) for v in phi]
        p = [ni*math.exp(-v/vt) for v in phi]
        jn,jp = equilibrium_currents(CONFIG,[0,1e-6,2e-6],phi,n,p)
        self.assertLess(max(abs(v) for v in jn+jp),1e-12)

    def test_vtm_preserves_1d_fields(self):
        state = dict(nodes={'x_cm':[0,1e-6,2e-6],'Potential_V':[0,0.1,0.2]},
                     edges={'x_cm':[0.5e-6,1.5e-6],'ElectricField_V_per_cm':[-1e5,-1e5]},
                     solver_info={'converged':True})
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)/'pn'
            self.assertEqual(export_vtm(state,prefix),['pn.vtu','pn.vtm'])
            tree = ET.parse(prefix.with_suffix('.vtu'))
            piece = tree.find('.//Piece')
            self.assertEqual(piece.get('NumberOfPoints'),'3')
            self.assertEqual(piece.get('NumberOfCells'),'2')
            self.assertEqual(tree.find(".//DataArray[@Name='types']").text.split(),['3','3'])
            self.assertEqual(tree.find(".//CellData/DataArray[@Name='ElectricField_V_per_cm']").text.split(),['-100000','-100000'])
            self.assertEqual(ET.parse(prefix.with_suffix('.vtm')).find('.//DataSet').get('file'),'pn.vtu')
            with self.assertRaises(FileExistsError):
                export_vtm(state,prefix)
