import tempfile
import unittest
from pathlib import Path
from rag.automation.run_loop import validate_patch


class ApprovedTbScope(unittest.TestCase):
    def test_explicit_tb_only(self):
        with tempfile.TemporaryDirectory() as d:
            patch = Path(d)/'candidate.diff'
            patch.write_text('--- a/tb/top_sim.sv\n+++ b/tb/top_sim.sv\n@@ -1 +1 @@\n-old\n+new\n',encoding='utf-8')
            with self.assertRaises(SystemExit):
                validate_patch(patch)
            self.assertEqual(validate_patch(patch,['tb/top_sim.sv']),['tb/top_sim.sv'])
            patch.write_text('--- a/memory/weights.mif\n+++ b/memory/weights.mif\n',encoding='utf-8')
            with self.assertRaises(SystemExit):
                validate_patch(patch,['memory/weights.mif'])
