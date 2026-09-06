"""CLI orchestrator for evidence collection, approval gating and revalidation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc

from detectors import detect
from parsers import collect_metrics


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
    artifact_root = ROOT / (args.artifact_root or f"artifacts/synthesis/{target}/run_001")
    target_root = ROOT / "experiments" / "automation_loop" / target
    run_id = args.run_id or next_run_id(target_root)
    run_root = target_root / run_id
    if run_root.exists() and any(run_root.iterdir()):
        raise SystemExit(f"Refusing to overwrite existing run: {run_root}")

    metrics = collect_metrics(artifact_root)
    findings = detect(metrics, config)
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
        "source": {"workspace": f"workspace/{target}", "artifact_root": artifact_root.relative_to(ROOT).as_posix(),
            "historical_baseline_used": False, "external_knowledge_used": False},
        "evidence_hashes": {path.name: sha256(path) for path in artifact_root.glob("*") if path.is_file()},
        "finding_ids": [item["finding_id"] for item in findings],
        "next_action": "human_review" if findings else "run_regression",
    })
    write_diagnosis(run_root / "diagnosis.md", target, run_id, findings)
    print(f"{status}: {run_root.relative_to(ROOT)}")
    return 2 if findings else 0


def approve(args: argparse.Namespace, config: dict[str, Any]) -> int:
    del config
    run_root = ROOT / "experiments" / "automation_loop" / args.target / args.run_id
    path = run_root / "approval.yaml"
    approval = load_yaml(path)
    if args.finding_id not in approval.get("items", {}):
        raise SystemExit(f"Unknown finding: {args.finding_id}")
    item = approval["items"][args.finding_id]
    item.update({"decision": args.decision, "rtl_change_allowed": args.decision == "approved",
                 "approved_spec_requirement": args.requirement_id,
                 "reviewed_at": datetime.now(timezone.utc).isoformat()})
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


def resume(args: argparse.Namespace, config: dict[str, Any]) -> int:
    run_root = ROOT / "experiments" / "automation_loop" / args.target / args.run_id
    approval = load_yaml(run_root / "approval.yaml")
    if approval.get("overall_state") != "approved_for_patch_generation":
        dump_json(run_root / "gate_status.json", {
            "schema_version": "1.0",
            "target": args.target,
            "run_id": args.run_id,
            "status": "not_approved",
            "message": "Run is not approved for patch generation.",
            "next_action": "Review every Finding and record an approved or rejected decision in approval.yaml.",
        })
        raise SystemExit("Run is not approved for patch generation.")
    patch_path = run_root / "proposed_patch.diff"
    if not patch_path.is_file():
        request = {
            "state": "waiting_for_agent_patch",
            "instruction": "Generate proposed_patch.diff from approved SPEC, current Workspace RTL and validated Automation Loop evidence only.",
            "approved_findings": [key for key, value in approval["items"].items() if value["decision"] == "approved"],
            "historical_baseline_access_allowed": False,
            "external_knowledge_allowed": False,
        }
        dump_json(run_root / "patch_request.json", request)
        dump_json(run_root / "gate_status.json", {
            "schema_version": "1.0", "target": args.target, "run_id": args.run_id,
            "status": "approved_waiting_for_agent_patch",
            "message": "Run is approved; waiting for an evidence-constrained Agent patch.",
        })
        print("waiting_for_agent_patch")
        return 3

    debug_root = ROOT / ".automation_debug" / args.target / args.run_id
    if debug_root.exists():
        raise SystemExit(f"Debug workspace already exists: {debug_root}")
    shutil.copytree(ROOT / "workspace" / args.target, debug_root)
    result = run_command(["git", "apply", "--check", str(patch_path)], debug_root, run_root / "patch_check.log")
    if result != 0:
        print("patch_check_failed")
        return 4
    result = run_command(["git", "apply", str(patch_path)], debug_root, run_root / "patch_apply.log")
    if result != 0:
        print("patch_apply_failed")
        return 4
    commands = config.get("commands", {}).get(args.target, [])
    for index, command in enumerate(commands, 1):
        code = run_command([str(part) for part in command], debug_root, run_root / f"command_{index:02d}.log")
        if code:
            print(f"command_failed:{index}")
            return code
    print("patch_applied_in_isolated_debug_workspace; collect artifacts and run analyze again")
    return 0


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
