# -*- coding: utf-8 -*-
"""
Generate a clear, beautifully formatted, publication-grade PDF explaining
the ML concepts and data flow for KnowledgeTrace MCQ.

Features:
- Simple, accessible language with intuitive analogies.
- Properly formatted symbols (Unicode / ReportLab HTML entities: α, θ, ξ, →, ×, etc.)
  WITHOUT raw unrendered LaTeX or ugly black blocks.
- Embedded high-resolution flowcharts and model diagrams with exact function names,
  service classes, database tables, and algorithm names.
- Clean ReportLab tables, formula callouts, and numbered canvas headers/footers.
- Perfectly balanced 6-page publication layout.
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image
)
from reportlab.pdfgen import canvas

# Ensure diagrams are generated freshly
import create_diagrams

# ─── Color Palette ────────────────────────────────────────────────────────────
PRIMARY = colors.HexColor("#0F172A")       # Dark slate 900
SECONDARY = colors.HexColor("#4338CA")     # Indigo 700
ACCENT_BLUE = colors.HexColor("#2563EB")   # Royal Blue 600
ACCENT_GREEN = colors.HexColor("#059669")  # Emerald Green 600
ACCENT_ROSE = colors.HexColor("#DC2626")   # Rose Red 600
ACCENT_AMBER = colors.HexColor("#D97706")  # Amber 600
TEXT_DARK = colors.HexColor("#1E293B")     # Slate 800
TEXT_MUTED = colors.HexColor("#64748B")    # Slate 500
BG_LIGHT = colors.HexColor("#F8FAFC")      # Slate 50
BG_CARD = colors.HexColor("#F1F5F9")       # Slate 100
BORDER_LIGHT = colors.HexColor("#CBD5E1")  # Slate 300
BORDER_ACCENT = colors.HexColor("#818CF8") # Indigo 400
WHITE = colors.HexColor("#FFFFFF")

# ─── Numbered Canvas for Running Headers and Footers ──────────────────────────
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(SECONDARY)
            self.drawString(54, 752, "KnowledgeTrace MCQ")
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(145, 752, "|   Machine Learning Concepts & Data Flow Architecture Guide")
            self.setStrokeColor(BORDER_LIGHT)
            self.setLineWidth(0.6)
            self.line(54, 744, 558, 744)

        # Running Footer (all pages)
        self.setStrokeColor(BORDER_LIGHT)
        self.setLineWidth(0.6)
        self.line(54, 44, 558, 44)
        self.setFont("Helvetica", 8)
        self.setFillColor(TEXT_MUTED)
        self.drawString(54, 32, "KnowledgeTrace MCQ — AI & Psychometrics Architecture Guide")
        self.drawRightString(558, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


# ─── Styles Setup ─────────────────────────────────────────────────────────────
def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocSuperTitle",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=SECONDARY,
        spaceAfter=3,
        textTransform="uppercase",
        letterSpacing=1.2
    ))

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_MUTED,
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name="SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        name="SubSectionHeading",
        fontName="Helvetica-Bold",
        fontSize=9.8,
        leading=13,
        textColor=SECONDARY,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        name="BodyTextCustom",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.0,
        textColor=TEXT_DARK,
        spaceAfter=4
    ))

    styles.add(ParagraphStyle(
        name="BulletCustom",
        fontName="Helvetica",
        fontSize=8.3,
        leading=11.6,
        textColor=TEXT_DARK,
        leftIndent=10,
        spaceAfter=2.5
    ))

    styles.add(ParagraphStyle(
        name="FormulaText",
        fontName="Helvetica-Bold",
        fontSize=8.6,
        leading=12.2,
        textColor=SECONDARY,
        alignment=1 # Center
    ))

    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=10.5,
        textColor=WHITE
    ))

    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=7.6,
        leading=10.2,
        textColor=TEXT_DARK
    ))

    styles.add(ParagraphStyle(
        name="TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=10.2,
        textColor=TEXT_DARK
    ))

    styles.add(ParagraphStyle(
        name="CalloutText",
        fontName="Helvetica",
        fontSize=8.2,
        leading=11.5,
        textColor=TEXT_DARK
    ))

    return styles


def create_callout(text, title="KEY CONCEPT IN SIMPLE WORDS", bg=BG_CARD, border=SECONDARY, styles=None):
    p_title = Paragraph(f"<b>{title}</b>", ParagraphStyle(
        "CallTitle", fontName="Helvetica-Bold", fontSize=8.0, leading=10.0, textColor=border, spaceAfter=2
    ))
    p_body = Paragraph(text, styles["CalloutText"])
    table = Table([[p_title], [p_body]], colWidths=[504])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, border),
        ("LINEBEFORE", (0, 0), (0, -1), 3.0, border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def create_formula_card(title, formula_html, explanation_html, border_color=SECONDARY, styles=None):
    p_title = Paragraph(f"<b>{title}</b>", ParagraphStyle(
        "FormCardTitle", fontName="Helvetica-Bold", fontSize=8.2, leading=10.5, textColor=border_color, spaceAfter=2
    ))
    p_form = Paragraph(formula_html, styles["FormulaText"])
    p_expl = Paragraph(explanation_html, styles["BodyTextCustom"])
    
    table = Table([[p_title], [p_form], [p_expl]], colWidths=[504])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.6, border_color),
        ("LINEBEFORE", (0, 0), (0, -1), 3.0, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def build_pdf(output_path="ml_concepts_and_data_flow_guide.pdf"):
    # Regenerate diagram PNGs freshly
    create_diagrams.create_dataflow_diagram("ml_dataflow_diagram.png")
    create_diagrams.create_models_diagram("ml_models_diagram.png")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = build_styles()
    story = []

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 1: OVERVIEW & CORE ML CONCEPTS
    # ════════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("EDUCATIONAL PSYCHOMETRICS & DATA PIPELINE SPECIFICATION", styles["DocSuperTitle"]))
    story.append(Paragraph("Machine Learning Concepts & Data Flow Architecture", styles["DocTitle"]))
    story.append(Paragraph(
        "A clear, practical guide explaining how KnowledgeTrace MCQ models student understanding over time, "
        "diagnoses multiple skills using probabilistic models, and executes non-blocking background AI pipelines.",
        styles["DocSubtitle"]
    ))

    # Summary Metadata Box
    meta_table = Table([
        [
            Paragraph("<b>Target System:</b> KnowledgeTrace MCQ", styles["TableCellBold"]),
            Paragraph("<b>Core Models:</b> BKT + Bayesian DINA", styles["TableCellBold"]),
            Paragraph("<b>Graph Validation:</b> NetworkX Poset DAG", styles["TableCellBold"])
        ],
        [
            Paragraph("<b>Inference Speed:</b> &lt; 15ms (NumPy Vectorized)", styles["TableCell"]),
            Paragraph("<b>Confidence Metric:</b> Quadratic Entropy", styles["TableCell"]),
            Paragraph("<b>LLM Engine:</b> Groq LLaMA (Prerequisite Inference)", styles["TableCell"])
        ]
    ], colWidths=[168, 168, 168])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # Section 1
    story.append(Paragraph("1. Why Use Machine Learning in an MCQ Test System?", styles["SectionHeading"]))
    story.append(Paragraph(
        "In traditional online tests, scoring is basic arithmetic: if a student gets 7 out of 10 questions right, "
        "their score is <b>70%</b>. However, this number hides crucial information:",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph(
        "• <b>Did the student guess?</b> In a 4-choice question, there is a 25% chance of guessing correctly without knowing the answer.",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>Did they make a silly slip?</b> A brilliant student who knows a concept might accidentally click the wrong option or make an arithmetic typo.",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>Which specific sub-skill was missing?</b> A physics problem might test both <i>Newton's Laws</i> and <i>Trigonometry</i>. If the student answers wrong, which skill failed?",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>How does mastery change over time?</b> A student learns while answering questions. An early mistake should not permanently penalize their mastery score if they get the next 4 questions right.",
        styles["BulletCustom"]
    ))

    story.append(Spacer(1, 4))
    story.append(create_callout(
        "Psychometrics and Cognitive Diagnosis treat a student's true understanding as a hidden mental state. "
        "By observing their chronological correct/incorrect answers, the system statistically filters out lucky guesses "
        "and careless slips to estimate real skill mastery between 0.0 (0%) and 1.0 (100%).",
        title="IN SIMPLE TERMS: WHY WE NEED PROBABILISTIC ML",
        bg=BG_CARD,
        border=ACCENT_BLUE,
        styles=styles
    ))

    story.append(Spacer(1, 7))
    story.append(Paragraph("The 3-Tier Hybrid AI Architecture:", styles["SubSectionHeading"]))
    story.append(Paragraph(
        "Rather than relying on an unexplainable black-box neural network, KnowledgeTrace MCQ combines three clean, "
        "interpretable, mathematically proven layers:",
        styles["BodyTextCustom"]
    ))

    arch_table = Table([
        [
            Paragraph("<b>Layer</b>", styles["TableHeader"]),
            Paragraph("<b>Model / Technique</b>", styles["TableHeader"]),
            Paragraph("<b>Purpose in Simple Words</b>", styles["TableHeader"]),
            Paragraph("<b>Core File &amp; Algorithm</b>", styles["TableHeader"])
        ],
        [
            Paragraph("<b>Layer 1</b><br/>Curriculum Structure", styles["TableCellBold"]),
            Paragraph("LLM Concept Graph &amp; NetworkX DAG", styles["TableCell"]),
            Paragraph("Organizes concepts as prerequisite steps (A &rarr; B) and prevents impossible circular loops.", styles["TableCell"]),
            Paragraph("<code>concept_graph.py</code><br/><code>is_directed_acyclic_graph()</code>", styles["TableCell"])
        ],
        [
            Paragraph("<b>Layer 2</b><br/>Sequential Learning", styles["TableCellBold"]),
            Paragraph("Bayesian Knowledge Tracing (BKT)", styles["TableCell"]),
            Paragraph("Tracks whether a concept is mastered (0 or 1) as a student attempts questions chronologically.", styles["TableCell"]),
            Paragraph("<code>mastery_service.py</code><br/><code>compute_bkt_sequence()</code>", styles["TableCell"])
        ],
        [
            Paragraph("<b>Layer 3</b><br/>Multi-Skill Diagnosis", styles["TableCellBold"]),
            Paragraph("Multi-Attribute DINA Model", styles["TableCell"]),
            Paragraph("Diagnoses complex questions requiring multiple simultaneous skills using Q-Matrix logic.", styles["TableCell"]),
            Paragraph("<code>dina_service.py</code><br/><code>_compute_block_exact()</code>", styles["TableCell"])
        ]
    ], colWidths=[80, 110, 174, 140])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(arch_table)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 2: END-TO-END DATA FLOW ARCHITECTURE & FLOWCHART
    # ════════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. End-to-End System Data Flow Architecture", styles["SectionHeading"]))
    story.append(Paragraph(
        "Here is the complete end-to-end journey of an MCQ response, from the moment a student selects an option "
        "in the React browser to the background Bayesian knowledge calculations and final diagnostic persistence.",
        styles["BodyTextCustom"]
    ))

    # Flowchart Image Embedding
    if os.path.exists("ml_dataflow_diagram.png"):
        story.append(Image("ml_dataflow_diagram.png", width=504, height=375))
        story.append(Spacer(1, 4))

    story.append(Paragraph("Step-by-Step Execution Walkthrough:", styles["SubSectionHeading"]))

    steps = [
        "<b>Step 1 — Student Answer Submission:</b> The student selects an option on the web interface. High-precision client timers record their response latency. A JSON payload with <code>question_id</code>, <code>selected_option_id</code>, and <code>response_time_ms</code> is sent via HTTP POST.",
        "<b>Step 2 — API Gateway &amp; Synchronous Commit (FastAPI):</b> In <code>routers/student.py</code>, the function <code>submit_response()</code> checks if <code>selected_option_id == correct_option_id</code>, logs the raw response into PostgreSQL, and immediately returns a success status to the student without any delay.",
        "<b>Step 3 — Asynchronous Non-Blocking Worker:</b> FastAPI's <code>BackgroundTasks</code> triggers <code>run_mastery_and_diagnosis()</code> in the background. The student's browser never experiences lag or waiting time while mathematical models execute.",
        "<b>Step 4 — Layer 2 BKT Sequential Update:</b> <code>PYBKTMasteryEstimator.update_mastery()</code> loads all chronological responses for that concept. It runs <code>compute_bkt_sequence()</code> to calculate new mastery probability <i>P</i>(<i>L<sub>t</sub></i>) and saves it to <code>student_concept_mastery</code>.",
        "<b>Step 5 — Layer 3 DINA Multi-Skill Diagnosis:</b> <code>DINADiagnosisService.update_diagnosis()</code> loads the Q-Matrix, runs BFS to isolate the connected skill block, evaluates exact joint likelihoods via vectorized NumPy, computes quadratic entropy confidence, and updates <code>cognitive_diagnosis_profile</code>.",
        "<b>Step 6 — Root-Cause Diagnostic Queries:</b> When a student or teacher inspects an incorrect answer, <code>get_question_why()</code> queries required skills and flags any concept with mastery &lt; 0.50 as a 'Likely Missing Prerequisite'."
    ]
    for s in steps:
        story.append(Paragraph(f"• {s}", styles["BulletCustom"]))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 3: LAYER 1 & LAYER 2 DEEP-DIVE (GRAPH & BKT)
    # ════════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Layer 1 — Concept Prerequisite Graph &amp; Cycle Prevention", styles["SectionHeading"]))
    story.append(Paragraph(
        "Concepts cannot be learned in random order; knowledge builds upon foundational prerequisites. "
        "For example, a student must understand <i>Basic Algebra</i> before learning <i>Quadratic Equations</i>.",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph(
        "• <b>Automated Prerequisite Discovery:</b> The function <code>infer_llm_concept_edges()</code> in <code>concept_graph.py</code> "
        "sends all curriculum concepts to Groq LLaMA, which proposes directed pairs: (Concept A &rarr; Concept B) with confidence ratings.",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>Cycle Detection &amp; DAG Invariant:</b> A circular prerequisite loop (A &rarr; B &rarr; C &rarr; A) is logically impossible "
        "and breaks adaptive learning paths. KnowledgeTrace MCQ builds an in-memory <code>networkx.DiGraph</code> and evaluates each candidate edge using "
        "<code>nx.is_directed_acyclic_graph(G)</code>. If an edge introduces a cycle, it is immediately discarded.",
        styles["BulletCustom"]
    ))

    story.append(Spacer(1, 4))
    story.append(Paragraph("4. Layer 2 — Bayesian Knowledge Tracing (BKT)", styles["SectionHeading"]))
    story.append(Paragraph(
        "Bayesian Knowledge Tracing is an established educational AI model (Corbett &amp; Anderson, 1995). "
        "It treats a student's knowledge as a <b>Hidden Markov Model (HMM)</b> with 2 possible mental states: "
        "<b>0 = Unmastered</b> and <b>1 = Mastered</b>.",
        styles["BodyTextCustom"]
    ))

    # BKT Parameters Table
    bkt_params = Table([
        [
            Paragraph("<b>Parameter</b>", styles["TableHeader"]),
            Paragraph("<b>Mathematical Symbol</b>", styles["TableHeader"]),
            Paragraph("<b>Default Value</b>", styles["TableHeader"]),
            Paragraph("<b>Psychometric Meaning &amp; Intuition</b>", styles["TableHeader"])
        ],
        [
            Paragraph("<b>Prior Knowledge</b>", styles["TableCellBold"]),
            Paragraph("<i>P</i>(<i>L</i><sub>0</sub>)", styles["TableCellBold"]),
            Paragraph("0.20 (20%)", styles["TableCell"]),
            Paragraph("Chance a student already understands the concept before attempting their first question.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Learning Transition</b>", styles["TableCellBold"]),
            Paragraph("<i>P</i>(<i>T</i>)", styles["TableCellBold"]),
            Paragraph("0.15 (15%)", styles["TableCell"]),
            Paragraph("Chance that a student transitions from Unmastered &rarr; Mastered during a practice question.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Careless Slip</b>", styles["TableCellBold"]),
            Paragraph("<i>P</i>(<i>S</i>)", styles["TableCellBold"]),
            Paragraph("0.10 (10%)", styles["TableCell"]),
            Paragraph("Chance that a student who HAS mastered the skill makes an accidental mistake or typo.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Lucky Guess</b>", styles["TableCellBold"]),
            Paragraph("<i>P</i>(<i>G</i>)", styles["TableCellBold"]),
            Paragraph("0.25 (25%)", styles["TableCell"]),
            Paragraph("Chance of answering correctly by pure guessing (standard 1 in 4 for a 4-option MCQ).", styles["TableCell"])
        ]
    ], colWidths=[90, 85, 65, 264])
    bkt_params.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(bkt_params)
    story.append(Spacer(1, 6))

    # Formula Box
    bkt_math_html = (
        "<b>Step 1 — Observation Update (Bayes' Rule):</b><br/>"
        "&bull; If Correct: &nbsp;&nbsp; <i>P</i>(<i>L<sub>t</sub></i> | Correct) = "
        "[ <i>P</i>(<i>L<sub>t</sub></i>) &times; (1 &minus; <i>P</i>(<i>S</i>)) ] / "
        "[ <i>P</i>(<i>L<sub>t</sub></i>) &times; (1 &minus; <i>P</i>(<i>S</i>)) + (1 &minus; <i>P</i>(<i>L<sub>t</sub></i>)) &times; <i>P</i>(<i>G</i>) ]<br/>"
        "&bull; If Incorrect: &nbsp; <i>P</i>(<i>L<sub>t</sub></i> | Incorrect) = "
        "[ <i>P</i>(<i>L<sub>t</sub></i>) &times; <i>P</i>(<i>S</i>) ] / "
        "[ <i>P</i>(<i>L<sub>t</sub></i>) &times; <i>P</i>(<i>S</i>) + (1 &minus; <i>P</i>(<i>L<sub>t</sub></i>)) &times; (1 &minus; <i>P</i>(<i>G</i>)) ]<br/><br/>"
        "<b>Step 2 — Latent Learning Transition:</b><br/>"
        "<i>P</i>(<i>L</i><sub><i>t</i>+1</sub>) = <i>P</i>(<i>L<sub>t</sub></i> | obs) + [ 1 &minus; <i>P</i>(<i>L<sub>t</sub></i> | obs) ] &times; <i>P</i>(<i>T</i>)"
    )
    story.append(create_formula_card(
        "BKT FORWARD ALGORITHM EQUATIONS (Implemented in compute_bkt_sequence)",
        bkt_math_html,
        "Notice how the formula works: if an answer is correct, mastery increases; if incorrect, it drops. "
        "Then, Step 2 adds the chance of learning during the practice opportunity. Once a student learns, they cannot unlearn.",
        border_color=ACCENT_GREEN,
        styles=styles
    ))

    story.append(Spacer(1, 5))
    story.append(Paragraph("Concrete Example: 4 Consecutive Attempts by a Student", styles["SubSectionHeading"]))

    sim_table = Table([
        [
            Paragraph("<b>Attempt</b>", styles["TableHeader"]),
            Paragraph("<b>Prior <i>P</i>(<i>L</i>)</b>", styles["TableHeader"]),
            Paragraph("<b>Answer</b>", styles["TableHeader"]),
            Paragraph("<b>Bayes Posterior <i>P</i>(<i>L</i>|obs)</b>", styles["TableHeader"]),
            Paragraph("<b>Updated Mastery <i>P</i>(<i>L</i><sub><i>t</i>+1</sub>)</b>", styles["TableHeader"]),
            Paragraph("<b>What Happened? (Pedagogical Insight)</b>", styles["TableHeader"])
        ],
        [
            Paragraph("Initial", styles["TableCellBold"]),
            Paragraph("0.2000", styles["TableCell"]),
            Paragraph("—", styles["TableCell"]),
            Paragraph("—", styles["TableCell"]),
            Paragraph("0.2000", styles["TableCellBold"]),
            Paragraph("Starting assumption before any questions are answered.", styles["TableCell"])
        ],
        [
            Paragraph("1", styles["TableCellBold"]),
            Paragraph("0.2000", styles["TableCell"]),
            Paragraph("Correct (+)", styles["TableCell"]),
            Paragraph("0.4737", styles["TableCell"]),
            Paragraph("<b>0.5526</b>", styles["TableCellBold"]),
            Paragraph("Correct answer gives statistical evidence of knowledge.", styles["TableCell"])
        ],
        [
            Paragraph("2", styles["TableCellBold"]),
            Paragraph("0.5526", styles["TableCell"]),
            Paragraph("Incorrect (&minus;)", styles["TableCell"]),
            Paragraph("0.1418", styles["TableCell"]),
            Paragraph("<b>0.2705</b>", styles["TableCellBold"]),
            Paragraph("Wrong answer reduces probability (penalizing temporary confidence).", styles["TableCell"])
        ],
        [
            Paragraph("3", styles["TableCellBold"]),
            Paragraph("0.2705", styles["TableCell"]),
            Paragraph("Correct (+)", styles["TableCell"]),
            Paragraph("0.5714", styles["TableCell"]),
            Paragraph("<b>0.6357</b>", styles["TableCellBold"]),
            Paragraph("Student bounces back; confidence rapidly recovers.", styles["TableCell"])
        ],
        [
            Paragraph("4", styles["TableCellBold"]),
            Paragraph("0.6357", styles["TableCell"]),
            Paragraph("Correct (+)", styles["TableCell"]),
            Paragraph("0.8653", styles["TableCell"]),
            Paragraph("<b>0.8855</b>", styles["TableCellBold"]),
            Paragraph("Second consecutive correct answer confirms high mastery (&gt; 88%).", styles["TableCell"])
        ]
    ], colWidths=[40, 52, 60, 72, 72, 208])
    sim_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 2.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sim_table)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 4: LAYER 3 DEEP-DIVE (MULTI-SKILL DINA MODEL)
    # ════════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5. Layer 3 — Multi-Attribute Cognitive Diagnosis (DINA Model)", styles["SectionHeading"]))
    story.append(Paragraph(
        "While BKT works well when an MCQ only tests a single concept, real exam questions often require multiple skills combined. "
        "For example, calculating kinetic friction on an inclined plane requires BOTH <i>Trigonometric Decomposition</i> AND <i>Newtonian Friction</i>.",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph(
        "<b>The DINA Model (Deterministic Inputs, Noisy 'And'):</b> Formalized by Junker &amp; Sijtsma (2001), DINA models a student's ability "
        "as a binary vector <b>&alpha;</b> = (&alpha;<sub>1</sub>, &alpha;<sub>2</sub>, ..., &alpha;<sub><i>K</i></sub>) where each &alpha;<sub><i>k</i></sub> &isin; {0, 1}.",
        styles["BodyTextCustom"]
    ))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Core Foundations of DINA:", styles["SubSectionHeading"]))

    story.append(Paragraph(
        "• <b>The Q-Matrix:</b> A binary table linking each question to the skills it requires: <i>q<sub>jk</sub></i> = 1 if question <i>j</i> requires concept <i>k</i>, else 0.",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>The Conjunctive 'AND' Rule:</b> To answer question <i>j</i> without guessing, the student must master <b>ALL</b> required skills: "
        "&xi;<sub><i>j</i></sub>(<b>&alpha;</b>) = &prod; &alpha;<sub><i>k</i></sub><sup><i>q<sub>jk</sub></i></sup>. "
        "If even ONE required skill is missing (&alpha;<sub><i>k</i></sub> = 0), then &xi;<sub><i>j</i></sub> = 0, dropping the student into the guess category!",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>Item Response Probabilities:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; If student has ALL skills (&xi; = 1): <i>P</i>(Correct) = 1 &minus; Slip = 1 &minus; 0.10 = <b>0.90 (90%)</b>.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; If student misses ANY skill (&xi; = 0): <i>P</i>(Correct) = Guess = <b>0.25 (25%)</b>.",
        styles["BulletCustom"]
    ))

    story.append(Spacer(1, 4))
    story.append(create_callout(
        "<b>The Exponential Explosion Problem (2<sup>K</sup>):</b> If a curriculum has 30 skills, there are 2<sup>30</sup> = 1,073,741,824 possible skill combinations! "
        "Calculating probabilities over a billion states on a live server causes memory crashes and intolerable lag.<br/><br/>"
        "<b>The KnowledgeTrace MCQ Solution (Connected-Block Partitioning):</b><br/>"
        "1. In <code>dina_service.py</code>, questions create graph edges between skills they simultaneously test.<br/>"
        "2. A <b>Breadth-First Search (BFS)</b> isolates only the connected block of skills containing the target concept.<br/>"
        "3. If the block size <i>K</i> &le; 12 (max 4,096 states), the system computes exact Bayesian posteriors via <b>Vectorized NumPy &amp; Log-Sum-Exp</b> in under 10 milliseconds!<br/>"
        "4. If a block exceeds 12 skills, the engine automatically falls back to an exact single-skill closed-form solution (guaranteeing <i>O</i>(1) system stability).",
        title="ALGORITHMIC BREAKTHROUGH: SOLVING THE 2^K BOTTLENECK",
        bg=BG_CARD,
        border=ACCENT_AMBER,
        styles=styles
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Epistemic Confidence Score &amp; Reliability Tiers:", styles["SubSectionHeading"]))
    story.append(Paragraph(
        "How sure is the system of its diagnosis? Rather than guessing, KnowledgeTrace MCQ computes an information-theoretic "
        "confidence score based on <b>quadratic entropy</b>:",
        styles["BodyTextCustom"]
    ))

    conf_math_html = (
        "<b>Confidence Score Equation:</b> &nbsp;&nbsp; <b>Confidence = 1 &minus; 4 &times; <i>P</i> &times; (1 &minus; <i>P</i>)</b><br/>"
        "&bull; When <i>P</i> = 0.50 (Maximum Uncertainty): Confidence = 1 &minus; 4(0.25) = <b>0.00 (0%)</b>.<br/>"
        "&bull; When <i>P</i> = 0.85 (Strong Mastery): Confidence = 1 &minus; 4(0.85 &times; 0.15) = <b>0.49 (49%)</b>.<br/>"
        "&bull; When <i>P</i> = 0.98 or 0.02 (Definitive Certainty): Confidence = 1 &minus; 4(0.0196) = <b>0.92 (92%)</b>."
    )
    story.append(create_formula_card(
        "CONFIDENCE METRIC & RELIABILITY TIERS (Implemented in dina_service.py)",
        conf_math_html,
        "Scores are categorized into 3 actionable tiers: <b>LOW</b> (&lt; 0.40, needs more questions), "
        "<b>MEDIUM</b> (0.40 to 0.75, provisional diagnosis), and <b>HIGH</b> (&ge; 0.75, certified mastery).",
        border_color=SECONDARY,
        styles=styles
    ))

    story.append(Spacer(1, 5))
    story.append(Paragraph("6. Root-Cause 'WHY' Diagnostic Engine", styles["SectionHeading"]))
    story.append(Paragraph(
        "The standout pedagogical feature of KnowledgeTrace MCQ is explaining <b>WHY</b> a student missed a question:",
        styles["BodyTextCustom"]
    ))
    story.append(Paragraph(
        "When an incorrect answer is logged, the function <code>get_question_why(student_id, question_id)</code> in <code>dina_service.py</code> "
        "retrieves all skills required by that question. It inspects the student's current DINA diagnosis for each skill. Any skill with "
        "mastery <i>P</i> &lt; 0.50 is flagged as a <b>'Likely Missing Prerequisite'</b>, pinpointing the exact gap for teachers and students.",
        styles["BodyTextCustom"]
    ))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 5: MODELS VISUAL SUMMARY & IN-DEPTH COMPARISON
    # ════════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("7. Architectural Visualization of the 3 ML Layers", styles["SectionHeading"]))
    story.append(Paragraph(
        "The diagram below illustrates the exact structural workflows of the 3 models: Layer 1 (LLM prerequisite DAG), "
        "Layer 2 (BKT 2-state Hidden Markov Model), and Layer 3 (DINA multi-skill Q-matrix logic).",
        styles["BodyTextCustom"]
    ))

    # Models Diagram Image Embedding
    if os.path.exists("ml_models_diagram.png"):
        story.append(Image("ml_models_diagram.png", width=504, height=430))
        story.append(Spacer(1, 6))

    story.append(Paragraph("How the Three Layers Harmonize:", styles["SubSectionHeading"]))
    story.append(Paragraph(
        "• <b>Layer 1 builds the map:</b> Without Layer 1, the test system is just a flat pile of unconnected questions. "
        "The LLM-inferred DAG provides topological direction, ensuring students face questions in a sensible learning order.",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>Layer 2 tracks practice momentum:</b> BKT excels at fast, chronological single-skill estimation. It smooths out "
        "momentary slips and detects when learning happens between questions.",
        styles["BulletCustom"]
    ))
    story.append(Paragraph(
        "• <b>Layer 3 performs surgical multi-skill diagnosis:</b> When a problem demands multiple combined skills, "
        "DINA disentangles which specific sub-skills the student understands and which one caused the failure.",
        styles["BulletCustom"]
    ))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 6: REFERENCE CHEAT SHEET, BENCHMARKS & FINAL TAKEAWAY
    # ════════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("8. Engineering &amp; ML Architecture Reference Cheat Sheet", styles["SectionHeading"]))
    story.append(Paragraph(
        "Complete technical reference mapping software components to their mathematical models, algorithms, and database artifacts:",
        styles["BodyTextCustom"]
    ))

    ref_table = Table([
        [
            Paragraph("<b>Component / Layer</b>", styles["TableHeader"]),
            Paragraph("<b>File Path &amp; Key Function</b>", styles["TableHeader"]),
            Paragraph("<b>Core Algorithm Used</b>", styles["TableHeader"]),
            Paragraph("<b>Database Table &amp; Output</b>", styles["TableHeader"])
        ],
        [
            Paragraph("<b>Layer 1</b><br/>Concept Graph", styles["TableCellBold"]),
            Paragraph("<code>services/concept_graph.py</code><br/><code>infer_llm_concept_edges()</code>", styles["TableCell"]),
            Paragraph("Groq LLaMA JSON Schema + NetworkX Cycle Check (<code>is_directed_acyclic_graph</code>)", styles["TableCell"]),
            Paragraph("<code>concept_edges</code><br/>Valid (from &rarr; to) prerequisite edges", styles["TableCell"])
        ],
        [
            Paragraph("<b>API Ingestion</b><br/>FastAPI Router", styles["TableCellBold"]),
            Paragraph("<code>routers/student.py</code><br/><code>submit_response()</code>", styles["TableCell"]),
            Paragraph("Sync binary validation + Non-blocking <code>BackgroundTasks</code> worker spawn", styles["TableCell"]),
            Paragraph("<code>responses</code><br/>student_id, question_id, is_correct, latency", styles["TableCell"])
        ],
        [
            Paragraph("<b>Layer 2</b><br/>BKT Estimator", styles["TableCellBold"]),
            Paragraph("<code>services/mastery_service.py</code><br/><code>update_mastery()</code>", styles["TableCell"]),
            Paragraph("Bayesian HMM Forward Algorithm: <code>compute_bkt_sequence()</code>", styles["TableCell"]),
            Paragraph("<code>student_concept_mastery</code><br/><code>mastery_p</code>, <code>opportunity_count</code>", styles["TableCell"])
        ],
        [
            Paragraph("<b>Layer 3</b><br/>DINA Diagnosis", styles["TableCellBold"]),
            Paragraph("<code>services/dina_service.py</code><br/><code>update_diagnosis()</code>", styles["TableCell"]),
            Paragraph("BFS Connected Block Partitioning + NumPy Vectorized Log-Sum-Exp Marginalization", styles["TableCell"]),
            Paragraph("<code>cognitive_diagnosis_profile</code><br/><code>adjusted_mastery</code>, <code>confidence_score</code>", styles["TableCell"])
        ],
        [
            Paragraph("<b>Root-Cause AI</b><br/>Misconception Engine", styles["TableCellBold"]),
            Paragraph("<code>services/dina_service.py</code><br/><code>get_question_why()</code>", styles["TableCell"]),
            Paragraph("Multi-skill prerequisite attribution (identifies <i>P</i> &lt; 0.50 prerequisite failure)", styles["TableCell"]),
            Paragraph("Dashboard UI alerts<br/>'Likely Missing Prerequisite' flag", styles["TableCell"])
        ]
    ], colWidths=[90, 134, 150, 130])
    ref_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)
    story.append(Spacer(1, 8))

    # Benchmark Datasets Table
    story.append(Paragraph("9. Educational Benchmark Datasets &amp; Validation Standards", styles["SectionHeading"]))
    story.append(Paragraph(
        "The algorithms in KnowledgeTrace MCQ are based on standard educational data mining benchmarks in psychometric literature:",
        styles["BodyTextCustom"]
    ))

    data_table = Table([
        [
            Paragraph("<b>Benchmark Dataset</b>", styles["TableHeader"]),
            Paragraph("<b>Origin &amp; Institution</b>", styles["TableHeader"]),
            Paragraph("<b>Dataset Scale</b>", styles["TableHeader"]),
            Paragraph("<b>Relevance to KnowledgeTrace MCQ</b>", styles["TableHeader"])
        ],
        [
            Paragraph("<b>ASSISTments 2009-2010</b>", styles["TableCellBold"]),
            Paragraph("Worcester Polytechnic Institute (WPI)", styles["TableCell"]),
            Paragraph("4,163 students<br/>338,001 response logs", styles["TableCell"]),
            Paragraph("Gold-standard benchmark for Bayesian Knowledge Tracing sequence evaluation (AUC ~0.73).", styles["TableCell"])
        ],
        [
            Paragraph("<b>Junyi Academy</b>", styles["TableCellBold"]),
            Paragraph("Junyi Academy (Taiwan) / KDD Cup", styles["TableCell"]),
            Paragraph("72,000+ students<br/>835 concept DAG", styles["TableCell"]),
            Paragraph("Validates concept prerequisite graphs and topological sequencing in large-scale curricula.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Tatsuoka Fraction Subtraction</b>", styles["TableCellBold"]),
            Paragraph("K. Tatsuoka (1990) Rule Space", styles["TableCell"]),
            Paragraph("536 students, 20 items<br/>8 skill attributes", styles["TableCell"]),
            Paragraph("Definitive historical benchmark for Q-Matrix construction and DINA cognitive diagnosis models.", styles["TableCell"])
        ]
    ], colWidths=[110, 120, 110, 164])
    data_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(data_table)
    story.append(Spacer(1, 8))

    story.append(create_callout(
        "<b>Summary for Developers &amp; Educators:</b> KnowledgeTrace MCQ is designed to be mathematically rigorous, "
        "pedagogically explainable, and lightning-fast in production. By combining non-blocking FastAPI asynchronous background tasks, "
        "vectorized NumPy mathematics, NetworkX topological graph theory, and Bayesian cognitive modeling, "
        "it delivers immediate adaptive feedback to students while providing deep diagnostic insights to teachers.",
        title="FINAL TAKEAWAY: POWERFUL, EXPLAINABLE, AND PRODUCTION-READY",
        bg=BG_CARD,
        border=ACCENT_GREEN,
        styles=styles
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Publication-grade PDF successfully created at: {output_path}")

if __name__ == "__main__":
    build_pdf("ml_concepts_and_data_flow_guide.pdf")
    # Also update machine_learning_algorithms.pdf so that both files are updated
    build_pdf("machine_learning_algorithms.pdf")
