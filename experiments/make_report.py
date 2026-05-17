"""Generate the final report PDF directly using reportlab Platypus.

Mirrors the structure of report.tex but compiles entirely in Python so the
user doesn't need a LaTeX install. Pure A4 portrait, 1-inch margins,
serif body, numbered sections, embedded figures, full inline ODD.

Run:
    python -m experiments.make_report
Output:
    report/report.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Image, Table, TableStyle, KeepTogether, NextPageTemplate,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib import utils as rl_utils


# ---------------------------------------------------------------------------
# Paths and palette
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "figures"
REPORT_DIR = PROJECT_ROOT / "report"
LOGO_PATH = REPORT_DIR / "logo.png"
OUT_PATH = REPORT_DIR / "report.pdf"

NUT_DARK   = HexColor("#0A1E3C")
NUT_ACCENT = HexColor("#006464")
INK        = HexColor("#1A1A1A")
MUTED      = HexColor("#6B6B6B")
HAIRLINE   = HexColor("#D8D8D8")
TINT_DARK  = HexColor("#EEF1F6")  # very light blue tint for cards


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

styles = getSampleStyleSheet()

BODY = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontName="Times-Roman", fontSize=11.5, leading=16.5,
    alignment=TA_JUSTIFY, textColor=INK, spaceAfter=6,
)
BODY_LEFT = ParagraphStyle(
    "BodyLeft", parent=BODY, alignment=TA_LEFT,
)
SECTION = ParagraphStyle(
    "Section", parent=styles["Heading1"],
    fontName="Times-Bold", fontSize=18, leading=22,
    textColor=NUT_DARK, spaceBefore=18, spaceAfter=10,
)
SUBSECTION = ParagraphStyle(
    "SubSection", parent=styles["Heading2"],
    fontName="Times-Bold", fontSize=14, leading=18,
    textColor=NUT_ACCENT, spaceBefore=12, spaceAfter=6,
)
SUBSUBSECTION = ParagraphStyle(
    "SubSubSection", parent=styles["Heading3"],
    fontName="Times-Bold", fontSize=12, leading=16,
    textColor=NUT_DARK, spaceBefore=8, spaceAfter=4,
)
CAPTION = ParagraphStyle(
    "Caption", parent=BODY,
    fontName="Times-Italic", fontSize=10, leading=13,
    textColor=MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=10,
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY,
    leftIndent=24, bulletIndent=10, alignment=TA_LEFT,
    spaceAfter=3,
)
QUOTE = ParagraphStyle(
    "Quote", parent=BODY,
    fontName="Times-Italic", fontSize=12, leading=17,
    leftIndent=18, rightIndent=18, textColor=INK,
    spaceBefore=6, spaceAfter=8,
)
CODE = ParagraphStyle(
    "Code", parent=BODY,
    fontName="Courier", fontSize=9, leading=12,
    alignment=TA_LEFT, leftIndent=10, rightIndent=10,
    backColor=HexColor("#F4F4F8"), borderColor=HAIRLINE,
    borderWidth=0.5, borderPadding=6,
    spaceBefore=4, spaceAfter=8,
)
ABSTRACT_HEADER = ParagraphStyle(
    "AbstractHeader", parent=SECTION,
    alignment=TA_CENTER, spaceBefore=0,
)

# Title page styles. Note: leading must be >= fontSize * 1.15 to avoid overlap
# between consecutive paragraph lines.
TP_UNI = ParagraphStyle(
    "TP_Uni", parent=BODY,
    fontName="Times-Bold", fontSize=22, leading=28, alignment=TA_CENTER,
    textColor=NUT_DARK, spaceBefore=0, spaceAfter=10,
)
TP_DEPT = ParagraphStyle(
    "TP_Dept", parent=BODY,
    fontName="Times-Roman", fontSize=13, leading=18, alignment=TA_CENTER,
    textColor=INK, spaceBefore=0, spaceAfter=16,
)
TP_PROJECT = ParagraphStyle(
    "TP_Project", parent=BODY,
    fontName="Times-Bold", fontSize=20, leading=26, alignment=TA_CENTER,
    textColor=NUT_DARK, spaceBefore=8, spaceAfter=8,
)
TP_SUBTITLE = ParagraphStyle(
    "TP_Sub", parent=BODY,
    fontName="Times-Italic", fontSize=13, leading=18, alignment=TA_CENTER,
    textColor=INK, spaceAfter=14,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fig(rel_name: str, width_frac: float = 0.85, caption: str | None = None,
        max_h_inch: float = 4.0) -> list:
    """Insert a figure scaled to width fraction of the content area."""
    path = FIG_DIR / rel_name
    if not path.exists():
        return [Paragraph(f"<i>[missing figure: {rel_name}]</i>", BODY)]
    # Get native size and scale.
    img_reader = rl_utils.ImageReader(str(path))
    iw, ih = img_reader.getSize()
    content_w = (A4[0] - 1.5 * inch) * width_frac  # 0.75 inch margins each side
    scale_w = content_w / iw
    scale_h = (max_h_inch * inch) / ih
    scale = min(scale_w, scale_h)
    final_w, final_h = iw * scale, ih * scale
    items = [Image(str(path), width=final_w, height=final_h, hAlign="CENTER")]
    if caption:
        items.append(Paragraph(f"<b>Figure.</b> {caption}", CAPTION))
    items.append(Spacer(1, 0.05 * inch))
    return items


def maketable(data: list[list[str]], col_widths: list[float],
              header_color=NUT_DARK, alt_tint=TINT_DARK,
              first_col_bold: bool = False) -> Table:
    """Build a styled report table."""
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10.5),
        ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, header_color),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, HAIRLINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, alt_tint]),
    ])
    if first_col_bold:
        style.add("FONTNAME", (0, 1), (0, -1), "Times-Bold")
    return Table(data, colWidths=col_widths, style=style)


def section(num: str, title: str, story: list, toc_level: int = 0):
    """Add a numbered section heading + entry to the TOC."""
    para = Paragraph(f"{num}. {title}", SECTION)
    para._toc_text = f"{num} {title}"
    para._toc_level = toc_level
    story.append(para)


def subsection(num: str, title: str, story: list):
    para = Paragraph(f"{num} {title}", SUBSECTION)
    para._toc_text = f"{num} {title}"
    para._toc_level = 1
    story.append(para)


def para(text: str, story: list, style: ParagraphStyle = BODY):
    story.append(Paragraph(text, style))


def bullets(items: list[str], story: list, style: ParagraphStyle = BULLET):
    for it in items:
        story.append(Paragraph(it, style, bulletText="▸"))


# ---------------------------------------------------------------------------
# Custom doc template -- title page + content frames + page numbers + TOC hooks
# ---------------------------------------------------------------------------


class ReportTemplate(BaseDocTemplate):

    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        self.allowSplitting = 1
        # Title page frame (no margins, full bleed).
        title_frame = Frame(
            0, 0, A4[0], A4[1],
            leftPadding=0.7 * inch, rightPadding=0.7 * inch,
            topPadding=0.7 * inch, bottomPadding=0.7 * inch,
            id="title", showBoundary=0,
        )
        # Content frame -- standard academic margins.
        content_frame = Frame(
            0.75 * inch, 0.75 * inch,
            A4[0] - 1.5 * inch, A4[1] - 1.5 * inch,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
            id="content", showBoundary=0,
        )
        self.addPageTemplates([
            PageTemplate(id="title", frames=[title_frame], onPage=self._title_decorations),
            PageTemplate(id="content", frames=[content_frame], onPage=self._content_decorations),
        ])

    # --- Page decorations ---------------------------------------------------

    def _title_decorations(self, canvas, doc):
        canvas.saveState()
        # Thin top + bottom band.
        canvas.setStrokeColor(NUT_DARK)
        canvas.setLineWidth(0.8)
        canvas.line(0.7 * inch, A4[1] - 0.5 * inch,
                    A4[0] - 0.7 * inch, A4[1] - 0.5 * inch)
        canvas.line(0.7 * inch, 0.5 * inch,
                    A4[0] - 0.7 * inch, 0.5 * inch)
        # Date drawn directly so it never overflows to page 2.
        from datetime import date
        canvas.setFillColor(MUTED)
        canvas.setFont("Times-Roman", 11)
        canvas.drawCentredString(A4[0] / 2, 0.7 * inch,
                                 date.today().strftime("%B %Y"))
        canvas.restoreState()

    def _content_decorations(self, canvas, doc):
        canvas.saveState()
        # Header rule + left/right header text.
        canvas.setStrokeColor(NUT_DARK)
        canvas.setLineWidth(0.5)
        canvas.line(0.75 * inch, A4[1] - 0.55 * inch,
                    A4[0] - 0.75 * inch, A4[1] - 0.55 * inch)
        canvas.setFillColor(NUT_DARK)
        canvas.setFont("Times-Bold", 9)
        canvas.drawString(0.75 * inch, A4[1] - 0.45 * inch, "ABM Semester Project")
        canvas.setFont("Times-Italic", 9)
        canvas.drawRightString(A4[0] - 0.75 * inch, A4[1] - 0.45 * inch,
                                "Water Commons + Q-Learning")
        # Footer with page number.
        canvas.setLineWidth(0.5)
        canvas.line(0.75 * inch, 0.55 * inch,
                    A4[0] - 0.75 * inch, 0.55 * inch)
        canvas.setFont("Times-Roman", 9)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(A4[0] / 2, 0.4 * inch, str(canvas.getPageNumber()))
        canvas.restoreState()

    # --- TOC integration ----------------------------------------------------

    def afterFlowable(self, flowable):
        """Auto-register section headings with the TOC."""
        if hasattr(flowable, "_toc_text"):
            text = flowable._toc_text
            level = getattr(flowable, "_toc_level", 0)
            self.notify("TOCEntry", (level, text, self.page))


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------


def build_title_page(story: list):
    # Spacer + university + department
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("National University of Technology", TP_UNI))
    story.append(Paragraph("Department of Artificial Intelligence", TP_DEPT))

    # Logo
    if LOGO_PATH.exists():
        img = rl_utils.ImageReader(str(LOGO_PATH))
        iw, ih = img.getSize()
        target_w = 1.7 * inch
        scale = target_w / iw
        story.append(Spacer(1, 0.2 * inch))
        story.append(Image(str(LOGO_PATH), width=iw * scale, height=ih * scale, hAlign="CENTER"))
        story.append(Spacer(1, 0.25 * inch))

    # Project label + title
    story.append(Paragraph("Semester Project", TP_PROJECT))
    story.append(Paragraph(
        "Agent-Based Modeling of Adaptive Water Extraction Strategies<br/>"
        "Using Q-Learning Under Climate Stress Scenarios",
        TP_SUBTITLE,
    ))
    story.append(Spacer(1, 0.25 * inch))

    # Group members box
    member_data = [
        ["Sr.", "Name"],
        ["01", "Saqlain Abbas"],
        ["02", "Aleena Tahir"],
        ["03", "Aena Habib"],
        ["04", "Eman Asghar"],
        ["05", "Dua Kamal"],
    ]
    members_tbl = Table(member_data, colWidths=[0.7 * inch, 3.6 * inch])
    members_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NUT_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, TINT_DARK]),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, HAIRLINE),
    ]))
    # Wrap member table + course info in a single bordered card.
    course_data = [
        ["Course:",     "Agent-Based Modeling"],
        ["Instructor:", "Ms. Sumera Aslam"],
        ["Batch:",      "AI-23"],
    ]
    course_tbl = Table(course_data, colWidths=[1.2 * inch, 3.1 * inch])
    course_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    # Composite outer table for the bordered card look.
    card = Table([
        [Paragraph("<b>Group Members</b>", ParagraphStyle("CardHeader", parent=BODY,
                                                          alignment=TA_CENTER,
                                                          fontName="Times-Bold",
                                                          fontSize=13, leading=16,
                                                          textColor=NUT_DARK))],
        [members_tbl],
        [Spacer(1, 0.1 * inch)],
        [course_tbl],
    ], colWidths=[4.4 * inch])
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.0, NUT_DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(card)

    # Date is drawn directly by _title_decorations so it never overflows.


def build_toc(story: list):
    story.append(Paragraph("Table of Contents", SECTION))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC0", parent=BODY, fontName="Times-Bold",
                       fontSize=11.5, leading=18, leftIndent=0, rightIndent=20,
                       textColor=INK),
        ParagraphStyle("TOC1", parent=BODY, fontName="Times-Roman",
                       fontSize=11, leading=16, leftIndent=24, rightIndent=20,
                       textColor=INK),
    ]
    story.append(toc)


def build_abstract(story: list):
    story.append(Paragraph("Abstract", ABSTRACT_HEADER))
    para(
        "Water scarcity is one of the defining challenges of the 21st century, and the "
        "classic &ldquo;tragedy of the commons&rdquo; makes shared irrigation systems "
        "particularly vulnerable. Existing agent-based models of water commons typically "
        "assign fixed behavioral rules to agents, ignoring the way real farming communities "
        "<i>learn</i> and adapt. This project develops a Mesa-based agent-based model in "
        "which each irrigator is a tabular Q-learning agent extracting water from a shared "
        "resource with logistic regeneration. We test whether sustainable extraction can "
        "emerge from decentralized learning, how learned strategies respond to four climate "
        "scenarios (stable, gradual decline, drought shock, stochastic), and how monitoring "
        "intensity affects the emergence of cooperation.",
        story,
    )
    para(
        "Three findings emerge: <b>(i)</b> decentralized Q-learners without enforcement "
        "reproduce the tragedy of the commons in every climate scenario; <b>(ii)</b> a "
        "moderate monitoring probability (p_detect &asymp; 0.3) is sufficient to flip the "
        "population into a cooperative equilibrium <b>under stable climate</b> (mean final "
        "water rises from 5 to 685 units of K=1000); but <b>(iii)</b> under any environmental "
        "stress the <i>same</i> enforcement intensity fails to prevent collapse, even when "
        "raised to p_detect = 0.9. The mechanism is structural: agents&rsquo; discretized "
        "action space is calibrated to baseline climate, so during drought even the &ldquo;fair "
        "share&rdquo; action is over-extraction. This implies real-world regulators cannot "
        "enforce fixed quotas under climate change; <i>climate-adaptive</i> quotas are required.",
        story,
    )


def build_introduction(story: list):
    section("1", "Introduction", story)
    para(
        "Agricultural communities worldwide depend on shared rivers, canals, and aquifers. "
        "When N farmers draw from the same source, each faces the fundamental commons "
        "dilemma: extracting more is privately rational in the short term but collectively "
        "catastrophic. Hardin (1968) formalised this as the Tragedy of the Commons. Under "
        "climate change &mdash; with shifting rainfall, prolonged droughts, and reduced natural "
        "regeneration &mdash; the dilemma is sharper than ever. Pakistan&rsquo;s Indus Basin, "
        "which supports over 90% of the country&rsquo;s agriculture, is classified as one of "
        "the world&rsquo;s most water-stressed basins. According to the UN World Water "
        "Development Report, nearly half of the global population will live in areas of high "
        "water stress by 2030.",
        story,
    )
    para(
        "Traditional models of the commons assume either perfectly rational agents (game "
        "theory) or fixed behavioural types (cooperate / defect / tit-for-tat). Neither "
        "captures the <i>learning</i> process through which real communities discover "
        "sustainable norms. This project equips each irrigator with an independent tabular "
        "Q-learning algorithm and tests whether sustainable extraction emerges, and how it "
        "responds to climate stress.",
        story,
    )

    subsection("1.1", "Research Question", story)
    para(
        "<b>Primary:</b> <i>How does the discount factor (gamma) in Q-learning agents affect "
        "the emergence of sustainable water extraction strategies under varying climate "
        "stress scenarios in an agent-based commons model?</i>",
        story, style=QUOTE,
    )
    para("<b>Sub-questions:</b>", story, style=BODY_LEFT)
    bullets([
        "Can Q-learning agents discover cooperative extraction strategies without external enforcement?",
        "How do learned strategies break down under sudden climate shocks, and how quickly do agents re-adapt?",
        "At what monitoring intensity do enforcement mechanisms become unnecessary because agents have learned self-regulation?",
    ], story)

    subsection("1.2", "Why Agent-Based Modeling", story)
    para(
        "ABM is uniquely suited to this problem because (a) the agents are <i>heterogeneous</i> "
        "&mdash; different farmers, different Q-tables, different luck of monitoring; "
        "(b) interactions are <i>local</i> via the social network and the shared resource; "
        "(c) the system exhibits <i>emergent</i> macro behavior that is not analytically "
        "tractable; and (d) we explicitly want to model <i>adaptive</i> learning, which "
        "equation-based or game-theoretic approaches cannot represent.",
        story,
    )


def build_literature(story: list):
    section("2", "Literature Review", story)
    para("We review four papers that bracket the problem space.", story)

    subsection("2.1", "Perolat et al. (2017) — NeurIPS", story)
    para(
        "Studied independently learning deep RL agents in a common-pool resource game on a "
        "2D grid. Found that when the resource was scarce, agents learned aggressive "
        "appropriation and a &ldquo;tagging&rdquo; punishment mechanism; with abundance, "
        "cooperative harvesting emerged. Establishes the feasibility of using RL agents to "
        "study commons dilemmas. Limitations: deep RL in an abstract grid environment "
        "without water-specific dynamics or climate stress.",
        story,
    )

    subsection("2.2", "Darbandsari et al. (2020) — Sustainable Cities and Society", story)
    para(
        "Presented a Stackelberg-game ABM for urban water management in Tehran, with "
        "heterogeneous stakeholders (municipal users, agricultural users, environmental "
        "agencies). Hierarchical governance with a regulatory leader steered stakeholders "
        "toward more equitable allocation. Used <i>fixed</i> game-theoretic strategies "
        "rather than adaptive learning.",
        story,
    )

    subsection("2.3", "Huber et al. (2019) — Sustainability (MDPI)", story)
    para(
        "Introduced <i>Aqua.MORE</i>, a NetLogo-based platform for coupled human&mdash;water "
        "systems at the catchment scale, applied to an Alpine catchment. Provides a "
        "validated example of water-resource ABM, including realistic regeneration dynamics, "
        "but with rule-based (non-learning) agents.",
        story,
    )

    subsection("2.4", "Weitz et al. (2016) — PNAS", story)
    para(
        "Proposed a coevolutionary game-theory framework where environment and agent "
        "strategies evolve together. Showed that overuse changes the environment, which in "
        "turn changes the incentive structure, leading to <i>oscillatory</i> dynamics. "
        "Provides the theoretical foundation for the climate-shock dynamics we expect to "
        "observe.",
        story,
    )

    subsection("2.5", "Comparative Synthesis", story)
    tbl = maketable([
        ["Aspect", "Perolat et al.", "Darbandsari et al.", "Huber et al.", "Weitz et al."],
        ["Agent type", "Deep RL (A3C)", "Game-theoretic", "Water users / mgrs", "Evolutionary"],
        ["Learning", "Yes (deep RL)", "No (fixed)", "No (rule-based)", "Replicator dyn."],
        ["Resource", "Abstract apples", "Urban water", "Catchment water", "Abstract commons"],
        ["Climate stress", "Not modeled", "Not modeled", "Scenario-based", "Env. feedback"],
        ["Tool", "Custom grid", "MATLAB / custom", "NetLogo", "Math (ODEs)"],
    ], col_widths=[1.0 * inch, 1.2 * inch, 1.4 * inch, 1.25 * inch, 1.2 * inch],
       first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 1. Comparative analysis of reviewed literature.", CAPTION))

    subsection("2.6", "Research Gap", story)
    para(
        "None of the reviewed models combine <i>tabular Q-learning agents</i> with "
        "<i>water-specific resource dynamics</i> under <i>explicit climate stress scenarios</i>. "
        "This project fills that gap with a transparent, interpretable Python/Mesa "
        "implementation.",
        story,
    )


def build_odd(story: list):
    section("3", "ODD Protocol", story)
    para(
        "This section follows the ODD (Overview, Design Concepts, Details) standard of "
        "Grimm et al. (2020) for full reproducibility.",
        story,
    )

    subsection("3.1", "Overview", story)

    story.append(Paragraph("3.1.1 Purpose and Patterns", SUBSUBSECTION))
    para(
        "The purpose of the model is to investigate how Q-learning agents discover "
        "extraction strategies for a shared water resource under climate stress, and at "
        "what monitoring intensity decentralised self-regulation becomes sufficient. The "
        "model is designed to reproduce three patterns documented in the literature: "
        "(i) tragedy of the commons under unmonitored extraction (Hardin 1968); "
        "(ii) scarcity-driven aggression and abundance-driven cooperation (Perolat et al. "
        "2017); and (iii) oscillatory dynamics under environmental shock (Weitz et al. 2016).",
        story,
    )

    story.append(Paragraph("3.1.2 Entities, State Variables, and Scales", SUBSUBSECTION))
    tbl = maketable([
        ["Entity", "State variables"],
        ["Irrigator agent", "q_table, cumulative_payoff, last_action_idx, last_extraction, fines_paid, strategy_type"],
        ["Water resource", "level, carrying_capacity, regeneration_rate, baseline_inflow, history"],
        ["Monitor agent", "p_detect, fine_factor, n_detections, total_fines_issued"],
        ["Climate scenario", "name, scenario-specific parameters (e.g., shock_start, mean_cf)"],
    ], col_widths=[1.5 * inch, 5.5 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 2. Entities and their state variables.", CAPTION))
    para(
        "<b>Spatial scale:</b> 20 &times; 20 grid; one column reserved as visual river; "
        "farmers occupy farmland cells. <b>Temporal scale:</b> one step &approx; one "
        "irrigation season; default run length 500 steps (&approx;125 years if mapped to "
        "quarterly seasons).",
        story,
    )

    story.append(Paragraph("3.1.3 Process Overview and Scheduling", SUBSUBSECTION))
    para("Each simulation step proceeds in three stages enforced by WaterCommonsModel.step():", story)
    bullets([
        "<b>Stage 1 (Act).</b> Each irrigator observes the current state and selects an action (extraction level); requests are pooled at the resource.",
        "<b>Stage 1.5 (Monitor).</b> The water authority probabilistically detects over-extractors and issues fines.",
        "<b>Stage 2 (Regenerate).</b> The water resource grows logistically (modulated by the climate factor) and receives baseline inflow; accumulated extraction is subtracted.",
        "<b>Stage 3 (Finalize).</b> Each irrigator computes its reward from the post-regen water state and updates its Q-table.",
    ], story)
    para(
        "Agent activation order within each stage is randomised "
        "(mesa.time.RandomActivation) so no agent has structural priority.",
        story,
    )

    subsection("3.2", "Design Concepts", story)
    tbl = maketable([
        ["Concept", "Implementation"],
        ["Basic principles", "Tragedy of the commons (Hardin 1968); Q-learning (Watkins & Dayan 1992); logistic resource dynamics."],
        ["Emergence", "Cooperation or collapse is not programmed; it emerges from the collective interaction of learning agents."],
        ["Adaptation", "Q-learners update Q-values via Bellman after every transition; epsilon decays exponentially."],
        ["Objectives", "Each agent maximises expected discounted reward: log-utility of extraction − sustainability penalty − fines."],
        ["Learning", "Tabular Q-learning with epsilon-greedy exploration. Fixed-strategy agents act as comparators."],
        ["Prediction", "Agents do not explicitly predict the future; gamma encodes future-value weighting."],
        ["Sensing", "Global water level, own previous action, average neighbour action, binary climate-stress flag."],
        ["Interaction", "Indirect through the shared resource; direct through the social network; mediated by the monitor."],
        ["Stochasticity", "Initial Q-table noise; epsilon-greedy actions; random social network; stochastic climate; monitor detection."],
        ["Collectives", "The set of irrigators sharing the resource; cooperation index and Gini are population-level summaries."],
        ["Observation", "DataCollector records 13 model-level and 6 agent-level variables every step; exported to CSV."],
    ], col_widths=[1.4 * inch, 5.6 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 3. ODD design concepts and their implementation.", CAPTION))

    subsection("3.3", "Details", story)
    story.append(Paragraph("3.3.1 Initialization", SUBSUBSECTION))
    tbl = maketable([
        ["Parameter", "Default", "Reference"],
        ["n_farmers", "20", "Mid-range of proposal (5–100)"],
        ["carrying_capacity (K)", "1000.0", "Normalised units; MSY = rK/4 = 25"],
        ["regeneration_rate (r)", "0.10", "Mid-range of proposal (0.01–0.3)"],
        ["baseline_inflow", "5.0", "Prevents permanent collapse from a single early shock"],
        ["initial_water_fraction", "0.80", "Healthy starting state"],
        ["max_extraction", "auto-scaled", "So action 2 = per-agent fair share of (MSY + baseline)"],
        ["alpha", "0.15", "Standard Q-learning"],
        ["gamma", "0.95", "Mid-range of proposal (0.5–0.99)"],
        ["epsilon_0", "0.30", "Lower than 1.0 to prevent initial-exploration collapse"],
        ["decay_rate", "0.010", "Exploration → exploitation by step ≈ 300"],
        ["sustainability_penalty", "2.0", "Quadratic in water scarcity"],
        ["social_degree (k)", "4", "Random k-regular graph"],
        ["p_detect", "0.0 or 0.30", "Compared empirically"],
        ["fine_factor", "3.0", "Scale of fine per unit excess extraction"],
        ["Climate scenario", "stable", "{stable, gradual, shock, stochastic}"],
    ], col_widths=[1.7 * inch, 1.2 * inch, 4.1 * inch])
    story.append(tbl)
    story.append(Paragraph("Table 4. Initialization parameters.", CAPTION))
    para(
        "Initial water level = initial_water_fraction &times; K = 800. Initial Q-tables are "
        "empty and lazy-initialised on first state visit with small uniform noise in "
        "[&minus;0.01, 0.01]. Initial agent positions are uniformly random over farmland "
        "cells.",
        story,
    )

    story.append(Paragraph("3.3.2 Input Data", SUBSUBSECTION))
    para(
        "No external time-series inputs. The climate factor c_f(t) is generated endogenously "
        "by the chosen scenario class. For validation we compare emergent dynamics "
        "qualitatively to FAO AQUASTAT recharge-rate statistics and the 2022 Indus Basin "
        "drought.",
        story,
    )

    story.append(Paragraph("3.3.3 Submodels", SUBSUBSECTION))
    para("<b>Water resource dynamics:</b>", story, style=BODY_LEFT)
    para("W(t+1) = max(0, min(K, W(t) + r &middot; c_f(t) &middot; W(t) &middot; (1 &minus; W(t)/K) "
         "+ b &middot; c_f(t) &minus; &Sigma;<sub>i</sub> e_i(t)))",
         story, style=QUOTE)
    para("<b>Q-learning update (Watkins & Dayan, 1992):</b>", story, style=BODY_LEFT)
    para("Q(s, a) &larr; Q(s, a) + &alpha; &middot; [ r + &gamma; &middot; max<sub>a&prime;</sub> Q(s&prime;, a&prime;) &minus; Q(s, a) ]",
         story, style=QUOTE)
    para(
        "The state s = (water_bin, own_last_action, neighbors_avg_bin, climate_stressed). "
        "Actions a &in; {0, 1, 2, 3, 4} map to extraction fractions {0, 0.25, 0.5, 0.75, 1.0} "
        "&times; max_extraction. <b>&epsilon;-greedy with exponential decay:</b> "
        "&epsilon;_t = max(&epsilon;_min, &epsilon;_0 &middot; exp(&minus;d &middot; t)).",
        story,
    )
    para("<b>Reward:</b> r = log(1 + extracted) &minus; sustainability_penalty &middot; (1 &minus; W/K)<sup>2</sup> &minus; fine.", story)
    para(
        "<b>Monitor:</b> for each agent with action &gt; 2, with probability p_detect a "
        "fine of (action_level &minus; 0.5) &middot; max_extraction &middot; fine_factor is "
        "deducted from that step&rsquo;s reward and propagated into the Q-update.",
        story,
    )
    para("<b>Climate scenarios:</b>", story, style=BODY_LEFT)
    bullets([
        "<b>Stable:</b> c_f = 1.0 for all t.",
        "<b>Gradual:</b> c_f declines linearly from 1.0 to 0.5 over 400 steps.",
        "<b>Shock:</b> c_f = 1.0 normally; drops to 0.3 for steps [200, 300).",
        "<b>Stochastic:</b> c_f ~ N(0.85, 0.15²) clipped to [0.3, 1.0], deterministic per (seed, t).",
    ], story)


def build_methods(story: list):
    section("4", "Implementation and Methods", story)

    subsection("4.1", "Tool Choice and Project Structure", story)
    para(
        "The model is implemented in Python 3.12 using Mesa 2.3.4 for the agent-based-model "
        "framework, NetworkX for the social network, NumPy for the Q-tables, and Matplotlib "
        "for analysis. The codebase is laid out as:",
        story,
    )
    para(
        "water_abm/<br/>"
        "&nbsp;&nbsp;q_learning.py    -- tabular Q-learner with epsilon-greedy + Bellman update<br/>"
        "&nbsp;&nbsp;climate.py       -- four climate scenario classes<br/>"
        "&nbsp;&nbsp;environment.py   -- shared water resource (logistic + baseline regen)<br/>"
        "&nbsp;&nbsp;agents.py        -- irrigator (Q-learner + 3 fixed variants) + monitor<br/>"
        "&nbsp;&nbsp;model.py         -- Mesa Model, DataCollector, CSV export<br/>"
        "&nbsp;&nbsp;server.py        -- Mesa visualization (grid + 9 sliders + 3 charts)<br/>"
        "experiments/<br/>"
        "&nbsp;&nbsp;batch_run.py        -- 340-run batch experiment<br/>"
        "&nbsp;&nbsp;sensitivity.py      -- &plusmn;20% parameter sweeps<br/>"
        "&nbsp;&nbsp;validate.py         -- three checks vs literature<br/>"
        "&nbsp;&nbsp;analyze.py          -- generates all report figures<br/>"
        "&nbsp;&nbsp;demo_screenshots.py -- pre/during/post-shock grid screenshots",
        story, style=CODE,
    )
    para(
        "The interactive simulation launches with <b>python run.py</b>, opening a browser UI "
        "at http://127.0.0.1:8521 with 9 sliders, 1 dropdown, 3 live charts, and a spatial grid.",
        story,
    )

    subsection("4.2", "Technical Requirements (PBL Section 4)", story)
    para(
        "This section explicitly maps the project to each requirement listed in the PBL document.",
        story,
    )
    para("<b>4.1 Minimum agent requirements.</b>", story, style=BODY_LEFT)
    para(
        "The model contains two distinct agent types: IrrigatorAgent (four behavioural "
        "variants &mdash; Q-learner, always-cooperate, always-defect, tit-for-tat) and "
        "MonitorAgent. Each irrigator has internal state variables (q_table, "
        "cumulative_payoff, last_action_idx, fines_paid); at least two behavioural rules "
        "(observe-decide-extract and learn-via-Bellman); and is heterogeneous &mdash; each "
        "agent has its own random seed and Q-table noise.",
        story,
    )
    para("<b>4.2 Environment requirements.</b>", story, style=BODY_LEFT)
    para(
        "The environment is a Mesa MultiGrid of 20 &times; 20 cells (river column + "
        "farmland) coupled to a shared water resource whose level evolves over time. Agents "
        "observe their local neighbourhood through a NetworkX random k-regular graph (default "
        "k = 4).",
        story,
    )
    para("<b>4.3 Simulation controls (interface).</b>", story, style=BODY_LEFT)
    para(
        "The Mesa visualization exposes 9 sliders (n_farmers, alpha, gamma, epsilon_0, r, "
        "p_detect, social_degree, seed, Q-learner proportion), 1 dropdown (climate scenario), "
        "3 live charts (water level, cooperation index, payoff + Gini), Setup/Step/Run "
        "buttons, and a speed slider. Exceeds the PBL minimum of &ge;4 sliders, &ge;2 plots, "
        "&ge;2 monitors.",
        story,
    )
    para("<b>4.4 Emergent behaviour demonstration.</b>", story, style=BODY_LEFT)
    para(
        "Three emergent phenomena are documented: (i) resource collapse from decentralized "
        "over-extraction (the tragedy); (ii) sharp action-distribution shift toward cooperation "
        "when p_detect exceeds &asymp; 0.2; (iii) climate-shock-induced collapse even under "
        "enforcement. Pre/during/post-shock grid screenshots are shown in section 5.6.",
        story,
    )
    para("<b>4.5 Validation and calibration.</b>", story, style=BODY_LEFT)
    para(
        "Section 6 documents three structured validation checks against published literature "
        "(Hardin 1968, Perolat et al. 2017, Indus Basin 2022). Section 6.3 reports &plusmn;20% "
        "sensitivity analyses for six headline parameters.",
        story,
    )

    subsection("4.3", "Experimental Design", story)
    tbl = maketable([
        ["Experiment", "Variables", "Runs"],
        ["A. Tragedy baseline", "4 climates × 30 seeds, no monitor", "120"],
        ["B. With enforcement", "4 climates × 30 seeds, p_detect = 0.3", "120"],
        ["C. Gamma sweep (primary RQ)", "2 climates × 5 gamma values × 10 seeds", "100"],
    ], col_widths=[2.4 * inch, 3.6 * inch, 0.8 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 5. Batch experimental design. Each run is 500 steps; metrics recorded every 10 steps. Total simulation steps: 170,000.", CAPTION))
    para(
        "The sensitivity study perturbs each of {alpha, gamma, epsilon_0, r, p_detect, N} "
        "by &plusmn;20% around the baseline, holding others fixed, with 10 seeds per setting.",
        story,
    )


def build_results(story: list):
    section("5", "Results", story)

    subsection("5.1", "Tragedy Baseline (Experiment A)", story)
    para(
        "Without enforcement, the water resource collapses within ~80 steps in <b>every</b> "
        "climate scenario (Figure 1, dashed lines).",
        story,
    )
    tbl = maketable([
        ["Climate", "Final water", "Mean cumulative payoff per agent"],
        ["stable",     "5.55 ± 0.0", "-755.9"],
        ["gradual",    "2.63 ± 0.0", "-795.2"],
        ["shock",      "5.55 ± 0.0", "-768.0"],
        ["stochastic", "5.44 ± 0.0", "-803.9"],
    ], col_widths=[1.5 * inch, 1.7 * inch, 3.2 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 6. Experiment A: tragedy baseline (n = 30 seeds per scenario).", CAPTION))
    para(
        "The standard deviation across seeds is effectively zero: the model converges "
        "deterministically on a low-water attractor where extraction equals baseline inflow. "
        "All scenarios produce strongly negative mean payoffs (&minus;750 to &minus;800 per "
        "agent), reproducing the classical tragedy of the commons.",
        story,
    )
    story.extend(fig("fig01_water_by_scenario.png", width_frac=0.90,
                     caption="Water level over time, tragedy baseline (dashed) vs. moderate enforcement (solid). Shaded bands show ±1 s.d. over 30 seeds."))

    subsection("5.2", "Enforcement Saves the Stable Climate (Experiment B)", story)
    para(
        "With p_detect = 0.3 and fine_factor = 3.0, the dynamics flip under the stable "
        "climate. Mean final water rises from 5.5 to 684.8 (125&times; improvement), payoff "
        "turns positive (+222.5), and 86% of agents pick cooperative actions.",
        story,
    )
    tbl = maketable([
        ["Climate", "Final water", "Mean payoff", "% coop", "% defect"],
        ["stable",     "684.8 ± 33.5",  "+222.5",  "86%", "14%"],
        ["gradual",    "2.6 ± 0.0",     "-576.8",  "68%", "32%"],
        ["shock",      "5.6 ± 0.0",     "-528.2",  "68%", "32%"],
        ["stochastic", "26.6 ± 116.0",  "-842.2",  "70%", "30%"],
    ], col_widths=[1.3 * inch, 1.4 * inch, 1.3 * inch, 1.0 * inch, 1.0 * inch],
       first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 7. Experiment B: with enforcement (p_detect = 0.3, n = 30 seeds).", CAPTION))
    story.extend(fig("fig02_enforcement_effect.png", width_frac=0.90,
                     caption="Final water level (left) and cooperation index (right) by climate scenario × enforcement."))
    story.extend(fig("fig06_action_distribution.png", width_frac=0.80,
                     caption="Final fraction of cooperative vs. defecting actions, by scenario (with enforcement)."))

    subsection("5.3", "Why Enforcement Fails Under Stress", story)
    para(
        "Under gradual / shock / stochastic scenarios, the same enforcement intensity is "
        "<b>insufficient</b>. Notably, 68%-70% of agents are still choosing cooperative "
        "actions in failing scenarios &mdash; they aren&rsquo;t selfishly defecting; the "
        "cooperative action itself is too aggressive for the reduced regeneration.",
        story,
    )
    tbl = maketable([
        ["p_detect", "stable: final water", "shock: final water"],
        ["0.3", "700", "5.6 (collapsed)"],
        ["0.6", "777", "5.6 (collapsed)"],
        ["0.9", "787", "5.6 (collapsed)"],
    ], col_widths=[1.6 * inch, 2.6 * inch, 2.6 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 8. Even near-perfect enforcement (p_detect = 0.9) cannot rescue the shock scenario.", CAPTION))
    para(
        "The reason is structural: the per-agent fair-share action is calibrated to baseline "
        "(c_f = 1.0) sustainability. When c_f drops to 0.3 during a shock, the same "
        "fair-share extraction is over-extraction relative to the reduced regeneration. The "
        "Q-learners&rsquo; discretised action space cannot scale finely enough with c_f. "
        "This is a substantive finding for water-policy practice: enforcing fixed quotas "
        "works under normal conditions, but climate stress requires <i>adaptive</i> quotas "
        "that contract with regeneration.",
        story,
    )

    subsection("5.4", "Discount Factor (Primary RQ, Experiment C)", story)
    tbl = maketable([
        ["gamma", "stable: final water", "shock: final water"],
        ["0.50", "748.3 ± 18.9", "5.55 ± 0.0"],
        ["0.70", "722.6 ± 28.3", "5.55 ± 0.0"],
        ["0.85", "703.5 ± 28.7", "5.55 ± 0.0"],
        ["0.95", "700.8 ± 34.9", "5.55 ± 0.0"],
        ["0.99", "688.3 ± 28.1", "5.55 ± 0.0"],
    ], col_widths=[1.2 * inch, 2.4 * inch, 2.4 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 9. Effect of discount factor gamma on final water level.", CAPTION))
    story.extend(fig("fig03_gamma_sweep.png", width_frac=0.90,
                     caption="Primary RQ: effect of discount factor on sustainable extraction."))
    para(
        "Two unexpected results: <b>(i)</b> under stable climate, water is mildly "
        "<i>decreasing</i> with gamma (lower-gamma agents end up with more water); "
        "<b>(ii)</b> under shock, gamma has no measurable effect &mdash; all gamma values "
        "collapse to identical final water. This refines the answer to the primary RQ: gamma "
        "matters at the margins under stable conditions, but the dominant determinant of "
        "resilience under stress is whether the action space can adapt to changing "
        "regeneration &mdash; not how much agents discount the future.",
        story,
    )

    subsection("5.5", "Inequality", story)
    para(
        "Figure below tracks the Gini coefficient of cumulative payoff over time, with "
        "enforcement on. Inequality rises quickly (~0.30 by step 100) and then plateaus. "
        "Stable and stochastic scenarios show a partial <i>decline</i> in Gini after step "
        "230, consistent with the oscillatory dynamics predicted in Weitz et al. (2016).",
        story,
    )
    story.extend(fig("fig05_gini_evolution.png", width_frac=0.85,
                     caption="Payoff inequality (Gini) over time, with enforcement."))

    subsection("5.6", "Emergent Spatial Dynamics", story)
    para(
        "Three snapshots from a shock-scenario run with enforcement. The river column "
        "shading reflects current water level; agent size scales with extraction level; the "
        "monitor is marked as a black star.",
        story,
    )
    # Three small images side by side
    story.extend(fig("fig08_grid_pre_shock.png", width_frac=0.7,
                     caption="Step 199: pre-shock cooperation. River is full, most agents picking cooperative actions.",
                     max_h_inch=3.5))
    story.extend(fig("fig09_grid_during_shock.png", width_frac=0.7,
                     caption="Step 260: mid-shock pressure. Climate factor drops; water level falls rapidly.",
                     max_h_inch=3.5))
    story.extend(fig("fig10_grid_recovery.png", width_frac=0.7,
                     caption="Step 450: post-shock low-water equilibrium.",
                     max_h_inch=3.5))


def build_validation(story: list):
    section("6", "Validation and Calibration", story)
    para(
        "Three structured validation checks are run automatically in "
        "experiments/validate.py, with the figure saved as fig07_validation.png and full "
        "numbers in data/results/validation.json. All three pass.",
        story,
    )
    tbl = maketable([
        ["Check", "Source", "Test", "Result"],
        ["1. Tragedy",
         "Hardin (1968)",
         "Without enforcement water should collapse (<50); with enforcement under stable climate it should sustain (>200).",
         "PASS — 5.6 vs 504"],
        ["2. Scarcity → aggression",
         "Perolat et al. (2017)",
         "Fraction of defecting actions during steps 200–300 should be higher under shock than under stable (both with enforcement).",
         "PASS — 25.3% vs 36.5%"],
        ["3. Shock signal",
         "Indus Basin 2022",
         "A drought cutting c_f by ~70% should leave a measurable dip in mean water level at step 300.",
         "PASS — 507 vs 1.5"],
    ], col_widths=[1.4 * inch, 1.4 * inch, 3.0 * inch, 1.2 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 10. Three structured validation checks.", CAPTION))
    story.extend(fig("fig07_validation.png", width_frac=0.95,
                     caption="Validation: three sanity checks against literature."))

    subsection("6.1", "External Calibration Benchmarks", story)
    bullets([
        "<b>FAO AQUASTAT</b> indicates natural aquifer recharge rates of 5%-15% of carrying capacity per year — brackets our default r = 0.10.",
        "The <b>2022 Indus Basin drought</b> reduced river flow by ~50%-70% at peak — matched by our shock_cf = 0.3 choice.",
        "<b>Perolat et al. (2017)</b>'s finding that scarcity drives aggressive appropriation is reproduced with the 44% increase in defection during the shock window.",
    ], story)

    subsection("6.2", "Sensitivity Analysis", story)
    tbl = maketable([
        ["Parameter", "-20% Δwater", "+20% Δwater"],
        ["p_detect",       "-39.4", "+37.6"],
        ["epsilon_0",      "-11.0", "-28.6"],
        ["N (n_farmers)",  "+16.9", "-25.7"],
        ["gamma",          "+22.0", "-12.4"],
        ["r (regen rate)", "-19.0", "-10.8"],
        ["alpha",          "-13.8",  "-2.4"],
    ], col_widths=[2.2 * inch, 1.8 * inch, 1.8 * inch], first_col_bold=True)
    story.append(tbl)
    story.append(Paragraph("Table 11. Sensitivity to ±20% parameter perturbations (10 seeds each).", CAPTION))
    story.extend(fig("fig04_sensitivity_tornado.png", width_frac=0.85,
                     caption="Sensitivity tornado: change in final water level under ±20% perturbations."))
    para(
        "Two patterns: (a) p_detect dominates &mdash; the largest signed range "
        "(&plusmn;38-40 units); (b) epsilon_0 and alpha are non-monotonic, with negative "
        "deltas in both directions, suggesting the baseline value is near a local optimum.",
        story,
    )


def build_discussion(story: list):
    section("7", "Discussion", story)
    subsection("7.1", "Answers to Research Questions", story)
    bullets([
        "<b>Sub-Q1 (cooperation without enforcement):</b> No. Pure Q-learners cannot escape the tragedy under any climate scenario. Each agent's action contributes only ~1/N of total extraction, so unilateral restraint produces no observable benefit. Matches Perolat et al. (2017).",
        "<b>Sub-Q2 (recovery from shock):</b> No, not within the 500-step horizon. Once the resource crashes during a shock, the system is trapped in a low-water attractor where all actions yield essentially the same reward, providing no gradient for relearning.",
        "<b>Sub-Q3 (monitoring threshold under stable climate):</b> Approximately p_detect = 0.2-0.3 flips the outcome from collapse to cooperation; returns saturate above 0.6. Under stress, no enforcement intensity tested (up to 0.9) is sufficient.",
        "<b>Primary RQ:</b> Gamma has minor effect under stable climate and limited effect under shock. The dominant determinant of resilience is whether the action space can contract with falling regeneration, not how much agents discount the future.",
    ], story)

    subsection("7.2", "Limitations", story)
    bullets([
        "<b>Fixed discretised action space.</b> The 5-level extraction grid is calibrated to baseline climate. A continuous or adaptive action space could scale extraction with current regeneration.",
        "<b>Static fair-share definition.</b> The monitor's fair-share threshold is fixed. A climate-aware monitor would tighten this during low-c_f periods.",
        "<b>Tabular Q-learning</b> limits state granularity. Deep RL could capture finer patterns at the cost of interpretability.",
        "<b>Single resource</b> — no spatial heterogeneity in water availability.",
        "<b>No agent heterogeneity in risk-aversion or wealth.</b>",
        "<b>500-step horizon</b> corresponds to ~125 years if one step is one season; longer horizons may show further structural shifts.",
        "<b>Exogenous monitor.</b> A richer model would let monitoring intensity evolve endogenously.",
    ], story)


def build_conclusion(story: list):
    section("8", "Conclusion", story)
    para(
        "This project shows that tabular Q-learning agents in a water commons reproduce the "
        "tragedy when left alone but can flip into cooperation under a modest external "
        "monitoring regime &mdash; in a stable climate. The headline contribution, however, "
        "is the negative result under climate stress: even near-perfect enforcement "
        "(p_detect = 0.9) cannot prevent collapse when the shock dynamics outpace the "
        "agents&rsquo; fixed-quota action space. The discount factor gamma matters most "
        "when the environment is stable, not when it is stressed. The interactive Mesa "
        "visualization makes the dynamics inspectable in real time, and the batch and "
        "sensitivity infrastructure makes the findings reproducible. Future work should "
        "explore continuous action spaces, climate-adaptive enforcement thresholds, and "
        "comparison with human commons experiments.",
        story,
    )


def build_references(story: list):
    story.append(Paragraph("References", SECTION))
    refs = [
        "Darbandsari, P., Kerachian, R., Malakpour-Estalaki, S., & Khorasani, H. (2020). An agent-based conflict resolution model for urban water resources management. <i>Sustainable Cities and Society</i>, 57, 102112.",
        "Grimm, V., Railsback, S. F., Vincenot, C. E., Berger, U., Gallagher, C., DeAngelis, D. L., et al. (2020). The ODD protocol for describing agent-based and other simulation models: A second update to improve clarity, replication, and structural realism. <i>Ecological Modelling</i>, 428.",
        "Hardin, G. (1968). The Tragedy of the Commons. <i>Science</i>, 162(3859), 1243-1248.",
        "Huber, L., Bahro, N., Leitinger, G., Tappeiner, U., & Strasser, U. (2019). Agent-Based Modelling of a Coupled Water Demand and Supply System at the Catchment Scale. <i>Sustainability</i>, 11(21), 6178.",
        "Ostrom, E. (1990). <i>Governing the Commons: The Evolution of Institutions for Collective Action</i>. Cambridge University Press.",
        "Perolat, J., Leibo, J.Z., Zambaldi, V., Beattie, C., Tuyls, K., & Graepel, T. (2017). A multi-agent reinforcement learning model of common-pool resource appropriation. <i>NeurIPS 2017</i>.",
        "Watkins, C.J.C.H., & Dayan, P. (1992). Q-Learning. <i>Machine Learning</i>, 8(3-4), 279-292.",
        "Weitz, J.S., Eksin, C., Paarporn, K., Brown, S.P., & Ratcliff, W.C. (2016). An oscillating tragedy of the commons in replicator dynamics with game-environment feedback. <i>PNAS</i>, 113(47), E7518-E7525.",
        "Wilensky, U., & Rand, W. (2015). <i>An Introduction to Agent-Based Modeling: Modeling Natural, Social, and Engineered Complex Systems with NetLogo</i>. MIT Press.",
    ]
    ref_style = ParagraphStyle("Ref", parent=BODY, leftIndent=24, bulletIndent=0, spaceAfter=4)
    for i, ref in enumerate(refs, start=1):
        story.append(Paragraph(f"[{i}] {ref}", ref_style))


def build_appendices(story: list):
    story.append(PageBreak())
    story.append(Paragraph("Appendix A: Parameter Reference", SECTION))
    tbl = maketable([
        ["Symbol", "Default", "Range explored", "Used in"],
        ["N",            "20",          "{16, 20, 24} (sensitivity)",       "Section 4.3"],
        ["alpha",        "0.15",        "{0.12, 0.15, 0.18}",               "Section 6.2"],
        ["gamma",        "0.95",        "{0.50, 0.70, 0.85, 0.95, 0.99}",   "Section 5.4"],
        ["epsilon_0",    "0.30",        "{0.24, 0.30, 0.36}",               "Section 6.2"],
        ["r",            "0.10",        "{0.08, 0.10, 0.12}",               "Section 6.2"],
        ["p_detect",     "0.00 / 0.30", "{0.24, 0.30, 0.36}",               "Section 5.2"],
        ["K",            "1000",        "fixed",                            "—"],
        ["b (baseline)", "5.0",         "fixed",                            "—"],
        ["fine_factor",  "3.0",         "fixed",                            "—"],
    ], col_widths=[1.2 * inch, 1.0 * inch, 2.3 * inch, 1.2 * inch], first_col_bold=True)
    story.append(tbl)

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Appendix B: How to Reproduce", SECTION))
    para(
        "pip install -r requirements.txt<br/>"
        "python -m experiments.batch_run         # ~8 min, writes data/results/batch_*.csv<br/>"
        "python -m experiments.sensitivity       # ~3 min, writes data/results/sensitivity.csv<br/>"
        "python -m experiments.validate          # ~1 min, validation vs literature<br/>"
        "python -m experiments.analyze           # writes figures/fig0*.png<br/>"
        "python -m experiments.demo_screenshots  # writes figures/fig08-10 grid screenshots<br/>"
        "python run.py                           # interactive viz at http://127.0.0.1:8521",
        story, style=CODE,
    )
    para(
        "Source available at "
        "<font color='#006464'>https://github.com/AleenaTahir1/Adaptive-water-extraction</font>.",
        story,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_pdf():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportTemplate(str(OUT_PATH), pagesize=A4,
                          title="Adaptive Water Extraction with Q-Learning",
                          author="Saqlain Abbas, Aleena Tahir, Aena Habib, Eman Asghar, Dua Kamal")
    story: list = []

    # --- Title page (uses 'title' template) -------------------------------
    build_title_page(story)
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # --- TOC -------------------------------------------------------------
    build_toc(story)
    story.append(PageBreak())

    # --- Abstract --------------------------------------------------------
    build_abstract(story)

    # --- Sections --------------------------------------------------------
    build_introduction(story)
    build_literature(story)
    story.append(PageBreak())
    build_odd(story)
    story.append(PageBreak())
    build_methods(story)
    build_results(story)
    story.append(PageBreak())
    build_validation(story)
    build_discussion(story)
    build_conclusion(story)

    # --- Refs + Appendices ----------------------------------------------
    story.append(PageBreak())
    build_references(story)
    build_appendices(story)

    # multiBuild ensures TOC populates correctly (2-pass build).
    doc.multiBuild(story)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    build_pdf()
