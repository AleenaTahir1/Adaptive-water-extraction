"""Minimalist Canva-style presentation PDF.

Design system:
  - Cream background (#FBF7F2)
  - Deep maroon primary (#7C1F2C) + plum accent (#5C2D5C)
  - Decorative flowing arcs in upper-right corner of every slide
  - Serif headings (Times Roman family) + sans body (Helvetica)
  - No em-dashes anywhere; punctuation only

Slide order:
  1. Title only (no university name, no author, no date)
  2. Group members (5 names)
  3. Contents (numbered TOC)
  4-N. Content
  Last. "Thank you" only

Run:
    python -m experiments.make_presentation
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus.tables import Table, TableStyle
from reportlab.lib import utils as rl_utils


# Page size: 16:9 widescreen.
W, H = 13.333 * inch, 7.5 * inch

# Palette (Canva-ish minimalist).
BG          = HexColor("#FBF7F2")  # warm cream
MAROON      = HexColor("#7C1F2C")  # primary
MAROON_SOFT = HexColor("#A84C5E")  # lighter maroon for accents
PLUM        = HexColor("#5C2D5C")  # purple accent (matches reference)
INK         = HexColor("#262626")  # near-black body text
MUTED       = HexColor("#8a8378")  # warm gray
GOLD        = HexColor("#B89968")  # warm gold accent (used sparingly)
CARD_BG     = HexColor("#FFFFFF")  # clean white cards

# Fonts (reportlab built-in).
F_SERIF      = "Times-Roman"
F_SERIF_BOLD = "Times-Bold"
F_SERIF_ITAL = "Times-Italic"
F_SANS       = "Helvetica"
F_SANS_BOLD  = "Helvetica-Bold"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "figures"
OUT_PATH = PROJECT_ROOT / "report" / "presentation.pdf"


# ---------------------------------------------------------------------------
# Decorative chrome (corner arcs, footer rule, page number)
# ---------------------------------------------------------------------------


def draw_background(c: Canvas, big_corner: bool = False):
    """Cream background + decorative corner arcs.

    `big_corner=True` is used on title-only slides where the motif is the
    visual focus; regular content slides use a smaller, tucked motif.
    """
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    if big_corner:
        # Title slide: bigger but still in the corner, kept out of center column.
        draw_corner_arcs(c, anchor_x=W + 0.3 * inch, anchor_y=H + 0.3 * inch,
                         inner_r=0.5 * inch, outer_r=3.2 * inch, n_arcs=16,
                         alpha_inner=0.35, alpha_outer=0.85)
    else:
        # Content slides: subtle accent.
        draw_corner_arcs(c, anchor_x=W + 0.3 * inch, anchor_y=H + 0.3 * inch,
                         inner_r=0.4 * inch, outer_r=2.2 * inch, n_arcs=11,
                         alpha_inner=0.20, alpha_outer=0.60)
    # Subtle accent rule along the left edge.
    c.setStrokeColor(MAROON)
    c.setLineWidth(2.5)
    c.line(0, 0, 0, H)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def draw_corner_arcs(c: Canvas, anchor_x: float, anchor_y: float,
                     inner_r: float, outer_r: float, n_arcs: int = 12,
                     alpha_inner: float = 0.25, alpha_outer: float = 0.7):
    """Concentric quarter arcs in the upper-right corner."""
    c.saveState()
    for i in range(n_arcs):
        t = i / (n_arcs - 1)
        r = _lerp(inner_r, outer_r, t)
        # Color: MAROON_SOFT -> MAROON as t grows. Use the alpha range
        # to fade in slowly so the motif feels airy, not heavy.
        alpha = _lerp(alpha_inner, alpha_outer, t)
        red   = int(_lerp(0xA8, 0x7C, t))
        green = int(_lerp(0x4C, 0x1F, t))
        blue  = int(_lerp(0x5E, 0x2C, t))
        # Approximate the alpha by mixing toward the BG color (#FBF7F2).
        bg_r, bg_g, bg_b = 0xFB, 0xF7, 0xF2
        rr = int(_lerp(bg_r, red, alpha))
        gg = int(_lerp(bg_g, green, alpha))
        bb = int(_lerp(bg_b, blue, alpha))
        c.setStrokeColorRGB(rr / 255, gg / 255, bb / 255)
        c.setLineWidth(_lerp(0.6, 1.2, t))
        c.arc(anchor_x - r, anchor_y - r, anchor_x + r, anchor_y + r,
              startAng=180, extent=90)
    c.restoreState()


def draw_footer(c: Canvas, page_num: int, total: int):
    """Thin maroon rule + small page indicator at the bottom."""
    c.setStrokeColor(MAROON)
    c.setLineWidth(0.6)
    c.line(0.6 * inch, 0.5 * inch, W - 0.6 * inch, 0.5 * inch)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 9)
    c.drawString(0.6 * inch, 0.3 * inch, "Adaptive Water Extraction with Q-Learning")
    c.drawRightString(W - 0.6 * inch, 0.3 * inch, f"{page_num} / {total}")


def draw_section_chip(c: Canvas, label: str, y: float):
    """Small all-caps chip with a maroon bar before a slide title."""
    c.setStrokeColor(MAROON)
    c.setLineWidth(2)
    c.line(0.6 * inch, y + 0.04 * inch, 0.85 * inch, y + 0.04 * inch)
    c.setFillColor(MAROON)
    c.setFont(F_SANS_BOLD, 10)
    c.drawString(0.95 * inch, y, label.upper())


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


def draw_paragraph(c: Canvas, text: str, x: float, y_top: float, max_w: float,
                   font: str = F_SANS, size: int = 13, color=INK,
                   leading_mult: float = 1.45) -> float:
    """Draw wrapped paragraph. Returns the bottom-y after drawing."""
    lines = wrap_text(c, text, max_w, font, size)
    c.setFillColor(color)
    c.setFont(font, size)
    leading = size * leading_mult
    for i, line in enumerate(lines):
        c.drawString(x, y_top - i * leading, line)
    return y_top - len(lines) * leading


def draw_bullet_list(c: Canvas, items: list[str], x: float, y_top: float,
                     max_w: float, size: int = 14, gap: float = 0.32 * inch) -> float:
    """Draw a list of bullet items with subtle maroon dot markers."""
    y = y_top
    for it in items:
        # Marker
        c.setFillColor(MAROON)
        c.circle(x + 0.05 * inch, y + 0.07 * inch, 3.0, fill=1, stroke=0)
        # Wrapped text
        wrapped = wrap_text(c, it, max_w - 0.35 * inch, F_SANS, size)
        c.setFillColor(INK)
        c.setFont(F_SANS, size)
        leading = size * 1.4
        for i, line in enumerate(wrapped):
            c.drawString(x + 0.3 * inch, y - i * leading, line)
        y -= gap + (len(wrapped) - 1) * leading
    return y


def draw_styled_table(c: Canvas, data: list[list[str]], x: float, y_top: float,
                      col_widths: list[float]):
    """Maroon header, alternating cream rows, no harsh borders."""
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MAROON),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), F_SANS_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTNAME", (0, 1), (-1, -1), F_SANS),
        ("FONTSIZE", (0, 1), (-1, -1), 10.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, MAROON),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, HexColor("#E7E0D6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 1), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, BG]),
    ])
    t = Table(data, colWidths=col_widths)
    t.setStyle(style)
    _, h = t.wrap(sum(col_widths), 0)
    t.drawOn(c, x, y_top - h)
    return y_top - h


def draw_image(c: Canvas, path: Path, x: float, y_bottom: float,
               max_w: float, max_h: float):
    if not path.exists():
        return 0, 0
    img = rl_utils.ImageReader(str(path))
    iw, ih = img.getSize()
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    # Center horizontally in the allocated box.
    x_centered = x + (max_w - w) / 2
    c.drawImage(img, x_centered, y_bottom, width=w, height=h, mask="auto")
    return w, h


def draw_slide_title(c: Canvas, title: str, subtitle: str | None = None,
                     section_chip: str | None = None):
    """Standard slide head: small section chip, big serif title, optional subtitle."""
    y = H - 1.1 * inch
    if section_chip:
        draw_section_chip(c, section_chip, y + 0.4 * inch)
    c.setFillColor(INK)
    c.setFont(F_SERIF_BOLD, 32)
    c.drawString(0.6 * inch, y, title)
    if subtitle:
        c.setFillColor(MUTED)
        c.setFont(F_SERIF_ITAL, 14)
        c.drawString(0.6 * inch, y - 0.4 * inch, subtitle)


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------


def slide_01_title(c: Canvas, page_num: int, total: int):
    """Title only.  No university name, no author, no date."""
    draw_background(c, big_corner=True)

    # Title is anchored on the LEFT, away from the corner motif.
    tx = 0.9 * inch
    ty = H / 2 + 0.6 * inch

    # Small "01" mark above the title.
    c.setFillColor(MAROON)
    c.setFont(F_SERIF_BOLD, 16)
    c.drawString(tx, ty + 1.6 * inch, "01")
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.2)
    c.line(tx + 0.4 * inch, ty + 1.68 * inch, tx + 1.0 * inch, ty + 1.68 * inch)

    # Topic name only -- big serif, two lines, left aligned.
    c.setFillColor(MAROON)
    c.setFont(F_SERIF_BOLD, 56)
    c.drawString(tx, ty + 0.3 * inch, "Adaptive Water")
    c.drawString(tx, ty - 0.55 * inch, "Extraction")
    # Italic clarifier.
    c.setFillColor(INK)
    c.setFont(F_SERIF_ITAL, 26)
    c.drawString(tx, ty - 1.5 * inch, "with Q Learning under Climate Stress")

    # Tagline anchor.
    c.setStrokeColor(PLUM)
    c.setLineWidth(0.6)
    c.line(tx, ty - 1.95 * inch, tx + 2.0 * inch, ty - 1.95 * inch)
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 14)
    c.drawString(tx, ty - 2.25 * inch, "An agent based model in Python")
    draw_footer(c, page_num, total)


def slide_02_team(c: Canvas, page_num: int, total: int):
    """Group members. Five names in a clean centered list."""
    draw_background(c)
    draw_section_chip(c, "team", H - 0.85 * inch)
    c.setFillColor(INK)
    c.setFont(F_SERIF_BOLD, 36)
    c.drawString(0.6 * inch, H - 1.4 * inch, "Group Members")
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 14)
    c.drawString(0.6 * inch, H - 1.8 * inch, "Five contributors. One model. One simulation.")

    members = [
        "Saqlain Abbas",
        "Aleena Tahir",
        "Aena Habib",
        "Eman Asghar",
        "Dua Kamal",
    ]

    # Card panel for the names.
    card_x, card_y = 1.5 * inch, 1.2 * inch
    card_w, card_h = W - 3.0 * inch, 4.4 * inch
    c.setFillColor(CARD_BG)
    c.roundRect(card_x, card_y, card_w, card_h, 12, fill=1, stroke=0)
    c.setStrokeColor(MAROON)
    c.setLineWidth(0.6)
    c.roundRect(card_x, card_y, card_w, card_h, 12, fill=0, stroke=1)

    # Render each name with a maroon serial circle on the left.
    row_h = card_h / (len(members) + 1)
    cx = card_x + 1.5 * inch
    for i, name in enumerate(members):
        row_y = card_y + card_h - row_h * (i + 1)
        # Circle with number.
        c.setFillColor(MAROON)
        c.circle(cx, row_y + 0.04 * inch, 0.22 * inch, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont(F_SERIF_BOLD, 13)
        c.drawCentredString(cx, row_y - 0.04 * inch, f"0{i + 1}")
        # Name.
        c.setFillColor(INK)
        c.setFont(F_SERIF, 22)
        c.drawString(cx + 0.55 * inch, row_y - 0.05 * inch, name)

    draw_footer(c, page_num, total)


def slide_03_contents(c: Canvas, page_num: int, total: int):
    """Table of contents."""
    draw_background(c)
    draw_slide_title(c, "Contents", section_chip="agenda",
                     subtitle="A guided tour of the model and its findings")

    sections = [
        ("01", "The Problem and the Research Question"),
        ("02", "How the Model Works"),
        ("03", "Climate Scenarios and Experimental Design"),
        ("04", "Result 1.   Tragedy Baseline"),
        ("05", "Result 2.   Enforcement Saves the Stable Climate"),
        ("06", "Result 3.   Why Enforcement Fails Under Stress"),
        ("07", "Primary RQ.   Effect of Discount Factor"),
        ("08", "Sensitivity and Validation"),
        ("09", "Conclusions and Future Work"),
    ]

    x_left = 0.9 * inch
    y = H - 2.4 * inch
    row_h = 0.46 * inch
    for num, title in sections:
        # Maroon serial.
        c.setFillColor(MAROON)
        c.setFont(F_SERIF_BOLD, 22)
        c.drawString(x_left, y, num)
        # Dotted leader line.
        c.setStrokeColor(HexColor("#D8C8B8"))
        c.setLineWidth(0.4)
        c.setDash(1, 3)
        c.line(x_left + 0.8 * inch, y + 0.05 * inch, W - 2.2 * inch, y + 0.05 * inch)
        c.setDash()
        # Section title.
        c.setFillColor(INK)
        c.setFont(F_SERIF, 16)
        c.drawString(x_left + 0.95 * inch, y, title)
        y -= row_h
    draw_footer(c, page_num, total)


def slide_04_problem(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "The Problem", section_chip="01 . context",
                     subtitle="Tragedy of the Commons meets a changing climate")

    bullets = [
        "Twenty farmers share one river. Each season every farmer decides how much water to extract.",
        "If everyone extracts heavily the resource collapses and everyone loses next year. Hardin (1968) called this the Tragedy of the Commons.",
        "Pakistan's Indus Basin sustains over 90 percent of the country's agriculture and is one of the world's most water stressed basins.",
        "By 2030 nearly half the global population will live in regions of high water stress (UN World Water Development Report).",
        "Real farmers do not follow fixed rules. They learn, observe neighbors, and adapt. Existing agent based models do not capture this learning.",
    ]
    draw_bullet_list(c, bullets, 0.7 * inch, H - 2.4 * inch,
                     max_w=W - 1.4 * inch, size=15, gap=0.40 * inch)
    draw_footer(c, page_num, total)


def slide_05_research_question(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "Research Question", section_chip="01 . focus")

    # Primary question card.
    card_x, card_y = 0.7 * inch, H - 4.3 * inch
    card_w, card_h = W - 1.4 * inch, 1.9 * inch
    c.setFillColor(CARD_BG)
    c.roundRect(card_x, card_y, card_w, card_h, 14, fill=1, stroke=0)
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.0)
    c.roundRect(card_x, card_y, card_w, card_h, 14, fill=0, stroke=1)

    c.setFillColor(MAROON)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(card_x + 0.4 * inch, card_y + card_h - 0.4 * inch, "PRIMARY QUESTION")
    c.setFillColor(INK)
    c.setFont(F_SERIF_ITAL, 18)
    wrap = wrap_text(c, "How does the discount factor gamma in Q learning agents affect the emergence of sustainable water extraction strategies under varying climate stress scenarios?",
                     card_w - 0.8 * inch, F_SERIF_ITAL, 18)
    for i, line in enumerate(wrap):
        c.drawString(card_x + 0.4 * inch,
                     card_y + card_h - 0.85 * inch - i * 0.36 * inch, line)

    # Sub questions
    c.setFillColor(MAROON)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.7 * inch, H - 4.7 * inch, "SUB QUESTIONS")
    subs = [
        "Can Q learning agents discover cooperative strategies without external enforcement?",
        "How do learned strategies break down under sudden drought shocks, and how fast do agents re adapt?",
        "At what monitoring intensity does enforcement become unnecessary?",
    ]
    draw_bullet_list(c, subs, 0.7 * inch, H - 5.1 * inch,
                     max_w=W - 1.4 * inch, size=13, gap=0.36 * inch)
    draw_footer(c, page_num, total)


def slide_06_model(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "How the Model Works", section_chip="02 . model",
                     subtitle="Three stage step. Each agent learns from experience.")
    bullets = [
        "Each irrigator chooses one of five extraction levels (0, 25, 50, 75, 100 percent of max).",
        "State observed by the agent is a tuple. Water level bin, own previous action, neighbors average action, climate stress flag.",
        "Reward equals log utility of water extracted minus a sustainability penalty minus any fine.",
        "Shared resource follows logistic regeneration with a baseline inflow modulated by climate factor.",
        "Monitor agent catches over extractors with probability p detect and issues a fine.",
        "Social network is a random k regular graph. Each farmer observes k neighbors.",
        "Implemented in Python 3.12 with Mesa 2.3.4. About 700 lines of clear code.",
    ]
    draw_bullet_list(c, bullets, 0.7 * inch, H - 2.5 * inch,
                     max_w=W - 1.4 * inch, size=14, gap=0.35 * inch)
    draw_footer(c, page_num, total)


def slide_07_q_learning(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "The Q Learning Update Rule",
                     section_chip="02 . math",
                     subtitle="Watkins and Dayan 1992. Tabular and interpretable.")

    # Formula card.
    card_x, card_y = 0.9 * inch, H - 4.5 * inch
    card_w, card_h = W - 1.8 * inch, 1.8 * inch
    c.setFillColor(CARD_BG)
    c.roundRect(card_x, card_y, card_w, card_h, 14, fill=1, stroke=0)
    c.setStrokeColor(PLUM)
    c.setLineWidth(0.7)
    c.roundRect(card_x, card_y, card_w, card_h, 14, fill=0, stroke=1)

    c.setFillColor(MAROON)
    c.setFont(F_SERIF_BOLD, 30)
    c.drawCentredString(W / 2, card_y + card_h / 2 + 0.2 * inch,
                        "Q ( s, a )   =   Q ( s, a )   +   alpha  [  r  +  gamma  max  Q ( s', a' )   minus   Q ( s, a )  ]")
    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 13)
    c.drawCentredString(W / 2, card_y + 0.35 * inch,
                        "alpha is the learning rate.   gamma is the discount factor.   s' is the post regen state.")

    notes = [
        "Exploration uses epsilon greedy with exponential decay. Epsilon starts at 0.30 and decays at rate 0.010.",
        "State space is small. About 150 unique state action pairs fit comfortably in a tabular Q table.",
        "Action 2 equals each agent's fair share of total sustainable yield. Auto scaled with N.",
        "Heterogeneity. Each agent has its own RNG and its own initial Q table noise.",
    ]
    draw_bullet_list(c, notes, 0.7 * inch, H - 5.0 * inch,
                     max_w=W - 1.4 * inch, size=12.5, gap=0.30 * inch)
    draw_footer(c, page_num, total)


def slide_08_climate(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "Climate Scenarios", section_chip="03 . scenarios",
                     subtitle="Four climate factor profiles test resilience")

    data = [
        ["Scenario", "Climate factor profile"],
        ["Stable",     "c_f = 1.0 forever.  Baseline. No climate change."],
        ["Gradual",    "c_f declines linearly from 1.0 to 0.5 over 400 steps."],
        ["Shock",      "c_f = 1.0 normally.  Drops to 0.3 between steps 200 and 300."],
        ["Stochastic", "c_f is gaussian noise around 0.85, clipped to between 0.3 and 1.0."],
    ]
    draw_styled_table(c, data, 0.7 * inch, H - 2.6 * inch,
                      col_widths=[2.4 * inch, W - 4.0 * inch])

    c.setFillColor(MUTED)
    c.setFont(F_SERIF_ITAL, 13)
    c.drawString(0.7 * inch, 1.4 * inch,
                 "c_f multiplies BOTH the logistic regeneration term AND the baseline inflow.")
    c.drawString(0.7 * inch, 1.10 * inch,
                 "Lower c_f means less water replenished each season.")
    draw_footer(c, page_num, total)


def slide_09_experiments(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "Experimental Design", section_chip="03 . experiments",
                     subtitle="Three batch experiments totaling 340 runs")

    data = [
        ["Experiment", "Variables", "Runs"],
        ["A.  Tragedy baseline", "4 climates  x  30 seeds.  No monitor.", "120"],
        ["B.  With enforcement", "4 climates  x  30 seeds.  p detect = 0.3", "120"],
        ["C.  Gamma sweep",      "stable and shock  x  5 gamma values  x  10 seeds", "100"],
    ]
    draw_styled_table(c, data, 0.7 * inch, H - 2.6 * inch,
                      col_widths=[3.5 * inch, 6.6 * inch, 1.6 * inch])

    extras = [
        "Each run is 500 simulation steps. About 125 seasons if one step is one quarter year.",
        "Sensitivity analysis varies alpha, gamma, epsilon, regeneration rate, p detect, N by plus or minus 20 percent.",
        "Validation. Three sanity checks against Hardin 1968, Perolat 2017, and Indus Basin 2022.",
    ]
    draw_bullet_list(c, extras, 0.7 * inch, 3.0 * inch,
                     max_w=W - 1.4 * inch, size=13, gap=0.32 * inch)
    draw_footer(c, page_num, total)


def slide_with_fig(c: Canvas, page_num: int, total: int,
                   chip: str, title: str, subtitle: str,
                   fig: str, takeaways: list[str]):
    draw_background(c)
    draw_slide_title(c, title, section_chip=chip, subtitle=subtitle)
    # Figure on left.
    fig_w = 7.4 * inch
    fig_h = H - 2.7 * inch
    draw_image(c, FIG_DIR / fig, x=0.5 * inch, y_bottom=0.9 * inch,
               max_w=fig_w, max_h=fig_h)
    # Takeaways on right.
    rx = 8.2 * inch
    c.setFillColor(MAROON)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(rx, H - 2.5 * inch, "WHAT IT MEANS")
    draw_bullet_list(c, takeaways, rx, H - 2.85 * inch,
                     max_w=W - rx - 0.5 * inch, size=12, gap=0.30 * inch)
    draw_footer(c, page_num, total)


def slide_enforcement_fails(c: Canvas, page_num: int, total: int):
    """Headline negative result. Dedicated layout."""
    draw_background(c)
    draw_slide_title(c, "Why Enforcement Fails Under Stress",
                     section_chip="06 . key finding",
                     subtitle="The fixed quota policy breaks when climate changes")

    # Red callout strip.
    c.setFillColor(MAROON)
    c.rect(0.6 * inch, H - 2.7 * inch, W - 1.2 * inch, 0.55 * inch, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(F_SERIF_BOLD, 19)
    c.drawString(0.85 * inch, H - 2.55 * inch,
                 "Even p detect = 0.9 cannot save the drought shock scenario.")

    # Evidence table.
    data = [
        ["p detect", "stable.  final water", "shock.  final water"],
        ["0.3", "700", "5.6  (collapsed)"],
        ["0.6", "777", "5.6  (collapsed)"],
        ["0.9", "787", "5.6  (collapsed)"],
    ]
    draw_styled_table(c, data, 0.7 * inch, H - 3.0 * inch,
                      col_widths=[2.0 * inch, 4.5 * inch, 5.0 * inch])

    # Why it happens.
    c.setFillColor(MAROON)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.7 * inch, H - 5.4 * inch, "WHY IT HAPPENS  (structural, not a tuning issue)")
    reasons = [
        "Agents' five action grid is calibrated to the baseline climate where c f = 1.0",
        "When c f drops to 0.3 during the shock, even the cooperative fair share action is over extraction.",
        "Sixty eight percent of agents are STILL choosing cooperative actions during failure. They are not selfish.",
        "Implication.  Real regulators need adaptive (climate aware) quotas. Fixed quotas are not enough.",
    ]
    draw_bullet_list(c, reasons, 0.7 * inch, H - 5.75 * inch,
                     max_w=W - 1.4 * inch, size=12, gap=0.28 * inch)
    draw_footer(c, page_num, total)


def slide_validation(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "Validation Against Literature",
                     section_chip="08 . validation",
                     subtitle="Three sanity checks.  All three pass.")
    data = [
        ["#", "Source", "Test", "Result"],
        ["1", "Hardin 1968",
         "No enforcement should collapse the resource. With enforcement under stable climate it should sustain.",
         "PASS    5.6 vs 504"],
        ["2", "Perolat et al 2017",
         "Scarcity should drive aggression.  Compare frac defect during steps 200 to 300 under stable vs shock with enforcement.",
         "PASS    25.3 percent vs 36.5 percent"],
        ["3", "Indus Basin 2022",
         "A 70 percent drop in c f should leave a measurable dip in water level at step 300.",
         "PASS    507 vs 1.5"],
    ]
    draw_styled_table(c, data, 0.5 * inch, H - 2.4 * inch,
                      col_widths=[0.4 * inch, 1.9 * inch, 6.6 * inch, 3.4 * inch])
    # Figure below the table.
    draw_image(c, FIG_DIR / "fig07_validation.png",
               x=2.0 * inch, y_bottom=0.85 * inch, max_w=8.5 * inch, max_h=2.4 * inch)
    draw_footer(c, page_num, total)


def slide_spatial(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "Emergent Spatial Dynamics",
                     section_chip="08 . evidence",
                     subtitle="Three snapshots from one shock scenario run")
    titles = ["Step 199.  Pre shock cooperation",
              "Step 260.  Mid shock pressure",
              "Step 450.  Post shock equilibrium"]
    files = ["fig08_grid_pre_shock.png",
             "fig09_grid_during_shock.png",
             "fig10_grid_recovery.png"]
    img_w = 3.7 * inch
    img_h = 3.9 * inch
    x_left = 0.55 * inch
    gap = 0.3 * inch
    for i, (t, f) in enumerate(zip(titles, files)):
        x = x_left + i * (img_w + gap)
        draw_image(c, FIG_DIR / f, x=x, y_bottom=1.3 * inch, max_w=img_w, max_h=img_h)
        c.setFillColor(MAROON)
        c.setFont(F_SERIF_BOLD, 13)
        c.drawCentredString(x + img_w / 2, 1.05 * inch, t)
    draw_footer(c, page_num, total)


def slide_conclusion(c: Canvas, page_num: int, total: int):
    draw_background(c)
    draw_slide_title(c, "Conclusions and Future Work",
                     section_chip="09 . wrap up", subtitle="What we learned.  What comes next.")

    c.setFillColor(MAROON)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.7 * inch, H - 2.4 * inch, "FINDINGS")
    findings = [
        "Pure Q learners reproduce the tragedy of the commons in every climate scenario.",
        "Moderate enforcement at p detect = 0.3 saves cooperation under stable climate.  Water rises from 5 to 685.",
        "The SAME enforcement fails under any climate stress.  Even p detect = 0.9 cannot rescue shock.",
        "Discount factor gamma matters at the margins under stable climate but is dominated by climate dynamics under stress.",
    ]
    draw_bullet_list(c, findings, 0.7 * inch, H - 2.7 * inch,
                     max_w=W - 1.4 * inch, size=12.5, gap=0.30 * inch)

    c.setFillColor(MAROON)
    c.setFont(F_SANS_BOLD, 11)
    c.drawString(0.7 * inch, H - 5.0 * inch, "FUTURE WORK")
    future = [
        "Continuous or adaptive action space so agents can scale extraction with current regeneration.",
        "Climate aware monitor that tightens the fair share threshold during droughts.",
        "Deep reinforcement learning extension.  Comparison with human commons experiments (Ostrom style).",
    ]
    draw_bullet_list(c, future, 0.7 * inch, H - 5.3 * inch,
                     max_w=W - 1.4 * inch, size=12.5, gap=0.30 * inch)
    draw_footer(c, page_num, total)


def slide_thank_you(c: Canvas, page_num: int, total: int):
    """Thank you only.  No other text."""
    draw_background(c, big_corner=True)
    # Big serif Thank you, centered.
    c.setFillColor(MAROON)
    c.setFont(F_SERIF_BOLD, 96)
    c.drawCentredString(W / 2, H / 2 + 0.2 * inch, "Thank you")
    # Subtle plum underline accent.
    c.setStrokeColor(PLUM)
    c.setLineWidth(0.8)
    c.line(W * 0.30, H / 2 - 0.6 * inch, W * 0.70, H / 2 - 0.6 * inch)
    draw_footer(c, page_num, total)


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
        lambda c, p, t: slide_with_fig(
            c, p, t,
            chip="04 . result 1",
            title="Tragedy Baseline",
            subtitle="Without enforcement every climate collapses",
            fig="fig01_water_by_scenario.png",
            takeaways=[
                "All four scenarios collapse to roughly 5 units of water within 80 steps.",
                "Mean payoff falls to between minus 755 and minus 804 per agent.",
                "Standard deviation across 30 seeds is effectively zero. Tragedy is deterministic.",
                "Reproduces Hardin (1968) at the population level.",
            ],
        ),
        lambda c, p, t: slide_with_fig(
            c, p, t,
            chip="05 . result 2",
            title="Enforcement Saves the Stable Climate",
            subtitle="Moderate monitoring flips the dynamics",
            fig="fig02_enforcement_effect.png",
            takeaways=[
                "Stable scenario.  Water rises from 5 to 685.  A 125 times improvement.",
                "Mean payoff turns positive.  Minus 756 becomes plus 222 per agent.",
                "Eighty six percent of agents choose cooperative actions.",
                "Three other scenarios still collapse.  See next slide for why.",
            ],
        ),
        slide_enforcement_fails,
        lambda c, p, t: slide_with_fig(
            c, p, t,
            chip="07 . primary RQ",
            title="Effect of the Discount Factor",
            subtitle="Gamma sweep over stable and shock scenarios",
            fig="fig03_gamma_sweep.png",
            takeaways=[
                "Stable scenario.  Final water mildly DECREASES with gamma.  From 748 down to 688.",
                "Shock scenario.  Final water is identical at 5.55 across all gamma values.",
                "Surprising direction.  Lower gamma (more myopic) is slightly better in stable climate.",
                "Refines the answer.  Gamma is not the resilience knob.  Action space matters more.",
            ],
        ),
        lambda c, p, t: slide_with_fig(
            c, p, t,
            chip="08 . sensitivity",
            title="Sensitivity Analysis",
            subtitle="Plus or minus 20 percent on six parameters",
            fig="fig04_sensitivity_tornado.png",
            takeaways=[
                "p detect dominates.  Plus or minus 38 units of final water.",
                "Epsilon zero and alpha are non monotonic.  Baseline is near a local optimum.",
                "Gamma effect is moderate.  Regeneration rate is small.",
                "Validates that p detect = 0.3 is a fair choice for the headline runs.",
            ],
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
