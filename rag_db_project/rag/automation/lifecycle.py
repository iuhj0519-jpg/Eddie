"""Versioned requirement lifecycle. Local, approval-gated; never edits baseline SPEC/RTL."""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml


def read(path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / "inputs/specifications").rglob("*.md"))}


def target_root(root, target):
    if target not in ("optimized_accelerator", "systolic_prototype"):
        raise SystemExit("Invalid target")
    return root / "experiments/automation_loop" / target


def sync(root):
    """Refresh allowlisted provenance inventory then the existing local RAG index."""
    receipt = root / "rag/runs/lifecycle_sync.yaml"
    write(receipt, {"state": "running"})
    commands = [
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(root / "manifests/refresh_automation_inventory.ps1")],
        [sys.executable, str(root / "rag/ingest/build_index.py"), "--project-root", str(root),
         "--config", str(root / "rag/config/automation_loop_index.yaml")]]
    for command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=300)
        if result.returncode:
            write(receipt, {"state": "failed", "detail": result.stdout + result.stderr})
            raise SystemExit("RAG refresh failed; inspect rag/runs/lifecycle_sync.yaml and retry sync")
    write(receipt, {"state": "ready", "updated_at": datetime.now(timezone.utc).isoformat()})


def condition(metric, op, value):
    return {"metric": metric, "op": op, "value": value}


def requirement(fid, evidence, index):
    """Conservative proposals, not claims that a root cause or fix has been proved."""
    check = []
    action = "Investigate the cited evidence, preserve functional contracts, and resolve or document the finding."
    risk = "Do not suppress a warning or relax a requirement merely to obtain PASS."
    kind = "compliance"
    if fid == "PPA-MEMORY-MAPPING-001":
        action = "Implement Weight storage in physical block memory with five-lane supply, correct initialization, capacity and synchronous read alignment."
        check = [condition("ram.weight_block_count", "gt", 0)]
        risk = "BRAM presence alone does not prove all weights are stored or five reads are supplied; verify bank coverage and data."
    elif fid == "PPA-TIMING-001":
        action = "Meet setup timing at the approved clock after routing; retain I/O and clock constraints."
        check = [condition("timing.wns_ns", "ge", 0), condition("timing.tns_ns", "ge", 0)]
    elif fid == "PPA-DSP-001":
        action = "Demonstrate the approved 25-PE independent MAC mapping and cycle-level concurrency; distinguish DSP allocation from PE activity."
        check = [condition("utilization.dsp", "ge", 25), condition("verification.peak_active_pe_count", "ge", 25)]
        risk = "Count alone cannot prove PE mapping. Confirm DSP instance ownership and numeric equivalence."
    elif fid == "PPA-POWER-001":
        action = "Collect representative activity, mapping coverage and identical environment settings; report activity-based power with limitations."
        risk = "No arbitrary toggle-rate changes; power confidence is evidence quality, not a power budget."
    elif fid.startswith("PPA-WEIGHT"):
        action = "Reduce Weight logic/selection overhead using banked storage; retain five-lane throughput and complete weight contents."
        kind = "optimization"
    elif fid in ("PPA-ADDRESS-001", "PPA-MUX-001", "PPA-PIPELINE-001", "PPA-ROUTE-DELAY-001", "PPA-FANOUT-001"):
        action = {"PPA-ADDRESS-001": "Restructure critical address arithmetic and bank decode with correct address/data/valid latency.",
                  "PPA-MUX-001": "Reduce critical selection depth and check memory inference rather than hiding selection in equivalent logic.",
                  "PPA-PIPELINE-001": "Partition the critical combinational path and align scheduler, valid and memory latency.",
                  "PPA-ROUTE-DELAY-001": "Reduce critical routing delay, checking placement and load distribution against the same constraints.",
                  "PPA-FANOUT-001": "Reduce high-fanout timing impact by reviewing replicated/local control and address distribution."}[fid]
        kind = "optimization"
        risk = "Extra registers, latency or area may be justified only by measured benefit under comparable workloads."
    elif fid.startswith("DRC-") or fid.startswith("IMPL-"):
        action = "Resolve or explicitly disposition " + fid + " using the full DRC evidence and actual board/clock/reset contract."
    elif fid.startswith("EVIDENCE-") or fid == "PPA-CONSTRAINT-001":
        kind = "evidence"
        action = "Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS."
    elif fid.startswith("REGRESSION-"):
        kind = "optimization"
        action = "Compare the parent and candidate under identical stage, clock, workload and activity assumptions; quantify the benefit/cost tradeoff before accepting regression."
        if fid == "REGRESSION-TOTAL-ON-CHIP-POWER-W":
            action = "Developer must choose average_power, energy_per_workload or balanced priority and record power_tradeoff with max_average_power_w, max_energy_per_workload_uj and rationale before SPEC approval. Preserve correctness and timing requirements. Verify both limits from comparable SAIF reports and matching workload durations before final acceptance."
            risk = "SAIF power and P*t energy are estimates; low direct annotation and timing failure prohibit claims of measured energy efficiency. No automatic priority or regression waiver."
    rid = "REQ-LOOP-" + re.sub(r"[^A-Z0-9]", "-", fid.upper())
    # Review evidence is required even when a numeric condition exists.
    check.append(condition("review." + rid, "eq", True))
    return {"requirement_id": rid, "finding_ids": [fid], "kind": kind,
            "before": evidence, "after": action, "acceptance": check,
            "verification": "Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.",
            "expected_benefit": "Remove the cited violation or demonstrate a justified PPA improvement.",
            "risk": risk, "status": "proposed"}


