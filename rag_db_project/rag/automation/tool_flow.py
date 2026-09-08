"""Local tool adapters. No RTL edits, network calls, or historical inputs."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path


def execute(command, cwd, log, timeout=600):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        stream.write("COMMAND " + json.dumps(command) + "\n")
        stream.flush()
        process = subprocess.Popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if __import__("os").name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            else:
                process.kill()
            process.wait()
            stream.write("\nTIMEOUT\n")
            return 124


def simulation_result(log: Path):
    text = log.read_text(encoding="utf-8", errors="replace")
    summary = re.search(r"FINAL_RESULT PASS=(\d+) FAIL=(\d+) ACCURACY=([\d.]+)%", text)
    samples = re.findall(r"(?:PASS|FAIL) sample=(\d+) detected=(\d+) expected=(\d+)", text)
    fatal = bool(re.search(r"(?i)\*\*\s*(?:Fatal|Error):|REFERENCE_GOLDEN_MATCH FAIL", text))
    data = {"completed": bool(summary and "REFERENCE_GOLDEN_MATCH PASS" in text and not fatal),
        "sample_results": samples, "protocol_errors": None, "peak_active_pe_count": None,
        "interrupt_count_per_batch": None, "measurement_note": "Uninstrumented metrics remain unknown; golden completion is not a substitute for protocol coverage."}
    if summary:
        data.update(pass_count=int(summary[1]), failure_count=int(summary[2]), accuracy_percent=float(summary[3]),
            image_count=int(summary[1]) + int(summary[2]))
    cycles = re.search(r"TOTAL_INFERENCE_CYCLES=(\d+)", text)
    if cycles:
        data["total_inference_cycles"] = int(cycles[1])
    return data


def run(stage, workspace, out, tool, tcl):
    workspace, out = Path(workspace).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if stage == "compile":
        vlib = str(Path(tool).with_name("vlib.exe"))
        if execute([vlib, "work"], workspace, out / "library.log"):
            return 1
        rtl = sorted((workspace / "rtl").glob("*.sv"))
        code = execute([tool, "-sv", "+incdir+rtl", *[str(p) for p in rtl], "tb/top_sim.sv"], workspace, out / "compile.log")
        return code
    if stage == "simulation":
        code = execute([tool, "-c", "-t", "1ps", "work.top_sim", "-do",
            "onerror {quit -code 1 -f}; onbreak {quit -code 1 -f}; run -all; quit -code 0 -f"], workspace, out / "simulation.log")
        result = simulation_result(out / "simulation.log")
        (out / "verification_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        lines = (out / "simulation.log").read_text(encoding="utf-8", errors="replace").splitlines()
        assertions = [line for line in lines if re.search(r"(?i)assert|fatal|intr|REFERENCE_GOLDEN", line)]
        (out / "protocol_assertions.log").write_text("\n".join(assertions), encoding="utf-8")
        return code or (0 if result["completed"] else 1)
    # .bat dispatch requires cmd.exe on Windows; arguments are local fixed paths.
    command = [tool, "-mode", "batch", "-source", str(tcl), "-tclargs", str(out)]
    if tool.lower().endswith(".bat"):
        command = ["cmd.exe", "/d", "/c", *command]
    return execute(command, workspace, out / "synthesis.log", timeout=1800)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["compile", "simulation", "synthesis"], required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--tool", required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.stage, args.workspace, args.out, args.tool, Path(__file__).with_name("synthesis.tcl")))
