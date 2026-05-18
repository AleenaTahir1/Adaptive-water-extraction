"""Tabular Q-learning for water-extraction decisions.

Pure logic — no Mesa imports — so it's easy to unit-test in isolation.

State (a hashable tuple, produced by `make_state`):
    (water_bin, own_last_action_idx, neighbors_avg_bin, climate_state)

Action: integer index into `agents.ACTION_LEVELS` (default 5 levels).

Update rule (Watkins 1989):
    Q(s, a) <- Q(s, a) + alpha * [r + gamma * max_a' Q(s', a') - Q(s, a)]

Policy: epsilon-greedy with exponential decay
    epsilon(t) = max(epsilon_min, epsilon_0 * exp(-decay_rate * t))
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np


def bin_value(value: float, n_bins: int, lo: float = 0.0, hi: float = 1.0) -> int:
    """Map `value` in [lo, hi] to an integer bin in [0, n_bins-1]."""
    if hi <= lo:
        return 0
    clipped = max(lo, min(hi, value))
    fraction = (clipped - lo) / (hi - lo)
    return min(n_bins - 1, int(fraction * n_bins))


def make_state(
    water_norm: float,
    own_last_action_idx: int,
    neighbors_avg_action_norm: Optional[float],
    climate_stressed: bool,
    n_water_bins: int = 3,
    n_neighbor_bins: int = 3,
) -> tuple:
    """Build a discrete state tuple from raw observations.

    `neighbors_avg_action_norm` is None when the agent has no neighbors yet
    (Phase 3 single-agent test); Phase 4 supplies a real value.
    """
    nbr_bin = (
        bin_value(neighbors_avg_action_norm, n_neighbor_bins)
        if neighbors_avg_action_norm is not None
        else -1
    )
    return (
        bin_value(water_norm, n_water_bins),
        own_last_action_idx,
        nbr_bin,
        int(climate_stressed),
    )


class QLearner:
    """Tabular Q-learner with epsilon-greedy exploration and exponential decay."""

    def __init__(
        self,
        n_actions: int = 5,
        alpha: float = 0.10,
        gamma: float = 0.95,
        epsilon_0: float = 1.0,
        epsilon_min: float = 0.05,
        decay_rate: float = 0.005,
        init_q_noise: float = 0.01,
        seed: Optional[int] = None,
    ):
        self.n_actions = n_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon_0 = epsilon_0
        self.epsilon_min = epsilon_min
        self.decay_rate = decay_rate
        self.init_q_noise = init_q_noise
        self.rng = np.random.default_rng(seed)
        self.q_table: dict[tuple, np.ndarray] = {}
        self.update_count: int = 0

    def epsilon(self) -> float:
        return max(
            self.epsilon_min,
            self.epsilon_0 * math.exp(-self.decay_rate * self.update_count),
        )

    def _q_row(self, state: tuple) -> np.ndarray:
        """Lazily initialize Q-values for unseen states with small noise."""
        if state not in self.q_table:
            self.q_table[state] = self.rng.uniform(
                -self.init_q_noise, self.init_q_noise, size=self.n_actions
            )
        return self.q_table[state]

    def select_action(self, state: tuple) -> int:
        """Epsilon-greedy: explore with prob epsilon, else greedy (ties broken at random)."""
        if self.rng.random() < self.epsilon():
            return int(self.rng.integers(self.n_actions))
        row = self._q_row(state)
        max_val = row.max()
        # Tie-break uniformly among co-optimal actions so symmetry doesn't lock us in.
        candidates = np.flatnonzero(row >= max_val - 1e-9)
        return int(self.rng.choice(candidates))

    def update(
        self,
        state: tuple,
        action: int,
        reward: float,
        next_state: tuple,
    ) -> None:
        q_sa = self._q_row(state)[action]
        max_next = float(self._q_row(next_state).max())
        td_target = reward + self.gamma * max_next
        self._q_row(state)[action] = q_sa + self.alpha * (td_target - q_sa)
        self.update_count += 1

    # --- introspection helpers (used by DataCollector and analysis) -------

    def mean_q(self) -> float:
        if not self.q_table:
            return 0.0
        return float(np.mean([row.mean() for row in self.q_table.values()]))

    def greedy_policy_summary(self) -> dict[tuple, int]:
        """Return {state: argmax_a Q(s,a)} — the current greedy policy."""
        return {state: int(row.argmax()) for state, row in self.q_table.items()}
