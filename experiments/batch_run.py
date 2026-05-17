"""Batch experiments for the Water Commons ABM.

Three experiments:
  A. Tragedy baseline   -- 4 climate scenarios x 30 seeds, NO monitor
  B. With enforcement   -- 4 climate scenarios x 30 seeds, p_detect = 0.3
  C. Gamma sweep        -- {stable, shock} x 5 gamma values x 10 seeds
                           (the primary research question)

Outputs CSVs to data/results/. Total runtime ~3-5 minutes on a laptop.

Run as:
    python -m experiments.batch_run
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
DATA_PERIOD = 10  # save model state every N steps


def run_experiment(
    name: str,
    parameters: dict,
    max_steps: int = MAX_STEPS,
    data_collection_period: int = DATA_PERIOD,
) -> pd.DataFrame:
    """Wrapper that runs mesa.batch_run and saves results to CSV."""
    t0 = time.time()
    print(f"\n=== Experiment {name} ===")
    print(f"Parameters: { {k: (v if not isinstance(v, list) else f'list[{len(v)}]') for k, v in parameters.items()} }")

    results = batch_run(
        WaterCommonsModel,
        parameters=parameters,
        iterations=1,
        max_steps=max_steps,
        number_processes=1,
        data_collection_period=data_collection_period,
        display_progress=True,
    )
    df = pd.DataFrame(results)
    out_path = OUT_DIR / f"batch_{name}.csv"
    df.to_csv(out_path, index=False)
    elapsed = time.time() - t0
    print(f"  -> {len(df)} rows -> {out_path.name}  ({elapsed:.1f}s)")
    return df


def main():
    seeds_30 = list(range(30))
    seeds_10 = list(range(10))
    scenarios_all = ["stable", "gradual", "shock", "stochastic"]

    common = {
        "n_farmers": 20,
        "proportion_q_learners": 1.0,
        "social_degree": 4,
        "alpha": 0.15,
        "gamma": 0.95,
        "epsilon_0": 0.30,
        "decay_rate": 0.010,
        "regeneration_rate": 0.10,
    }

    # --- Experiment A: tragedy baseline (no monitor) ----------------
    run_experiment(
        "A_tragedy_baseline",
        parameters={
            **common,
            "p_detect": 0.0,
            "climate_scenario": scenarios_all,
            "seed": seeds_30,
        },
    )

    # --- Experiment B: moderate enforcement -------------------------
    run_experiment(
        "B_with_enforcement",
        parameters={
            **common,
            "p_detect": 0.3,
            "fine_factor": 3.0,
            "climate_scenario": scenarios_all,
            "seed": seeds_30,
        },
    )

    # --- Experiment C: gamma sweep (primary RQ) ---------------------
    run_experiment(
        "C_gamma_sweep",
        parameters={
            **common,
            "p_detect": 0.3,
            "fine_factor": 3.0,
            "climate_scenario": ["stable", "shock"],
            "gamma": [0.50, 0.70, 0.85, 0.95, 0.99],
            "seed": seeds_10,
        },
    )

    print("\nAll experiments complete.")


if __name__ == "__main__":
    main()
