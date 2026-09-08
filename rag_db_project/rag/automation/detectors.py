"""Generic detectors. No detector is restricted to a known DSP or SRAM issue."""

from __future__ import annotations

from typing import Any


def _finding(fid: str, category: str, severity: str, evidence: dict[str, Any], summary: str) -> dict[str, Any]:
    return {
        "finding_id": fid,
        "category": category,
        "severity": severity,
        "state": "detected_pending_human_approval",
        "evidence": evidence,
        "summary": summary,
        "automatic_action": "document_and_request_approval",
        "prohibited_action": "modify_rtl_spec_or_test_expectation_before_approval",
    }


def _base_detect(metrics: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    util = metrics.get("utilization", {})
    timing = metrics.get("timing", {})
    power = metrics.get("power", {})
    ram = metrics.get("ram", {})
    hierarchy = metrics.get("hierarchy", {})
    implementation = metrics.get("implementation", {})
    thresholds = policy.get("thresholds", {})
    architecture = policy.get("architecture", {})

    expected_dsp = int(architecture.get("array_rows", 5)) * int(architecture.get("array_columns", 5))
    observed_dsp = util.get("dsp")
    if observed_dsp is not None and observed_dsp < expected_dsp:
        findings.append(_finding(
            "PPA-DSP-001", "architecture_parallelism", "high",
            {"expected_concurrent_pe_count": expected_dsp, "observed_dsp48_count": observed_dsp,
             "artifact_path": "utilization.rpt"},
            "The report does not demonstrate one independently mapped DSP MAC per PE; confirm with cycle-level PE activity before changing RTL.",
        ))

    total_lut = util.get("lut") or 0
    hotspot_ratio = float(thresholds.get("module_lut_hotspot_ratio", 0.50))
    for instance, row in hierarchy.items():
        if row.get("module") == "(top)":
            continue
        ratio = row.get("total_lut", 0) / total_lut if total_lut else 0
        if ratio >= hotspot_ratio:
            finding_id = "PPA-WEIGHT-001" if "weight_sram" in instance.lower() else "PPA-HOTSPOT-" + str(len(findings) + 1).zfill(3)
            findings.append(_finding(
                finding_id, "hierarchical_lut_hotspot", "high",
                {"instance": instance, "instance_lut": row.get("total_lut"), "total_lut": total_lut,
                 "lut_ratio": round(ratio, 4), "ramb18": row.get("ramb18"),
                 "artifact_path": "utilization_hierarchical.rpt"},
                "One hierarchy consumes more than the configured share of total LUT resources.",
            ))

    if timing.get("wns_ns") is not None and timing["wns_ns"] < float(thresholds.get("minimum_wns_ns", 0.0)):
        findings.append(_finding(
            "PPA-TIMING-001", "setup_timing", "critical",
            {**timing, "artifact_path": "timing_summary.rpt"},
            "Setup timing constraints are not met; implementation timing must be rechecked after an approved pipeline or memory-path change.",
        ))

    confidence = str(power.get("confidence", "")).lower()
    if confidence and confidence not in {"high", "medium"}:
        findings.append(_finding(
            "PPA-POWER-001", "power_evidence_quality", "medium",
            {**power, "artifact_path": "power.rpt"},
            "Power confidence is low, so the value is directional and requires activity-based analysis before acceptance.",
        ))

    bram_efficiency = ram.get("minimum_bram_bit_efficiency_percent")
    if bram_efficiency is not None and bram_efficiency < float(thresholds.get("minimum_bram_bit_efficiency_percent", 35.0)):
        findings.append(_finding(
            "PPA-BRAM-001", "bram_efficiency", "medium",
            {**ram, "artifact_path": "ram_utilization.rpt"},
            "At least one inferred Block RAM has low bit utilization.",
        ))

    for key, fid in (("lut", "PPA-LUT-001"), ("ff", "PPA-FF-001"), ("io", "PPA-IO-001")):
        value = util.get(key)
        limit = thresholds.get(f"maximum_{key}_count")
        if value is not None and limit is not None and value > float(limit):
            findings.append(_finding(fid, "resource_budget", "high", {"observed": value, "limit": limit,
                "artifact_path": "utilization.rpt"}, f"{key.upper()} usage exceeds the configured project budget."))

    log_errors = sum(item.get("error_count", 0) for item in metrics.get("logs", []))
    assertion_errors = sum(item.get("assertion_failure_count", 0) for item in metrics.get("logs", []))
    timeouts = any(item.get("timeout_detected") for item in metrics.get("logs", []))
    if log_errors:
        findings.append(_finding("VERIFY-COMPILE-001", "compile_or_runtime_error", "critical",
            {"error_count": log_errors, "artifact_paths": [item["path"] for item in metrics["logs"]]},
            "One or more tool logs contain ERROR or FATAL records."))
    if assertion_errors:
        findings.append(_finding("VERIFY-PROTOCOL-001", "assertion_failure", "critical",
            {"assertion_failure_count": assertion_errors}, "Protocol or functional assertions failed."))
    if timeouts:
        findings.append(_finding("VERIFY-TIMEOUT-001", "simulation_timeout", "critical", {},
            "The simulation did not reach its completion condition before the watchdog expired."))

    if implementation.get("drc_violations", 0) or implementation.get("critical_warnings", 0):
        findings.append(_finding("IMPL-DRC-001", "implementation_drc", "critical",
            {**implementation, "artifact_path": "drc.rpt"},
            "Post-Route DRC contains violations or critical warnings."))
    if implementation.get("unrouted_nets") not in {None, 0}:
        findings.append(_finding("IMPL-ROUTE-001", "unrouted_nets", "critical",
            {**implementation, "artifact_path": "route_status.rpt"},
            "Implementation completed with unrouted nets."))

    result = metrics.get("verification", {})
    expected = policy.get("acceptance", {})
    observed_accuracy = result.get("accuracy_percent")
    observed_failures = result.get("failure_count")
    observed_protocol_errors = result.get("protocol_errors")
    observed_interrupts = result.get("interrupt_count_per_batch")
    observed_cycles = result.get("cycles_per_batch")
    peak_active_pe = result.get("peak_active_pe_count")
    if observed_accuracy is not None and observed_accuracy != expected.get("expected_accuracy_percent"):
        findings.append(_finding("VERIFY-ACCURACY-001", "accuracy_regression", "critical",
            {"observed": observed_accuracy, "expected": expected.get("expected_accuracy_percent")},
            "Accuracy differs from the approved acceptance value."))
    if observed_failures is not None and observed_failures != expected.get("expected_failures"):
        findings.append(_finding("VERIFY-FAILCOUNT-001", "classification_failure_count", "critical",
            {"observed": observed_failures, "expected": expected.get("expected_failures")},
            "Classification failure count differs from the approved acceptance value."))
    if observed_protocol_errors is not None and observed_protocol_errors != expected.get("protocol_errors", 0):
        findings.append(_finding("VERIFY-PROTOCOL-002", "protocol_error_count", "critical",
            {"observed": observed_protocol_errors, "expected": expected.get("protocol_errors", 0)},
            "Protocol error count differs from the approved acceptance value."))
    if observed_interrupts is not None and observed_interrupts != expected.get("interrupt_count_per_batch"):
        findings.append(_finding("VERIFY-INTR-001", "interrupt_contract", "critical",
            {"observed": observed_interrupts, "expected": expected.get("interrupt_count_per_batch")},
            "Interrupt count per batch differs from the Reference Model contract."))
    maximum_cycles = expected.get("maximum_cycles_per_batch")
    if observed_cycles is not None and maximum_cycles is not None and observed_cycles > maximum_cycles:
        findings.append(_finding("PERF-CYCLE-001", "cycle_budget", "high",
            {"observed": observed_cycles, "maximum": maximum_cycles},
            "Cycle count exceeds the approved performance budget."))
    if peak_active_pe is not None and peak_active_pe < expected_dsp:
        findings.append(_finding("PERF-PE-UTIL-001", "pe_activity", "high",
            {"observed_peak_active_pe_count": peak_active_pe, "expected_concurrent_pe_count": expected_dsp,
             "artifact_path": "verification_result.json"},
            "Cycle-level activity does not demonstrate simultaneous use of all Systolic Array PEs."))
    return findings


def detect(metrics: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    findings = _base_detect(metrics, policy)
    limits = policy.get("thresholds", {})
    def add(fid, category, evidence, summary, severity="high"):
        findings.append(_finding(fid, category, severity, evidence, summary))
    for requirement in policy.get("memory_mapping_requirements", []):
        rows = [(name, row) for name, row in metrics.get("hierarchy", {}).items()
                if row.get("module") == requirement["module"]]
        if not rows:
            add("EVIDENCE-MEMORY-MAPPING-001", "missing_memory_mapping_evidence", requirement,
                "Required memory hierarchy was not found. Physical mapping is UNKNOWN, not passed.", "medium")
        for name, row in rows:
            if requirement.get("storage") == "block_ram" and row.get("ramb18", 0) + row.get("ramb36", 0) == 0:
                add("PPA-MEMORY-MAPPING-001", "physical_memory_mapping", {
                    **requirement, "instance": name, "logic_lut": row.get("logic_lut"),
                    "lutram": row.get("lutram"), "ramb18": row.get("ramb18"), "ramb36": row.get("ramb36"),
                    "artifact_path": "utilization_hierarchical.rpt"},
                    "Requested block-memory mapping is absent. An SRAM module name or synchronous output register does not prove BRAM inference. Review banked storage/ROM inference and address selection, independently of the LUT hotspot threshold.")
    paths = [p for p in metrics.get("paths", []) if p["slack_ns"] < 0]
    for fid, category, selected, description in (
        ("PPA-ADDRESS-001", "address_generation_path", [p for p in paths if p["address_path"]],
         "Failing path includes address/control generation. Review widths, arithmetic and memory access latency; cause remains a hypothesis until RTL/netlist review."),
        ("PPA-MUX-001", "large_selection_path", [p for p in paths if p["mux_present"]],
         "Failing path traverses dedicated MUX resources. Review selection depth and BRAM inference without assuming a specific fix."),
        ("PPA-PIPELINE-001", "pipeline_depth", [p for p in paths if p.get("logic_levels", 0) >= limits.get("maximum_logic_levels", 12)],
         "Deep failing combinational paths require pipeline review including valid, address and scheduler alignment."),
        ("PPA-ROUTE-DELAY-001", "route_delay_dominance", [p for p in paths if p.get("route_ns", 0) / max(p.get("delay_ns", 0), .001) >= limits.get("route_delay_ratio", .6)],
         "Routing dominates a failing path. Review fanout and placement with logic changes; this is not proof of congestion.")):
        if selected:
            add(fid, category, {"paths": selected[:20]}, description)
    fanout = [p for p in metrics.get("fanout", []) if p["fanout"] >= limits.get("maximum_fanout", 500)]
    if fanout:
        add("PPA-FANOUT-001", "high_fanout", {"nets": fanout}, "High-fanout drivers require load distribution and timing review.")
    for rule in metrics.get("drc_rules", []):
        add("DRC-" + rule["rule"], "drc_rule", rule,
            "Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.",
            "critical" if rule["severity"] in ("Error", "Critical Warning") else "medium")
    if any(metrics.get("unconstrained_io", {}).values()):
        add("PPA-CONSTRAINT-001", "io_timing_coverage", metrics["unconstrained_io"], "External I/O delays are missing; timing coverage is incomplete.")
    if metrics.get("unbound_checkpoint_source"):
        add("EVIDENCE-PROVENANCE-001", "checkpoint_source_binding", {"artifact_path": "run_manifest.yaml"},
            "Checkpoint identity is hashed, but its original RTL source hash was not recorded. Do not infer source equivalence from the model name.", "medium")
    if metrics.get("implementation", {}).get("routing_errors", 0):
        add("IMPL-ROUTE-ERROR-001", "routing_errors", metrics["implementation"], "Routing errors require review.", "critical")
    warnings = [log for log in metrics.get("logs", []) if log.get("warning_count", 0)]
    if warnings:
        add("TOOL-WARNING-001", "unclassified_warning_review", {"logs": warnings}, "Review all raw warning records, including warnings not classified by a specific detector.", "medium")
    for key, fid in (("whs_ns", "PPA-HOLD-001"), ("wpws_ns", "PPA-PULSE-001")):
        value = metrics.get("timing", {}).get(key)
        if value is not None and value < 0:
            add(fid, "timing", {key: value}, "Timing check failed.", "critical")
    unknown = [key for key, row in metrics.get("coverage", {}).items() if row["state"] == "unknown"]
    if metrics.get("timing", {}).get("wns_ns") is None:
        unknown.append("parsed_setup_timing")
    if metrics.get("utilization", {}).get("lut") is None:
        unknown.append("parsed_utilization")
    if "whs_ns" not in metrics.get("timing", {}):
        unknown.append("hold_timing")
    verification = metrics.get("verification", {})
    for key in ("protocol_errors", "peak_active_pe_count", "interrupt_count_per_batch"):
        if verification.get(key) is None:
            unknown.append(key)
    if metrics.get("execution") and not metrics["execution"].get("all_tools_passed"):
        add("VERIFY-EXECUTION-001", "tool_execution", metrics["execution"], "Tool execution failed or stages were skipped; inspect raw logs.", "critical")
    if verification and not verification.get("completed", True):
        add("VERIFY-COMPLETION-001", "simulation_incomplete", verification, "Expected simulation completion was not observed.", "critical")
    previous = metrics.get("previous_metrics") or {}
    for group, key, lower_worse in (("timing", "wns_ns", True), ("utilization", "lut", False),
            ("utilization", "ff", False), ("power", "total_on_chip_power_w", False),
            ("verification", "total_inference_cycles", False)):
        before, after = previous.get(group, {}).get(key), metrics.get(group, {}).get(key)
        if before is not None and after is not None and (after < before if lower_worse else after > before):
            add("REGRESSION-" + key.upper().replace("_", "-"), "previous_run_regression",
                {"before": before, "after": after, "metric": key}, "Metric worsened versus parent run; review the tradeoff, not an automatic rejection of all design changes.")
    samples_before = previous.get("verification", {}).get("sample_results")
    samples_after = verification.get("sample_results")
    if samples_before and samples_after and samples_before != samples_after:
        add("VERIFY-SAMPLE-REGRESSION-001", "sample_prediction_regression",
            {"before": samples_before, "after": samples_after}, "Per-sample prediction changed despite possible equal aggregate accuracy.", "critical")
    if unknown:
        add("EVIDENCE-COVERAGE-001", "missing_evidence", {"unknown": sorted(set(unknown))},
            "Missing/unparsed evidence is UNKNOWN, never a pass. Collect evidence or request a human decision.", "medium")
    for item in findings:
        evidence = item["evidence"]
        name = evidence.get("artifact_path")
        if name:
            evidence["artifact_path"] = metrics.get("sources", {}).get(name.removesuffix(".rpt"), name)
    return findings
