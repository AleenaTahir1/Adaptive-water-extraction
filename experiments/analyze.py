"""Generate all report figures from the batch_run CSVs.

Reads:
    data/results/batch_A_tragedy_baseline.csv
    data/results/batch_B_with_enforcement.csv
    data/results/batch_C_gamma_sweep.csv
    data/results/sensitivity.csv

Writes PNGs to figures/:
    fig01_water_by_scenario.png   -- water level over time, A vs B, by scenario
    fig02_enforcement_effect.png  -- final water vs p_detect (qualitative summary)
    fig03_gamma_sweep.png         -- final water & coop vs gamma, primary RQ
    fig04_sensitivity_tornado.png -- +/-20% effect on final water
    fig05_gini_evolution.png      -- payoff inequality over time per scenario
    fig06_action_distribution.png -- final action distribution by scenario

Run as:
    python -m experiments.analyze
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Match colors to research-paper convention: blue=stable, orange=gradual, red=shock, purple=stochastic
SCENARIO_COLORS = {
    "stable": "#1f77b4",
    "gradual": "#ff7f0e",
    "shock": "#d62728",
    "stochastic": "#9467bd",
}


SUSTAINABLE_YIELD = 30.0  # msy=25 + baseline_inflow=5 (default model config)


def dedupe_model_rows(df: pd.DataFrame) -> pd.DataFrame:
    """batch_run repeats model rows per agent; keep one row per (RunId, Step)."""
    return df.drop_duplicates(subset=["RunId", "Step"]).reset_index(drop=True)


def add_corrected_coop_index(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute the (originally buggy) cooperation_index from raw columns.

    new_coop = water_normalized * (1 - clip(excess_frac, 0, 1))
    where excess_frac = (total_extraction - sustainable_yield) / sustainable_yield.

    This separates collapse (water=0 -> coop=0) from sustained cooperation
    (water=K, ext<=msy -> coop=1). The original metric scored 1.0 in both
    regimes because no extraction is technically "no excess".
    """
    excess = (df["total_extraction"] - SUSTAINABLE_YIELD) / SUSTAINABLE_YIELD
    excess = excess.clip(lower=0, upper=1)
    df = df.copy()
    df["cooperation_index"] = df["water_normalized"] * (1 - excess)
    return df


def load_batch(name: str) -> pd.DataFrame:
    df = pd.read_csv(RESULTS_DIR / f"batch_{name}.csv")
    df = dedupe_model_rows(df)
    df = add_corrected_coop_index(df)
    return df


# ---------------------------------------------------------------------------
# Figure 1: water level over time, A vs B, by climate scenario
# ---------------------------------------------------------------------------
def fig_water_by_scenario():
    A = load_batch("A_tragedy_baseline")
    B = load_batch("B_with_enforcement")

    scenarios = ["stable", "gradual", "shock", "stochastic"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharey=True)
    axes = axes.flatten()
    for ax, sc in zip(axes, scenarios):
        for df, label, ls, alpha in [
            (A, "No enforcement", "--", 0.9),
            (B, "p_detect=0.3", "-", 1.0),
        ]:
            sub = df[df["climate_scenario"] == sc]
            agg = sub.groupby("Step")["water_level"].agg(["mean", "std"])
            ax.plot(agg.index, agg["mean"], color=SCENARIO_COLORS[sc],
                    linestyle=ls, alpha=alpha, label=label, linewidth=2)
            ax.fill_between(
                agg.index, agg["mean"] - agg["std"], agg["mean"] + agg["std"],
                color=SCENARIO_COLORS[sc], alpha=0.12,
            )
        ax.axhline(200, color="grey", linestyle=":", linewidth=1, label="critical (20% K)")
        ax.set_title(f"Climate: {sc}")
        ax.set_xlabel("step")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9, loc="best")
        ax.set_ylabel("water level (mean +/- sd over 30 seeds)")
    fig.suptitle("Water level over time -- tragedy baseline vs moderate enforcement", fontsize=14)
    fig.tight_layout()
    out = FIGURES_DIR / "fig01_water_by_scenario.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {out.name}")


