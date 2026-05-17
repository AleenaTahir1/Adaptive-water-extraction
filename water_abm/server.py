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

from .agents import IrrigatorAgent, MonitorAgent, RiverCellAgent
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


def water_to_color(normalized_level: float) -> str:
    """Map water level (0..1) to a river color.

    High water: deep blue. Mid: medium blue. Low: pale blue.
    Collapsed (~0): brown/dry-bed color to visually signal disaster.
    """
    if normalized_level <= 0.02:
        return "#7a5230"  # dry brown bed
    if normalized_level < 0.15:
        return "#c9d9e8"  # pale blue, near-empty
    if normalized_level < 0.35:
        return "#7fb3d5"  # light blue
    if normalized_level < 0.65:
        return "#2980b9"  # mid blue
    return "#1b4f72"      # deep blue, full


def agent_portrayal(agent):
    """Tell Mesa how to draw each agent (and each river/land patch)."""
    # --- River cells: color reflects current water level ----------------
    if isinstance(agent, RiverCellAgent):
        return {
            "Shape": "rect",
            "Filled": "true",
            "Color": water_to_color(agent.model.water.normalized_level),
            "Layer": 0,
            "w": 1.0,
            "h": 1.0,
        }

    # --- Monitor: black star ---------------------------------------------
    if isinstance(agent, MonitorAgent):
        return {
            "Shape": "rect",
            "Filled": "true",
            "Color": "#000000",
            "Layer": 2,
            "w": 0.9,
            "h": 0.9,
            "text": "M",
            "text_color": "yellow",
        }

    # --- Irrigators: color = action level, size scales with extraction ---
    if isinstance(agent, IrrigatorAgent):
        color = ACTION_COLORS[agent.last_action_idx]
        shape = STRATEGY_SHAPES.get(agent.strategy_type, "circle")
        # Radius grows with action level so over-extractors look BIG and red,
        # cooperators stay small and blue. Much easier to read at a glance.
        radius = 0.35 + 0.25 * (agent.last_action_idx / 4.0)
        portrayal = {
            "Shape": shape,
            "Filled": "true",
            "Color": color,
            "Layer": 1,
        }
        if shape == "circle":
            portrayal["r"] = radius
        else:
            portrayal["w"] = radius * 1.2
            portrayal["h"] = radius * 1.2
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
    """Big visual status banner: water bar + climate state + verdict."""

    def render(self, model):
        water_pct = model.water.normalized_level * 100
        cf = model.current_climate_factor()
        coop = model.cooperation_index
        det = model.monitor.n_detections

        # Color the water bar by health.
        if water_pct >= 60:
            bar_color = "#1b4f72"; verdict = "HEALTHY"
        elif water_pct >= 30:
            bar_color = "#2980b9"; verdict = "STRESSED"
        elif water_pct >= 10:
            bar_color = "#e67e22"; verdict = "DEPLETING"
        else:
            bar_color = "#c0392b"; verdict = "COLLAPSED"

        # Climate label.
        if cf >= 0.9:
            climate_state = "NORMAL"
            climate_color = "#27ae60"
        elif cf >= 0.6:
            climate_state = "MILD STRESS"
            climate_color = "#f39c12"
        else:
            climate_state = "DROUGHT"
            climate_color = "#c0392b"

        bar_pct = max(2.0, water_pct)
        scenario_name = type(model.climate).__name__.replace("Climate", "").replace("Decline", " decline")
        return f"""
<div style="font-family: -apple-system, sans-serif; padding: 12px; background: #f7f9fa; border-radius: 8px; margin: 8px 0;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
    <div style="font-size: 16px;"><b>Step {model.step_count}</b> &nbsp;&middot;&nbsp; <span style="color: #555;">scenario: <b>{scenario_name}</b></span></div>
    <div style="font-size: 22px; font-weight: bold; color: {bar_color};">RIVER: {verdict}</div>
  </div>
  <div style="background: #ddd; border-radius: 6px; height: 28px; position: relative; overflow: hidden;">
    <div style="background: {bar_color}; height: 100%; width: {bar_pct}%; transition: width 0.3s;"></div>
    <div style="position: absolute; top: 0; left: 0; right: 0; height: 100%; line-height: 28px; text-align: center; color: white; font-weight: bold; text-shadow: 0 0 4px rgba(0,0,0,0.6);">
      {model.water.level:.0f} / {model.water.carrying_capacity:.0f} units ({water_pct:.1f}%)
    </div>
  </div>
  <div style="display: flex; justify-content: space-around; margin-top: 12px; font-size: 14px;">
    <div>Climate: <b style="color: {climate_color};">{climate_state}</b> (cf={cf:.2f})</div>
    <div>Mean extraction/step: <b>{model.mean_extraction_this_step:.2f}</b></div>
    <div>Cooperation index: <b>{coop:.2f}</b></div>
    <div>Cumulative detections: <b>{det}</b></div>
  </div>
</div>
"""


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
    # Status banner FIRST so the user sees the big water bar before the grid.
    return ModularServer(
        WaterCommonsModel,
        [status, grid_canvas, water_chart, cooperation_chart, inequality_chart],
        "Water Commons ABM with Q-Learning",
        model_params,
    )


if __name__ == "__main__":
    create_server().launch()