def render(folder, proposal):
    write(folder / "requirements.yaml", proposal)
    lines = ["# SPEC change proposal — pending human approval", "",
             "This is an additive overlay; baseline SPEC is not replaced or weakened.", "",
             "Proposal digest: `" + digest(proposal) + "`", ""]
    for row in proposal["requirements"]:
        lines += ["## " + row["requirement_id"], "", "- Type: " + row["kind"],
                  "- Findings: " + ", ".join(row["finding_ids"]),
                  "- Before/evidence: " + json.dumps(row["before"], ensure_ascii=False),
                  "- Required change: " + row["after"],
                  "- Acceptance: " + json.dumps(row["acceptance"], ensure_ascii=False),
                  "- Verification: " + row["verification"], "- Benefit: " + row["expected_benefit"],
                  "- Risk: " + row["risk"], ""]
        if "power_tradeoff" in row:
            lines += ["- Developer power/energy decision: " + json.dumps(row["power_tradeoff"], ensure_ascii=False), ""]
    (folder / "spec_change_proposal.md").write_text("\n".join(lines), encoding="utf-8")


def propose(root, run, target, findings, revision=None):
    previous = get_revision(root, target, revision)["requirements"] if revision else []
    rows = {r["requirement_id"]: r for r in previous}
    for i, f in enumerate(findings):
        # A failed approved requirement remains the same contract, not a weaker replacement.
        if f["finding_id"].startswith("SPEC-CHECK-"):
            continue
        row = requirement(f["finding_id"], f["evidence"], i)
        if row["requirement_id"] not in rows:
            rows[row["requirement_id"]] = row
    proposal = {"schema_version": "2.0", "target": target, "parent_revision": revision,
                "state": "draft", "origin": run.name, "requirements": list(rows.values())}
    render(run, proposal)


def intake(root, target, request_id, source):
    if not re.fullmatch(r"request_[0-9]{3,}", request_id):
        raise SystemExit("Use request_NNN")
    folder = target_root(root, target) / "requests" / request_id
    if folder.exists():
        raise SystemExit("Request already exists")
    raw = source.read_text(encoding="utf-8")
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    if not parts:
        raise SystemExit("Request is empty")
    folder.mkdir(parents=True)
    (folder / "request.md").write_text(raw, encoding="utf-8")
    rows = []
    for n, part in enumerate(parts, 1):
        row = requirement("USER-" + request_id.upper() + "-" + str(n), {"raw_request": part}, n)
        row.update(after=part, kind="developer_request", verification="Define measurable acceptance before approval.",
                   acceptance=[], status="needs_acceptance_definition")
        rows.append(row)
    render(folder, {"schema_version": "2.0", "target": target, "origin": request_id,
                    "parent_revision": None, "state": "draft", "requirements": rows})
    sync(root)
    return folder


def attach_request(root, run, target, request_id):
    if not re.fullmatch(r"request_[0-9]{3,}", request_id):
        raise SystemExit("Use request_NNN")
    request = read(target_root(root, target) / "requests" / request_id / "requirements.yaml")
    proposal = read(run / "requirements.yaml")
    known = {r["requirement_id"] for r in proposal["requirements"]}
    proposal["requirements"] += [r for r in request["requirements"] if r["requirement_id"] not in known]
    proposal["request_digest"] = digest(request)
    render(run, proposal)


