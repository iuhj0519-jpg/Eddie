"""Offline orchestration regression tests; fixture results are NOT RTL verification."""
import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_loop as loop
from parsers import parse_timing, parse_log, parse_paths, parse_fanout, collect_metrics
from detectors import detect
from tool_flow import simulation_result


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous = loop.ROOT
        loop.ROOT = self.root
        self.config = {"thresholds": {}, "loop": {"max_iterations": 5, "stop_on_repeated_fingerprint": 2},
            "commands": {"optimized_accelerator": [{"stage": name, "tool": __file__} for name in ("compile", "simulation", "synthesis")]}}
        for folder in ("rtl", "tb", "memory", "scripts"):
            p = self.root / "workspace/optimized_accelerator" / folder
            p.mkdir(parents=True)
            (p / ("top.sv" if folder == "rtl" else "fixture.txt")).write_text("module top; endmodule\n")
        self.artifact = self.root / "artifacts/synthesis/optimized_accelerator/run_001"
        self.artifact.mkdir(parents=True)
        self.args = argparse.Namespace(target="optimized_accelerator", run_id="run_001", artifact_root=None)

    def tearDown(self):
        loop.ROOT = self.previous
        self.temp.cleanup()

    def file(self, name, text):
        p = self.root / name
        p.write_text(text)
        return p

    def test_min_max(self):
        data = parse_timing(self.file("timing.rpt", "WNS(ns) TNS(ns) WHS(ns)\n-----\n-5 -200 70 3000 0.1 0 0 3000 4.5 0 0 1400\n"))
        self.assertEqual(data["whs_ns"], .1)
        self.assertEqual(data["wpws_ns"], 4.5)

    def test_max_only(self):
        data = parse_timing(self.file("timing.rpt", "WNS(ns) TNS(ns)\n-----\n-5 -200 70 3000 4.5 0 0 1400\n"))
        self.assertNotIn("whs_ns", data)

    def test_zero_errors(self):
        self.assertEqual(parse_log(self.file("a.log", "Errors: 0, Warnings: 0\n"))["error_count"], 0)

    def test_fatal(self):
        self.assertEqual(parse_log(self.file("a.log", "# ** Fatal: TIMEOUT\n"))["error_count"], 1)

    def test_unknown_never_pass(self):
        ids = [f["finding_id"] for f in detect(collect_metrics(self.artifact), self.config)]
        self.assertIn("EVIDENCE-COVERAGE-001", ids)

    def test_path_detectors(self):
        path = self.file("a.rpt", "Slack (VIOLATED) : -5ns\nSource: controller/cycle/C\nDestination: weight/read/D\nData Path Delay: 15ns (logic 5ns (33%) route 10ns (67%))\nLogic Levels: 17 (MUXF7=1)\nweight_read_address\n")
        fan = self.file("fan.rpt", "| weight/net | 2401 | DSP48E1 | -5 | 2.4 |\n")
        ids = {f["finding_id"] for f in detect({"paths": parse_paths(path), "fanout": parse_fanout(fan)}, self.config)}
        self.assertTrue({"PPA-ADDRESS-001", "PPA-MUX-001", "PPA-PIPELINE-001", "PPA-FANOUT-001"} <= ids)

    def test_not_approved(self):
        loop.analyze(self.args, self.config)
        with self.assertRaisesRegex(SystemExit, "not approved"):
            loop.resume(self.args, self.config)
        self.assertFalse((self.root / ".automation_debug").exists())

    def approve_all(self):
        run = loop.safe_run(self.args.target, self.args.run_id)
        for fid in loop.load_yaml(run / "approval.yaml")["items"]:
            loop.approve(argparse.Namespace(**vars(self.args), finding_id=fid, decision="approved", requirement_id="TEST-ONLY-001"), self.config)

    def test_stale(self):
        loop.analyze(self.args, self.config)
        self.approve_all()
        (self.artifact / "changed.log").write_text("changed")
        with self.assertRaisesRegex(SystemExit, "Stale"):
            loop.resume(self.args, self.config)

    def test_patch_scope(self):
        p = self.file("p.diff", "--- a/../rtl/a.sv\n+++ b/../rtl/a.sv\n")
        with self.assertRaises(SystemExit):
            loop.validate_patch(p)

    def test_simulation_completion(self):
        p = self.file("sim.log", "FINAL_RESULT PASS=99 FAIL=1 ACCURACY=99.0%\n")
        self.assertFalse(simulation_result(p)["completed"])

    def test_failed_compile_creates_unapproved_child(self):
        loop.analyze(self.args, self.config)
        self.approve_all()
        run = loop.safe_run(self.args.target, self.args.run_id)
        (run / "proposed_patch.diff").write_text("--- a/rtl/top.sv\n+++ b/rtl/top.sv\n@@ -1 +1 @@\n-module top; endmodule\n+module top; wire a; endmodule\n")
        loop.dump_yaml(run / "patch_trace.yaml", {"changes": [{"finding_id": "EVIDENCE-COVERAGE-001", "requirement_id": "TEST-ONLY-001", "files": ["rtl/top.sv"], "explanation": "fixture"}]})
        with patch.object(loop, "run_command", return_value=0), patch.object(loop.tool_flow, "run", return_value=1):
            self.assertEqual(loop.resume(self.args, self.config), 2)
        child = loop.safe_run(self.args.target, "run_002")
        result = json.loads((child / "revalidation_result.json").read_text())
        self.assertFalse(result["all_tools_passed"])
        self.assertEqual(len(result["stages"]), 1)
        self.assertEqual(loop.load_yaml(child / "approval.yaml")["overall_state"], "pending_human_approval")
        self.assertEqual((self.root / "workspace/optimized_accelerator/rtl/top.sv").read_text(), "module top; endmodule\n")

    def test_complete_stages_still_need_evidence_and_review(self):
        loop.analyze(self.args, self.config)
        self.approve_all()
        run = loop.safe_run(self.args.target, self.args.run_id)
        (run / "proposed_patch.diff").write_text("--- a/rtl/top.sv\n+++ b/rtl/top.sv\n@@ -1 +1 @@\n-module top; endmodule\n+module top; wire a; endmodule\n")
        loop.dump_yaml(run / "patch_trace.yaml", {"changes": [{"finding_id": "EVIDENCE-COVERAGE-001", "requirement_id": "TEST-ONLY-001", "files": ["rtl/top.sv"], "explanation": "fixture"}]})
        with patch.object(loop, "run_command", return_value=0), patch.object(loop.tool_flow, "run", return_value=0):
            loop.resume(self.args, self.config)
        result = json.loads((run / "revalidation_result.json").read_text())
        self.assertTrue(result["all_tools_passed"])
        self.assertEqual(len(result["stages"]), 3)
        self.assertEqual(result["state"], "pending_human_review")
        self.assertFalse(result["promoted"])

    def test_config_change_invalidates_approval(self):
        loop.analyze(self.args, self.config)
        self.config["thresholds"]["minimum_wns_ns"] = -99
        with self.assertRaisesRegex(SystemExit, "Stale"):
            self.approve_all()

    def test_missing_spec_id(self):
        loop.analyze(self.args, self.config)
        with self.assertRaisesRegex(SystemExit, "Requirement ID"):
            loop.approve(argparse.Namespace(**vars(self.args), finding_id="EVIDENCE-COVERAGE-001", decision="approved", requirement_id=None), self.config)

    def test_existing_run_preserved(self):
        loop.analyze(self.args, self.config)
        with self.assertRaisesRegex(SystemExit, "overwrite"):
            loop.analyze(self.args, self.config)

    def test_bad_identifier(self):
        with self.assertRaises(SystemExit):
            loop.safe_run("optimized_accelerator", "../main")

    def test_sample_regression(self):
        fs = detect({"previous_metrics": {"verification": {"sample_results": [["0", "1", "1"]]}},
            "verification": {"sample_results": [["0", "2", "1"]]}}, self.config)
        self.assertIn("VERIFY-SAMPLE-REGRESSION-001", [f["finding_id"] for f in fs])

    def test_dsp_is_not_pe_utilization(self):
        fs = detect({"utilization": {"dsp": 5}, "verification": {"peak_active_pe_count": 25}}, self.config)
        self.assertIn("PPA-DSP-001", [f["finding_id"] for f in fs])
        self.assertNotIn("PERF-PE-UTIL-001", [f["finding_id"] for f in fs])

    def test_iteration_limit(self):
        loop.analyze(self.args, self.config)
        self.approve_all()
        run = loop.safe_run(self.args.target, self.args.run_id)
        manifest = loop.load_yaml(run / "run_manifest.yaml")
        manifest["iteration"] = 5
        loop.dump_yaml(run / "run_manifest.yaml", manifest)
        with self.assertRaisesRegex(SystemExit, "stop condition"):
            loop.resume(self.args, self.config)

    def test_repeated_findings_stop(self):
        loop.analyze(self.args, self.config)
        self.approve_all()
        run = loop.safe_run(self.args.target, self.args.run_id)
        manifest = loop.load_yaml(run / "run_manifest.yaml")
        manifest["stop_reason"] = "repeated_findings_require_human_replan"
        loop.dump_yaml(run / "run_manifest.yaml", manifest)
        with self.assertRaisesRegex(SystemExit, "stop condition"):
            loop.resume(self.args, self.config)

    def test_empty_commands(self):
        self.config["commands"]["optimized_accelerator"] = []
        loop.analyze(self.args, self.config)
        self.approve_all()
        with self.assertRaisesRegex(SystemExit, "must all be configured"):
            loop.resume(self.args, self.config)

    def test_memory_mapping_not_hotspot_dependent(self):
        policy = {"memory_mapping_requirements": [{"module": "weight_sram", "storage": "block_ram"}]}
        metrics = {"utilization": {"lut": 1000}, "hierarchy": {"weight": {"module": "weight_sram", "total_lut": 10,
            "logic_lut": 10, "lutram": 0, "ramb18": 0, "ramb36": 0}}}
        ids = [f["finding_id"] for f in detect(metrics, policy)]
        self.assertIn("PPA-MEMORY-MAPPING-001", ids)
        self.assertNotIn("PPA-WEIGHT-001", ids)
        metrics["hierarchy"]["weight"]["ramb18"] = 5
        self.assertNotIn("PPA-MEMORY-MAPPING-001", [f["finding_id"] for f in detect(metrics, policy)])

    def test_memory_missing_unknown(self):
        fs = detect({}, {"memory_mapping_requirements": [{"module": "weight_sram", "storage": "block_ram"}]})
        self.assertIn("EVIDENCE-MEMORY-MAPPING-001", [f["finding_id"] for f in fs])


if __name__ == "__main__":
    unittest.main()
