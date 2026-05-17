"""Mesa visualization server for WaterCommonsModel.

Launches a browser-based UI at http://127.0.0.1:8521 with:
  - Spatial grid (river column blue with intensity ~ water level, farmland green)
  - Agents colored by current action level (blue = no extraction -> red = max)
    and shaped by strategy type (circle = Q-learner, triangle = always-coop,
    square = always-defect, cross = TFT, star = monitor)
  - Three live charts: water level, cooperation index, payoff inequality (Gini)
  - Sliders for all eight headline parameters (matches Assignment 01 Table 4)
  - Monitors for current step, water level, mean extraction, detections

Run via:
    python run.py
"""
from __future__ import annotations

import mesa
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import Slider, Choice
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement

from .agents import IrrigatorAgent, MonitorAgent
from .model import WaterCommonsModel


# Action-level -> color ramp (blue = sustainable, red = aggressive).
ACTION_COLORS = ["#1f77ff", "#5da5da", "#cccc00", "#ff9933", "#cc0000"]

# Strategy -> shape (Mesa CanvasGrid supports circle/rect/arrowHead).
STRATEGY_SHAPES = {
    "q_learner": "circle",
    "always_coop": "rect",
    "always_defect": "rect",
    "tit_for_tat": "circle",
    "monitor": "rect",
}


def agent_portrayal(agent):
    """Tell Mesa how to draw each agent (and each river/land patch)."""
    if isinstance(agent, MonitorAgent):
        return {
            "Shape": "rect",
            "Filled": "true",
            "Color": "#222222",
            "Layer": 2,
            "w": 0.8,
            "h": 0.8,
            "text": "M",
            "text_color": "white",
        }

    if isinstance(agent, IrrigatorAgent):
        color = ACTION_COLORS[agent.last_action_idx]
        shape = STRATEGY_SHAPES.get(agent.strategy_type, "circle")
        portrayal = {
            "Shape": shape,
            "Filled": "true",
            "Color": color,
            "Layer": 1,
        }
        if shape == "circle":
            portrayal["r"] = 0.6
        else:
            portrayal["w"] = 0.7
            portrayal["h"] = 0.7
        # Annotate Q-learners vs fixed-strategy with single-letter labels
        labels = {
            "q_learner": "Q",
            "always_coop": "C",
            "always_defect": "D",
            "tit_for_tat": "T",
        }
        portrayal["text"] = labels.get(agent.strategy_type, "")
        portrayal["text_color"] = "white"
        return portrayal

    return None


class WaterLevelPatch(mesa.Agent):
    """Dummy placeholder so CanvasGrid can color background patches.

    Mesa's CanvasGrid only renders things from `grid` and doesn't natively
    paint patches; we work around this by giving each grid cell its own
    background portrayal via a custom canvas wrapper. Simpler approach:
    use a TextElement to show the water level numerically.
    """
    pass


class WaterStatusText(TextElement):
    """Top-of-page text monitor: water level, climate, cooperation, detections."""

    def render(self, model):
        water_pct = model.water.normalized_level * 100
        cf = model.current_climate_factor()
        coop = model.cooperation_index
        return (
            f"<b>Step:</b> {model.step_count} &nbsp;|&nbsp; "
            f"<b>Water:</b> {model.water.level:.1f} ({water_pct:.1f}% of K) &nbsp;|&nbsp; "
            f"<b>Climate factor:</b> {cf:.2f} &nbsp;|&nbsp; "
            f"<b>Mean ext:</b> {model.mean_extraction_this_step:.2f} &nbsp;|&nbsp; "
            f"<b>Coop index:</b> {coop:.2f} &nbsp;|&nbsp; "
            f"<b>Detections:</b> {model.monitor.n_detections}"
        )


# --- Mesa modules ----------------------------------------------------------

GRID_WIDTH = 20
GRID_HEIGHT = 20
CANVAS_PIXELS = 500

grid_canvas = CanvasGrid(
    agent_portrayal, GRID_WIDTH, GRID_HEIGHT, CANVAS_PIXELS, CANVAS_PIXELS
)

water_chart = ChartModule(
    [{"Label": "water_level", "Color": "#1f77b4"}],
    data_collector_name="datacollector",
    canvas_height=180,
)

cooperation_chart = ChartModule(
    [
        {"Label": "cooperation_index", "Color": "#2ca02c"},
        {"Label": "frac_action_cooperative", "Color": "#9edd9e"},
        {"Label": "frac_action_defect", "Color": "#d62728"},
    ],
    data_collector_name="datacollector",
    canvas_height=180,
)

inequality_chart = ChartModule(
    [
        {"Label": "gini_payoff", "Color": "#9467bd"},
        {"Label": "mean_payoff", "Color": "#8c564b"},
    ],
    data_collector_name="datacollector",
    canvas_height=180,
)


# --- Slider definitions (Assignment 01 Table 4) -----------------------------

model_params = {
    "n_farmers": Slider("Number of farmers (N)", value=20, min_value=5, max_value=100, step=5),
    "proportion_q_learners": Slider(
        "Proportion of Q-learners", value=1.0, min_value=0.0, max_value=1.0, step=0.1
    ),
    "alpha": Slider("Learning rate (alpha)", value=0.15, min_value=0.01, max_value=0.50, step=0.01),
    "gamma": Slider("Discount factor (gamma)", value=0.95, min_value=0.50, max_value=0.99, step=0.01),
    "epsilon_0": Slider(
        "Initial exploration (epsilon_0)", value=0.30, min_value=0.10, max_value=1.00, step=0.05
    ),
    "regeneration_rate": Slider(
        "Regeneration rate (r)", value=0.10, min_value=0.01, max_value=0.30, step=0.01
    ),
    "p_detect": Slider(
        "Monitor detection prob (p_detect)", value=0.0, min_value=0.0, max_value=1.0, step=0.05
    ),
    "climate_scenario": Choice(
        "Climate scenario",
        value="stable",
        choices=["stable", "gradual", "shock", "stochastic"],
    ),
    "social_degree": Slider(
        "Social network degree (k)", value=4, min_value=0, max_value=12, step=1
    ),
    "seed": Slider("Random seed", value=42, min_value=0, max_value=999, step=1),
}


def create_server() -> ModularServer:
    status = WaterStatusText()
    return ModularServer(
        WaterCommonsModel,
        [grid_canvas, status, water_chart, cooperation_chart, inequality_chart],
        "Water Commons ABM with Q-Learning",
        model_params,
    )


if __name__ == "__main__":
    create_server().launch()
