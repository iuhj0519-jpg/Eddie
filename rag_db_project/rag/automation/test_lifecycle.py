"""Temporary-fixture SPEC lifecycle tests, not production optimization approval."""
import argparse
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import lifecycle as lc
import run_loop as loop


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = "optimized_accelerator"
        self.run = lc.target_root(self.root, self.target) / "run_001"
        self.run.mkdir(parents=True)
        self.mock = patch.object(lc, "sync")
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        self.tmp.cleanup()

    def draft(self):
        fs = [{"finding_id": "PPA-TIMING-001", "evidence": {"wns_ns": -5}},
              {"finding_id": "PPA-FANOUT-001", "evidence": {"fanout": 2415}}]
        lc.propose(self.root, self.run, self.target, fs)
        return lc.read(self.run / "requirements.yaml")

    def approve(self):
        doc = self.draft()
        return lc.approve_spec(self.root, self.target, self.run, "fixture-reviewer", lc.digest(doc))

    def test_power_priority_is_not_automatically_selected(self):
        row = lc.requirement("REGRESSION-TOTAL-ON-CHIP-POWER-W", {"before": .544, "after": .607}, 0)
        with self.assertRaisesRegex(SystemExit, "priority required"):
            lc.validate_power_tradeoff(row)

    def test_power_choice_requires_limits_and_review(self):
        row = lc.requirement("REGRESSION-TOTAL-ON-CHIP-POWER-W", {}, 0)
        row["power_tradeoff"] = {"priority": "energy_per_workload", "rationale": "fixture only"}
        with self.assertRaisesRegex(SystemExit, "limits required"):
            lc.validate_power_tradeoff(row)
        row["power_tradeoff"].update(max_average_power_w=0.7, max_energy_per_workload_uj=1000)
        lc.validate_power_tradeoff(row)
        row["acceptance"] = []
        with self.assertRaisesRegex(SystemExit, "evidence review required"):
            lc.validate_power_tradeoff(row)

    def test_power_pending_blocks_spec_approval(self):
        lc.propose(self.root, self.run, self.target,
                   [{"finding_id": "REGRESSION-TOTAL-ON-CHIP-POWER-W", "evidence": {"before": .544, "after": .607}}])
        doc = lc.read(self.run / "requirements.yaml")
        with self.assertRaisesRegex(SystemExit, "priority required"):
            lc.approve_spec(self.root, self.target, self.run, "fixture-reviewer", lc.digest(doc))
        self.assertFalse((self.run.parent / "spec_versions").exists())

    def test_every_finding_gets_contract(self):
        doc = self.draft()
        self.assertEqual(len(doc["requirements"]), 2)
        for row in doc["requirements"]:
            for key in ("after", "acceptance", "verification", "risk", "expected_benefit"):
                self.assertTrue(row[key])

    def test_intake_preserves_raw_and_is_not_approved(self):
        source = self.root / "input.md"
        raw = "Reduce memory logic.\n\nPreserve all numerical outputs."
        source.write_text(raw)
        folder = lc.intake(self.root, self.target, "request_001", source)
        self.assertEqual((folder / "request.md").read_text(), raw)
        doc = lc.read(folder / "requirements.yaml")
        self.assertEqual(len(doc["requirements"]), 2)
        with self.assertRaisesRegex(SystemExit, "Define acceptance"):
            lc.approve_spec(self.root, self.target, folder, "tester", lc.digest(doc))
        lc.sync.assert_called_once()

    def test_digest_blocks_changed_proposal(self):
        self.draft()
        with self.assertRaisesRegex(SystemExit, "digest"):
            lc.approve_spec(self.root, self.target, self.run, "tester", "wrong")

    def test_real_id_validation(self):
        rev = self.approve()
        with self.assertRaisesRegex(SystemExit, "not authorized"):
            lc.authorize(self.root, self.target, rev, "NOT-IN-SPEC", "PPA-TIMING-001")
        lc.authorize(self.root, self.target, rev, "REQ-LOOP-PPA-TIMING-001", "PPA-TIMING-001")

    def test_wrong_finding_validation(self):
        rev = self.approve()
        with self.assertRaises(SystemExit):
            lc.authorize(self.root, self.target, rev, "REQ-LOOP-PPA-TIMING-001", "PPA-DSP-001")

    def test_tampered_version_rejected(self):
        rev = self.approve()
        path = lc.target_root(self.root, self.target) / "spec_versions" / rev / "spec.yaml"
        doc = lc.read(path)
        doc["requirements"][0]["after"] = "changed"
        lc.write(path, doc)
        with self.assertRaisesRegex(SystemExit, "invalid"):
            lc.get_revision(self.root, self.target, rev)

    def test_baseline_changed_invalidates(self):
        rev = self.approve()
        path = self.root / "inputs/specifications/base.md"
        path.parent.mkdir(parents=True)
        path.write_text("new")
        with self.assertRaises(SystemExit):
            lc.get_revision(self.root, self.target, rev)

    def test_unknown_not_pass_and_regression_fails(self):
        row = self.draft()["requirements"][0]
        self.assertEqual(lc.evaluate({"requirements": [row]}, {})[0]["state"], "unknown")
        self.assertEqual(lc.evaluate({"requirements": [row]}, {"timing": {"wns_ns": -5}})[0]["state"], "fail")

    def test_all_predicates_pass(self):
        row = self.draft()["requirements"][0]
        result = lc.evaluate({"requirements": [row]}, {"timing": {"wns_ns": 0, "tns_ns": 0},
                           "review": {row["requirement_id"]: True}})
        self.assertEqual(result[0]["state"], "pass")

    def test_next_spec_preserves_old_requirements(self):
        rev = self.approve()
        child = self.run.parent / "run_002"
        child.mkdir()
        lc.propose(self.root, child, self.target, [{"finding_id": "PPA-MUX-001", "evidence": {}}], rev)
        draft = lc.read(child / "requirements.yaml")
        self.assertEqual(len(draft["requirements"]), 3)
        second = lc.approve_spec(self.root, self.target, child, "tester", lc.digest(draft))
        self.assertEqual(second, "spec_002")
        self.assertEqual(lc.get_revision(self.root, self.target, second)["parent_revision"], rev)

    def test_cannot_relax_previous_contract(self):
        rev = self.approve()
        child = self.run.parent / "run_002"
        child.mkdir()
        lc.propose(self.root, child, self.target, [], rev)
        draft = lc.read(child / "requirements.yaml")
        draft["requirements"][0]["acceptance"][0]["value"] = -99
        lc.write(child / "requirements.yaml", draft)
        with self.assertRaisesRegex(SystemExit, "relaxed"):
            lc.approve_spec(self.root, self.target, child, "tester", lc.digest(draft))

    def test_path_escape_rejected(self):
        self.draft()
        with self.assertRaises(SystemExit):
            lc.approve_spec(self.root, self.target, self.root, "tester", "x")

    def acceptance_fixture(self):
        rev = self.approve()
        spec = lc.get_revision(self.root, self.target, rev)
        artifact = self.root / "artifacts/fixture"
        artifact.mkdir(parents=True)
        evidence = artifact / "route_status.rpt"
        evidence.write_text("fixture only")
        binding = {"source_hashes": {"rtl/top.sv": "fixture"}}
        lc.write(artifact / "execution_result.json", {"source_hashes": binding["source_hashes"],
            "stages": [{"stage": s, "exit_code": 0} for s in ("compile", "simulation", "synthesis", "implementation")]})
        lc.write(self.run / "run_manifest.yaml", {"spec_revision": rev, "source": {"artifact_root": "artifacts/fixture"}})
        metrics = {"timing": {"wns_ns": 0, "tns_ns": 0, "whs_ns": 0, "wpws_ns": 0},
            "coverage": {"fixture": {"state": "observed"}}, "implementation": {"unrouted_nets": 0, "routing_errors": 0},
            "verification": {"completed": True}}
        lc.write(self.run / "analysis_result.json", {"metrics": metrics, "finding_ids": []})
        reviews = {r["requirement_id"]: {"pass": True, "reviewer": "fixture", "rationale": "fixture",
            "evidence": "artifacts/fixture/route_status.rpt", "evidence_sha256": lc.hashlib.sha256(evidence.read_bytes()).hexdigest(),
            "binding_sha256": lc.digest(binding), "spec_sha256": lc.digest(spec)} for r in spec["requirements"]}
        lc.write(self.run / "requirement_reviews.yaml", reviews)
        fake = SimpleNamespace(ROOT=self.root, DEFAULT_CONFIG=self.root / "config.yaml", load_yaml=lambda p: {},
            safe_run=lambda t, r: self.run, verify_binding=lambda r, c: binding, fingerprint=lc.digest)
        args = argparse.Namespace(target=self.target, run_id="run_001", reviewer="fixture", rationale="fixture tradeoff")
        return fake, args, artifact

    def test_final_acceptance_is_explicit_and_no_promotion(self):
        fake, args, artifact = self.acceptance_fixture()
        lc.accept(fake, args)
        self.assertFalse(lc.read(self.run / "final_acceptance.yaml")["promoted"])
        with self.assertRaisesRegex(SystemExit, "already recorded"):
            lc.accept(fake, args)

    def test_acceptance_blocks_missing_postroute(self):
        fake, args, artifact = self.acceptance_fixture()
        result = lc.read(artifact / "execution_result.json")
        result["stages"][-1]["exit_code"] = 1
        lc.write(artifact / "execution_result.json", result)
        with self.assertRaisesRegex(SystemExit, "execution evidence"):
            lc.accept(fake, args)

    def test_acceptance_blocks_unknown_review(self):
        fake, args, artifact = self.acceptance_fixture()
        lc.write(self.run / "requirement_reviews.yaml", {})
        with self.assertRaisesRegex(SystemExit, "UNKNOWN"):
            lc.accept(fake, args)

    def test_acceptance_blocks_unreviewed_new_findings(self):
        fake, args, artifact = self.acceptance_fixture()
        result = lc.read(self.run / "analysis_result.json")
        result["finding_ids"] = ["PPA-DSP-001"]
        lc.write(self.run / "analysis_result.json", result)
        with self.assertRaisesRegex(SystemExit, "New findings"):
            lc.accept(fake, args)

    def test_review_tamper_blocks_acceptance(self):
        fake, args, artifact = self.acceptance_fixture()
        (artifact / "route_status.rpt").write_text("tampered fixture")
        with self.assertRaisesRegex(SystemExit, "Stale"):
            lc.accept(fake, args)

    def test_stage_mismatch_is_not_proven_improvement(self):
        context = {"stage": "synthesis", "clock_period_ns": 10, "workload_sha256": "fixture", "activity_kind": "saif"}
        metrics = {"previous_metrics": {"comparison_context": context, "utilization": {"lut": 100}},
                   "comparison_context": {**context, "stage": "post_route"}, "utilization": {"lut": 90}}
        self.assertFalse(lc.compare(metrics)["comparison_context_validated"])
        metrics["comparison_context"] = context
        self.assertTrue(lc.compare(metrics)["comparison_context_validated"])

    def test_request_is_attached_without_losing_findings(self):
        self.draft()
        path = self.root / "request.txt"
        path.write_text("Preserve latency")
        lc.intake(self.root, self.target, "request_001", path)
        lc.attach_request(self.root, self.run, self.target, "request_001")
        doc = lc.read(self.run / "requirements.yaml")
        self.assertEqual(len(doc["requirements"]), 3)
        self.assertIn("request_digest", doc)
        self.assertFalse(doc["requirements"][-1]["acceptance"])


if __name__ == "__main__":
    unittest.main()
