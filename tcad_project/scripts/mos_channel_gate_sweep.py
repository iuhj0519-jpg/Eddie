"""Independent constant-mobility gate sweep using the installed Gmsh example.

Run in the DEVSIM venv. A new output directory is required; no original results
are overwritten. Geometry and physics parameters are not changed.
"""
import argparse
import csv
import os
from pathlib import Path
import runpy
import shutil

import devsim as ds
import numpy as np
from devsim.python_packages import simple_physics as sp
from devsim.python_packages.model_create import CreateSolution
from devsim.python_packages.ramp import rampbias


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--vg-max", type=float, default=2.0)
    parser.add_argument("--vd", type=float, default=0.05)
    args = parser.parse_args()
    if not 0 < args.vg_max <= 2.0 or not 0 <= args.vd <= 0.05:
        parser.error("Initial diagnostic range: 0 < vg-max <= 2 V; 0 <= vd <= 0.05 V")
    source, out = args.example_dir.resolve(), args.out.resolve()
    for name in ("gmsh_mos2d_create.py", "gmsh_mos2d.msh"):
        if not (source / name).is_file():
            raise FileNotFoundError(source / name)
    out.mkdir(parents=True, exist_ok=False)
    for name in ("gmsh_mos2d_create.py", "gmsh_mos2d.msh"):
        shutil.copy2(source / name, out / name)
    os.chdir(out)  # Basename-only VTK writes avoid duplicated relative paths.
    runpy.run_path("gmsh_mos2d_create.py")
    device = "mos2d"
    silicon = ("gate", "bulk")
    for region in (*silicon, "oxide"):
        CreateSolution(device, region, "Potential")
    for region in silicon:
        sp.SetSiliconParameters(device, region, 300)
        sp.CreateSiliconPotentialOnly(device, region)
    sp.SetOxideParameters(device, "oxide", 300)
    sp.CreateOxidePotentialOnly(device, "oxide", "log_damp")
    contacts = ds.get_contact_list(device=device)
    for contact in contacts:
        region = ds.get_region_list(device=device, contact=contact)[0]
        sp.CreateSiliconPotentialOnlyContact(device, region, contact)
        ds.set_parameter(device=device, name=sp.GetContactBiasName(contact), value=0.0)
    for interface in ("bulk_oxide", "gate_oxide"):
        sp.CreateSiliconOxideInterface(device, interface)
    ds.solve(type="dc", absolute_error=1e-13, relative_error=1e-12, maximum_iterations=100)
    for region in silicon:
        for variable, initial in (("Electrons", "IntrinsicElectrons"), ("Holes", "IntrinsicHoles")):
            CreateSolution(device, region, variable)
            ds.set_node_values(device=device, region=region, name=variable, init_from=initial)
        sp.CreateSiliconDriftDiffusion(device, region, "mu_n", "mu_p")
    for contact in contacts:
        region = ds.get_region_list(device=device, contact=contact)[0]
        sp.CreateSiliconDriftDiffusionAtContact(device, region, contact)
    ds.solve(type="dc", absolute_error=1e30, relative_error=1e-10, maximum_iterations=100)
    rampbias(device, "drain", args.vd, 0.01, 1e-5, 100, 1e-10, 1e30, sp_print)
    bulk = dict(device=device, region="bulk")
    ds.node_solution(**bulk, name="ElectronsAtGateZero")
    ds.set_node_values(**bulk, name="ElectronsAtGateZero", values=ds.get_node_model_values(**bulk, name="Electrons"))
    # Floors only protect visualization logarithms; they do not alter physics.
    models = {
        "logElectrons": "log(max(Electrons,1e-30))/log(10)",
        "logHoles": "log(max(Holes,1e-30))/log(10)",
        "logElectronHoleRatio": "log(max(Electrons,1e-30)/max(Holes,1e-30))/log(10)",
        "logElectronGain": "log(max(Electrons,1e-30)/max(ElectronsAtGateZero,1e-30))/log(10)",
        "logElectronToAcceptor": "log(max(Electrons,1e-30)/max(Acceptors,1))/log(10)",
    }
    for name, expression in models.items():
        ds.node_model(**bulk, name=name, equation=expression)
    x = np.asarray(ds.get_node_model_values(**bulk, name="x"))
    y = np.asarray(ds.get_node_model_values(**bulk, name="y"))
    center = int(np.argmin((x - 5e-5)**2 + y**2))
    with open("channel_summary.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["snapshot", "Vg_V", "Vd_V", "sample_x_cm", "sample_y_cm", "n_cm-3", "p_cm-3", "logElectronGain", "logElectronHoleRatio", "Id_raw", "current_sum_raw"])
        index = 0

        def save(device):
            nonlocal index
            vg = ds.get_parameter(device=device, name="gate_bias")
            vd = ds.get_parameter(device=device, name="drain_bias")
            name = f"channel_{index:03d}"
            ds.write_devices(file=name, type="vtk")
            currents = {}
            for contact in contacts:
                currents[contact] = sum(ds.get_contact_current(device=device, contact=contact, equation=eq) for eq in ("ElectronContinuityEquation", "HoleContinuityEquation"))
            values = [ds.get_node_model_values(**bulk, name=m)[center] for m in ("Electrons", "Holes", "logElectronGain", "logElectronHoleRatio")]
            writer.writerow([name, vg, vd, x[center], y[center], *values, currents["drain"], sum(currents.values())])
            file.flush()
            print(f"[SNAPSHOT] {name} Vg={vg:.8g} Vd={vd:.8g} center(n,p,gain,ratio)={values}", flush=True)
            index += 1

        save(device)
        rampbias(device, "gate", args.vg_max, 0.1, 1e-4, 100, 1e-10, 1e30, save)
    print("OUTPUT:", out)


def sp_print(device):
    for contact in ds.get_contact_list(device=device):
        sp.PrintCurrents(device, contact)


if __name__ == "__main__":
    main()
