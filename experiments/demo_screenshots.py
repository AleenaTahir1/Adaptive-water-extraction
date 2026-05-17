"""Produce 'before/after' screenshots for the report:

  fig08_grid_pre_shock.png    -- grid state at step 199 (just before shock)
  fig09_grid_during_shock.png -- grid state at step 250 (mid-shock)
  fig10_grid_recovery.png     -- grid state at step 450 (post-shock, recovered)

These satisfy the assignment's 'before/after screenshots of the emergent
state' requirement (section 4.4).

Run as:
    python -m experiments.demo_screenshots
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from water_abm.agents import IrrigatorAgent, MonitorAgent, ACTION_LEVELS
from water_abm.model import WaterCommonsModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

ACTION_COLORS = ["#1f77ff", "#5da5da", "#cccc00", "#ff9933", "#cc0000"]


def render_grid(m: WaterCommonsModel, title: str, out_path: Path):
    """Render a static snapshot of the grid: river column shaded by water
    level, farmers colored by action level, monitor as a black square."""
    fig, ax = plt.subplots(figsize=(7, 7))
    W, H = m.grid.width, m.grid.height

    # River column shading
    water_intensity = m.water.normalized_level
    river_color = (0.2, 0.4, 1.0, max(0.15, water_intensity))
    for y in range(H):
        ax.add_patch(plt.Rectangle((m.river_column - 0.5, y - 0.5), 1, 1, color=river_color))

    # Farmland (light green)
    for x in range(m.river_column + 1, W):
        for y in range(H):
            ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, color="#eaf5e0"))

    # Agents
    for agent in m.schedule.agents:
        x, y = agent.pos
        color = ACTION_COLORS[agent.last_action_idx]
        marker = {"q_learner": "o", "always_coop": "s", "always_defect": "s",
                  "tit_for_tat": "D"}.get(agent.strategy_type, "o")
        ax.scatter(x, y, c=color, s=200, marker=marker, edgecolors="black", linewidths=0.5,
                   zorder=2)
    # Monitor
    mx, my = m.monitor.pos
    ax.scatter(mx, my, c="black", s=300, marker="*", zorder=3)

    # Legend
    handles = [
        plt.scatter([], [], c=ACTION_COLORS[0], s=120, marker="o", label="action 0 (none)"),
        plt.scatter([], [], c=ACTION_COLORS[2], s=120, marker="o", label="action 2 (coop fair-share)"),
        plt.scatter([], [], c=ACTION_COLORS[4], s=120, marker="o", label="action 4 (max defect)"),
        plt.scatter([], [], c="black", s=120, marker="*", label="monitor"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8)
    ax.set_xlim(-0.6, W - 0.4); ax.set_ylim(-0.6, H - 0.4)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(
        f"{title}\nstep={m.step_count}  water={m.water.level:.1f}  "
        f"cf={m.current_climate_factor():.2f}  coop_idx={m.cooperation_index:.2f}",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main():
    m = WaterCommonsModel(
        n_farmers=20,
        proportion_q_learners=1.0,
        climate_scenario="shock",
        p_detect=0.3,
        seed=42,
    )

    # Run to step 199 (just before shock, cooperation established)
    for _ in range(199):
        m.step()
    render_grid(m, "Pre-shock: cooperation established", FIG_DIR / "fig08_grid_pre_shock.png")

    # Run to step 260 (mid-shock)
    for _ in range(61):
        m.step()
    render_grid(m, "Mid-shock: drought pressure", FIG_DIR / "fig09_grid_during_shock.png")

    # Run to step 450 (post-shock recovery)
    for _ in range(190):
        m.step()
    render_grid(m, "Post-shock: recovered equilibrium", FIG_DIR / "fig10_grid_recovery.png")

    print("Wrote fig08-fig10 grid screenshots to figures/")


if __name__ == "__main__":
    main()
