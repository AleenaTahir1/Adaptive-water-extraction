"""Agent classes for the water commons model.

Step is split into two stages so the Q-learning Bellman update sees the
correct s' (the state AFTER the resource has regenerated):

    Stage 1 -- act():        observe s_t, pick a_t, extract
    Stage 2 -- (model)       water resource regenerates
    Stage 3 -- finalize():   observe s_{t+1}, compute reward, update Q(s_t, a_t)

Phase 1 used a simpler one-stage step; we replace it here so Q-learning
can converge on the true Markov dynamics.
"""
from __future__ import annotations

from typing import Optional

import mesa

from .q_learning import QLearner, make_state

# Five discrete extraction levels as fractions of the per-step maximum.
ACTION_LEVELS = [0.0, 0.25, 0.5, 0.75, 1.0]


class IrrigatorAgent(mesa.Agent):
    """Irrigator farmer with a Q-learning policy over 5 extraction levels.

    Subclasses can override `choose_action` to implement fixed strategies
    (Phase 4: AlwaysCooperate, AlwaysDefect, TitForTat).
    """

    def __init__(
        self,
        unique_id: int,
        model: mesa.Model,
        max_extraction: float = 2.5,
        # Q-learning hyperparameters
        alpha: float = 0.10,
        gamma: float = 0.95,
        epsilon_0: float = 1.0,
        epsilon_min: float = 0.05,
        decay_rate: float = 0.005,
        # Reward shaping
        utility_scale: float = 1.0,
        sustainability_penalty: float = 2.0,
        critical_fraction: float = 0.20,
        # Per-agent seed for Q-table initialization (heterogeneity)
        seed: Optional[int] = None,
    ):
        super().__init__(unique_id, model)
        self.max_extraction = max_extraction
        self.utility_scale = utility_scale
        self.sustainability_penalty = sustainability_penalty
        self.critical_fraction = critical_fraction
        self.strategy_type: str = "q_learner"

        self.q_learner = QLearner(
            n_actions=len(ACTION_LEVELS),
            alpha=alpha,
            gamma=gamma,
            epsilon_0=epsilon_0,
            epsilon_min=epsilon_min,
            decay_rate=decay_rate,
            seed=seed,
        )

        # Per-step bookkeeping
        self.last_action_idx: int = 0
        self.last_extraction: float = 0.0
        self.last_reward: float = 0.0
        self.cumulative_payoff: float = 0.0
        self.fines_paid: float = 0.0

        # Stage-1 scratchpad — populated by act(), consumed by finalize()
        self._current_state: Optional[tuple] = None
        self._current_action: Optional[int] = None
        self._current_granted: float = 0.0

    # --- Observation -----------------------------------------------------

    def _observe_state(self) -> tuple:
        water_norm = self.model.water.normalized_level
        climate_stressed = self.model.climate.is_stressed(self.model.step_count)
        neighbors_avg = self._neighbors_avg_action_norm()
        return make_state(
            water_norm=water_norm,
            own_last_action_idx=self.last_action_idx,
            neighbors_avg_action_norm=neighbors_avg,
            climate_stressed=climate_stressed,
        )

    def _neighbors_avg_action_norm(self) -> Optional[float]:
        """Phase-4 hook: returns average neighbor action level in [0, 1].

        Returns None when no social network is configured (Phase 3 baseline).
        """
        neighbors = getattr(self.model, "social_neighbors", {}).get(self.unique_id)
        if not neighbors:
            return None
        actions = [
            ACTION_LEVELS[self.model.schedule._agents[nid].last_action_idx]
            for nid in neighbors
            if nid in self.model.schedule._agents
        ]
        if not actions:
            return None
        return sum(actions) / len(actions)

    # --- Action selection (overridable) ---------------------------------

    def choose_action(self, state: tuple) -> int:
        return self.q_learner.select_action(state)

    # --- Reward ---------------------------------------------------------

    def _reward(self, granted: float, water_norm_after: float) -> float:
        """Per-step reward: utility - sustainability penalty - fines.

        utility:  log(1 + granted * utility_scale)         -- diminishing returns
        penalty:  smooth quadratic, sustainability_penalty * (1 - water_norm)^2
                  -- non-zero at all water levels so the learning signal is
                  always present (a hard threshold left agents with no
                  gradient once water collapsed).
        fines:    deducted via apply_fine() (Phase 5 monitor)
        """
        import math

        utility = math.log1p(granted * self.utility_scale)
        scarcity = 1.0 - water_norm_after
        penalty = self.sustainability_penalty * scarcity * scarcity
        return utility - penalty - self._pending_fine

    # --- Monitor hook ---------------------------------------------------

    _pending_fine: float = 0.0

    def apply_fine(self, amount: float) -> None:
        """Phase 5 monitor calls this when it catches over-extraction."""
        self._pending_fine += max(0.0, amount)
        self.fines_paid += max(0.0, amount)

    # --- Two-stage step -------------------------------------------------

    def act(self) -> None:
        """Stage 1: observe state, choose action, extract water."""
        state = self._observe_state()
        action_idx = self.choose_action(state)
        requested = ACTION_LEVELS[action_idx] * self.max_extraction
        granted = self.model.water.request_extraction(requested)

        self._current_state = state
        self._current_action = action_idx
        self._current_granted = granted
        self._pending_fine = 0.0  # reset before monitor stage

    def finalize(self) -> None:
        """Stage 3: post-regen reward + Q-table update."""
        water_norm_after = self.model.water.normalized_level
        reward = self._reward(self._current_granted, water_norm_after)
        next_state = self._observe_state()

        if self.strategy_type == "q_learner" and self._current_state is not None:
            self.q_learner.update(
                self._current_state,
                self._current_action,
                reward,
                next_state,
            )

        # Bookkeeping for DataCollector & UI
        self.last_action_idx = self._current_action
        self.last_extraction = self._current_granted
        self.last_reward = reward
        self.cumulative_payoff += reward

    # Mesa's scheduler calls .step(); we delegate to act() so the model can
    # invoke finalize() in a second pass after regeneration.
    def step(self) -> None:
        self.act()