def get_revision(root, target, revision):
    if not revision or not re.fullmatch(r"spec_[0-9]{3,}", revision):
        raise SystemExit("An approved SPEC revision is required")
    folder = target_root(root, target) / "spec_versions" / revision
    document, approval = read(folder / "spec.yaml"), read(folder / "approval.yaml")
    if (document.get("target") != target or document.get("state") != "approved"
            or digest(document) != approval.get("spec_sha256")
            or document.get("baseline_hashes") != hashes(root)):
        raise SystemExit("Stale or invalid approved SPEC revision")
    for parent, expected in document.get("ancestor_hashes", {}).items():
        if digest(get_revision(root, target, parent)) != expected:
            raise SystemExit("Stale parent SPEC")
    return document


def validate_power_tradeoff(row):
    if "REGRESSION-TOTAL-ON-CHIP-POWER-W" not in row.get("finding_ids", []):
        return
    decision = row.get("power_tradeoff") or {}
    if not isinstance(decision, dict) or decision.get("priority") not in (
            "average_power", "energy_per_workload", "balanced"):
        raise SystemExit("Developer power/energy priority required before SPEC approval")
    if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
        raise SystemExit("Developer power/energy rationale required")
    for key in ("max_average_power_w", "max_energy_per_workload_uj"):
        value = decision.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise SystemExit("Positive finite power/energy limits required")
    rid = row["requirement_id"]
    if condition("review." + rid, "eq", True) not in row.get("acceptance", []):
        raise SystemExit("Power/energy evidence review required before final acceptance")


def approve_spec(root, target, folder, reviewer, expected):
    folder = folder.resolve()
    if not folder.is_relative_to(target_root(root, target).resolve()):
        raise SystemExit("Proposal outside target")
    proposal = read(folder / "requirements.yaml")
    if not reviewer.strip() or digest(proposal) != expected or proposal.get("target") != target:
        raise SystemExit("Reviewer/proposal digest mismatch")
    rows = proposal.get("requirements", [])
    if not rows or len({r["requirement_id"] for r in rows}) != len(rows):
        raise SystemExit("Requirements must be nonempty and unique")
    for row in rows:
        validate_power_tradeoff(row)
        if not all(row.get(k) for k in ("after", "verification", "risk", "acceptance")):
            raise SystemExit("Define acceptance and verification before SPEC approval")
        for c in row["acceptance"]:
            if c.get("op") not in ("eq", "ge", "le", "gt", "lt") or not c.get("metric") or "value" not in c:
                raise SystemExit("Invalid acceptance predicate")
    parent = proposal.get("parent_revision")
    ancestors = {}
    if parent:
        prior = get_revision(root, target, parent)
        ancestors = {parent: digest(prior)}
        current_rows = {r["requirement_id"]: r for r in rows}
        for r in prior["requirements"]:
            if current_rows.get(r["requirement_id"]) != r:
                raise SystemExit("Existing approved requirements cannot be removed/relaxed by additive revision")
    versions = target_root(root, target) / "spec_versions"
    number = max([int(p.name.split("_")[1]) for p in versions.glob("spec_*")], default=0) + 1
    name = f"spec_{number:03d}"
    destination = versions / name
    destination.mkdir(parents=True, exist_ok=False)
    doc = {**proposal, "state": "approved", "revision": name, "baseline_hashes": hashes(root),
           "ancestor_hashes": ancestors}
    doc["requirements"] = [{**r, "status": "approved"} for r in rows]
    write(destination / "spec.yaml", doc)
    write(destination / "approval.yaml", {"reviewer": reviewer, "spec_sha256": digest(doc),
          "proposal_sha256": expected, "approved_at": datetime.now(timezone.utc).isoformat()})
    (destination / "SPEC.md").write_text("# Approved additive SPEC " + name + "\n\n" +
        "\n\n".join("## " + r["requirement_id"] + "\n" + r["after"] + "\nAcceptance: " +
                    json.dumps(r["acceptance"], ensure_ascii=False) for r in rows), encoding="utf-8")
    sync(root)
    return name


def evaluate(document, metrics):
    results = []
    for row in document["requirements"]:
        checks = []
        for c in row["acceptance"]:
            value = metrics
            for key in c["metric"].split("."):
                value = value.get(key) if isinstance(value, dict) else None
            if value is None:
                state = "unknown"
            else:
                try:
                    right = c["value"]
                    ok = {"eq": lambda: value == right, "ge": lambda: value >= right,
                          "le": lambda: value <= right, "gt": lambda: value > right,
                          "lt": lambda: value < right}[c["op"]]()
                    state = "pass" if ok else "fail"
                except (TypeError, KeyError):
                    state = "unknown"
            checks.append({**c, "observed": value, "state": state})
        states = [c["state"] for c in checks]
        results.append({"requirement_id": row["requirement_id"], "checks": checks,
                        "state": "fail" if "fail" in states else "unknown" if not states or "unknown" in states else "pass"})
    return results


