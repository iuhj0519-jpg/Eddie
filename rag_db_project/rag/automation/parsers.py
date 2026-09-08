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
    parents: list[tuple[int, str]] = []
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
        raw_name = line.split("|")[1]
        depth = len(raw_name) - len(raw_name.lstrip())
        while parents and parents[-1][0] >= depth:
            parents.pop()
        instance = "/".join([p[1] for p in parents] + [cells[0]])
        parents.append((depth, cells[0]))
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
    header = re.search(r"WNS\(ns\)[^\n]*", text)
    if header:
        rows = text[header.end():].splitlines()
        for row in rows[:5]:
            fields = row.split()
            if len(fields) in (8, 12) and all(re.fullmatch(NUMBER, v) for v in fields):
                keys = ["wns_ns", "tns_ns", "setup_failing_endpoints", "setup_total_endpoints"]
                if "WHS(ns)" in header.group():
                    keys += ["whs_ns", "ths_ns", "hold_failing_endpoints", "hold_total_endpoints"]
                keys += ["wpws_ns", "tpws_ns", "pulse_failing_endpoints", "pulse_total_endpoints"]
                return dict(zip(keys, map(float, fields)))
    return {}




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
    # Do not count "Errors: 0", "Warnings: 0" or filenames containing timeout.
    bad = [line for line in text.splitlines() if re.search(r"(?i)(?:\*\*\s*(?:error|fatal)|^\s*(?:#\s*)?(?:ERROR|FATAL)[: ]|Errors:\s*[1-9])", line)]
    return {
        "path": path.as_posix(),
        "error_count": len(bad),
        "warning_count": len(re.findall(r"(?im)^.*\bWARNING\s*[:\[].*$", text)),
        "error_records": bad,
        "assertion_failure_count": len(re.findall(r"(?i)(?:assertion.*(?:fail|error)|\*\*\s*(?:error|fatal))", text)),
        "timeout_detected": bool(re.search(r"(?im)(?:Fatal:.*TIMEOUT|^TIMEOUT$|watchdog expired)", text)),
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
    errors = re.search(r"nets with routing errors\.+\s*:\s*(\d+)", route_text)
    total = re.search(r"of routable nets\.+\s*:\s*(\d+)", route_text)
    done = re.search(r"of fully routed nets\.+\s*:\s*(\d+)", route_text)
    return {
        "drc_violations": len(re.findall(r"(?im)^.*\bVIOLATED\b.*$", drc_text)),
        "critical_warnings": len(re.findall(r"(?im)^.*\bCRITICAL WARNING\b.*$", drc_text)),
        "unrouted_nets": int(unrouted.group(1)) if unrouted else (int(total[1]) - int(done[1]) if total and done else None),
        "routing_errors": int(errors[1]) if errors else None,
    }


def collect_metrics(artifact_root: Path) -> dict[str, Any]:
    def select(stem: str) -> Path:
        names = [f"{stem}_post_route.rpt", f"post_route_{stem}.rpt", f"{stem}.rpt"]
        return next((artifact_root / name for name in names if (artifact_root / name).is_file()), artifact_root / names[-1])
    post_route_timing = artifact_root / "timing_summary_post_route.rpt"
    metrics: dict[str, Any] = {
        "utilization": parse_utilization(select("utilization")),
        "hierarchy": parse_hierarchy(select("utilization_hierarchical")),
        "timing": parse_timing(select("timing_summary")),
        "power": parse_power(select("power")),
        "ram": parse_ram(artifact_root / "ram_utilization.rpt"),
        "verification": parse_json(artifact_root / "verification_result.json"),
        "execution": parse_json(artifact_root / "execution_result.json"),
        "implementation": parse_implementation(artifact_root),
        "logs": [],
    }
    for pattern in ("*.log", "**/*.log"):
        for path in sorted(artifact_root.glob(pattern)):
            if path.is_file() and not any(item["path"] == path.as_posix() for item in metrics["logs"]):
                metrics["logs"].append(parse_log(path))
    metrics["sources"] = {stem: select(stem).name for stem in ("utilization", "utilization_hierarchical", "timing_summary", "power")}
    if metrics["utilization"].get("lut") is None:
        top = next((row for row in metrics["hierarchy"].values() if row["module"] == "(top)"), None)
        if top:
            metrics["utilization"].update(lut=top["total_lut"], lut_logic=top["logic_lut"],
                lut_memory=top["lutram"], ff=top["ff"], ramb18=top["ramb18"],
                bram_tile=top["ramb36"] + top["ramb18"] / 2, dsp=top["dsp"])
            metrics["sources"]["utilization"] = select("utilization_hierarchical").name
    path = artifact_root / "critical_paths.rpt"
    if not path.is_file():
        path = select("timing_summary")
    metrics["paths"] = parse_paths(path)
    metrics["fanout"] = parse_fanout(artifact_root / "high_fanout_nets.rpt")
    drc = _read(select("drc"))
    rules = []
    for number, line in enumerate(drc.splitlines(), 1):
        m = re.match(r"\|\s*([A-Z0-9]+-\d+)\s*\|\s*(Critical Warning|Warning|Error)\s*\|.*\|\s*(\d+)\s*\|", line)
        if m:
            rules.append({"rule": m[1], "severity": m[2], "count": int(m[3]), "line": number, "artifact_path": select("drc").name})
    metrics["drc_rules"] = rules
    timing_text = _read(select("timing_summary"))
    metrics["unconstrained_io"] = {name: int(m[1]) for name in ("no_input_delay", "no_output_delay")
        if (m := re.search(re.escape(name) + r" \((\d+)\)", timing_text))}
    metrics["unbound_checkpoint_source"] = "not_recorded_in_original_checkpoint_manifest" in _read(artifact_root / "run_manifest.yaml")
    metrics["coverage"] = {name: {"state": "observed" if file.is_file() and file.stat().st_size else "unknown", "artifact_path": file.name}
        for name, file in {"critical_paths": path, "fanout": artifact_root / "high_fanout_nets.rpt", "drc": select("drc"),
            "ram": artifact_root / "ram_utilization.rpt", "verification": artifact_root / "verification_result.json",
            **{stem: select(stem) for stem in metrics["sources"]}}.items()}
    return metrics


def parse_paths(path: Path) -> list[dict[str, Any]]:
    text = _read(path)
    result = []
    for match in re.finditer(r"Slack \((?:VIOLATED|MET)\)\s*:\s*(" + NUMBER + r")ns", text):
        end = text.find("Slack (", match.end())
        block = text[match.start():end if end >= 0 else len(text)]
        data = {"slack_ns": float(match[1]), "artifact_path": path.name, "line": text[:match.start()].count("\n") + 1}
        for key, pattern in {"source": r"Source:\s*(\S+)", "destination": r"Destination:\s*(\S+)",
            "logic_levels": r"Logic Levels:\s*(\d+)", "delay_ns": r"Data Path Delay:\s*([\d.]+)ns",
            "logic_ns": r"\(logic ([\d.]+)ns", "route_ns": r"route ([\d.]+)ns"}.items():
            found = re.search(pattern, block)
            if found:
                data[key] = found[1] if key in ("source", "destination") else float(found[1])
        data["mux_present"] = "MUXF" in block
        data["address_path"] = bool(re.search(r"(?i)address|memory_bank|consumed_feature", block))
        data["dsp_present"] = "DSP48" in block
        result.append(data)
    return result


def parse_fanout(path: Path) -> list[dict[str, Any]]:
    result = []
    for number, line in enumerate(_read(path).splitlines(), 1):
        cells = [v.strip() for v in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[1].isdigit():
            result.append({"net": cells[0], "fanout": int(cells[1]), "driver": cells[2], "slack": cells[3],
                "artifact_path": path.name, "line": number})
    return result
