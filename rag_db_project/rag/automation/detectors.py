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


def detect(metrics: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
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
