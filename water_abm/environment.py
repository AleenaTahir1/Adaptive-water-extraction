"""Shared water resource with logistic regeneration dynamics.

Implements the resource dynamics from the research proposal:

    W(t+1) = W(t) + r * cf(t) * W(t) * (1 - W(t)/K) - sum_i e_i(t)

where r is the regeneration rate, K is carrying capacity, cf(t) is the
climate factor (in [0, 1]) for step t, and e_i(t) is agent i's extraction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class WaterResource:
    """A single shared water resource (river or aquifer).

    Regeneration combines two terms:
      - logistic growth: r * cf(t) * W * (1 - W/K)         (depends on W)
      - baseline inflow: baseline_inflow * cf(t)            (constant per step)

    The baseline term models background flow (rainfall, snowmelt, deep aquifer
    seepage) that persists even at W=0, so the resource can recover from
    collapse. Without it, a single early over-extraction event traps the
    system at W=0 with no learning signal.
    """

    carrying_capacity: float = 1000.0
    regeneration_rate: float = 0.10
    baseline_inflow: float = 5.0
    initial_level: float = 800.0

    level: float = field(init=False)
    history: List[float] = field(default_factory=list, init=False)
    extraction_this_step: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        self.level = self.initial_level
        self.history.append(self.level)

    @property
    def critical_threshold(self) -> float:
        """Below this level the resource is considered depleted (20% of K)."""
        return 0.20 * self.carrying_capacity

    @property
    def is_depleted(self) -> bool:
        return self.level <= self.critical_threshold

    @property
    def normalized_level(self) -> float:
        """Water level expressed as a fraction of carrying capacity (in [0, 1])."""
        return max(0.0, min(1.0, self.level / self.carrying_capacity))

    def request_extraction(self, amount: float) -> float:
        """Try to extract `amount` from the resource. Returns actual amount granted.

        If insufficient water remains, returns whatever is available.
        Accumulates total step extraction so regenerate() can apply it once.
        """
        amount = max(0.0, amount)
        granted = min(amount, max(0.0, self.level - self.extraction_this_step))
        self.extraction_this_step += granted
        return granted

    def regenerate(self, climate_factor: float) -> None:
        """Apply logistic regeneration + baseline inflow, then subtract extraction.

        Called once per simulation step, after all agents have extracted.
        """
        cf = max(0.0, climate_factor)
        logistic = (
            self.regeneration_rate
            * cf
            * self.level
            * (1.0 - self.level / self.carrying_capacity)
        )
        baseline = self.baseline_inflow * cf
        regen = logistic + baseline
        self.level = max(0.0, min(self.carrying_capacity, self.level + regen - self.extraction_this_step))
        self.history.append(self.level)
        self.extraction_this_step = 0.0

    def reset(self) -> None:
        self.level = self.initial_level
        self.history = [self.level]
        self.extraction_this_step = 0.0
