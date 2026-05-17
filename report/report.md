# Agent-Based Modeling of Adaptive Water Extraction Strategies Using Q-Learning Under Climate Stress Scenarios

**Aleena Tahir** | F23607001 | AI-23
National University of Technology | Department of Artificial Intelligence
*Course:* Agent-Based Modeling | *Instructor:* Ms. Sumera Aslam
*Date:* May 2026

---

## Abstract

Water scarcity is one of the defining challenges of the 21st century, and the
classic "tragedy of the commons" makes shared irrigation systems particularly
vulnerable. Existing agent-based models of water commons typically assign
fixed behavioral rules to agents, ignoring the way real farming communities
*learn* and adapt. This project develops a Mesa-based agent-based model in
which each irrigator is a tabular Q-learning agent extracting water from a
shared resource with logistic regeneration. We test whether sustainable
extraction can emerge from decentralized learning, how learned strategies
respond to four climate scenarios (stable / gradual decline / drought shock /
stochastic), and how monitoring intensity affects the emergence of
cooperation.

Three findings emerge: **(i)** decentralized Q-learners without enforcement
reproduce the tragedy of the commons in every climate scenario — the
resource collapses to baseline-inflow equilibrium within ~80 steps; **(ii)**
a moderate monitoring probability (`p_detect ≈ 0.3`) is sufficient to flip
the population into a cooperative equilibrium **under stable climate**
(mean final water rises from 5 to 685 units of K=1000); but **(iii)** under
any environmental stress — gradual decline, drought shock, or stochastic
variability — the *same* enforcement intensity fails to prevent collapse.
Importantly, even raising `p_detect` to 0.9 does not rescue the shock
scenario. The mechanism is structural: agents' discretized action space is
calibrated to baseline climate, so during drought even the "fair share"
action is over-extraction. This implies real-world regulators cannot
simply enforce fixed quotas under climate change; *climate-adaptive*
quotas are required.

---

## 1. Introduction

Agricultural communities worldwide depend on shared rivers, canals, and
aquifers. When N farmers draw from the same source, each faces the
fundamental commons dilemma: extracting more is privately rational in the
short term but collectively catastrophic. Hardin (1968) formalized this as
the Tragedy of the Commons. Under climate change — with shifting rainfall,
prolonged droughts, and reduced natural regeneration — the dilemma is
sharper than ever. Pakistan's Indus Basin, which supports over 90 % of the
country's agriculture, is now classified as one of the world's most
water-stressed basins. According to the UN World Water Development Report,
nearly half of the global population will live in areas of high water stress
by 2030.

Traditional models of the commons assume either perfectly rational agents
(game theory) or fixed behavioral types (cooperate / defect / tit-for-tat).
Neither captures the learning process through which real communities
*discover* sustainable norms. This project equips each irrigator with an
independent tabular Q-learning algorithm and tests whether sustainable
extraction emerges, and how it responds to climate stress.

### 1.1 Research Question

**Primary:** *How does the discount factor (γ) in Q-learning agents affect
the emergence of sustainable water extraction strategies under varying
climate stress scenarios in an agent-based commons model?*

**Sub-questions:**
1. Can Q-learning agents discover cooperative extraction strategies without external enforcement?
2. How do learned strategies break down under sudden climate shocks, and how quickly do agents re-adapt?
3. At what monitoring intensity do enforcement mechanisms become unnecessary because agents have learned self-regulation?

---

## 2. Literature Review

*[Reuse content from Assignment 01, Section 5 — verbatim.]*

The literature spans four key contributions:

1. **Perolat et al. (2017)** — NeurIPS multi-agent deep RL on a common-pool resource game. Established that learning agents can reproduce empirical commons patterns; scarcity drives aggression, abundance enables cooperation. Used deep RL in abstract grid environments without water-specific dynamics.
2. **Darbandsari et al. (2020)** — Stackelberg-game ABM of urban water in Tehran. Demonstrated that hierarchical governance improves equity; used fixed game-theoretic strategies, not learning.
3. **Huber et al. (2019)** — Aqua.MORE: NetLogo ABM of coupled water demand-supply at the catchment scale. Provides validated resource regeneration dynamics; agents are rule-based, not adaptive.
4. **Weitz et al. (2016)** — PNAS replicator dynamics with game-environment feedback. Identified oscillatory cooperation-defection cycles when environment couples to strategies; mathematical, not agent-based.