# ---------------------------------------------------------------------------
# Figure 2: final water level by scenario, with vs without enforcement (bar)
# ---------------------------------------------------------------------------
def fig_enforcement_effect():
    A = load_batch("A_tragedy_baseline")
    B = load_batch("B_with_enforcement")
    scenarios = ["stable", "gradual", "shock", "stochastic"]
    final = {"sc": [], "label": [], "mean_water": [], "std": [], "coop": []}
    for sc in scenarios:
        for df, label in [(A, "No enforcement"), (B, "p_detect=0.3")]:
            sub = df[(df["climate_scenario"] == sc)].sort_values("Step").groupby("RunId").tail(1)
            final["sc"].append(sc)
            final["label"].append(label)
            final["mean_water"].append(sub["water_level"].mean())
            final["std"].append(sub["water_level"].std())
            final["coop"].append(sub["cooperation_index"].mean())
    df_f = pd.DataFrame(final)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    x = np.arange(len(scenarios))
    width = 0.35
    for i, label in enumerate(["No enforcement", "p_detect=0.3"]):
        vals = df_f[df_f["label"] == label]["mean_water"].values
        errs = df_f[df_f["label"] == label]["std"].values
        ax1.bar(x + (i - 0.5) * width, vals, width, yerr=errs, capsize=4, label=label)
    ax1.set_xticks(x); ax1.set_xticklabels(scenarios)
    ax1.set_ylabel("final water level (mean +/- sd)")
    ax1.set_title("Final water level by climate x enforcement")
    ax1.legend(); ax1.grid(alpha=0.3, axis="y")

    for i, label in enumerate(["No enforcement", "p_detect=0.3"]):
        vals = df_f[df_f["label"] == label]["coop"].values
        ax2.bar(x + (i - 0.5) * width, vals, width, label=label)
    ax2.set_xticks(x); ax2.set_xticklabels(scenarios)
    ax2.set_ylabel("cooperation index")
    ax2.set_title("Cooperation index by climate x enforcement")
    ax2.set_ylim(0, 1.1)
    ax2.legend(); ax2.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    out = FIGURES_DIR / "fig02_enforcement_effect.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {out.name}")


# ---------------------------------------------------------------------------
# Figure 3: gamma sweep (the primary research question)
# ---------------------------------------------------------------------------
def fig_gamma_sweep():
    C = load_batch("C_gamma_sweep")
    finals = C.sort_values("Step").groupby("RunId").tail(1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for sc in ["stable", "shock"]:
        sub = finals[finals["climate_scenario"] == sc]
        agg = sub.groupby("gamma").agg(
            water_mean=("water_level", "mean"),
            water_std=("water_level", "std"),
            coop_mean=("cooperation_index", "mean"),
            coop_std=("cooperation_index", "std"),
        ).reset_index()
        axes[0].errorbar(agg["gamma"], agg["water_mean"], yerr=agg["water_std"],
                         marker="o", capsize=4, label=f"{sc}", linewidth=2)
        axes[1].errorbar(agg["gamma"], agg["coop_mean"], yerr=agg["coop_std"],
                         marker="o", capsize=4, label=f"{sc}", linewidth=2)
    axes[0].set_xlabel("discount factor gamma"); axes[0].set_ylabel("final water level")
    axes[0].set_title("Final water level vs gamma"); axes[0].grid(alpha=0.3); axes[0].legend()
    axes[1].set_xlabel("discount factor gamma"); axes[1].set_ylabel("cooperation index")
    axes[1].set_title("Cooperation index vs gamma"); axes[1].grid(alpha=0.3); axes[1].legend()
    axes[1].set_ylim(0, 1.1)
    fig.suptitle("Primary RQ: effect of discount factor on sustainable extraction", fontsize=13)
    fig.tight_layout()
    out = FIGURES_DIR / "fig03_gamma_sweep.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {out.name}")