# ---------------------------------------------------------------------------
# Fixed-strategy variants used as baselines / mixed-population comparators
# ---------------------------------------------------------------------------


class AlwaysCooperateAgent(IrrigatorAgent):
    """Always picks the cooperative fair-share action (index 2)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.strategy_type = "always_coop"

    def choose_action(self, state: tuple) -> int:
        return 2


class AlwaysDefectAgent(IrrigatorAgent):
    """Always picks the maximum-extraction action (index 4)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.strategy_type = "always_defect"

    def choose_action(self, state: tuple) -> int:
        return 4


class TitForTatAgent(IrrigatorAgent):
    """Mirrors the average action level observed among neighbors.

    Defaults to the cooperative action (index 2) when no neighbor signal
    is available (first step or no social network configured).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.strategy_type = "tit_for_tat"

    def choose_action(self, state: tuple) -> int:
        nbr_avg = self._neighbors_avg_action_norm()
        if nbr_avg is None:
            return 2
        # nbr_avg is in [0, 1]; round to nearest action index
        return min(4, max(0, round(nbr_avg * 4)))


STRATEGY_REGISTRY: dict[str, type[IrrigatorAgent]] = {
    "q_learner": IrrigatorAgent,
    "always_coop": AlwaysCooperateAgent,
    "always_defect": AlwaysDefectAgent,
    "tit_for_tat": TitForTatAgent,
}


# ---------------------------------------------------------------------------
# Monitor / water-authority agent (Phase 5)
# ---------------------------------------------------------------------------

# Actions > this index are considered "over-extraction" (above the cooperative
# fair share). The monitor only checks for these.
FAIR_SHARE_ACTION_IDX = 2


class MonitorAgent(mesa.Agent):
    """Water authority that probabilistically detects and fines over-extractors.

    The monitor runs in a dedicated stage between agent extraction and resource
    regeneration. Detection is a Bernoulli draw with probability `p_detect`
    against each over-extractor; the fine is proportional to the excess
    extraction above fair share, scaled by `fine_factor`.

    Not registered in the scheduler -- the model invokes `run()` directly
    at the correct stage.
    """

    def __init__(
        self,
        unique_id: int,
        model: mesa.Model,
        p_detect: float = 0.0,
        fine_factor: float = 2.0,
    ):
        super().__init__(unique_id, model)
        self.p_detect = p_detect
        self.fine_factor = fine_factor
        self.total_fines_issued: float = 0.0
        self.n_detections: int = 0
        self.n_checks: int = 0
        self.strategy_type: str = "monitor"

    def run(self) -> None:
        """Check every irrigator that took an over-extraction action."""
        if self.p_detect <= 0:
            return
        for agent in self.model.schedule.agents:
            if not isinstance(agent, IrrigatorAgent):
                continue
            if agent._current_action is None:
                continue
            if agent._current_action <= FAIR_SHARE_ACTION_IDX:
                continue
            self.n_checks += 1
            if self.random.random() >= self.p_detect:
                continue
            excess_level = (
                ACTION_LEVELS[agent._current_action]
                - ACTION_LEVELS[FAIR_SHARE_ACTION_IDX]
            )
            fine = excess_level * agent.max_extraction * self.fine_factor
            agent.apply_fine(fine)
            self.total_fines_issued += fine
            self.n_detections += 1
