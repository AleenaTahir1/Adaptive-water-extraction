"""WaterCommonsModel — Mesa model wiring agents to a shared water resource.

Each simulation step has THREE stages:
    1. All agents observe state and extract (agent.act, via schedule.step)
    2. Resource regenerates under the current climate factor
    3. All agents finalize: compute reward, perform Bellman update

This ordering is required so the Q-learning update sees the correct
post-regen next-state s_{t+1}.
"""
from __future__ import annotations

from typing import Optional

import mesa
import networkx as nx
import numpy as np
from mesa.datacollection import DataCollector
from mesa.space import MultiGrid
from mesa.time import RandomActivation

from .agents import (
    AlwaysCooperateAgent,
    AlwaysDefectAgent,
    IrrigatorAgent,
    MonitorAgent,
    STRATEGY_REGISTRY,
    TitForTatAgent,
)
from .climate import ClimateScenario, build_scenario
from .environment import WaterResource


def gini_coefficient(values) -> float:
    """Gini coefficient on a sequence of non-negative numbers.

    Values are shifted to be non-negative first so cumulative payoffs
    (which can go negative under heavy enforcement) still produce a
    well-defined inequality measure. Returns 0 when all values are equal.
    """
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return 0.0
    arr = arr - arr.min()  # shift so min is 0
    total = arr.sum()
    if total <= 0:
        return 0.0
    arr = np.sort(arr)
    n = arr.size
    cumulative = np.cumsum(arr)
    return (2.0 * np.sum((np.arange(1, n + 1)) * arr) - (n + 1) * total) / (n * total)


def build_social_network(
    n: int, k: int, seed: Optional[int] = None
) -> dict[int, list[int]]:
    """Random k-regular graph of N farmers. Returns {node: [neighbors]}.

    Falls back gracefully when k > n-1 or n*k is odd. Returns empty
    adjacency dict when k <= 0 (Phase-3 'no neighbors' mode).
    """
    if k <= 0 or n <= 1:
        return {i: [] for i in range(n)}
    k = min(k, n - 1)
    if (n * k) % 2 != 0:
        k = max(1, k - 1)
    if k <= 0:
        return {i: [] for i in range(n)}
    g = nx.random_regular_graph(d=k, n=n, seed=seed)
    return {node: list(g.neighbors(node)) for node in g.nodes()}


# Defaults chosen so total sustainable yield = MSY + baseline_inflow ~= 30 / step.
DEFAULT_CARRYING_CAPACITY = 1000.0
DEFAULT_REGENERATION_RATE = 0.10
DEFAULT_BASELINE_INFLOW = 5.0
MSY = DEFAULT_REGENERATION_RATE * DEFAULT_CARRYING_CAPACITY / 4.0  # 25.0