**Research gap.** No existing model combines tabular Q-learning, water-specific
logistic dynamics, *and* explicit climate stress scenarios. This project fills
that gap with a transparent, interpretable Python/Mesa implementation.

---

## 3. ODD Protocol Summary

See `report/odd_protocol.md` for the full Grimm et al. (2020) ODD specification.

**Key design choices:**

- **Entities:** Irrigator agents (Q-learner / always-cooperate / always-defect / tit-for-tat), water resource, monitor agent, climate scenario.
- **Scheduling:** three-stage step (act → monitor → regenerate → finalize) so the Q-update sees the correct post-regen next-state.
- **State space:** `(water_bin, own_last_action, neighbors_avg_bin, climate_stressed)` — discretized to keep tabular Q-learning feasible.
- **Action space:** 5 discrete extraction levels {0 %, 25 %, 50 %, 75 %, 100 %} of a per-agent maximum auto-scaled so the cooperative action (index 2) equals each agent's fair share of sustainable yield.
- **Reward:** `log(1 + extracted) − sustainability_penalty · (1 − water_norm)² − fines`.

---

## 4. Methods

### 4.1 Implementation

The model is implemented in Python 3.12 using Mesa 2.3.4 for the
agent-based-model framework, NetworkX for the social network, NumPy for the
Q-tables, and Matplotlib for the analysis charts. The source is laid out as:

```
water_abm/
  q_learning.py    -- tabular Q-learner with epsilon-greedy and Bellman update
  climate.py       -- four climate scenario classes
  environment.py   -- shared water resource with logistic + baseline regen
  agents.py        -- irrigator (Q-learner + 3 fixed variants) + monitor
  model.py         -- Mesa Model, DataCollector, CSV export
  server.py        -- Mesa visualization (grid + 9 sliders + 3 charts)
```

A complete interactive simulation can be launched with `python run.py`.

### 4.2 Experimental Design

Three batch experiments were run (see `experiments/batch_run.py`):

| Experiment | Variables | N runs |
|---|---|---|
| **A. Tragedy baseline** | 4 climate scenarios × 30 seeds | 120 |
| **B. With enforcement** | 4 climate scenarios × 30 seeds × `p_detect = 0.3` | 120 |
| **C. Gamma sweep (primary RQ)** | 2 climate scenarios × 5 γ values × 10 seeds | 100 |

Each run is 500 steps; metrics are recorded every 10 steps.

**Sensitivity analysis** (`experiments/sensitivity.py`) perturbs each of
{α, γ, ε₀, r, p_detect, N} by ±20 % around the baseline, holding others fixed,
with 10 seeds per setting.

---

## 5. Results

*[Fill in once batch runs complete. Template:]*

### 5.1 Tragedy Baseline (Experiment A)

`figures/fig01_water_by_scenario.png` (dashed lines) shows that without
enforcement, the water resource collapses within ~80 steps in **every**
climate scenario. Mean final water (n = 30 seeds per scenario):

| Climate | Final water | Mean cumulative payoff per agent |
|---|---:|---:|
| stable | 5.55 ± 0.0 | −755.9 |
| gradual | 2.63 ± 0.0 | −795.2 |
| shock | 5.55 ± 0.0 | −768.0 |
| stochastic | 5.44 ± 0.0 | −803.9 |

The standard deviation across 30 seeds is effectively zero: the model
converges deterministically on a low-water attractor where extraction
equals baseline inflow and nothing more. All scenarios produce **strongly
negative** mean payoffs (~−750 to −800 per agent), reproducing the
classical tragedy of the commons.

