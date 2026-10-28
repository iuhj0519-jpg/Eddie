"""Plot existing DEVSIM bias CSV; does not run or modify a simulation."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    gate = df[df.stage == "gate_ramp"]
    if gate.empty:
        raise ValueError("Missing successful gate-ramp state")
    start = gate.iloc[-1].snapshot
    selected = df[(df.snapshot == start) | (df.stage == "drain_ramp")]
    currents = selected.pivot(index="snapshot", columns="contact", values="total_current_raw")
    bias = selected.groupby("snapshot")[["Vg_V", "Vd_V"]].first()
    table = bias.join(currents).sort_values("Vd_V")
    contacts = ["gate", "drain", "source", "body"]
    if not np.isfinite(table[contacts].to_numpy()).all():
        raise ValueError("Missing or non-finite contact currents")
    if not np.allclose(table.Vg_V, table.Vg_V.iloc[0]):
        raise ValueError("Expected a fixed gate voltage")
    v = table.Vd_V.to_numpy()
    if len(v) < 2 or np.any(np.diff(v) <= 0):
        raise ValueError("Need distinct increasing drain biases")
    table["sum_raw"] = table[contacts].sum(axis=1)
    scale = table[contacts].abs().max(axis=1)
    table["relative_mismatch"] = table.sum_raw.abs() / scale.replace(0, np.nan)
    table.loc[table.Vd_V == 0, "relative_mismatch"] = np.nan
    drain = selected[selected.contact == "drain"].set_index("snapshot").loc[table.index]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for col, label in [("electron_current_raw", "|Id electron|"), ("hole_current_raw", "|Id hole|")]:
        values = drain[col].abs()
        axes[0, 0].semilogy(v, values.where(values > 0), "o-", label=label)
    axes[0, 0].set_ylabel("Drain components [raw API units]")
    axes[0, 0].legend()
    for contact in ["gate", "body"]:
        axes[0, 1].plot(v, table[contact], "o-", label=contact)
    axes[0, 1].set_ylabel("Signed current [raw API units]")
    axes[0, 1].ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    axes[0, 1].legend()
    axes[1, 0].semilogy(v, table.relative_mismatch.where(table.relative_mismatch > 0), "o-")
    axes[1, 0].set_ylabel("Relative current imbalance [dimensionless]")
    axes[1, 0].set_title("Zero-bias point excluded")
    slope = np.diff(table.drain.to_numpy()) / np.diff(v)
    axes[1, 1].plot((v[:-1] + v[1:]) / 2, slope, "o-")
    axes[1, 1].set_ylabel("Interval dId/dVd [raw API units / V]")
    axes[1, 1].set_title("Finite differences, not a fitted derivative")
    for ax in axes.flat:
        ax.set_xlabel("Drain bias [V]")
        ax.grid(True)
    fig.suptitle(f"Bias diagnostics: Vg = {table.Vg_V.iloc[0]:g} V")
    fig.tight_layout()
    args.out.mkdir(parents=True, exist_ok=False)
    fig.savefig(args.out / "bias_diagnostics.png", dpi=180)
    plt.close(fig)
    table.to_csv(args.out / "diagnostics.csv")
    print(table[["Vd_V", "sum_raw", "relative_mismatch"]].to_string())
    print("Interval slopes:", slope)
    print("Plot:", args.out / "bias_diagnostics.png")


if __name__ == "__main__":
    main()