# ---------------------------------------------------------------------------
# Figure 4: sensitivity tornado
# ---------------------------------------------------------------------------
def fig_sensitivity_tornado():
    path = RESULTS_DIR / "sensitivity.csv"
    if not path.exists():
        print("  (skipped: run experiments/sensitivity.py first)")
        return
    df = pd.read_csv(path)
    params = df["param"].unique()

    # For each param, compute mean final water at low (-20%), baseline, high (+20%).
    rows = []
    for p in params:
        sub = df[df["param"] == p]
        values_sorted = sorted(sub["value"].unique())
        low, base, high = values_sorted[0], values_sorted[1], values_sorted[2]
        low_water = sub[sub["value"] == low]["final_water"].mean()
        base_water = sub[sub["value"] == base]["final_water"].mean()
        high_water = sub[sub["value"] == high]["final_water"].mean()
        rows.append({"param": p, "low": low_water - base_water, "high": high_water - base_water})

    tornado = pd.DataFrame(rows)
    # Sort by absolute effect size
    tornado["abs"] = tornado[["low", "high"]].abs().max(axis=1)
    tornado = tornado.sort_values("abs")

    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(tornado))
    ax.barh(y, tornado["low"], color="#1f77b4", label="-20%")
    ax.barh(y, tornado["high"], color="#d62728", label="+20%")
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(y); ax.set_yticklabels(tornado["param"])
    ax.set_xlabel("Change in final water level vs baseline (mean over 10 seeds)")
    ax.set_title("Sensitivity to +/-20% parameter perturbations")
    ax.legend()
    ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    out = FIGURES_DIR / "fig04_sensitivity_tornado.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {out.name}")


# ---------------------------------------------------------------------------
# Figure 5: Gini coefficient (payoff inequality) over time
# ---------------------------------------------------------------------------
def fig_gini_evolution():
    B = load_batch("B_with_enforcement")
    scenarios = ["stable", "gradual", "shock", "stochastic"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for sc in scenarios:
        sub = B[B["climate_scenario"] == sc]
        agg = sub.groupby("Step")["gini_payoff"].mean()
        ax.plot(agg.index, agg.values, label=sc, color=SCENARIO_COLORS[sc], linewidth=2)
    ax.set_xlabel("step"); ax.set_ylabel("Gini coefficient of cumulative payoff")
    ax.set_title("Payoff inequality (Gini) over time, with enforcement")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    out = FIGURES_DIR / "fig05_gini_evolution.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {out.name}")


# ---------------------------------------------------------------------------
# Figure 6: final action distribution by scenario
# ---------------------------------------------------------------------------
def fig_action_distribution():
    B = load_batch("B_with_enforcement")
    scenarios = ["stable", "gradual", "shock", "stochastic"]
    finals = B.sort_values("Step").groupby("RunId").tail(1)
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.18
    x = np.arange(len(scenarios))
    for i, sc in enumerate(scenarios):
        sub = finals[finals["climate_scenario"] == sc]
        coop = sub["frac_action_cooperative"].mean()
        defect = sub["frac_action_defect"].mean()
        ax.bar(i - width / 2, coop, width, color="#2ca02c", label="cooperative (action <= 2)" if i == 0 else "")
        ax.bar(i + width / 2, defect, width, color="#d62728", label="defecting (action >= 3)" if i == 0 else "")
    ax.set_xticks(x); ax.set_xticklabels(scenarios)
    ax.set_ylabel("fraction of farmers"); ax.set_ylim(0, 1.05)
    ax.set_title("Final action distribution by climate scenario (with enforcement)")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    out = FIGURES_DIR / "fig06_action_distribution.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {out.name}")


def main():
    print(f"Generating figures to {FIGURES_DIR}/")
    fig_water_by_scenario()
    fig_enforcement_effect()
    fig_gamma_sweep()
    fig_sensitivity_tornado()
    fig_gini_evolution()
    fig_action_distribution()
    print("Done.")


if __name__ == "__main__":
    main()