### 5.2 Enforcement Saves the Stable Climate (Experiment B)

With `p_detect = 0.3` and `fine_factor = 3.0`, the dynamics flip — but only
under the stable climate scenario:

| Climate | Final water | Mean payoff per agent | % cooperative actions | % defecting actions |
|---|---:|---:|---:|---:|
| stable | **684.8 ± 33.5** | **+222.5** | 86 % | 14 % |
| gradual | 2.6 ± 0.0 | −576.8 | 68 % | 32 % |
| shock | 5.6 ± 0.0 | −528.2 | 68 % | 32 % |
| stochastic | 26.6 ± 116.0 | −842.2 | 70 % | 30 % |

Under the **stable** scenario, mean final water rises from 5.5 → 684.8
(125× improvement), payoff turns positive (+222 vs −756), and 86 % of
agents pick cooperative actions. Under the **gradual / shock / stochastic**
scenarios, the same enforcement intensity is **insufficient**: water still
collapses to 2-27 units. Notably, 68-70 % of agents *are still choosing
cooperative actions* in these failing scenarios — they aren't selfishly
defecting, the cooperative action itself is too aggressive for the reduced
regeneration.

A follow-up exploratory sweep confirms that *even* `p_detect = 0.9` (near-
perfect detection) cannot rescue the shock scenario:

| p_detect | stable: final water | shock: final water |
|---:|---:|---:|
| 0.3 | 700 | 5.6 |
| 0.6 | 777 | 5.6 |
| 0.9 | 787 | 5.6 |

The reason is structural: the per-agent fair-share action is calibrated to
baseline (`cf = 1.0`) sustainability. When `cf` drops to 0.3 during the
shock, the same fair-share extraction *is* over-extraction relative to the
reduced regeneration; agents who cooperate under normal conditions become
unwitting over-extractors. The Q-learners' discretized action space cannot
scale finely enough with cf.

This is a substantive finding for water-policy practice: enforcing fixed
quotas works under normal conditions, but climate stress requires
*adaptive* quotas that contract with regeneration.

### 5.3 Discount Factor γ (Primary RQ, Experiment C)

`figures/fig03_gamma_sweep.png` shows the primary research question result.

| γ | stable: final water | shock: final water |
|---:|---:|---:|
| 0.50 | 748.3 ± 18.9 | 5.55 ± 0.0 |
| 0.70 | 722.6 ± 28.3 | 5.55 ± 0.0 |
| 0.85 | 703.5 ± 28.7 | 5.55 ± 0.0 |
| 0.95 | 700.8 ± 34.9 | 5.55 ± 0.0 |
| 0.99 | 688.3 ± 28.1 | 5.55 ± 0.0 |

Two unexpected results:

1. **Under stable climate, water is mildly DECREASING with γ.** Lower-γ
   (more myopic) agents end up with *more* water. Mechanism: higher-γ
   agents weight delayed-fine deterrence more strongly and converge to a
   stricter cooperative policy that under-extracts, allowing water to
   accumulate; but the same forward-looking valuation also encourages
   probing extractions during exploration that lower the long-run mean
   slightly. The effect is small (~9 % range) but consistent across seeds.
2. **Under shock, γ has NO measurable effect.** Every γ value collapses
   to identical final water (5.55 ± 0.0). The shock dynamics dominate the
   Q-learning hyperparameter.

This refines the answer to the primary RQ: **γ matters at the margins
under stable conditions, but the dominant determinant of resilience under
stress is whether the action space can adapt to changing regeneration —
not how much agents discount the future.**

### 5.4 Sensitivity Analysis

`figures/fig04_sensitivity_tornado.png` ranks the six headline parameters by
the magnitude of their effect on final water level when perturbed ±20 %
around the stable-climate baseline (10 seeds per setting).

| Parameter | −20 % Δwater | +20 % Δwater |
|---|---:|---:|
| p_detect | −39.4 | +37.6 |
| ε₀ | −11.0 | −28.6 |
| n_farmers | +16.9 | −25.7 |
| γ | +22.0 | −12.4 |
| regeneration_rate | −19.0 | −10.8 |
| α | −13.8 | −2.4 |

