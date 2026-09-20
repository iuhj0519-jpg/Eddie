"""Offline tests: no production approval, no RTL optimization."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tool_flow
from detectors import detect
import lifecycle

class VivadoFlowTests(unittest.TestCase):
    def test_approved_energy_and_power_limits_are_not_waived(self):
        row = {'requirement_id': 'fixture', 'acceptance': [], 'power_tradeoff': {
            'priority': 'balanced', 'max_average_power_w': .544, 'max_energy_per_workload_uj': 900}}
        result = lifecycle.evaluate({'requirements': [row]}, {'power': {'total_on_chip_power_w': .607, 'energy_per_workload_uj': 850}})
        self.assertEqual(result[0]['state'], 'fail')
        self.assertEqual(lifecycle.evaluate({'requirements': [row]}, {})[0]['state'], 'unknown')

    def test_energy_regression_is_reported(self):
        findings = detect({'previous_metrics': {'power': {'energy_per_workload_uj': 900}},
                           'power': {'energy_per_workload_uj': 980}}, {})
        self.assertIn('REGRESSION-ENERGY-PER-WORKLOAD-UJ', [f['finding_id'] for f in findings])

    def test_saif_ps_energy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            saif, power = root/'a.saif', root/'power.rpt'
            saif.write_text('(TIMESCALE 1 ps) (DURATION 1837345000)')
            power.write_text('| Total On-Chip Power (W) | 0.544 |')
            result = tool_flow.activity_metrics(saif, power)
            self.assertEqual(result['duration_ns'], 1837345)
            self.assertAlmostEqual(result['energy_per_workload_uj'], 999.51568)

    def test_missing_duration_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'a'
            p.write_text('')
            with self.assertRaises(ValueError): tool_flow.activity_metrics(p, p)

    def test_missing_data_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): tool_flow.prepare_xsim_data(Path(directory)/'workspace/target')

    def test_xsim_memory_and_inputs_are_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root/'workspace/target'
            (work/'memory').mkdir(parents=True)
            (work/'memory/w.mif').write_text('0')
            data = root/'inputs/reference_model/testdata'
            data.mkdir(parents=True)
            (data/'test_data_0000.txt').write_text('0')
            tool_flow.prepare_xsim_data(work)
            sim = work/'.vivado_flow/project/accelerator.sim/sim_1/behav/xsim'
            self.assertTrue((sim/'memory/w.mif').exists())
            self.assertTrue((sim/'../../inputs/reference_model/testdata/test_data_0000.txt').resolve().exists())

    def test_xsim_error_cannot_be_golden_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory)/'simulation.log'
            log.write_text('ERROR: missing input\nFINAL_RESULT PASS=99 FAIL=1 ACCURACY=99%\nREFERENCE_GOLDEN_MATCH PASS')
            self.assertFalse(tool_flow.simulation_result(log)['completed'])

    def test_vivado_stage_dispatch(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(tool_flow, 'execute', return_value=0) as execute:
            root = Path(directory)
            self.assertEqual(tool_flow.run('implementation', root, root/'out', 'C:/Vivado/vivado.bat', root/'synthesis.tcl'), 0)
            command = execute.call_args.args[0]
            self.assertIn('implementation', command)
            self.assertTrue(any(str(s).endswith('vivado_flow.tcl') for s in command))

if __name__ == '__main__': unittest.main()