def compare(metrics):
    previous = metrics.get("previous_metrics") or {}
    before_context, after_context = previous.get("comparison_context", {}), metrics.get("comparison_context", {})
    required = ("stage", "clock_period_ns", "workload_sha256", "activity_kind")
    comparable = all(before_context.get(k) is not None and before_context.get(k) == after_context.get(k) for k in required)
    rows = []
    for group, key, maximize in (("timing", "wns_ns", True), ("utilization", "lut", False),
                                ("utilization", "ff", False), ("power", "total_on_chip_power_w", False),
                                ("verification", "total_inference_cycles", False)):
        a, b = previous.get(group, {}).get(key), metrics.get(group, {}).get(key)
        row = {"metric": group + "." + key, "before": a, "after": b, "comparison_validated": comparable}
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            row.update(delta=b-a, direction="unchanged" if a == b else "better" if (b > a) == maximize else "worse")
        else:
            row["direction"] = "unknown"
        rows.append(row)
    return {"metrics": rows, "comparison_context_validated": comparable,
            "decision": "human_tradeoff_review" if comparable else "collect_comparable_evidence",
            "note": "Raw deltas do not prove an improvement when stage/clock/workload/activity differ or are missing."}


def authorize(root, target, revision, rid, fid):
    doc = get_revision(root, target, revision)
    matches = [r for r in doc["requirements"] if r["requirement_id"] == rid and
               (fid in r["finding_ids"] or fid == "SPEC-CHECK-" + rid)]
    if not matches:
        raise SystemExit("Requirement ID is not authorized for this finding in the approved SPEC")
    return digest(doc)


def review_requirement(loop, args):
    run = loop.safe_run(args.target, args.run_id)
    binding = loop.verify_binding(run, loop.load_yaml(loop.DEFAULT_CONFIG))
    manifest = read(run / "run_manifest.yaml")
    doc = get_revision(loop.ROOT, args.target, manifest.get("spec_revision"))
    if args.requirement_id not in {r["requirement_id"] for r in doc["requirements"]}:
        raise SystemExit("Unknown requirement")
    evidence = args.evidence.resolve()
    artifact = (loop.ROOT / manifest["source"]["artifact_root"]).resolve()
    if not args.reviewer.strip() or not evidence.is_relative_to(artifact) or not evidence.is_file():
        raise SystemExit("Use an existing evidence file from the bound artifact directory and name the reviewer")
    path = run / "requirement_reviews.yaml"
    reviews = read(path) if path.exists() else {}
    if args.requirement_id in reviews:
        raise SystemExit("Review is immutable; create a fresh analysis for a revised decision")
    reviews[args.requirement_id] = {"pass": args.decision == "pass", "reviewer": args.reviewer,
        "rationale": args.rationale, "evidence": evidence.relative_to(loop.ROOT).as_posix(),
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        "binding_sha256": loop.fingerprint(binding), "spec_sha256": digest(doc)}
    write(path, reviews)
    sync(loop.ROOT)
    return 0


def bind_spec(loop, args):
    run = loop.safe_run(args.target, args.run_id)
    loop.verify_binding(run, loop.load_yaml(loop.DEFAULT_CONFIG))
    manifest = read(run / "run_manifest.yaml")
    decisions = read(run / "approval.yaml")
    if manifest.get("spec_revision") or any(r["decision"] != "pending" for r in decisions["items"].values()):
        raise SystemExit("Cannot rebind SPEC after binding or finding decisions; create a fresh analysis")
    spec = get_revision(loop.ROOT, args.target, args.spec_revision)
    covered = {f for row in spec["requirements"] for f in row["finding_ids"]}
    if not set(manifest["finding_ids"]) <= covered:
        raise SystemExit("SPEC does not cover all detected findings")
    manifest.update(spec_revision=args.spec_revision, spec_sha256=digest(spec))
    write(run / "run_manifest.yaml", manifest)
    results = evaluate(spec, read(run / "analysis_result.json")["metrics"])
    loop.dump_json(run / "requirements_result.json", {"spec_revision": args.spec_revision,
        "state": "pass" if all(r["state"] == "pass" for r in results) else "needs_review", "results": results})
    sync(loop.ROOT)
    return 0