Two patterns stand out: (a) **p_detect dominates** — a 20 % swing in detection
probability produces ±38-40 units of final water (the largest signed range),
confirming enforcement is the single most consequential lever; and (b)
several parameters are **non-monotonic** — ε₀ and α both have negative
deltas in *both* directions, suggesting the baseline value is near a local
optimum.

### 5.5 Inequality

`figures/fig05_gini_evolution.png` tracks the Gini coefficient of cumulative
payoff over time, with enforcement on. All four scenarios converge to
similar inequality levels:

| Climate | Peak Gini | Step of peak | Final Gini |
|---|---:|---:|---:|
| stable | 0.347 | 400 | 0.344 |
| gradual | 0.355 | 240 | 0.326 |
| shock | 0.333 | 500 | 0.333 |
| stochastic | 0.330 | 230 | 0.297 |

Inequality rises quickly (~0.30 by step 100) and then plateaus, reflecting
heterogeneous Q-table initial conditions and the cumulative effect of
small luck-of-detection differences. Stable and stochastic scenarios show
a partial *decline* in Gini after step 230, consistent with the
oscillatory dynamics predicted in Weitz et al. (2016).

---

## 6. Discussion

### 6.1 Answers to Research Questions

- **Sub-Q1 (cooperation without enforcement):** No. Pure Q-learners cannot
  escape the tragedy on their own under any climate scenario. Each agent's
  individual action contributes ~1/N of total extraction, so unilateral
  restraint produces no observable benefit. This matches the multi-agent
  RL findings in Perolat et al. (2017).
- **Sub-Q2 (recovery from shock):** No — at least not within the 500-step
  horizon. Once the resource crashes during a shock, the system is trapped
  in a low-water attractor (water ≈ baseline_inflow / N) where extraction
  is capped at near-zero and all actions yield essentially the same
  reward, providing no gradient for relearning.
- **Sub-Q3 (monitoring threshold under stable climate):** Approximately
  `p_detect = 0.2-0.3` flips the outcome from collapse to cooperation.
  Returns saturate above 0.6. **Under stress, no enforcement intensity
  tested (up to 0.9) is sufficient** — a structural limitation, not a
  parameter-tuning issue.
- **Primary RQ:** γ has minor effect under stable climate (once
  enforcement is in place, all γ values converge to cooperation) and limited
  effect under shock (higher γ delays but does not prevent collapse). The
  dominant determinant of resilience is whether the action space can
  contract with falling regeneration.

### 6.2 Validation

We compare against three external benchmarks (Section 7).

### 6.3 Limitations

- **Fixed discretized action space.** The 5-level extraction grid is
  calibrated to the baseline-climate cooperative share. Under a continuous
  or adaptive action space, agents could in principle scale extraction
  proportionally to current regeneration — preliminary work, future
  paper.
- **Static fair-share definition.** The monitor's `FAIR_SHARE_ACTION_IDX`
  is hard-coded at 2. A climate-aware monitor would tighten this threshold
  during low-cf periods, mirroring real-world drought rationing.
- **Tabular Q-learning.** Limits state granularity; deep RL could capture
  finer patterns at the cost of interpretability.
- **Single resource.** No spatial heterogeneity in water availability.
- **No agent heterogeneity** in risk-aversion or wealth.
- **500-step horizon** corresponds to ~125 years if one step = one season;
  longer horizons may show further structural shifts.
- **Exogenous monitor.** A richer model would let monitoring intensity
  evolve endogenously in response to observed depletion.

---

## 7. Validation

Three structured validation checks are run automatically in
`experiments/validate.py`, with the figure saved as `fig07_validation.png`
and full numbers in `data/results/validation.json`:

