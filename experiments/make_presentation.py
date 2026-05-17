"""Modern minimalist presentation PDF.

Design system v2:
  - Pure white background
  - Multi-color palette: indigo (primary) + coral + teal + amber accents
  - Section-color chips so each topic has a visual identity
  - Decorative shapes: filled half-circles and dot constellations
  - No footer, no per-slide page number text
  - Serif headings (Times) + sans body (Helvetica)
  - Tightly aligned layouts; images anchored at the TOP, never the bottom

Slide order:
  1. Title only (topic only)
  2. Group members
  3. Contents
  4-17. Content
  18. Thank you

Run:
    python -m experiments.make_presentation
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus.tables import Table, TableStyle
from reportlab.lib import utils as rl_utils


# Page size: 16:9 widescreen.
W, H = 13.333 * inch, 7.5 * inch

# ---------------------------------------------------------------------------
# Color palette: modern multi-color on white
# ---------------------------------------------------------------------------

BG       = HexColor("#FFFFFF")
INK      = HexColor("#111827")  # near-black for body text
MUTED    = HexColor("#6B7280")  # warm gray
HAIRLINE = HexColor("#E5E7EB")  # very light gray rule

# Primary brand color (used on most headings, footer line, etc.)
INDIGO       = HexColor("#1E1B4B")
INDIGO_SOFT  = HexColor("#6366F1")

# Accent palette (each section gets one).
CORAL  = HexColor("#EF4444")  # warm red-orange
TEAL   = HexColor("#0D9488")  # rich teal
AMBER  = HexColor("#F59E0B")  # warm yellow-orange
EMERALD = HexColor("#10B981")  # cooperation green
PURPLE = HexColor("#7C3AED")  # vivid purple for math/RQ

# Light tints (5-10% saturation) used for card backgrounds.
TINT_CORAL  = HexColor("#FEF2F2")
TINT_TEAL   = HexColor("#F0FDFA")
TINT_AMBER  = HexColor("#FFFBEB")
TINT_INDIGO = HexColor("#EEF2FF")
TINT_PURPLE = HexColor("#F5F3FF")
TINT_EMERALD = HexColor("#ECFDF5")

# Fonts.
F_SERIF      = "Times-Roman"
F_SERIF_BOLD = "Times-Bold"
F_SERIF_ITAL = "Times-Italic"
F_SANS       = "Helvetica"
F_SANS_BOLD  = "Helvetica-Bold"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "figures"
OUT_PATH = PROJECT_ROOT / "report" / "presentation.pdf"


# ---------------------------------------------------------------------------
# Decorative chrome
# ---------------------------------------------------------------------------


def draw_dot_cluster(c: Canvas, cx: float, cy: float, color, n: int = 6,
                     radius: float = 0.04 * inch, spread: float = 0.4 * inch,
                     seed: int = 0):
    """Scatter `n` dots around (cx, cy) deterministically."""
    rng = random.Random(seed)
    c.setFillColor(color)
    for _ in range(n):
        angle = rng.uniform(0, math.tau)
        dist  = rng.uniform(0.15, 1.0) * spread
        rr    = radius * rng.uniform(0.7, 1.3)
        c.circle(cx + math.cos(angle) * dist,
                 cy + math.sin(angle) * dist, rr, fill=1, stroke=0)


def draw_corner_circle(c: Canvas, cx: float, cy: float, r: float, color):
    """Filled disc, used as a corner accent."""
    c.setFillColor(color)
    c.circle(cx, cy, r, fill=1, stroke=0)


def draw_background(c: Canvas, accent=INDIGO, big: bool = False):
    """White background with a colored corner accent and dot constellation."""
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Top thin colored stripe (4 pt) -- visual identity per section.
    c.setFillColor(accent)
    c.rect(0, H - 0.06 * inch, W, 0.06 * inch, fill=1, stroke=0)

    # Upper-right corner half-circle (subtle).
    radius = (2.0 if big else 1.2) * inch
    c.saveState()
    c.setFillColor(accent)
    # Approximate alpha by mixing the accent toward white.
    r, g, b = accent.rgb()
    alpha = 0.15 if big else 0.10
    mixed_r = r + (1 - r) * (1 - alpha)
    mixed_g = g + (1 - g) * (1 - alpha)
    mixed_b = b + (1 - b) * (1 - alpha)
    c.setFillColorRGB(mixed_r, mixed_g, mixed_b)
    c.circle(W, H, radius, fill=1, stroke=0)
    c.restoreState()

    # Sparse dot constellation in the upper-right zone.
    draw_dot_cluster(c, W - 1.2 * inch, H - 1.6 * inch, accent,
                     n=5, radius=0.05 * inch, spread=0.6 * inch, seed=1)
    # A small accent dot on the lower-left for visual balance.
    c.setFillColor(accent)
    c.circle(0.35 * inch, 0.45 * inch, 0.07 * inch, fill=1, stroke=0)


def draw_section_chip(c: Canvas, label: str, x: float, y: float, color):
    """Small all-caps chip with a colored bar before a slide title."""
    c.setStrokeColor(color)
    c.setLineWidth(2.5)
    c.line(x, y + 0.04 * inch, x + 0.30 * inch, y + 0.04 * inch)
    c.setFillColor(color)
    c.setFont(F_SANS_BOLD, 10)
    c.drawString(x + 0.42 * inch, y, label.upper())


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def wrap_text(c: Canvas, text: str, max_w: float, font: str, size: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if c.stringWidth(trial, font, size) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def draw_bullet_list(c: Canvas, items: list[str], x: float, y_top: float,
                     max_w: float, size: int = 14, gap: float = 0.32 * inch,
                     marker_color=CORAL) -> float:
    """Bullet list with section-colored markers."""
    y = y_top
    for it in items:
        c.setFillColor(marker_color)
        c.circle(x + 0.05 * inch, y + 0.07 * inch, 3.5, fill=1, stroke=0)
        wrapped = wrap_text(c, it, max_w - 0.35 * inch, F_SANS, size)
        c.setFillColor(INK)
        c.setFont(F_SANS, size)
        leading = size * 1.42
        for i, line in enumerate(wrapped):
            c.drawString(x + 0.32 * inch, y - i * leading, line)
        y -= gap + (len(wrapped) - 1) * leading
    return y


def draw_styled_table(c: Canvas, data: list[list[str]], x: float, y_top: float,
                      col_widths: list[float], header_color=INDIGO,
                      alt_tint=TINT_INDIGO):
    """Modern table: header in section color, alternating tinted rows."""
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), F_SANS_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTNAME", (0, 1), (-1, -1), F_SANS),
        ("FONTSIZE", (0, 1), (-1, -1), 10.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, header_color),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, HAIRLINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG, alt_tint]),
    ])
    t = Table(data, colWidths=col_widths)
    t.setStyle(style)
    _, h = t.wrap(sum(col_widths), 0)
    t.drawOn(c, x, y_top - h)
    return y_top - h


def draw_image_top(c: Canvas, path: Path, x: float, y_top: float,
                   max_w: float, max_h: float):
    """Draw image with its TOP anchored to y_top. Centered horizontally
    in [x, x+max_w]. Returns (rendered_w, rendered_h, y_bottom)."""
    if not path.exists():
        return 0, 0, y_top
    img = rl_utils.ImageReader(str(path))
    iw, ih = img.getSize()
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    x_centered = x + (max_w - w) / 2
    y_bottom = y_top - h
    c.drawImage(img, x_centered, y_bottom, width=w, height=h, mask="auto")
    return w, h, y_bottom


def draw_slide_head(c: Canvas, title: str, chip_label: str, color):
    """Standard slide head: section chip + title (no subtitle by default)."""
    chip_y = H - 0.95 * inch
    draw_section_chip(c, chip_label, 0.7 * inch, chip_y, color)
    c.setFillColor(INDIGO)
    c.setFont(F_SERIF_BOLD, 30)
    c.drawString(0.7 * inch, chip_y - 0.5 * inch, title)


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------


def slide_01_title(c: Canvas, idx: int, total: int):
    """Title only.  No tagline, no university, no author, no footer."""
    draw_background(c, accent=CORAL, big=True)

    # Decorative: big coral disc anchored just off the upper-right corner.
    # (draw_background already draws a soft tinted disc; add a small accent.)
    c.setFillColor(AMBER)
    c.circle(W - 1.4 * inch, H - 2.5 * inch, 0.12 * inch, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.circle(W - 2.2 * inch, H - 1.3 * inch, 0.10 * inch, fill=1, stroke=0)
    c.setFillColor(PURPLE)
    c.circle(W - 0.9 * inch, H - 3.1 * inch, 0.08 * inch, fill=1, stroke=0)

    # Lower-left accent shape: coral half-circle.
    c.setFillColor(TINT_CORAL)
    c.circle(0.0, 0.0, 1.6 * inch, fill=1, stroke=0)
    c.setFillColor(CORAL)
    c.circle(0.0, 0.0, 0.4 * inch, fill=1, stroke=0)

    # "01" chip + rule.
    tx = 1.2 * inch
    ty_top = H / 2 + 1.8 * inch
    c.setFillColor(CORAL)
    c.setFont(F_SANS_BOLD, 13)
    c.drawString(tx, ty_top, "TOPIC")
    c.setStrokeColor(CORAL)
    c.setLineWidth(2)
    c.line(tx + 0.65 * inch, ty_top + 0.06 * inch,
           tx + 1.40 * inch, ty_top + 0.06 * inch)

    # Topic name (two lines, left aligned).
    c.setFillColor(INDIGO)
    c.setFont(F_SERIF_BOLD, 64)
    c.drawString(tx, ty_top - 1.0 * inch, "Adaptive Water")
    c.drawString(tx, ty_top - 1.9 * inch, "Extraction")
    # Italic clarifier.
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 26)
    c.drawString(tx, ty_top - 2.55 * inch, "with Q Learning under Climate Stress")


def slide_02_team(c: Canvas, idx: int, total: int):
    """Group members.  No subtitle, no footer."""
    draw_background(c, accent=TEAL)
    draw_section_chip(c, "team", 0.7 * inch, H - 0.95 * inch, TEAL)
    c.setFillColor(INDIGO)
    c.setFont(F_SERIF_BOLD, 44)
    c.drawString(0.7 * inch, H - 1.6 * inch, "Group Members")

    members = [
        ("Saqlain Abbas", CORAL),
        ("Aleena Tahir",  TEAL),
        ("Aena Habib",    AMBER),
        ("Eman Asghar",   PURPLE),
        ("Dua Kamal",     EMERALD),
    ]
    # Single column, centered card.
    card_x, card_y = 1.5 * inch, 0.8 * inch
    card_w, card_h = W - 3.0 * inch, 4.6 * inch
    c.setFillColor(TINT_TEAL)
    c.roundRect(card_x, card_y, card_w, card_h, 16, fill=1, stroke=0)

    cx = card_x + 1.5 * inch
    row_h = card_h / (len(members) + 0.6)
    for i, (name, color) in enumerate(members):
        row_y = card_y + card_h - row_h * (i + 0.85)
        # Colored circle with serial.
        c.setFillColor(color)
        c.circle(cx, row_y + 0.05 * inch, 0.26 * inch, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont(F_SERIF_BOLD, 14)
        c.drawCentredString(cx, row_y - 0.03 * inch, f"0{i + 1}")
        # Name.
        c.setFillColor(INDIGO)
        c.setFont(F_SERIF, 24)
        c.drawString(cx + 0.65 * inch, row_y - 0.05 * inch, name)


def slide_03_contents(c: Canvas, idx: int, total: int):
    """Table of contents.  No subtitle, no footer."""
    draw_background(c, accent=AMBER)
    draw_section_chip(c, "agenda", 0.7 * inch, H - 0.95 * inch, AMBER)
    c.setFillColor(INDIGO)
    c.setFont(F_SERIF_BOLD, 44)
    c.drawString(0.7 * inch, H - 1.6 * inch, "Contents")

    sections = [
        ("01", "The Problem and the Research Question", CORAL),
        ("02", "How the Model Works",                   INDIGO_SOFT),
        ("03", "Climate Scenarios and Experimental Design", TEAL),
        ("04", "Result 1.   Tragedy Baseline",          AMBER),
        ("05", "Result 2.   Enforcement Saves the Stable Climate", EMERALD),
        ("06", "Result 3.   Why Enforcement Fails Under Stress",  CORAL),
        ("07", "Primary RQ.   Effect of Discount Factor", PURPLE),
        ("08", "Sensitivity and Validation",            TEAL),
        ("09", "Conclusions and Future Work",           INDIGO_SOFT),
    ]
    x_left = 0.9 * inch
    y = H - 2.4 * inch
    row_h = 0.46 * inch
    for num, title, color in sections:
        # Colored serial.
        c.setFillColor(color)
        c.setFont(F_SERIF_BOLD, 22)
        c.drawString(x_left, y, num)
        # Hairline rule.
        c.setStrokeColor(HAIRLINE)
        c.setLineWidth(0.6)
        c.setDash(1, 4)
        c.line(x_left + 0.7 * inch, y + 0.05 * inch,
               W - 1.6 * inch, y + 0.05 * inch)
        c.setDash()
        # Section title.
        c.setFillColor(INDIGO)
        c.setFont(F_SERIF, 16)
        c.drawString(x_left + 0.85 * inch, y, title)
        y -= row_h


def slide_04_problem(c: Canvas, idx: int, total: int):
    draw_background(c, accent=CORAL)
    draw_slide_head(c, "The Problem", "01 . context", CORAL)
    bullets = [
        "Twenty farmers share one river.  Each season every farmer decides how much water to extract.",
        "If everyone extracts heavily the resource collapses and everyone loses.  Hardin (1968) called this the Tragedy of the Commons.",
        "Pakistan's Indus Basin sustains over 90 percent of national agriculture and is one of the world's most water stressed basins.",
        "By 2030 nearly half the global population will live in regions of high water stress (UN World Water Development Report).",
        "Real farmers learn, observe neighbors, and adapt.  Existing agent based models do not capture this learning.",
    ]
    draw_bullet_list(c, bullets, 0.8 * inch, H - 2.4 * inch,
                     max_w=W - 1.6 * inch, size=15, gap=0.42 * inch,
                     marker_color=CORAL)


def slide_05_research_question(c: Canvas, idx: int, total: int):
    draw_background(c, accent=PURPLE)
    draw_slide_head(c, "Research Question", "01 . focus", PURPLE)

    # Primary question card.
    card_x = 0.8 * inch
    card_y = H - 4.3 * inch
    card_w = W - 1.6 * inch
    card_h = 1.9 * inch
    c.setFillColor(TINT_PURPLE)
    c.roundRect(card_x, card_y, card_w, card_h, 16, fill=1, stroke=0)
    # Left vertical bar in the section color.
    c.setFillColor(PURPLE)
    c.rect(card_x, card_y, 0.10 * inch, card_h, fill=1, stroke=0)

    c.setFillColor(PURPLE)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(card_x + 0.45 * inch, card_y + card_h - 0.4 * inch, "PRIMARY QUESTION")
    c.setFillColor(INK)
    c.setFont(F_SERIF_ITAL, 18)
    wrap = wrap_text(c,
        "How does the discount factor gamma in Q learning agents affect the emergence of "
        "sustainable water extraction strategies under varying climate stress scenarios?",
        card_w - 0.9 * inch, F_SERIF_ITAL, 18)
    for i, line in enumerate(wrap):
        c.drawString(card_x + 0.45 * inch,
                     card_y + card_h - 0.85 * inch - i * 0.36 * inch, line)

    # Sub questions
    c.setFillColor(PURPLE)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.8 * inch, H - 4.7 * inch, "SUB QUESTIONS")
    subs = [
        "Can Q learning agents discover cooperative strategies without external enforcement?",
        "How do learned strategies break down under sudden drought shocks, and how fast do agents re adapt?",
        "At what monitoring intensity does enforcement become unnecessary?",
    ]
    draw_bullet_list(c, subs, 0.8 * inch, H - 5.1 * inch,
                     max_w=W - 1.6 * inch, size=13, gap=0.36 * inch,
                     marker_color=PURPLE)


def slide_06_model(c: Canvas, idx: int, total: int):
    draw_background(c, accent=INDIGO_SOFT)
    draw_slide_head(c, "How the Model Works", "02 . model", INDIGO_SOFT)
    bullets = [
        "Each irrigator chooses one of five extraction levels (0, 25, 50, 75, 100 percent of max).",
        "Observed state.  Water level bin, own previous action, neighbors average action, climate stress flag.",
        "Reward equals log utility of water extracted minus a sustainability penalty minus any fine.",
        "Shared resource follows logistic regeneration with a baseline inflow modulated by climate factor.",
        "Monitor agent catches over extractors with probability p detect and issues a fine.",
        "Social network is a random k regular graph.  Each farmer observes k neighbors.",
        "Implemented in Python 3.12 with Mesa 2.3.4.  About 700 lines of clear code.",
    ]
    draw_bullet_list(c, bullets, 0.8 * inch, H - 2.4 * inch,
                     max_w=W - 1.6 * inch, size=14, gap=0.36 * inch,
                     marker_color=INDIGO_SOFT)


def slide_07_q_learning(c: Canvas, idx: int, total: int):
    """The Q-learning formula.  Smaller font + safer margins so it never clips."""
    draw_background(c, accent=PURPLE)
    draw_slide_head(c, "The Q Learning Update Rule", "02 . math", PURPLE)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 13)
    c.drawString(0.7 * inch, H - 1.95 * inch,
                 "Watkins and Dayan, 1992.  Tabular and interpretable.")

    # Formula card -- wider, with smaller, safely contained text.
    card_x = 0.6 * inch
    card_y = H - 4.4 * inch
    card_w = W - 1.2 * inch
    card_h = 1.9 * inch
    c.setFillColor(TINT_PURPLE)
    c.roundRect(card_x, card_y, card_w, card_h, 14, fill=1, stroke=0)
    # Left bar.
    c.setFillColor(PURPLE)
    c.rect(card_x, card_y, 0.10 * inch, card_h, fill=1, stroke=0)

    # The formula -- spelled out in plain ASCII, font size auto-fit.
    formula = "Q(s, a)   =   Q(s, a)   +   alpha   [   r   +   gamma . max Q(s', a')   minus   Q(s, a)   ]"
    # Choose the largest size that fits comfortably in the card.
    target_w = card_w - 0.8 * inch
    for size in (28, 26, 24, 22, 20, 18, 16):
        if c.stringWidth(formula, F_SERIF_BOLD, size) <= target_w:
            break
    c.setFillColor(INDIGO)
    c.setFont(F_SERIF_BOLD, size)
    c.drawCentredString(card_x + card_w / 2,
                        card_y + card_h / 2 + 0.15 * inch, formula)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 12)
    c.drawCentredString(card_x + card_w / 2, card_y + 0.35 * inch,
                        "alpha is the learning rate.   gamma is the discount factor.   "
                        "s' is the post regen state.")

    notes = [
        "Exploration uses epsilon greedy with exponential decay.  Epsilon starts at 0.30, decays at rate 0.010.",
        "State space is small.  About 150 unique state action pairs.  Fits comfortably in a tabular Q table.",
        "Action 2 equals each agent's fair share of total sustainable yield.  Auto scaled with N.",
        "Heterogeneity.  Each agent has its own RNG and its own initial Q table noise.",
    ]
    draw_bullet_list(c, notes, 0.7 * inch, H - 5.0 * inch,
                     max_w=W - 1.4 * inch, size=12, gap=0.28 * inch,
                     marker_color=PURPLE)


def slide_08_climate(c: Canvas, idx: int, total: int):
    draw_background(c, accent=TEAL)
    draw_slide_head(c, "Climate Scenarios", "03 . scenarios", TEAL)
    data = [
        ["Scenario", "Climate factor profile"],
        ["Stable",     "c_f = 1.0 forever.  Baseline.  No climate change."],
        ["Gradual",    "c_f declines linearly from 1.0 to 0.5 over 400 steps."],
        ["Shock",      "c_f = 1.0 normally.  Drops to 0.3 between steps 200 and 300."],
        ["Stochastic", "c_f is gaussian noise around 0.85, clipped to between 0.3 and 1.0."],
    ]
    draw_styled_table(c, data, 0.7 * inch, H - 2.4 * inch,
                      col_widths=[2.5 * inch, W - 4.0 * inch],
                      header_color=TEAL, alt_tint=TINT_TEAL)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 13)
    c.drawString(0.7 * inch, 1.4 * inch,
                 "c_f multiplies BOTH the logistic regeneration term AND the baseline inflow.")
    c.drawString(0.7 * inch, 1.10 * inch,
                 "Lower c_f means less water replenished each season.")


def slide_09_experiments(c: Canvas, idx: int, total: int):
    draw_background(c, accent=AMBER)
    draw_slide_head(c, "Experimental Design", "03 . experiments", AMBER)
    data = [
        ["Experiment", "Variables", "Runs"],
        ["A.  Tragedy baseline", "4 climates  x  30 seeds.  No monitor.", "120"],
        ["B.  With enforcement", "4 climates  x  30 seeds.  p detect = 0.3", "120"],
        ["C.  Gamma sweep",      "stable and shock  x  5 gamma values  x  10 seeds", "100"],
    ]
    draw_styled_table(c, data, 0.7 * inch, H - 2.4 * inch,
                      col_widths=[3.6 * inch, 6.6 * inch, 1.5 * inch],
                      header_color=AMBER, alt_tint=TINT_AMBER)
    extras = [
        "Each run is 500 simulation steps.  About 125 seasons if one step is one quarter year.",
        "Sensitivity analysis varies alpha, gamma, epsilon, regeneration rate, p detect, N by plus or minus 20 percent.",
        "Validation.  Three sanity checks against Hardin 1968, Perolat 2017, and Indus Basin 2022.",
    ]
    draw_bullet_list(c, extras, 0.7 * inch, 3.2 * inch,
                     max_w=W - 1.4 * inch, size=13, gap=0.32 * inch,
                     marker_color=AMBER)


def slide_with_fig(c: Canvas, idx: int, total: int,
                   chip: str, title: str, fig: str,
                   takeaways: list[str], color, tint):
    """Figure on left, takeaways on right.  Image anchored at TOP so there is
    no awkward gap between title and chart."""
    draw_background(c, accent=color)
    draw_slide_head(c, title, chip, color)

    # Figure region: anchored from the top, leaves a small margin below.
    img_y_top = H - 2.0 * inch
    img_max_h = H - 2.4 * inch    # leaves ~0.5 inch above the bottom edge
    img_max_w = 7.4 * inch
    draw_image_top(c, FIG_DIR / fig, x=0.5 * inch, y_top=img_y_top,
                   max_w=img_max_w, max_h=img_max_h)

    # Right column: takeaway card.
    rx = 8.4 * inch
    rw = W - rx - 0.6 * inch
    card_top = img_y_top + 0.2 * inch
    card_h = img_max_h
    c.setFillColor(tint)
    c.roundRect(rx, card_top - card_h, rw, card_h, 14, fill=1, stroke=0)
    c.setFillColor(color)
    c.rect(rx, card_top - card_h, 0.08 * inch, card_h, fill=1, stroke=0)

    # Card heading + body.
    c.setFillColor(color)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(rx + 0.3 * inch, card_top - 0.4 * inch, "WHAT IT MEANS")
    draw_bullet_list(c, takeaways, rx + 0.3 * inch,
                     card_top - 0.8 * inch,
                     max_w=rw - 0.5 * inch, size=12, gap=0.30 * inch,
                     marker_color=color)


def slide_enforcement_fails(c: Canvas, idx: int, total: int):
    """Headline negative result.  Dedicated emphasis layout."""
    draw_background(c, accent=CORAL)
    draw_slide_head(c, "Why Enforcement Fails Under Stress",
                    "06 . key finding", CORAL)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 13)
    c.drawString(0.7 * inch, H - 2.0 * inch,
                 "The fixed quota policy breaks when climate changes.")

    # Red callout strip.
    c.setFillColor(CORAL)
    c.roundRect(0.7 * inch, H - 2.8 * inch, W - 1.4 * inch, 0.55 * inch, 8, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(F_SERIF_BOLD, 19)
    c.drawString(0.95 * inch, H - 2.65 * inch,
                 "Even p detect = 0.9 cannot save the drought shock scenario.")

    # Evidence table.
    data = [
        ["p detect", "stable.  final water", "shock.  final water"],
        ["0.3", "700", "5.6  (collapsed)"],
        ["0.6", "777", "5.6  (collapsed)"],
        ["0.9", "787", "5.6  (collapsed)"],
    ]
    draw_styled_table(c, data, 0.7 * inch, H - 3.0 * inch,
                      col_widths=[2.2 * inch, 4.5 * inch, 5.0 * inch],
                      header_color=CORAL, alt_tint=TINT_CORAL)

    # Why it happens.
    c.setFillColor(CORAL)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.7 * inch, H - 5.6 * inch, "WHY IT HAPPENS  (structural, not a tuning issue)")
    reasons = [
        "Agents' five action grid is calibrated to baseline climate where c f = 1.0",
        "When c f drops to 0.3 during the shock, even the cooperative fair share action is over extraction.",
        "Sixty eight percent of agents are STILL choosing cooperative actions during failure.  Not selfish.",
        "Implication.  Real regulators need adaptive (climate aware) quotas.  Fixed quotas are not enough.",
    ]
    draw_bullet_list(c, reasons, 0.7 * inch, H - 5.95 * inch,
                     max_w=W - 1.4 * inch, size=12, gap=0.26 * inch,
                     marker_color=CORAL)


def slide_validation(c: Canvas, idx: int, total: int):
    draw_background(c, accent=EMERALD)
    draw_slide_head(c, "Validation Against Literature", "08 . validation", EMERALD)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 13)
    c.drawString(0.7 * inch, H - 2.0 * inch,
                 "Three sanity checks.  All three pass.")
    data = [
        ["#", "Source", "Test", "Result"],
        ["1", "Hardin 1968",
         "No enforcement should collapse the resource.  With enforcement under stable climate it should sustain.",
         "PASS    5.6 vs 504"],
        ["2", "Perolat et al 2017",
         "Scarcity should drive aggression.  Compare frac defect during steps 200 to 300 under stable vs shock with enforcement.",
         "PASS    25.3 percent vs 36.5 percent"],
        ["3", "Indus Basin 2022",
         "A 70 percent drop in c f should leave a measurable dip in water level at step 300.",
         "PASS    507 vs 1.5"],
    ]
    draw_styled_table(c, data, 0.5 * inch, H - 2.4 * inch,
                      col_widths=[0.4 * inch, 1.8 * inch, 6.7 * inch, 3.4 * inch],
                      header_color=EMERALD, alt_tint=TINT_EMERALD)
    draw_image_top(c, FIG_DIR / "fig07_validation.png",
                   x=2.0 * inch, y_top=H - 4.7 * inch,
                   max_w=8.5 * inch, max_h=2.3 * inch)


def slide_spatial(c: Canvas, idx: int, total: int):
    draw_background(c, accent=AMBER)
    draw_slide_head(c, "Emergent Spatial Dynamics", "08 . evidence", AMBER)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 13)
    c.drawString(0.7 * inch, H - 2.0 * inch,
                 "Three snapshots from one shock scenario run.")
    titles = ["Step 199.  Pre shock cooperation",
              "Step 260.  Mid shock pressure",
              "Step 450.  Post shock equilibrium"]
    files = ["fig08_grid_pre_shock.png",
             "fig09_grid_during_shock.png",
             "fig10_grid_recovery.png"]
    img_w = 3.7 * inch
    img_h = 4.0 * inch
    x_left = 0.55 * inch
    gap = 0.3 * inch
    y_top = H - 2.3 * inch
    for i, (t, f) in enumerate(zip(titles, files)):
        x = x_left + i * (img_w + gap)
        draw_image_top(c, FIG_DIR / f, x=x, y_top=y_top,
                       max_w=img_w, max_h=img_h)
        c.setFillColor(AMBER)
        c.setFont(F_SERIF_BOLD, 13)
        c.drawCentredString(x + img_w / 2, y_top - img_h - 0.2 * inch, t)


def slide_conclusion(c: Canvas, idx: int, total: int):
    draw_background(c, accent=INDIGO_SOFT)
    draw_slide_head(c, "Conclusions and Future Work", "09 . wrap up", INDIGO_SOFT)
    c.setFillColor(INDIGO_SOFT)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.7 * inch, H - 2.3 * inch, "FINDINGS")
    findings = [
        "Pure Q learners reproduce the tragedy of the commons in every climate scenario.",
        "Moderate enforcement at p detect = 0.3 saves cooperation under stable climate.  Water rises from 5 to 685.",
        "The SAME enforcement fails under any climate stress.  Even p detect = 0.9 cannot rescue shock.",
        "Discount factor gamma matters at the margins under stable climate but is dominated by climate dynamics under stress.",
    ]
    draw_bullet_list(c, findings, 0.7 * inch, H - 2.65 * inch,
                     max_w=W - 1.4 * inch, size=13, gap=0.32 * inch,
                     marker_color=INDIGO_SOFT)
    c.setFillColor(CORAL)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.7 * inch, H - 5.0 * inch, "FUTURE WORK")
    future = [
        "Continuous or adaptive action space so agents can scale extraction with current regeneration.",
        "Climate aware monitor that tightens the fair share threshold during droughts.",
        "Deep reinforcement learning extension.  Comparison with human commons experiments (Ostrom style).",
    ]
    draw_bullet_list(c, future, 0.7 * inch, H - 5.35 * inch,
                     max_w=W - 1.4 * inch, size=13, gap=0.32 * inch,
                     marker_color=CORAL)


def slide_thank_you(c: Canvas, idx: int, total: int):
    """Thank you only.  No other text, no footer."""
    draw_background(c, accent=CORAL, big=True)
    # Decorative dots in upper-right + accent shapes.
    c.setFillColor(TEAL);   c.circle(W - 1.4 * inch, H - 2.1 * inch, 0.10 * inch, fill=1, stroke=0)
    c.setFillColor(AMBER);  c.circle(W - 0.9 * inch, H - 3.0 * inch, 0.08 * inch, fill=1, stroke=0)
    c.setFillColor(PURPLE); c.circle(W - 2.0 * inch, H - 1.4 * inch, 0.07 * inch, fill=1, stroke=0)
    # Big "Thank you" centered.
    c.setFillColor(INDIGO)
    c.setFont(F_SERIF_BOLD, 110)
    c.drawCentredString(W / 2, H / 2 - 0.2 * inch, "Thank you")
    # Coral underline accent.
    c.setStrokeColor(CORAL)
    c.setLineWidth(3)
    c.line(W * 0.30, H / 2 - 1.1 * inch, W * 0.70, H / 2 - 1.1 * inch)
    # Lower-left coral half-circle decorative element.
    c.setFillColor(TINT_CORAL)
    c.circle(0.0, 0.0, 1.8 * inch, fill=1, stroke=0)
    c.setFillColor(CORAL)
    c.circle(0.0, 0.0, 0.4 * inch, fill=1, stroke=0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_pdf():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(OUT_PATH), pagesize=(W, H))

    slides = [
        slide_01_title,
        slide_02_team,
        slide_03_contents,
        slide_04_problem,
        slide_05_research_question,
        slide_06_model,
        slide_07_q_learning,
        slide_08_climate,
        slide_09_experiments,
        lambda c, i, t: slide_with_fig(
            c, i, t,
            chip="04 . result 1",
            title="Tragedy Baseline",
            fig="fig01_water_by_scenario.png",
            takeaways=[
                "All four scenarios collapse to roughly 5 units of water within 80 steps.",
                "Mean payoff falls to between minus 755 and minus 804 per agent.",
                "Standard deviation across 30 seeds is effectively zero.  Tragedy is deterministic.",
                "Reproduces Hardin (1968) at the population level.",
            ],
            color=AMBER, tint=TINT_AMBER,
        ),
        lambda c, i, t: slide_with_fig(
            c, i, t,
            chip="05 . result 2",
            title="Enforcement Saves the Stable Climate",
            fig="fig02_enforcement_effect.png",
            takeaways=[
                "Stable scenario.  Water rises from 5 to 685.  A 125 times improvement.",
                "Mean payoff turns positive.  Minus 756 becomes plus 222 per agent.",
                "Eighty six percent of agents choose cooperative actions.",
                "Three other scenarios still collapse.  See next slide for why.",
            ],
            color=EMERALD, tint=TINT_EMERALD,
        ),
        slide_enforcement_fails,
        lambda c, i, t: slide_with_fig(
            c, i, t,
            chip="07 . primary RQ",
            title="Effect of the Discount Factor",
            fig="fig03_gamma_sweep.png",
            takeaways=[
                "Stable scenario.  Final water mildly DECREASES with gamma.  From 748 down to 688.",
                "Shock scenario.  Final water is identical at 5.55 across all gamma values.",
                "Surprising direction.  Lower gamma is slightly better in stable climate.",
                "Refines the answer.  Gamma is not the resilience knob.  Action space matters more.",
            ],
            color=PURPLE, tint=TINT_PURPLE,
        ),
        lambda c, i, t: slide_with_fig(
            c, i, t,
            chip="08 . sensitivity",
            title="Sensitivity Analysis",
            fig="fig04_sensitivity_tornado.png",
            takeaways=[
                "p detect dominates.  Plus or minus 38 units of final water.",
                "Epsilon zero and alpha are non monotonic.  Baseline is near a local optimum.",
                "Gamma effect is moderate.  Regeneration rate is small.",
                "Validates that p detect = 0.3 is a fair choice for the headline runs.",
            ],
            color=TEAL, tint=TINT_TEAL,
        ),
        slide_validation,
        slide_spatial,
        slide_conclusion,
        slide_thank_you,
    ]

    total = len(slides)
    for i, render in enumerate(slides, start=1):
        render(c, i, total)
        c.showPage()
    c.save()
    print(f"Wrote {OUT_PATH}  ({total} slides)")


if __name__ == "__main__":
    build_pdf()
