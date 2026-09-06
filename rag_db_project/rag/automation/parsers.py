"""Parsers for Vivado, ModelSim and normalized verification artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


NUMBER = r"[-+]?\d+(?:\.\d+)?"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _table_value(text: str, label: str) -> float | None:
    match = re.search(rf"\|\s*{re.escape(label)}(?:\*|\s)*\|\s*({NUMBER})\s*\|", text)
    return float(match.group(1)) if match else None


def parse_utilization(path: Path) -> dict[str, Any]:
    text = _read(path)
    return {
        "lut": _table_value(text, "Slice LUTs"),
        "lut_logic": _table_value(text, "LUT as Logic"),
        "lut_memory": _table_value(text, "LUT as Memory"),
        "ff": _table_value(text, "Slice Registers"),
        "bram_tile": _table_value(text, "Block RAM Tile"),
        "ramb18": _table_value(text, "RAMB18"),
        "dsp": _table_value(text, "DSPs"),
        "io": _table_value(text, "Bonded IOB"),
    }


def parse_hierarchy(path: Path) -> dict[str, dict[str, Any]]:
    modules: dict[str, dict[str, Any]] = {}
    for line in _read(path).splitlines():
        if not line.startswith("|") or "Instance" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 10 or not cells[0] or cells[0].startswith("("):
            continue
        try:
            values = [float(value) for value in cells[2:]]
        except ValueError:
            continue
        instance = cells[0]
        modules[instance] = {
            "module": cells[1],
            "total_lut": values[0],
            "logic_lut": values[1],
            "lutram": values[2],
            "srl": values[3],
            "ff": values[4],
            "ramb36": values[5],
            "ramb18": values[6],
            "dsp": values[7],
        }
    return modules


def parse_timing(path: Path) -> dict[str, Any]:
    text = _read(path)
    match = re.search(
        rf"WNS\(ns\).*?\n\s*-+.*?\n\s*({NUMBER})\s+({NUMBER})\s+(\d+)\s+(\d+)\s+({NUMBER})\s+({NUMBER})\s+(\d+)\s+(\d+)",
        text,
        re.DOTALL,
    )
    if not match:
        return {}
    return {
        "wns_ns": float(match.group(1)),
        "tns_ns": float(match.group(2)),
        "setup_failing_endpoints": int(match.group(3)),
        "setup_total_endpoints": int(match.group(4)),
        "wpws_ns": float(match.group(5)),
        "tpws_ns": float(match.group(6)),
        "pulse_failing_endpoints": int(match.group(7)),
    }


def parse_power(path: Path) -> dict[str, Any]:
    text = _read(path)
    result: dict[str, Any] = {}
    power = re.search(r"\|\s*Total On-Chip Power \(W\)\s*\|\s*(%s)" % NUMBER, text)
    confidence = re.search(r"\|\s*Confidence Level\s*\|\s*([^|]+)\|", text)
    dynamic = re.search(r"\|\s*Dynamic(?: \(W\))?\s*\|\s*(%s)" % NUMBER, text)
    static = re.search(r"\|\s*Device Static(?: \(W\))?\s*\|\s*(%s)" % NUMBER, text)
    if power:
        result["total_on_chip_power_w"] = float(power.group(1))
    if confidence:
        result["confidence"] = confidence.group(1).strip()
    if dynamic:
        result["dynamic_power_w"] = float(dynamic.group(1))
    if static:
        result["static_power_w"] = float(static.group(1))
    return result


def parse_ram(path: Path) -> dict[str, Any]:
    text = _read(path)
    instances = set(re.findall(r"\|\s*([^|]+_reg)\s*\|\s*RAMB18E1", text))
    efficiencies = [
        float(value)
        for value in re.findall(r"RAMB18E1\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(%s)" % NUMBER, text)
    ]
    return {
        "ramb18_instances": len(instances),
        "minimum_bram_bit_efficiency_percent": min(efficiencies) if efficiencies else None,
    }


def parse_log(path: Path) -> dict[str, Any]:
    text = _read(path)
    return {
        "path": path.as_posix(),
        "error_count": len(re.findall(r"(?im)^.*(?:\berror\b|\bfatal\b).*$", text)),
        "warning_count": len(re.findall(r"(?im)^.*\bwarning\b.*$", text)),
        "assertion_failure_count": len(re.findall(r"(?i)(?:assertion.*(?:fail|error)|\*\*\s*(?:error|fatal))", text)),
        "timeout_detected": bool(re.search(r"(?i)(?:timeout|watchdog expired)", text)),
    }


def parse_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(_read(path))
    except json.JSONDecodeError:
        return {"parse_error": True}


def parse_implementation(artifact_root: Path) -> dict[str, Any]:
    drc_text = _read(artifact_root / "drc.rpt")
    route_text = _read(artifact_root / "route_status.rpt")
    unrouted = re.search(r"(?i)(?:number|#)\s+of\s+unrouted\s+nets?\s*[:|]\s*(\d+)", route_text)
    return {
        "drc_violations": len(re.findall(r"(?im)^.*\bVIOLATED\b.*$", drc_text)),
        "critical_warnings": len(re.findall(r"(?im)^.*\bCRITICAL WARNING\b.*$", drc_text)),
        "unrouted_nets": int(unrouted.group(1)) if unrouted else None,
    }


def collect_metrics(artifact_root: Path) -> dict[str, Any]:
    post_route_timing = artifact_root / "timing_summary_post_route.rpt"
    metrics: dict[str, Any] = {
        "utilization": parse_utilization(artifact_root / "utilization.rpt"),
        "hierarchy": parse_hierarchy(artifact_root / "utilization_hierarchical.rpt"),
        "timing": parse_timing(post_route_timing if post_route_timing.is_file() else artifact_root / "timing_summary.rpt"),
        "power": parse_power(artifact_root / "power.rpt"),
        "ram": parse_ram(artifact_root / "ram_utilization.rpt"),
        "verification": parse_json(artifact_root / "verification_result.json"),
        "implementation": parse_implementation(artifact_root),
        "logs": [],
    }
    for pattern in ("*.log", "**/*.log"):
        for path in sorted(artifact_root.glob(pattern)):
            if path.is_file() and not any(item["path"] == path.as_posix() for item in metrics["logs"]):
                metrics["logs"].append(parse_log(path))
    return metrics
