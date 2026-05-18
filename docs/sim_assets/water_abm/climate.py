"""Climate scenarios — how the climate factor cf(t) evolves over time.

cf(t) in [0, 1] multiplies the logistic regeneration term in the
WaterResource. cf = 1.0 means full natural regeneration; cf = 0.3
means a 70% drop in recharge (severe drought).

Four scenarios, matching the research proposal:
  - Stable:     cf == 1.0 for all t
  - Gradual:    cf linearly declines from 1.0 to `min_cf` over `decline_steps`
  - Shock:      cf == 1.0 normally, drops to `shock_cf` between
                `shock_start` and `shock_end`, then recovers
  - Stochastic: cf = mean + gaussian noise, clipped to [min_cf, 1.0]
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod


class ClimateScenario(ABC):
    """Base class for climate scenarios. Subclasses implement climate_factor(t)."""

    name: str = "base"

    @abstractmethod
    def climate_factor(self, t: int) -> float:
        """Return the climate multiplier for simulation step t."""

    def is_stressed(self, t: int) -> bool:
        """Coarse binary stress flag — used as part of the Q-learning state."""
        return self.climate_factor(t) < 0.7


class StableClimate(ClimateScenario):
    """cf == 1.0 forever. Baseline 'no climate change' scenario."""

    name = "stable"

    def __init__(self, cf: float = 1.0):
        self.cf = cf

    def climate_factor(self, t: int) -> float:
        return self.cf


class GradualDecline(ClimateScenario):
    """cf decays linearly from start_cf to min_cf over `decline_steps`."""

    name = "gradual"

    def __init__(
        self,
        start_cf: float = 1.0,
        min_cf: float = 0.5,
        decline_steps: int = 400,
    ):
        self.start_cf = start_cf
        self.min_cf = min_cf
        self.decline_steps = max(1, decline_steps)

    def climate_factor(self, t: int) -> float:
        progress = min(1.0, t / self.decline_steps)
        return self.start_cf - progress * (self.start_cf - self.min_cf)


class DroughtShock(ClimateScenario):
    """Sudden drought between [shock_start, shock_end]; cf otherwise = baseline_cf."""

    name = "shock"

    def __init__(
        self,
        baseline_cf: float = 1.0,
        shock_cf: float = 0.3,
        shock_start: int = 200,
        shock_end: int = 300,
    ):
        self.baseline_cf = baseline_cf
        self.shock_cf = shock_cf
        self.shock_start = shock_start
        self.shock_end = shock_end

    def climate_factor(self, t: int) -> float:
        if self.shock_start <= t < self.shock_end:
            return self.shock_cf
        return self.baseline_cf


class StochasticClimate(ClimateScenario):
    """Gaussian noise around `mean_cf`, clipped to [min_cf, max_cf].

    Uses a deterministic seed for reproducibility — the noise is computed
    from t so that two runs with the same seed see the same cf trajectory.
    """

    name = "stochastic"

    def __init__(
        self,
        mean_cf: float = 0.85,
        sigma: float = 0.15,
        min_cf: float = 0.3,
        max_cf: float = 1.0,
        seed: int = 0,
    ):
        self.mean_cf = mean_cf
        self.sigma = sigma
        self.min_cf = min_cf
        self.max_cf = max_cf
        self.seed = seed
        self._rng = random.Random(seed)
        self._cache: dict[int, float] = {}

    def climate_factor(self, t: int) -> float:
        if t in self._cache:
            return self._cache[t]
        # Deterministic stream per (seed, t) so results are reproducible.
        # Python 3.11+ rejects tuple seeds, so we combine into an int.
        local_rng = random.Random(hash((self.seed, t)) & 0xFFFFFFFF)
        sample = local_rng.gauss(self.mean_cf, self.sigma)
        cf = max(self.min_cf, min(self.max_cf, sample))
        self._cache[t] = cf
        return cf


# Registry so model / UI can build scenarios by name.
SCENARIO_REGISTRY: dict[str, type[ClimateScenario]] = {
    "stable": StableClimate,
    "gradual": GradualDecline,
    "shock": DroughtShock,
    "stochastic": StochasticClimate,
}


def build_scenario(name: str, **kwargs) -> ClimateScenario:
    """Factory: build a scenario by name with optional keyword overrides."""
    if name not in SCENARIO_REGISTRY:
        raise ValueError(
            f"Unknown climate scenario {name!r}. "
            f"Choose from: {sorted(SCENARIO_REGISTRY)}"
        )
    return SCENARIO_REGISTRY[name](**kwargs)
