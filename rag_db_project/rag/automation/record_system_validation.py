"""Record real test evidence without labeling infrastructure tests as DUT acceptance."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--first-smoke", required=True)
    p.add_argument("--retry-smoke", required=True)
    args = p.parse_args()
    project = Path(args.project).resolve()
    out = project / "artifacts/automation_system_tests/run_001"
    out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "unittest", "discover", "-s", str(Path(__file__).parent), "-p", "test_automation.py", "-v"]
    result = subprocess.run(command, capture_output=True, text=True)
    (out / "unittest.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    for name, directory in (("initial_failure", args.first_smoke), ("retry", args.retry_smoke)):
        source = Path(directory)
        dest = out / name
        dest.mkdir(exist_ok=True)
        for file in (source / "evidence").glob("*"):
            if file.is_file() and file.suffix in (".log", ".rpt", ".json"):
                shutil.copy2(file, dest / file.name)
        shutil.copy2(source / "smoke_result.json", dest / "smoke_result.json")
    data = {"kind": "automation_infrastructure_verification", "unit_test_exit_code": result.returncode,
        "real_tool_result": json.loads((Path(args.retry_smoke) / "smoke_result.json").read_text()),
        "rtl_modified": False, "design_approval_granted": False, "production_run_003_created": False,
        "limitations": ["No approved production RTL patch was executed", "DUT PPA violations remain", "Full protocol/PE activity coverage remains unknown"],
        "evidence_hashes": {f.relative_to(out).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in out.rglob("*") if f.is_file() and f.name != "system_verification.json"}}
    (out / "system_verification.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    raise SystemExit(result.returncode)
