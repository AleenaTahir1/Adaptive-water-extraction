"""Validation: compare emergent model dynamics to external benchmarks.

We do three lightweight validation checks (the project doesn't require
fitting real time-series, only a qualitative sanity check per assignment
section 4.5):

  1. Tragedy of the commons (Hardin 1968): without enforcement,
     unmonitored Q-learners should collapse the resource.
  2. Perolat et al. (2017): scarcity should increase the rate of
     aggressive (high-extraction) actions vs abundance.
  3. Indus Basin 2022 drought: a shock that cuts inflow ~50-70 % should
     measurably depress emergent water level even with enforcement.

This produces `data/results/validation.json` with the pass/fail summary
and a printed report, plus `figures/fig07_validation.png`.

Run as:
    python -m experiments.validate
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from water_abm.model import WaterCommonsModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "results"
FIG_DIR = PROJECT_ROOT / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)


def run_to_history(seed: int, **kwargs) -> dict:
    """Run a single model and return its time-series."""
    m = WaterCommonsModel(seed=seed, **kwargs)
    for _ in range(500):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    return {
        "step": df["step"].tolist(),
        "water_level": df["water_level"].tolist(),
        "frac_defect": df["frac_action_defect"].tolist(),
        "mean_payoff": df["mean_payoff"].tolist(),
    }


def avg_runs(runs: list[dict], key: str) -> np.ndarray:
    arr = np.array([r[key] for r in runs])
    return arr.mean(axis=0)


def main():
    seeds = list(range(10))
    report = {}

    # Check 1: tragedy without enforcement (stable climate)
    runs_no_enf = [run_to_history(s, n_farmers=20, climate_scenario="stable", p_detect=0.0) for s in seeds]
    runs_enf = [run_to_history(s, n_farmers=20, climate_scenario="stable", p_detect=0.3) for s in seeds]
    avg_water_no_enf = avg_runs(runs_no_enf, "water_level")
    avg_water_enf = avg_runs(runs_enf, "water_level")

    final_water_no_enf = float(avg_water_no_enf[-1])
    final_water_enf = float(avg_water_enf[-1])
    check1_pass = final_water_no_enf < 50 and final_water_enf > 200
    report["check1_tragedy"] = {
        "passed": check1_pass,
        "no_enforcement_final_water": final_water_no_enf,
        "with_enforcement_final_water": final_water_enf,
        "note": "Without enforcement, resource should collapse (< 50 units); with enforcement, it should sustain (> 200).",
    }

    # Check 2: scarcity drives aggression (Perolat 2017)
    # With enforcement so the resource doesn't immediately collapse, compare
    # frac_defect during a period of ABUNDANCE (stable, steps 200-300, water ~500)
    # versus the same wall-clock period under SHOCK (water plunges to near-zero).
    runs_shock_enf = runs_enf_shock = [
        run_to_history(s, climate_scenario="shock", p_detect=0.3) for s in seeds
    ]

    def window_mean(runs, key, lo, hi):
        return float(np.mean([np.mean(r[key][lo:hi]) for r in runs]))

    stable_def_window = window_mean(runs_enf, "frac_defect", 200, 300)
    shock_def_window = window_mean(runs_shock_enf, "frac_defect", 200, 300)
    check2_pass = shock_def_window >= stable_def_window
    report["check2_scarcity_aggression"] = {
        "passed": check2_pass,
        "stable_frac_defect_shockwindow": stable_def_window,
        "shock_frac_defect_shockwindow": shock_def_window,
        "note": "Perolat et al. 2017: scarcity should drive aggression. With enforcement on, compare frac_defect during steps 200-300 under stable (abundant) vs shock (scarce).",
    }

    # Check 3: shock measurably depresses water vs stable (even with enforcement)
    avg_enf_shock = avg_runs(runs_enf_shock, "water_level")
    # Compare water at end of shock window (step 300) vs same step in stable+enforcement
    water_at_300_stable_enf = float(avg_water_enf[300])
    water_at_300_shock_enf = float(avg_enf_shock[300])
    check3_pass = water_at_300_shock_enf < water_at_300_stable_enf
    report["check3_shock_signal"] = {
        "passed": check3_pass,
        "stable_water_at_step_300": water_at_300_stable_enf,
        "shock_water_at_step_300": water_at_300_shock_enf,
        "note": "Indus 2022-style shock should leave a measurable dip in water level.",
    }

    # Save report
    out_json = OUT_DIR / "validation.json"
    out_json.write_text(json.dumps(report, indent=2))

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].plot(avg_water_no_enf, label="no enforcement", color="#d62728", linewidth=2)
    axes[0].plot(avg_water_enf, label="p_detect=0.3", color="#1f77b4", linewidth=2)
    axes[0].axhline(50, color="grey", linestyle=":", label="collapse threshold")
    axes[0].set_title("Check 1: Tragedy + enforcement effect")
    axes[0].set_xlabel("step"); axes[0].set_ylabel("water level")
    axes[0].legend(); axes[0].grid(alpha=0.3)

    axes[1].bar(["stable\n(abundant)", "shock\n(scarce)"], [stable_def_window, shock_def_window],
                color=["#2ca02c", "#d62728"])
    axes[1].set_title("Check 2: Scarcity -> aggression\n(frac defect during steps 200-300, both with enforcement)")
    axes[1].set_ylabel("frac defect"); axes[1].grid(alpha=0.3, axis="y")

    axes[2].plot(avg_water_enf, label="stable + enforcement", color="#1f77b4", linewidth=2)
    axes[2].plot(avg_enf_shock, label="shock + enforcement", color="#d62728", linewidth=2)
    axes[2].axvspan(200, 300, color="orange", alpha=0.15, label="shock window")
    axes[2].set_title("Check 3: Drought shock leaves measurable dip")
    axes[2].set_xlabel("step"); axes[2].set_ylabel("water level")
    axes[2].legend(); axes[2].grid(alpha=0.3)

    fig.suptitle("Model validation: three sanity checks against literature", fontsize=13)
    fig.tight_layout()
    out_fig = FIG_DIR / "fig07_validation.png"
    fig.savefig(out_fig, dpi=140, bbox_inches="tight")
    plt.close(fig)

    print("\n=== Validation report ===")
    for name, body in report.items():
        status = "PASS" if body["passed"] else "FAIL"
        print(f"  [{status}] {name}")
        for k, v in body.items():
            if k == "passed":
                continue
            if isinstance(v, float):
                print(f"        {k}: {v:.2f}")
            else:
                print(f"        {k}: {v}")
    print(f"\nReport JSON: {out_json}")
    print(f"Figure:      {out_fig}")


if __name__ == "__main__":
    main()