def accept(loop, args):
    run = loop.safe_run(args.target, args.run_id)
    binding = loop.verify_binding(run, loop.load_yaml(loop.DEFAULT_CONFIG))
    manifest = read(run / "run_manifest.yaml")
    doc = get_revision(loop.ROOT, args.target, manifest.get("spec_revision"))
    analysis = read(run / "analysis_result.json")
    metrics = analysis["metrics"]
    reviews = read(run / "requirement_reviews.yaml") if (run / "requirement_reviews.yaml").exists() else {}
    metrics["review"] = {}
    for rid, review in reviews.items():
        evidence = loop.ROOT / review["evidence"]
        if (review["binding_sha256"] != loop.fingerprint(binding) or review["spec_sha256"] != digest(doc)
                or hashlib.sha256(evidence.read_bytes()).hexdigest() != review["evidence_sha256"]):
            raise SystemExit("Stale requirement review")
        metrics["review"][rid] = review["pass"]
    results = evaluate(doc, metrics)
    if not results or any(r["state"] != "pass" for r in results):
        raise SystemExit("Approved requirements are FAIL/UNKNOWN; collect evidence or propose a new revision")
    artifact = loop.ROOT / manifest["source"]["artifact_root"]
    provenance = read(artifact / "execution_result.json") if (artifact / "execution_result.json").exists() else {}
    required = {"compile", "simulation", "synthesis", "implementation"}
    if (provenance.get("source_hashes") != binding["source_hashes"] or
            not required <= {s["stage"] for s in provenance.get("stages", []) if s["exit_code"] == 0}):
        raise SystemExit("Same-source compile/simulation/synthesis/post-route execution evidence is required")
    if (not (artifact / "route_status.rpt").exists() or
            not metrics.get("coverage") or
            metrics.get("implementation", {}).get("unrouted_nets") != 0 or
            metrics.get("implementation", {}).get("routing_errors") != 0 or
            not metrics.get("verification", {}).get("completed") or
            any(metrics.get("timing", {}).get(k, -1) < 0 for k in ("wns_ns", "whs_ns", "wpws_ns")) or
            any(r.get("state") == "unknown" for r in metrics.get("coverage", {}).values())):
        raise SystemExit("Post-route timing or evidence coverage incomplete")
    if (any(r.get("severity") in ("Error", "Critical Warning") for r in metrics.get("drc_rules", []))
            or any(metrics.get("unconstrained_io", {}).values())):
        raise SystemExit("Resolve critical DRC and I/O timing coverage before final acceptance")
    covered = {fid for row in doc["requirements"] for fid in row["finding_ids"]}
    if any(fid not in covered and not fid.startswith("SPEC-CHECK-") for fid in analysis["finding_ids"]):
        raise SystemExit("New findings need a SPEC proposal and fresh approval before final acceptance")
    # All non-optimization warnings remain subject to the approved manual evidence checks.
    if not args.reviewer.strip() or not args.rationale.strip():
        raise SystemExit("Human reviewer and tradeoff rationale required")
    path = run / "final_acceptance.yaml"
    if path.exists():
        raise SystemExit("Final acceptance already recorded")
    write(path, {"state": "human_accepted", "reviewer": args.reviewer, "rationale": args.rationale,
                 "binding_sha256": loop.fingerprint(binding), "spec_sha256": digest(doc),
                 "requirements": results, "promoted": False})
    sync(loop.ROOT)
    return 0


def register_cli(sub):
    p = sub.add_parser("intake")
    p.add_argument("--target", required=True)
    p.add_argument("--request-id", required=True)
    p.add_argument("--request-file", type=Path, required=True)
    p = sub.add_parser("approve-spec")
    p.add_argument("--target", required=True)
    p.add_argument("--proposal", type=Path, required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--expected-digest", required=True)
    sub.add_parser("sync")
    p = sub.add_parser("bind-spec")
    p.add_argument("--target", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--spec-revision", required=True)
    p = sub.add_parser("review-requirement")
    p.add_argument("--target", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--requirement-id", required=True)
    p.add_argument("--decision", choices=["pass", "fail"], required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--rationale", required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p = sub.add_parser("accept")
    p.add_argument("--target", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--rationale", required=True)


def dispatch(args, root):
    if args.command == "intake":
        print(intake(root, args.target, args.request_id, args.request_file))
    elif args.command == "approve-spec":
        print(approve_spec(root, args.target, args.proposal, args.reviewer, args.expected_digest))
    else:
        sync(root)
    return 0
