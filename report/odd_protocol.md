# ODD Protocol

**Model:** Agent-Based Model of Adaptive Water Extraction Strategies Using Q-Learning Under Climate Stress Scenarios
**Author:** Aleena Tahir (F23607001)
**Following:** Grimm et al. (2020), *Ecological Modelling*, vol. 428

---

## 1. Overview

### 1.1 Purpose and Patterns

The purpose of the model is to investigate how Q-learning agents discover
extraction strategies for a shared water resource under climate stress,
and at what monitoring intensity decentralized self-regulation becomes
sufficient. The model is designed to reproduce three patterns
documented in the empirical and theoretical literature:

1. **Tragedy of the commons** (Hardin 1968): unmonitored over-extraction
   leads to resource collapse.
2. **Scarcity drives aggression, abundance enables cooperation**
   (Perolat et al. 2017): the behavioral response to resource state.
3. **Oscillatory dynamics under environmental shock** (Weitz et al. 2016):
   cooperation can break down under stress and recover after relaxation.

### 1.2 Entities, State Variables, and Scales

| Entity | State variables |
|---|---|
| **Irrigator agent** | `q_table`, `cumulative_payoff`, `last_action_idx`, `last_extraction`, `fines_paid`, `strategy_type` |
| **Water resource** | `level`, `carrying_capacity`, `regeneration_rate`, `baseline_inflow`, `history` |
| **Monitor agent** | `p_detect`, `fine_factor`, `n_detections`, `total_fines_issued` |
| **Climate scenario** | `name`, scenario-specific parameters (e.g., `shock_start`, `mean_cf`) |

- **Spatial scale:** 20 × 20 grid; one column reserved as river (visualization only); farmers occupy farmland cells.
- **Temporal scale:** one step ≈ one irrigation season; default run length 500 steps (~125 years if mapped to quarterly seasons).

### 1.3 Process Overview and Scheduling

Each simulation step proceeds in three stages, enforced by `WaterCommonsModel.step()`:

1. **Stage 1 (act):** Each irrigator observes the current state and selects an
   action (extraction level). All extraction requests are pooled at the resource.
2. **Stage 1.5 (monitor):** The water authority probabilistically detects
   over-extractors and issues fines.
3. **Stage 2 (regenerate):** The water resource grows logistically (modulated by
   the climate factor) and supplies baseline inflow; accumulated extraction is
   subtracted.
4. **Stage 3 (finalize):** Each irrigator computes its reward from the post-regen
   water state and (if a Q-learner) updates its Q-table using the Bellman rule.

Agent activation order within each stage is randomized
(`mesa.time.RandomActivation`) so no agent has structural priority.

---

## 2. Design Concepts

| Concept | Implementation in this model |
|---|---|
| **Basic principles** | Tragedy of the commons (Hardin 1968); Q-learning (Watkins & Dayan 1992); logistic resource dynamics. |
| **Emergence** | Cooperation or collapse is *not programmed* — it emerges from the collective interaction of independently-learning agents with a shared resource. |
| **Adaptation** | Q-learners update Q-values via the Bellman equation after every transition; ε decays exponentially so the population gradually shifts from exploration to exploitation. |
| **Objectives** | Each agent maximizes expected discounted reward, where reward = log-utility of extraction − sustainability penalty − fines. |
| **Learning** | Tabular Q-learning with ε-greedy exploration. Fixed-strategy agents (always-cooperate, always-defect, tit-for-tat) provide comparators. |
| **Prediction** | Agents do not explicitly predict the future; the discount factor γ encodes how much they value future rewards. |
| **Sensing** | Agents observe the global water level, their own previous action, the average action of social-network neighbors, and a binary climate-stress flag. |
| **Interaction** | Indirect through the shared resource; direct through social-network observation; mediated by the monitor for detection. |
| **Stochasticity** | (i) Initial Q-table noise; (ii) ε-greedy random actions; (iii) random social network topology; (iv) stochastic climate scenario; (v) random monitor detection draws. |
| **Collectives** | The set of irrigators sharing the resource constitutes the relevant collective; cooperation_index and Gini are population-level summaries. |
| **Observation** | `mesa.DataCollector` records 13 model-level and 6 agent-level variables every step; CSV export feeds matplotlib analysis. |

---

## 3. Details

### 3.1 Initialization

| Parameter | Default | Reference |
|---|---|---|
| `n_farmers` | 20 | Mid-range of proposal table (5–100) |
| `carrying_capacity (K)` | 1000.0 | Normalized units; MSY = r·K/4 = 25 |
| `regeneration_rate (r)` | 0.10 | Mid-range of proposal table (0.01–0.3) |
| `baseline_inflow` | 5.0 | Prevents permanent collapse from a single early shock |
| `initial_water_fraction` | 0.80 | Healthy starting state |
| `max_extraction (per agent)` | auto-scaled so action 2 == per-agent fair share of (MSY + baseline_inflow) | Keeps dilemma invariant under N |
| `alpha` | 0.15 | Standard Q-learning |
| `gamma` | 0.95 | Mid-range of proposal (0.5–0.99) |
| `epsilon_0` | 0.30 | Lower than 1.0 to prevent initial-exploration collapse |
| `decay_rate` | 0.010 | Exploration -> exploitation by step ~300 |
| `sustainability_penalty` | 2.0 | Quadratic in water scarcity |
| `social_degree (k)` | 4 | Random k-regular graph |
| `p_detect` | 0.0 (baseline) or 0.30 (enforcement) | Compared empirically |
| `fine_factor` | 3.0 | Scale of fine per unit excess extraction |
| Climate scenario | `stable` | One of {stable, gradual, shock, stochastic} |

Initial water level: `initial_water_fraction × K = 800`.
Initial Q-tables: empty (lazy-initialized on first state visit with small uniform noise in [-0.01, 0.01]).
Initial agent positions: uniformly random over farmland cells.

### 3.2 Input Data

No external time-series inputs. The climate factor `cf(t)` is generated
endogenously by the chosen scenario class. For validation (Phase 11) we
compare emergent dynamics qualitatively to FAO water-stress statistics
and the Indus Basin drought of 2022.

### 3.3 Submodels

#### Water resource dynamics

W(t+1) = max(0, min(K, W(t) + r · cf(t) · W(t) · (1 − W(t)/K) + baseline_inflow · cf(t) − Σᵢ eᵢ(t)))

#### Q-learning update (Watkins & Dayan 1992)

Q(s, a) ← Q(s, a) + α · [r + γ · maxₐ′ Q(s′, a′) − Q(s, a)]

State s = (water_bin, own_last_action, neighbors_avg_bin, climate_stressed)
Action a ∈ {0, 1, 2, 3, 4} mapping to extraction fractions {0, 0.25, 0.5, 0.75, 1.0} × max_extraction.

#### Reward

r = log(1 + extracted) − sustainability_penalty · (1 − water_norm_after)² − fine

#### Monitor

For each agent with action > 2:
  - With probability `p_detect`, fine = `(action_level − 0.5) · max_extraction · fine_factor`
  - Fine deducted from that step's reward, propagating into the Q-update.

#### Climate scenarios

- **Stable:** cf = 1.0 ∀t
- **Gradual:** cf linearly declines from 1.0 to 0.5 over 400 steps
- **Shock:** cf = 1.0 normally, drops to 0.3 for steps [200, 300)
- **Stochastic:** cf ~ N(0.85, 0.15²), clipped to [0.3, 1.0], deterministic per (seed, t)
