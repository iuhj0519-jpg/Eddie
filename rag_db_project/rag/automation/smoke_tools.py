"""Explicit infrastructure smoke test on unmodified copies, never a design approval."""
import argparse
import json
import shutil
from pathlib import Path
import tool_flow

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--synthesis", action="store_true")
    args = p.parse_args()
    out = Path(args.out).resolve()
    work = out / "project/workspace/target"
    work.mkdir(parents=True, exist_ok=False)
    for name in ("rtl", "tb", "memory", "scripts"):
        shutil.copytree(Path(args.source) / name, work / name)
    data = Path(args.source).resolve().parents[1] / "inputs/reference_model/testdata"
    data_out = out / "project/inputs/reference_model/testdata"
    data_out.mkdir(parents=True)
    for file in data.glob("test_data_*.txt"):
        shutil.copy2(file, data_out / file.name)
    result = {"purpose": "unmodified tool adapter smoke test, not approved debugging", "stages": []}
    for stage, tool in [("compile", "C:/intelFPGA/18.1/modelsim_ase/win32aloem/vlog.exe"),
                        ("simulation", "C:/intelFPGA/18.1/modelsim_ase/win32aloem/vsim.exe"),
                        *(([("synthesis", "C:/Xilinx/Vivado/2022.1/bin/vivado.bat")]) if args.synthesis else [])]:
        print("START " + stage, flush=True)
        code = tool_flow.run(stage, work, out / "evidence", tool, Path(__file__).with_name("synthesis.tcl").resolve())
        result["stages"].append({"stage": stage, "exit_code": code})
        (out / "smoke_result.json").write_text(json.dumps(result, indent=2))
        print(f"END {stage}: {code}", flush=True)
        if code:
            raise SystemExit(code)
