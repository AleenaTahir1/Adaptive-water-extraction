"""Minimal Mesa compatibility shim for Pyodide.

Pyodide can't easily install the full mesa package (with tornado/solara/etc.),
so we provide just the small subset of mesa's API that water_abm/ uses.
This file is loaded BEFORE water_abm so that `import mesa` resolves to this
shim instead of failing.

What we implement:
  mesa.Agent                       (base agent class)
  mesa.Model                       (base model class with `random`)
  mesa.time.RandomActivation       (scheduler)
  mesa.space.MultiGrid             (2D grid of agent lists)
  mesa.datacollection.DataCollector (state recorder)

This is intentionally small and faithful to mesa 2.3.x semantics for the
parts we use. It is NOT a general-purpose mesa replacement.
"""
import random
import sys
import types


# ---------- mesa.Agent / mesa.Model ----------------------------------------


class Agent:
    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.pos = None

    @property
    def random(self):
        return self.model.random


class Model:
    def __init__(self):
        self.random = random.Random()
        self.running = True

    def reset_randomizer(self, seed):
        self.random = random.Random(seed)
        try:
            import numpy as np
            np.random.seed(seed)
        except ImportError:
            pass


# ---------- mesa.time.RandomActivation -------------------------------------


class RandomActivation:
    """Calls .step() on every agent in randomised order each step."""

    def __init__(self, model):
        self.model = model
        self._agents = {}     # mesa 2.x stores agents by id internally
        self.steps = 0
        self.time = 0

    @property
    def agents(self):
        return list(self._agents.values())

    def add(self, agent):
        self._agents[agent.unique_id] = agent

    def remove(self, agent):
        self._agents.pop(agent.unique_id, None)

    def step(self):
        agent_list = list(self._agents.values())
        self.model.random.shuffle(agent_list)
        for a in agent_list:
            a.step()
        self.steps += 1
        self.time += 1

    def get_agent_count(self):
        return len(self._agents)


# ---------- mesa.space.MultiGrid -------------------------------------------


class MultiGrid:
    """2D grid where each cell can hold multiple agents. List-of-lists impl."""

    def __init__(self, width, height, torus=False):
        self.width = width
        self.height = height
        self.torus = torus
        # grid[x][y] is a list of agents at (x, y).
        self.grid = [[[] for _ in range(height)] for _ in range(width)]

    def place_agent(self, agent, pos):
        x, y = pos
        agent.pos = pos
        self.grid[x][y].append(agent)

    def remove_agent(self, agent):
        if agent.pos is None:
            return
        x, y = agent.pos
        if agent in self.grid[x][y]:
            self.grid[x][y].remove(agent)
        agent.pos = None

    def move_agent(self, agent, pos):
        self.remove_agent(agent)
        self.place_agent(agent, pos)

    def coord_iter(self):
        for x in range(self.width):
            for y in range(self.height):
                yield (self.grid[x][y], x, y)

    def iter_neighbors(self, pos, moore=True, include_center=False, radius=1):
        x, y = pos
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0 and not include_center:
                    continue
                if not moore and abs(dx) + abs(dy) > radius:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    for a in self.grid[nx][ny]:
                        yield a


# ---------- mesa.datacollection.DataCollector ------------------------------


class DataCollector:
    """Mesa-compatible data collector. Stores model-level and agent-level
    series in memory; .get_model_vars_dataframe() returns a list of dicts
    instead of pandas (Pyodide loads pandas separately if needed)."""

    def __init__(self, model_reporters=None, agent_reporters=None):
        self.model_reporters = model_reporters or {}
        self.agent_reporters = agent_reporters or {}
        self.model_vars = {k: [] for k in self.model_reporters}
        self.agent_vars = {k: [] for k in self.agent_reporters}

    def _eval(self, reporter, target):
        if callable(reporter):
            return reporter(target)
        if isinstance(reporter, str):
            return getattr(target, reporter, None)
        return reporter

    def collect(self, model):
        for k, rep in self.model_reporters.items():
            try:
                self.model_vars[k].append(self._eval(rep, model))
            except Exception:
                self.model_vars[k].append(None)
        for k, rep in self.agent_reporters.items():
            try:
                self.agent_vars[k].append(
                    [self._eval(rep, a) for a in model.schedule.agents]
                )
            except Exception:
                self.agent_vars[k].append([])

    def get_model_vars_dataframe(self):
        rows = []
        n = len(next(iter(self.model_vars.values()), []))
        for i in range(n):
            rows.append({k: self.model_vars[k][i] for k in self.model_reporters})
        return rows

    def get_agent_vars_dataframe(self):
        return self.agent_vars


# ---------- Install into sys.modules so `import mesa` works ----------------


def install():
    mesa_module = types.ModuleType("mesa")
    mesa_module.Agent = Agent
    mesa_module.Model = Model

    time_module = types.ModuleType("mesa.time")
    time_module.RandomActivation = RandomActivation
    mesa_module.time = time_module

    space_module = types.ModuleType("mesa.space")
    space_module.MultiGrid = MultiGrid
    mesa_module.space = space_module

    dc_module = types.ModuleType("mesa.datacollection")
    dc_module.DataCollector = DataCollector
    mesa_module.datacollection = dc_module

    sys.modules["mesa"] = mesa_module
    sys.modules["mesa.time"] = time_module
    sys.modules["mesa.space"] = space_module
    sys.modules["mesa.datacollection"] = dc_module


install()
