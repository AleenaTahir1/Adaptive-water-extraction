"""Sensitivity analysis: vary each key parameter +/-20% (and at baseline)
around its default, holding everything else fixed.

Output is a single CSV per parameter that the analysis script reads to
produce a tornado plot showing each parameter's effect on the final
water level and cooperation index. Uses 10 seeds per setting so the
estimate is robust to stochastic noise.

Run as:
    python -m experiments.sensitivity
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
from mesa.batchrunner import batch_run

from water_abm.model import WaterCommonsModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_STEPS = 500
SEEDS = list(range(10))


# Baseline parameters (same as default WaterCommonsModel + moderate enforcement).
BASELINE = {
    "n_farmers": 20,
    "proportion_q_learners": 1.0,
    "social_degree": 4,
    "alpha": 0.15,
    "gamma": 0.95,
    "epsilon_0": 0.30,
    "decay_rate": 0.010,
    "regeneration_rate": 0.10,
    "p_detect": 0.30,
    "fine_factor": 3.0,
    "climate_scenario": "stable",
}

# Parameters to perturb (+/-20%). For probability parameters we clip to [0, 1].
PARAMS_TO_VARY = ["alpha", "gamma", "epsilon_0", "regeneration_rate", "p_detect", "n_farmers"]


def perturbed_values(name: str, base: float) -> list:
    """Return [base*0.8, base, base*1.2] clipped where appropriate."""
    lo = base * 0.8
    hi = base * 1.2
    if name in ("gamma", "p_detect", "epsilon_0"):
        lo = max(0.0, min(1.0, lo))
        hi = max(0.0, min(1.0, hi))
    if name == "n_farmers":
        lo = max(2, int(round(lo)))
        hi = int(round(hi))
        return [lo, int(base), hi]
    return [round(lo, 4), base, round(hi, 4)]


def run_sensitivity():
    rows = []
    for param in PARAMS_TO_VARY:
        base_val = BASELINE[param]
        values = perturbed_values(param, base_val)
        print(f"\n=== Sweep: {param} -- values {values} ===")
        for val in values:
            params = dict(BASELINE)
            params[param] = val
            params["seed"] = SEEDS

            t0 = time.time()
            results = batch_run(
                WaterCommonsModel,
                parameters=params,
                iterations=1,
                max_steps=MAX_STEPS,
                number_processes=1,
                # Only keep the final step to save space
                data_collection_period=MAX_STEPS,
                display_progress=False,
            )
            df = pd.DataFrame(results)
            # data_collection_period=MAX_STEPS means we collect at t=0 (init) AND
            # at t=MAX_STEPS, with N agent rows at each. Keep the final-step
            # model-level row per RunId (sort by Step DESC, take first per RunId).
            df = df.sort_values("Step", ascending=False).drop_duplicates(subset=["RunId"])
            for _, r in df.iterrows():
                rows.append({
                    "param": param,
                    "value": val,
                    "is_baseline": val == base_val,
                    "seed": r["seed"],
                    "final_water": r["water_level"],
                    "cooperation_index": r["cooperation_index"],
                    "mean_payoff": r["mean_payoff"],
                    "gini_payoff": r["gini_payoff"],
                })
            print(
                f"  {param}={val} -- "
                f"mean final water = {df['water_level'].mean():.1f}, "
                f"({time.time()-t0:.1f}s)"
            )

    out = OUT_DIR / "sensitivity.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSensitivity results -> {out}")


if __name__ == "__main__":
    run_sensitivity()
