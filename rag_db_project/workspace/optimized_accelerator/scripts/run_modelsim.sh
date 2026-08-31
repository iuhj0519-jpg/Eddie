#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

modelsim_bin="/mnt/c/intelFPGA/18.1/modelsim_ase/win32aloem"
"$modelsim_bin/vsim.exe" -c -do scripts/run_modelsim.do
