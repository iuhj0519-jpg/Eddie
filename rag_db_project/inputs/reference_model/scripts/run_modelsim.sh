#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
reference_dir="$(cd -- "${script_dir}/.." && pwd)"
modelsim_bin="${MODELSIM_BIN:-/c/intelFPGA/18.1/modelsim_ase/win32aloem}"
run_id="modelsim_$(date +%Y%m%d_%H%M%S)"
run_dir="${reference_dir}/.sim/${run_id}"

mkdir -p "${run_dir}"
cp "${reference_dir}"/model/rtl/*.v "${run_dir}/"
cp "${reference_dir}"/model/tb/top_sim.v "${run_dir}/"
cp "${reference_dir}"/weights/*.mif "${run_dir}/"
cp "${reference_dir}"/biases/*.mif "${run_dir}/"
cp "${reference_dir}"/activation/sigContent.mif "${run_dir}/"
cp "${reference_dir}"/testdata/test_data_*.txt "${run_dir}/"

cd "${run_dir}"
"${modelsim_bin}/vlib.exe" work
"${modelsim_bin}/vlog.exe" -work work +incdir+. ./*.v 2>&1 | tee compile.log
"${modelsim_bin}/vsim.exe" -c work.top_sim -do "run -all; quit -f" 2>&1 | tee simulation.log

printf 'ModelSim run completed: %s\n' "${run_dir}"
