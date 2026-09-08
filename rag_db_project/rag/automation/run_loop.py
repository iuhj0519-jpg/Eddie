"""CLI orchestrator for evidence collection, approval gating and revalidation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc

if __package__:
    from .detectors import detect
    from .parsers import collect_metrics
    from . import tool_flow
else:
    from detectors import detect
    from parsers import collect_metrics
    import tool_flow


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "rag" / "config" / "automation_loop.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def dump_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def source_hashes(workspace: Path) -> dict:
    result = {}
    for folder in ("rtl", "tb", "memory", "scripts"):
        for path in sorted((workspace / folder).rglob("*")):
            if path.is_symlink():
                raise SystemExit("Symlink inputs are forbidden")
            if path.is_file():
                result[path.relative_to(workspace).as_posix()] = sha256(path)
    if not result:
        raise SystemExit("Workspace source is missing")
    return result


def testdata_hashes():
    folder = ROOT / "inputs/reference_model/testdata"
    return {p.name: sha256(p) for p in sorted(folder.glob("test_data_*.txt")) if p.is_file() and not p.is_symlink()}


def spec_hashes():
    folder = ROOT / "inputs/specifications"
    return {p.relative_to(folder).as_posix(): sha256(p) for p in sorted(folder.rglob("*.md")) if p.is_file() and not p.is_symlink()}


def runtime_hashes():
    paths = list((ROOT / "rag/automation").glob("*.py")) + list((ROOT / "rag/automation").glob("*.tcl"))
    paths += [ROOT / "manifests" / name for name in ("automation_loop_policy.yaml", "phase_access_policy.yaml")]
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths if p.is_file()}


def safe_run(target, run_id):
    if target not in ("systolic_prototype", "optimized_accelerator") or not re.fullmatch(r"(?:run_\d{3,}|review_\d{8})", run_id):
        raise SystemExit("Invalid target/run identifier")
    return ROOT / "experiments" / "automation_loop" / target / run_id


def bound_artifact(path):
    path = path.resolve()
    if not path.is_relative_to((ROOT / "artifacts").resolve()) or not path.is_dir():
        raise SystemExit("Evidence must be an existing local artifacts directory")
    return path


def next_run_id(target_root: Path) -> str:
    ids = [int(path.name.split("_")[-1]) for path in target_root.glob("run_[0-9][0-9][0-9]")]
    return f"run_{max(ids, default=0) + 1:03d}"


def run_command(command: list[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(command, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")
    log_path.write_text(process.stdout + "\n" + process.stderr, encoding="utf-8")
    return process.returncode


def write_diagnosis(path: Path, target: str, run_id: str, findings: list[dict[str, Any]]) -> None:
    lines = [f"# {target} {run_id} Diagnosis", "", "이 문서는 도구가 수집한 원본 증거에서 자동 생성되었습니다.", ""]
    if not findings:
        lines.extend(["## Result", "", "설정된 탐지 규칙에서 Finding이 발견되지 않았습니다."])
    for finding in findings:
        lines.extend([
            f"## {finding['finding_id']}", "",
            f"- Category: `{finding['category']}`",
            f"- Severity: `{finding['severity']}`",
            f"- State: `{finding['state']}`",
            f"- Summary: {finding['summary']}",
            f"- Evidence: `{json.dumps(finding['evidence'], ensure_ascii=False)}`",
            "- Required chain: `SPEC Requirement ID → 실패 증거 → 수정 내용 → 재검증 결과`", "",
        ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(args: argparse.Namespace, config: dict[str, Any]) -> int:
    target = args.target
    artifact_root = bound_artifact(ROOT / (args.artifact_root or f"artifacts/synthesis/{target}/run_001"))
    target_root = ROOT / "experiments" / "automation_loop" / target
    run_id = args.run_id or next_run_id(target_root)
    run_root = safe_run(target, run_id)
    if run_root.exists() and any(run_root.iterdir()):
        raise SystemExit(f"Refusing to overwrite existing run: {run_root}")

    metrics = collect_metrics(artifact_root)
    metrics["previous_metrics"] = getattr(args, "previous_metrics", None)
    findings = detect(metrics, config)
    workspace = Path(getattr(args, "source_workspace", None) or ROOT / "workspace" / target)
    if not workspace.resolve().is_relative_to(ROOT.resolve()):
        raise SystemExit("Workspace must be local")
    binding = {"workspace": workspace.relative_to(ROOT).as_posix(), "source_hashes": source_hashes(workspace),
        "testdata_hashes": testdata_hashes(),
        "spec_hashes": spec_hashes(),
        "runtime_hashes": runtime_hashes(),
        "config_sha256": fingerprint(config), "findings_sha256": fingerprint(findings),
        "evidence_hashes": {path.name: sha256(path) for path in artifact_root.iterdir() if path.is_file()}}
    status = "findings_detected_pending_human_approval" if findings else "analysis_passed_pending_regression"
    dump_json(run_root / "analysis_result.json", {
        "schema_version": "1.0", "target": target, "run_id": run_id, "status": status,
        "artifact_root": artifact_root.relative_to(ROOT).as_posix(), "metrics": metrics,
        "finding_ids": [item["finding_id"] for item in findings],
    })
    dump_yaml(run_root / "findings.yaml", {"schema_version": "1.0", "target": target,
        "run_id": run_id, "findings": findings})
    dump_yaml(run_root / "approval.yaml", {"schema_version": "1.0", "target": target,
        "run_id": run_id, "overall_state": "pending_human_approval" if findings else "not_required",
        "items": {item["finding_id"]: {"decision": "pending", "rtl_change_allowed": False,
            "approved_spec_requirement": None} for item in findings}})
    dump_yaml(run_root / "run_manifest.yaml", {
        "schema_version": "1.0", "experiment_type": "automation_loop", "target": target,
        "run_id": run_id, "status": status,
        "binding": binding,
        "parent_run": getattr(args, "parent_run", None),
        "iteration": getattr(args, "iteration", 0),
        "source": {"workspace": f"workspace/{target}", "artifact_root": artifact_root.relative_to(ROOT).as_posix(),
            "historical_baseline_used": False, "external_knowledge_used": False},
        "evidence_hashes": {path.name: sha256(path) for path in artifact_root.glob("*") if path.is_file()},
        "finding_ids": [item["finding_id"] for item in findings],
        "next_action": "human_review" if findings else "run_regression",
    })
    write_diagnosis(run_root / "diagnosis.md", target, run_id, findings)
    dump_json(run_root / "coverage.json", metrics.get("coverage", {}))
    dump_json(run_root / "gate_status.json", {"status": "not_approved", "message": "Run is not approved for patch generation."})
    (run_root / "spec_change_proposal.md").write_text(
        "# Pending review — not an approved SPEC\n\n" + "\n".join(f"- {f['finding_id']}: {f['summary']}" for f in findings)
        + "\n\nAssign an approved SPEC Requirement ID to each authorized change. No approved SPEC was modified.\n", encoding="utf-8")
    print(f"{status}: {run_root.relative_to(ROOT)}")
    return 2 if findings else 0


def approve(args: argparse.Namespace, config: dict[str, Any]) -> int:
    run_root = safe_run(args.target, args.run_id)
    manifest = load_yaml(run_root / "run_manifest.yaml")
    binding = verify_binding(run_root, config)
    if args.decision == "approved" and not args.requirement_id:
        raise SystemExit("An approved SPEC Requirement ID is required")
    path = run_root / "approval.yaml"
    approval = load_yaml(path)
    if args.finding_id not in approval.get("items", {}):
        raise SystemExit(f"Unknown finding: {args.finding_id}")
    item = approval["items"][args.finding_id]
    item.update({"decision": args.decision, "rtl_change_allowed": args.decision == "approved",
                 "approved_spec_requirement": args.requirement_id,
                 "reviewed_at": datetime.now(timezone.utc).isoformat()})
    item["binding_sha256"] = fingerprint(binding)
    decisions = [entry["decision"] for entry in approval["items"].values()]
    approval["overall_state"] = "approved_for_patch_generation" if "pending" not in decisions and "approved" in decisions else (
        "closed_without_patch" if set(decisions) == {"rejected"} else "pending_human_approval")
    dump_yaml(path, approval)
    dump_json(run_root / "gate_status.json", {
        "schema_version": "1.0",
        "target": args.target,
        "run_id": args.run_id,
        "status": approval["overall_state"],
        "message": "Run is approved for patch generation." if approval["overall_state"] == "approved_for_patch_generation" else "Run is not approved for patch generation.",
    })
    print(approval["overall_state"])
    return 0




def verify_binding(run_root, config):
    manifest = load_yaml(run_root / "run_manifest.yaml")
    binding = manifest.get("binding")
    if not binding:
        raise SystemExit("Legacy run has no approval binding; collect a fresh analysis before approval")
    workspace = (ROOT / binding["workspace"]).resolve()
    if not workspace.is_relative_to(ROOT.resolve()):
        raise SystemExit("Invalid bound source")
    artifact = bound_artifact(ROOT / manifest["source"]["artifact_root"])
    current = {"workspace": binding["workspace"], "source_hashes": source_hashes(workspace),
        "testdata_hashes": testdata_hashes(),
        "spec_hashes": spec_hashes(),
        "runtime_hashes": runtime_hashes(),
        "config_sha256": fingerprint(config),
        "findings_sha256": fingerprint(load_yaml(run_root / "findings.yaml")["findings"]),
        "evidence_hashes": {path.name: sha256(path) for path in artifact.iterdir() if path.is_file()}}
    if current != binding:
        raise SystemExit("Stale evidence/source/config: approval invalidated; re-analyze")
    return binding


def validate_patch(path):
    text = path.read_text(encoding="utf-8")
    headers = re.findall(r"(?m)^(?:---|\+\+\+) ([^\t\r\n]+)", text)
    if not headers or len(headers) % 2 or re.search(r"(?m)^(?:rename |copy |old mode|new mode|new file mode|deleted file mode|GIT binary)", text):
        raise SystemExit("Only text modifications of existing RTL files are permitted")
    touched = []
    for name in headers:
        if not re.fullmatch(r"[ab]/rtl/[A-Za-z0-9_]+\.svh?", name):
            raise SystemExit("Patch path is outside the authorized RTL scope")
        touched.append(name[2:])
    for a, b in zip(touched[::2], touched[1::2]):
        if a != b:
            raise SystemExit("Patch may not rename files")
    for a, b in re.findall(r"(?m)^diff --git (\S+) (\S+)$", text):
        if a[2:] not in touched or b[2:] != a[2:] or not a.startswith("a/") or not b.startswith("b/"):
            raise SystemExit("Conflicting patch headers")
    return sorted(set(touched))


def resume(args: argparse.Namespace, config: dict[str, Any]) -> int:
    run_root = safe_run(args.target, args.run_id)
    approval = load_yaml(run_root / "approval.yaml")
    if approval.get("overall_state") != "approved_for_patch_generation":
        dump_json(run_root / "gate_status.json", {"status": "not_approved", "message": "Run is not approved for patch generation."})
        raise SystemExit("Run is not approved for patch generation.")
    binding = verify_binding(run_root, config)
    if any(row.get("binding_sha256") != fingerprint(binding) or row.get("decision") not in ("approved", "rejected") for row in approval["items"].values()):
        raise SystemExit("Every finding requires a fresh bound human decision")
    manifest = load_yaml(run_root / "run_manifest.yaml")
    if manifest.get("iteration", 0) >= config["loop"]["max_iterations"] or manifest.get("stop_reason"):
        raise SystemExit("Iteration stop condition reached")
    commands = config.get("commands", {}).get(args.target, [])
    if [c.get("stage") for c in commands] != ["compile", "simulation", "synthesis"]:
        raise SystemExit("Compile/simulation/synthesis commands must all be configured")
    if any(not Path(c["tool"]).is_file() for c in commands):
        raise SystemExit("Configured tool is missing")
    patch = run_root / "proposed_patch.diff"
    if not patch.is_file():
        dump_json(run_root / "patch_request.json", {"state": "waiting_for_agent_patch",
            "approved_findings": [fid for fid, row in approval["items"].items() if row["decision"] == "approved"],
            "binding_sha256": fingerprint(binding), "required_patch_trace": "patch_trace.yaml: finding_id -> requirement_id -> files -> explanation",
            "external_llm_api": False, "historical_baselines": False})
        return 3
    touched = validate_patch(patch)
    trace = load_yaml(run_root / "patch_trace.yaml")
    authorized_files = set()
    for item in trace.get("changes", []):
        decision = approval["items"].get(item["finding_id"], {})
        if decision.get("decision") != "approved" or item.get("requirement_id") != decision.get("approved_spec_requirement") or not item.get("explanation"):
            raise SystemExit("Patch trace is not covered by approved findings")
        authorized_files.update(item["files"])
    if set(touched) != authorized_files:
        raise SystemExit("Patch trace must cover exactly the touched RTL files")
    isolation = ROOT / ".automation_debug" / args.target / args.run_id
    debug = isolation / "project" / "workspace" / args.target
    if isolation.exists():
        raise SystemExit("Debug workspace already exists; inspect prior execution instead of overwriting")
    baseline = ROOT / binding["workspace"]
    debug.mkdir(parents=True)
    for folder in ("rtl", "tb", "memory", "scripts"):
        shutil.copytree(baseline / folder, debug / folder)
    data_out = isolation / "project/inputs/reference_model/testdata"
    data_out.mkdir(parents=True)
    for name in binding["testdata_hashes"]:
        shutil.copy2(ROOT / "inputs/reference_model/testdata" / name, data_out / name)
    if source_hashes(debug) != binding["source_hashes"]:
        raise SystemExit("Source changed during isolation copy; refusing patch")
    if {p.name: sha256(p) for p in data_out.iterdir()} != binding["testdata_hashes"]:
        raise SystemExit("Testdata changed during isolation copy")
    if run_command(["git", "init", "--quiet"], debug, run_root / "isolation.log"):
        raise SystemExit("Cannot initialize isolated debug repository")
    for mode in ("--check", ""):
        command = ["git", "apply", *([mode] if mode else []), str(patch.resolve())]
        if run_command(command, debug, run_root / ("patch_check.log" if mode else "patch_apply.log")):
            dump_json(run_root / "gate_status.json", {"status": "patch_failed", "promoted": False})
            return 4
    child = next_run_id(run_root.parent)
    combined = ROOT / "artifacts" / "automation_loop" / args.target / child
    combined.mkdir(parents=True, exist_ok=False)
    stages = []
    for command in commands:
        stage = command["stage"]
        kind = "synthesis" if stage == "synthesis" else "verification"
        out = ROOT / "artifacts" / kind / args.target / child
        out.mkdir(parents=True, exist_ok=True)
        dump_json(run_root / "progress.json", {"stage": stage, "child_run": child, "state": "running"})
        try:
            code = tool_flow.run(stage, debug, out, command["tool"], Path(__file__).with_name("synthesis.tcl"))
        except Exception as exc:
            (out / f"{stage}.log").write_text(f"ERROR: {exc}\n", encoding="utf-8")
            code = 1
        stages.append({"stage": stage, "exit_code": code, "tool": command["tool"], "artifact_root": out.relative_to(ROOT).as_posix()})
        for file in out.iterdir():
            if file.is_file() and file.suffix in (".log", ".rpt", ".json"):
                shutil.copy2(file, combined / file.name)
        if code:
            break
    result = {"parent_run": args.run_id, "child_run": child, "stages": stages, "patch_sha256": sha256(patch),
        "source_hashes": source_hashes(debug), "all_tools_passed": len(stages) == 3 and all(s["exit_code"] == 0 for s in stages), "promoted": False}
    dump_json(combined / "execution_result.json", result)
    analyze(argparse.Namespace(target=args.target, run_id=child, artifact_root=combined.relative_to(ROOT).as_posix(),
        source_workspace=debug, parent_run=args.run_id, iteration=manifest.get("iteration", 0) + 1,
        previous_metrics=json.loads((run_root / "analysis_result.json").read_text(encoding="utf-8"))["metrics"]), config)
    child_root = run_root.parent / child
    child_manifest = load_yaml(child_root / "run_manifest.yaml")
    child_findings = load_yaml(child_root / "findings.yaml")["findings"]
    ids = sorted(f["finding_id"] for f in child_findings)
    previous_ids = sorted(manifest.get("finding_ids", []))
    repeats = manifest.get("repeat_count", 0) + 1 if ids == previous_ids else 0
    child_manifest["repeat_count"] = repeats
    if repeats >= config["loop"]["stop_on_repeated_fingerprint"]:
        child_manifest["stop_reason"] = "repeated_findings_require_human_replan"
    child_manifest["status"] = "pending_human_review" if child_findings else "candidate_pending_full_regression_and_human_acceptance"
    dump_yaml(child_root / "run_manifest.yaml", child_manifest)
    result["finding_ids"] = ids
    result["resolved_finding_ids"] = sorted(set(previous_ids) - set(ids))
    old_metrics = json.loads((run_root / "analysis_result.json").read_text(encoding="utf-8"))["metrics"]
    new_metrics = json.loads((child_root / "analysis_result.json").read_text(encoding="utf-8"))["metrics"]
    result["metric_comparison"] = {key: {"before": old_metrics.get(key), "after": new_metrics.get(key)}
        for key in ("utilization", "timing", "power", "verification")}
    before_samples = old_metrics.get("verification", {}).get("sample_results")
    after_samples = new_metrics.get("verification", {}).get("sample_results")
    result["sample_regression"] = "unknown" if not before_samples or not after_samples else ("pass" if before_samples == after_samples else "fail")
    result["post_route_revalidation"] = "not_run_pending_implementation"
    result["state"] = child_manifest["status"]
    dump_json(child_root / "revalidation_result.json", result)
    dump_json(run_root / "revalidation_result.json", result)
    dump_json(run_root / "progress.json", {"state": "awaiting_human_review", "child_run": child})
    return 2 if child_findings or not result["all_tools_passed"] else 0


def status(args: argparse.Namespace, config: dict[str, Any]) -> int:
    del config
    target_root = ROOT / "experiments" / "automation_loop" / args.target
    for path in sorted(target_root.glob("run_*/run_manifest.yaml")):
        manifest = load_yaml(path)
        print(f"{manifest.get('run_id')}: {manifest.get('status')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)
    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("--target", required=True, choices=["systolic_prototype", "optimized_accelerator"])
    analyze_parser.add_argument("--artifact-root")
    analyze_parser.add_argument("--run-id")
    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--target", required=True)
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--finding-id", required=True)
    approve_parser.add_argument("--decision", required=True, choices=["approved", "rejected"])
    approve_parser.add_argument("--requirement-id")
    resume_parser = sub.add_parser("resume")
    resume_parser.add_argument("--target", required=True)
    resume_parser.add_argument("--run-id", required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--target", required=True)
    args = parser.parse_args()
    config = load_yaml(args.config)
    return {"analyze": analyze, "approve": approve, "resume": resume, "status": status}[args.command](args, config)


if __name__ == "__main__":
    sys.exit(main())
