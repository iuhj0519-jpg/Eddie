"""Local tool adapters. No RTL edits, network calls, or historical inputs."""
from __future__ import annotations
import argparse
import json
import hashlib
import shutil
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
    fatal = bool(re.search(r"(?im)\*\*\s*(?:Fatal|Error):|^\s*(?:ERROR:|Fatal:)|REFERENCE_GOLDEN_MATCH FAIL|cannot be opened|TIMEOUT", text))
    data = {"completed": bool(summary and "REFERENCE_GOLDEN_MATCH PASS" in text and not fatal),
        "sample_results": samples, "protocol_errors": None, "peak_active_pe_count": None,
        "interrupt_count_per_batch": None, "measurement_note": "Uninstrumented metrics remain unknown; golden completion is not a substitute for protocol coverage."}
    if summary:
        data.update(pass_count=int(summary[1]), failure_count=int(summary[2]), accuracy_percent=float(summary[3]),
            image_count=int(summary[1]) + int(summary[2]))
    cycles = re.search(r"TOTAL_INFERENCE_CYCLES=(\d+)", text)
    if cycles:
        data["total_inference_cycles"] = int(cycles[1])
    for label, key in (('PROTOCOL_ERRORS', 'protocol_errors'), ('PEAK_ACTIVE_PE_COUNT', 'peak_active_pe_count'),
                       ('INTERRUPT_COUNT_PER_BATCH', 'interrupt_count_per_batch'), ('AXI_BACKPRESSURE_CYCLES', 'axi_backpressure_cycles')):
        measured = re.search(r'(?m)^\s*(?:#\s*)?' + label + r'=(\d+)\s*$', text)
        if measured:
            data[key] = int(measured[1])
    return data


def prepare_xsim_data(workspace):
    sim = workspace / '.vivado_flow/project/accelerator.sim/sim_1/behav/xsim'
    tests = workspace.parent.parent / 'inputs/reference_model/testdata'
    if not tests.is_dir() or not list(tests.glob('test_data_*.txt')):
        raise ValueError('Missing isolated workload files')
    for source, destination in ((workspace / 'memory', sim / 'memory'),
                                (tests, sim.parent.parent / 'inputs/reference_model/testdata')):
        shutil.copytree(source, destination, dirs_exist_ok=True)


def activity_metrics(saif, power):
    header = saif.read_text(encoding='utf-8', errors='replace')[:4096]
    scale = re.search(r'\(TIMESCALE\s+([\d.]+)\s+(ps|ns|us|ms|s)\)', header)
    duration = re.search(r'\(DURATION\s+([\d.]+)\)', header)
    watts = re.search(r'Total On-Chip Power \(W\)\s*\|\s*([\d.]+)', power.read_text(encoding='utf-8', errors='replace'))
    if not (scale and duration and watts):
        raise ValueError('Missing SAIF duration or power; energy must remain unknown')
    ns = float(duration[1]) * float(scale[1]) * {'ps': .001, 'ns': 1, 'us': 1e3, 'ms': 1e6, 's': 1e9}[scale[2]]
    if ns <= 0:
        raise ValueError('SAIF duration must be positive')
    return {'duration_ns': ns, 'energy_per_workload_uj': float(watts[1])*ns/1000,
            'method': 'SAIF_average_power_times_collection_duration_estimate',
            'saif_sha256': hashlib.sha256(saif.read_bytes()).hexdigest()}


def run(stage, workspace, out, tool, tcl):
    workspace, out = Path(workspace).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if Path(tool).name.lower() in ('vivado.bat', 'vivado', 'vivado.exe'):
        if stage == 'simulation':
            prepare_xsim_data(workspace)
        script = Path(tcl).with_name('vivado_flow.tcl')
        command = [tool, '-mode', 'batch', '-source', str(script), '-tclargs', stage, str(out)]
        if tool.lower().endswith('.bat'):
            command = ['cmd.exe', '/d', '/c', *command]
        code = execute(command, workspace, out / f'{stage}.log', timeout=7200)
        if stage == 'simulation':
            result = simulation_result(out / 'simulation.log')
            (out / 'verification_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            (out / 'run_summary.yaml').write_text(json.dumps({'stage': 'simulation', 'completed': result['completed'], 'rtl_modified_by_adapter': False}, indent=2), encoding='utf-8')
            (out / 'protocol_assertions.log').write_text('Protocol coverage remains UNKNOWN unless instrumented.\n', encoding='utf-8')
            code = code or (0 if result['completed'] else 1)
        if stage == 'power' and not code:
            activity = activity_metrics(workspace / '.vivado_flow/activity.saif', out / 'power_post_route.rpt')
            (out / 'activity_metrics.json').write_text(json.dumps(activity, indent=2), encoding='utf-8')
            tests = workspace.parent.parent / 'inputs/reference_model/testdata'
            workload = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(tests.glob('test_data_*.txt'))}
            report = (out / 'power_post_route.rpt').read_text(encoding='utf-8', errors='replace')
            clock = re.search(r'\|\s*s_axi_aclk\s*\|[^|]+\|\s*([\d.]+)\s*\|', report)
            context = {'stage': 'post_route', 'clock_period_ns': float(clock[1]) if clock else None, 'activity_kind': 'behavioral_saif_full_workload',
                       'workload_sha256': hashlib.sha256(json.dumps(workload, sort_keys=True).encode()).hexdigest()}
            (out / 'comparison_context.json').write_text(json.dumps(context, indent=2), encoding='utf-8')
        return code
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
    if stage != 'synthesis':
        raise ValueError('Unsupported non-Vivado stage')
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