class WaterCommonsModel(mesa.Model):
    """A shared water resource managed by N irrigator agents."""

    def __init__(
        self,
        # --- Population --------------------------------------------------
        n_farmers: int = 20,
        proportion_q_learners: float = 1.0,  # Phase 4 uses 0..1
        # --- Resource ---------------------------------------------------
        carrying_capacity: float = DEFAULT_CARRYING_CAPACITY,
        regeneration_rate: float = DEFAULT_REGENERATION_RATE,
        baseline_inflow: float = DEFAULT_BASELINE_INFLOW,
        initial_water_fraction: float = 0.80,
        # max_extraction: if None, auto-scale so cooperative action (idx 2)
        # equals each agent's fair share of sustainable yield. User can override.
        max_extraction: Optional[float] = None,
        # --- Climate ----------------------------------------------------
        climate_scenario: str | ClimateScenario = "stable",
        climate_kwargs: Optional[dict] = None,
        # --- Q-learning hyperparameters --------------------------------
        alpha: float = 0.15,
        gamma: float = 0.95,
        epsilon_0: float = 0.30,
        epsilon_min: float = 0.05,
        decay_rate: float = 0.010,
        # --- Reward shaping ---------------------------------------------
        sustainability_penalty: float = 2.0,
        critical_fraction: float = 0.20,
        # --- Spatial layout ---------------------------------------------
        grid_width: int = 20,
        grid_height: int = 20,
        # --- Social network --------------------------------------------
        social_degree: int = 4,
        # --- Monitoring (Phase 5) --------------------------------------
        p_detect: float = 0.0,
        fine_factor: float = 2.0,
        # --- Reproducibility --------------------------------------------
        seed: Optional[int] = None,
    ):
        super().__init__()
        if seed is not None:
            self.reset_randomizer(seed)
        self._seed = seed

        self.n_farmers = n_farmers
        self.proportion_q_learners = proportion_q_learners

        # Auto-scale per-agent max_extraction so the cooperative-share action
        # (index 2 = 0.5 * max_extraction) equals each agent's fair share of
        # total sustainable yield (MSY + baseline_inflow). Keeps the commons
        # dilemma invariant under N for sensitivity sweeps.
        msy = regeneration_rate * carrying_capacity / 4.0
        sustainable_yield = msy + baseline_inflow
        if max_extraction is None:
            fair_share = sustainable_yield / max(1, n_farmers)
            max_extraction = fair_share / 0.5  # so action 2 == fair_share
        self.max_extraction = max_extraction
        self.msy = msy
        self.sustainable_yield = sustainable_yield

        self.water = WaterResource(
            carrying_capacity=carrying_capacity,
            regeneration_rate=regeneration_rate,
            baseline_inflow=baseline_inflow,
            initial_level=initial_water_fraction * carrying_capacity,
        )

        if isinstance(climate_scenario, ClimateScenario):
            self.climate = climate_scenario
        else:
            self.climate = build_scenario(
                climate_scenario, **(climate_kwargs or {})
            )

        self.schedule = RandomActivation(self)
        self.grid = MultiGrid(grid_width, grid_height, torus=False)
        self.river_column = 0

        # Build social network: each farmer observes social_degree neighbors.
        self.social_neighbors = build_social_network(
            n_farmers, social_degree, seed=seed
        )

        # --- Build agents (mixed population) --------------------------
        # Distribute fixed-strategy slots evenly across coop/defect/tft.
        n_q = int(round(proportion_q_learners * n_farmers))
        n_fixed = n_farmers - n_q
        n_coop = n_fixed // 3
        n_defect = n_fixed // 3
        n_tft = n_fixed - n_coop - n_defect
        strategy_plan = (
            ["q_learner"] * n_q
            + ["always_coop"] * n_coop
            + ["always_defect"] * n_defect
            + ["tit_for_tat"] * n_tft
        )
        # Shuffle so strategy assignment is not correlated with position / id.
        self.random.shuffle(strategy_plan)

        for i, strat_name in enumerate(strategy_plan):
            AgentCls = STRATEGY_REGISTRY[strat_name]
            agent = AgentCls(
                unique_id=i,
                model=self,
                max_extraction=max_extraction,
                alpha=alpha,
                gamma=gamma,
                epsilon_0=epsilon_0,
                epsilon_min=epsilon_min,
                decay_rate=decay_rate,
                sustainability_penalty=sustainability_penalty,
                critical_fraction=critical_fraction,
                seed=(seed if seed is None else seed + i),
            )
            self.schedule.add(agent)
            x = self.random.randrange(self.river_column + 1, grid_width)
            y = self.random.randrange(grid_height)
            self.grid.place_agent(agent, (x, y))

        # Monitor agent: lives outside the schedule; placed on the river column
        # for visualization. unique_id chosen to avoid collisions with farmers.
        self.monitor = MonitorAgent(
            unique_id=n_farmers + 1000,
            model=self,
            p_detect=p_detect,
            fine_factor=fine_factor,
        )
        # Place visually at the top of the river column.
        self.grid.place_agent(self.monitor, (self.river_column, grid_height // 2))

        self.running = True
        self.step_count = 0

        # --- DataCollector ----------------------------------------------
        self.datacollector = DataCollector(
            model_reporters={
                "step": lambda m: m.step_count,
                "water_level": lambda m: m.water.level,
                "water_normalized": lambda m: m.water.normalized_level,
                "climate_factor": lambda m: m.current_climate_factor(),
                "total_extraction": lambda m: m.total_extraction_this_step,
                "mean_extraction": lambda m: m.mean_extraction_this_step,
                "cooperation_index": lambda m: m.cooperation_index,
                "gini_payoff": lambda m: gini_coefficient(
                    a.cumulative_payoff for a in m.schedule.agents
                ),
                "mean_payoff": lambda m: float(
                    np.mean([a.cumulative_payoff for a in m.schedule.agents])
                ),
                "mean_q_value": lambda m: float(
                    np.mean([a.q_learner.mean_q() for a in m.schedule.agents
                             if a.strategy_type == "q_learner"])
                ) if any(a.strategy_type == "q_learner" for a in m.schedule.agents) else 0.0,
                "n_detections_cumulative": lambda m: m.monitor.n_detections,
                "frac_action_cooperative": lambda m: (
                    sum(1 for a in m.schedule.agents if a.last_action_idx <= 2)
                    / max(1, len(m.schedule.agents))
                ),
                "frac_action_defect": lambda m: (
                    sum(1 for a in m.schedule.agents if a.last_action_idx >= 3)
                    / max(1, len(m.schedule.agents))
                ),
            },
            agent_reporters={
                "strategy": "strategy_type",
                "action": "last_action_idx",
                "extraction": "last_extraction",
                "reward": "last_reward",
                "cumulative_payoff": "cumulative_payoff",
                "fines_paid": "fines_paid",
            },
        )
        # Capture initial state (t=0 before first step)
        self.datacollector.collect(self)

    def current_climate_factor(self) -> float:
        return self.climate.climate_factor(self.step_count)

    # --- Three-stage step -------------------------------------------

    def step(self) -> None:
        # Stage 1: agents observe & act
        self.schedule.step()
        # Stage 1.5: monitor checks for over-extraction and fines offenders
        self.monitor.run()
        # Stage 2: resource regenerates
        self.water.regenerate(self.current_climate_factor())
        # Stage 3: agents finalize (reward + Q-update)
        for agent in self.schedule.agents:
            agent.finalize()

        self.step_count += 1
        self.datacollector.collect(self)

        if self.water.level <= 0.0 and self.step_count > 10:
            self.running = False

    # --- CSV export ------------------------------------------------

    def export_results(self, out_dir: str | None = None, tag: str = "") -> tuple[str, str]:
        """Dump model-level and agent-level DataFrames to CSV.

        Returns (model_csv_path, agent_csv_path). Filenames include a
        timestamp and an optional tag so multiple runs don't collide.
        """
        import os
        from datetime import datetime

        out_dir = out_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "results"
        )
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{tag}" if tag else ""

        model_df = self.datacollector.get_model_vars_dataframe()
        agent_df = self.datacollector.get_agent_vars_dataframe()

        model_path = os.path.join(out_dir, f"model_{stamp}{suffix}.csv")
        agent_path = os.path.join(out_dir, f"agents_{stamp}{suffix}.csv")
        model_df.to_csv(model_path, index_label="step")
        agent_df.to_csv(agent_path)
        return model_path, agent_path

    # --- Aggregates used by DataCollector / UI ---------------------

    @property
    def total_extraction_this_step(self) -> float:
        return sum(a.last_extraction for a in self.schedule.agents)

    @property
    def mean_extraction_this_step(self) -> float:
        if not self.schedule.agents:
            return 0.0
        return self.total_extraction_this_step / len(self.schedule.agents)

    @property
    def cooperation_index(self) -> float:
        """Combined health metric in [0, 1]: high water AND no over-extraction.

        cooperation_index = water_normalized * (1 - excess_extraction_fraction)

        - 1.0 means water is at carrying capacity AND extraction is at or below
          sustainable yield (the cooperative ideal).
        - 0.0 means either the resource is depleted OR agents are extracting
          far beyond sustainable yield.

        This metric was previously water-level-blind: a "stuck at 5 units"
        equilibrium (everyone effectively unable to extract) scored 1.0,
        masking collapse. The combined form correctly separates collapse
        from sustained cooperation.
        """
        if self.sustainable_yield <= 0:
            return 0.0
        excess_frac = max(
            0.0,
            (self.total_extraction_this_step - self.sustainable_yield)
            / self.sustainable_yield,
        )
        excess_frac = min(1.0, excess_frac)
        return self.water.normalized_level * (1.0 - excess_frac)