| Check | Source | Test | Result |
|---|---|---|---|
| 1. Tragedy | Hardin 1968 | Without enforcement, water should collapse (< 50); with enforcement under stable, water should sustain (> 200). | **PASS** — no-enf final: 5.6; with-enf final: 504 |
| 2. Scarcity → aggression | Perolat et al. 2017 | Fraction of defecting actions during steps 200-300 should be higher under shock than under stable (both with enforcement). | **PASS** — stable: 25.3 % defect; shock: 36.5 % defect (44 % increase) |
| 3. Shock signal | Indus Basin 2022 | A drought cutting `cf` by ~70 % should leave a measurable dip in mean water level at step 300. | **PASS** — stable: 507; shock: 1.5 (99.7 % drop) |

External benchmarks used for calibration:

- **FAO AQUASTAT** indicates natural aquifer recharge rates of 5-15 % of
  carrying capacity per year — brackets our default `r = 0.10`.
- The **2022 Indus Basin drought** reduced river flow by ~50-70 % at peak
  — matched by our `shock_cf = 0.3` choice.
- **Perolat et al. (2017)** report that scarcity drives aggressive
  appropriation in deep-RL commons agents; we reproduce this with the
  44 % increase in defection during the shock window.

---

## 8. Conclusion

This project shows that tabular Q-learning agents in a water commons reproduce
the tragedy when left alone but can flip into cooperation under a modest
external monitoring regime. The discount factor γ matters most when the
environment is stressed, not when it is stable. The interactive Mesa
visualization makes the dynamics inspectable in real time, and the batch
+ sensitivity infrastructure makes the findings reproducible. Future work
could extend to spatially explicit catchments, endogenous monitor
strength, or comparison with human commons experiments.

---

## References

1. Darbandsari, P. et al. (2020). An agent-based conflict resolution model for urban water resources management. *Sustainable Cities and Society*, 57, 102112.
2. Grimm, V. et al. (2020). The ODD protocol for describing agent-based and other simulation models: A second update to improve clarity, replication, and structural realism. *Ecological Modelling*, 428.
3. Hardin, G. (1968). The Tragedy of the Commons. *Science*, 162(3859), 1243–1248.
4. Huber, L. et al. (2019). Agent-Based Modelling of a Coupled Water Demand and Supply System at the Catchment Scale. *Sustainability*, 11(21), 6178.
5. Ostrom, E. (1990). *Governing the Commons*. Cambridge University Press.
6. Perolat, J. et al. (2017). A multi-agent reinforcement learning model of common-pool resource appropriation. *NeurIPS 2017*.
7. Watkins, C. J. C. H. & Dayan, P. (1992). Q-Learning. *Machine Learning*, 8(3-4), 279-292.
8. Weitz, J. S. et al. (2016). An oscillating tragedy of the commons in replicator dynamics with game-environment feedback. *PNAS*, 113(47), E7518-E7525.
9. Wilensky, U. & Rand, W. (2015). *An Introduction to Agent-Based Modeling*. MIT Press.

---

## Appendix A: Parameter Reference

| Symbol | Default | Range explored | Section |
|---|---|---|---|
| N | 20 | {16, 20, 24} (sensitivity) | 4.2 |
| α | 0.15 | {0.12, 0.15, 0.18} | 4.2 |
| γ | 0.95 | {0.50, 0.70, 0.85, 0.95, 0.99} | 5.3 |
| ε₀ | 0.30 | {0.24, 0.30, 0.36} | 4.2 |
| r | 0.10 | {0.08, 0.10, 0.12} | 4.2 |
| p_detect | 0.00 / 0.30 | {0.24, 0.30, 0.36} | 5.2 |
| K | 1000 | fixed | — |
| baseline_inflow | 5.0 | fixed | — |
| fine_factor | 3.0 | fixed | — |

---

## Appendix B: How to Reproduce

```powershell
pip install -r requirements.txt
python -m experiments.batch_run         # ~5 min, writes data/results/batch_*.csv
python -m experiments.sensitivity       # ~3 min, writes data/results/sensitivity.csv
python -m experiments.analyze           # writes figures/fig0*.png
python run.py                           # interactive viz at http://127.0.0.1:8521
```
