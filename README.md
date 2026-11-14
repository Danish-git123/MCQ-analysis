# KnowledgeTrace MCQ: Advanced Machine Learning Analytics & Cognitive Diagnostic Engine

## Academic Session 2026-2027 | CSE Mega Project
**Branch:** `ml-advanced-analytics`  
**System Architecture:** Neuro-Symbolic Cognitive Diagnosis, Psychometric Item Profiling, and Agentic Remediation  

---

## 1. Executive Overview

Standard Learning Management Systems (LMS) and computer-based testing engines evaluate student performance using raw percentage arithmetic (for example, 7/10 = 70%). This scalar score is pedagogically uninformative because it fails to address five fundamental realities of human testing:

1. **Guessing Blindness:** In a standard 4-option multiple-choice question, random guessing carries a 25% baseline success probability. Traditional scoring awards full credit for lucky guesses.
2. **Careless Slip Penalties:** A high-mastery student who understands a topic may make an accidental typographical or reading error. Traditional grading treats this error identically to complete ignorance.
3. **Multi-Skill Confounding:** Engineering and technical assessments test compound skills. If an assessment item requires both SQL Execution and Query Optimization, a single score cannot determine which sub-skill failed.
4. **Compounding Prerequisite Debt:** When foundational concepts are unmastered, failures compound downstream. Traditional systems fail to trace learning deficits back to their root blockers.
5. **Item Psychometric Defects:** Exam questions often contain ambiguous phrasing or misleading trick distractors that confuse high-performing students. Traditional systems assume every exam question is flawless.

The `ml-advanced-analytics` branch implements an interpretable, non-blocking, publication-grade **Neuro-Symbolic Cognitive Diagnostic Architecture**. It integrates **Bayesian Knowledge Tracing (BKT)**, the **Multi-Attribute DINA Model**, **Response-Time Effort (RTE)** behavioral telemetry, **Multivariate Logistic Regression** slip detection, **Point-Biserial Item Discrimination** ($r_{pb}$), and **NetworkX Directed Acyclic Graph (DAG)** causal analysis into a unified, responsive platform.

---

## 2. End-to-End System Workflow

The complete system workflow operates across five distinct phases:

```
[Phase 1: Curriculum & Test Authoring]
                  │
                  ▼
[Phase 2: High-Precision Student Telemetry]
                  │
                  ▼
[Phase 3: Asynchronous Background ML Inference]
                  │
                  ▼
[Phase 4: Teacher Cohort Psychometrics & Heatmaps]
                  │
                  ▼
[Phase 5: Closed-Loop AI Remediation & Assignment]
```

### Phase 1: Curriculum & Test Authoring (Teacher)
* **Topological Prerequisite Control:** Teachers define dependency links between concepts (e.g., Recursion -> Binary Trees). The system uses NetworkX to enforce an acyclic invariant, immediately rejecting circular logic ($A \to B \to A$) with an HTTP 400 validation error.
* **Multi-Skill Q-Matrix Tagging:** Each question is mapped to one primary concept and multiple secondary skill attributes in the database `question_skills` table.
* **Two Creation Workflows:**
  1. *Bulk Question Import:* Teachers paste plain-text blocks (`Q1 - Concept: Name ...`), which the system parses, extracts options, validates answer keys, and auto-links concepts.
  2. *AI Curriculum Generator:* Teachers enter a topic name, and the agent auto-extracts concepts, validates DAG links, and synthesizes candidate multi-skill MCQs for instructor review.

### Phase 2: High-Precision Student Telemetry (Student)
* As the student reads and solves questions, a client-side performance timer captures millisecond latency (`response_time_ms`).
* **Non-Blocking Ingestion:** When the student submits an answer, FastAPI writes the record to PostgreSQL and returns an HTTP 200 payload in under 15 milliseconds. The student advances immediately with zero server lag.

### Phase 3: Asynchronous Background ML Inference (FastAPI BackgroundTasks)
A decoupled worker executes multi-model cognitive evaluation in the background:
1. **Bayesian Knowledge Tracing (BKT):** Updates latent mastery probabilities after each attempt using Bayes' rule.
2. **DINA Conjunctive Solver:** Evaluates student latent attribute vectors across the $2^K$ skill space to isolate which specific sub-skill caused an incorrect response.
3. **Cognitive Latency Profiler:** Compares actual solving latency against calibrated reading and context-switching expectations ($T_{\text{expected}}$) to assign one of four behavioral quadrants.
4. **Careless Slip Detector:** Uses multivariate logistic regression to identify when a high-mastery student suffered an accidental slip.

### Phase 4: Teacher Cohort Psychometrics (Teacher Dashboard)
When the instructor opens test results, the engine aggregates cohort performance:
* **Student x Concept Mastery Heatmap:** A visual matrix showing continuous DINA mastery percentages across all students and curriculum topics.
* **Point-Biserial Discrimination ($r_{pb}$):** Calculates Pearson correlation between individual question accuracy and total test score to tag items as STRONG, FAIR, or REVIEW NEEDED.
* **Distractor Magnet Analysis:** Aggregates option selection distributions and flags the top incorrect option with a Top Trap indicator.
* **Prerequisite Bottleneck Graph:** Evaluates class-wide mastery against the DAG to highlight root blocker nodes choking downstream comprehension.

### Phase 5: Closed-Loop AI Remediation & Assignment
* The teacher clicks "Analyze Class with AI Agent".
* The agent reviews cohort metrics and writes a concise executive briefing advising what to reteach first.
* The agent automatically drafts a targeted 3-to-5 question remedial quiz targeting the identified root bottlenecks.
* **Human-in-the-Loop Safety:** The teacher can edit stems, modify options, and adjust answer keys in a live preview.
* **Selective Assignment:** The teacher selects specific struggling student checkboxes and clicks "Approve & Assign". The remedial quiz is created and dispatched immediately to those students.

---

## 3. Mathematical Foundations & Formulations

### 1. DINA Multi-Skill Conjunctive Model
*File:* `backend/app/services/dina_service.py`

The Deterministic Inputs, Noisy "And" gate model evaluates binary latent attribute vectors $\boldsymbol{\alpha}_i = (\alpha_{i1}, \dots, \alpha_{iK})$ against the binary Q-matrix $Q \in \{0, 1\}^{J \times K}$:

$$\eta_{ij} = \prod_{k=1}^K \alpha_{ik}^{q_{jk}}$$

* **Plain Text:** The ideal latent response $\eta_{ij}$ equals 1 if and only if the student has mastered every concept required by question $j$. If even one concept is missing ($\alpha_{ik} = 0$), $\eta_{ij}$ collapses to 0.

### 2. DINA Item Response Likelihood
*File:* `backend/app/services/dina_service.py`

Maps latent knowledge to observed response probabilities:

$$P(X_{ij} = 1 \mid \boldsymbol{\alpha}_i) = g_j^{1 - \eta_{ij}} (1 - s_j)^{\eta_{ij}}$$

* **Guessing Floor ($g_j = 0.25$):** If the student lacks the required skills ($\eta_{ij} = 0$), probability of a correct response is $25\%$ on 4-option MCQs.
* **Mastery Ceiling ($1 - s_j = 0.90$):** If the student possesses all skills ($\eta_{ij} = 1$), probability of success is $90\%$, accounting for a $10\%$ slip rate ($s_j = 0.10$).

### 3. Epistemic Confidence via Normalized Quadratic Entropy
*File:* `backend/app/services/dina_service.py`

Measures diagnostic certainty of a mastery probability $P \in [0.0, 1.0]$:

$$\text{Confidence}(P) = 1 - 4 \cdot P \cdot (1 - P)$$

* **At $P = 0.50$ (Maximum uncertainty):** $\text{Confidence} = 1 - 4(0.25) = 0.00$ ($0\%$ certainty).
* **At $P = 0.85$ (Strong evidence):** $\text{Confidence} = 1 - 4(0.1275) = 0.49$ ($49\%$ certainty).
* **At $P = 0.98$ (Definitive mastery):** $\text{Confidence} = 1 - 4(0.0196) = 0.92$ ($92\%$ certainty).

### 4. Bayesian Knowledge Tracing (BKT) Forward Algorithm
*File:* `backend/app/services/mastery_service.py`

Updates concept mastery belief $P(L_t)$ upon observing attempt result $o_t \in \{0, 1\}$:

$$\text{If Correct: } \quad P(L_t \mid o_t = 1) = \frac{P(L_t)(1 - P(S))}{P(L_t)(1 - P(S)) + (1 - P(L_t))P(G)}$$

$$\text{If Incorrect: } \quad P(L_t \mid o_t = 0) = \frac{P(L_t)P(S)}{P(L_t)P(S) + (1 - P(L_t))(1 - P(G))}$$

$$\text{Practice Learning Step: } \quad P(L_{t+1}) = P(L_t \mid o_t) + \left[1 - P(L_t \mid o_t)\right] \cdot P(T)$$

* **Parameters:** Prior $P(L_0) = 0.20$, Transition Rate $P(T) = 0.15$, Slip $P(S) = 0.10$, Guess $P(G) = 0.25$.

### 5. Response-Time Effort (RTE) & Behavioral Quadrants
*File:* `backend/app/services/cognitive_analytics_service.py`

Establishes expected reading and context-switching duration:

$$T_{\text{expected}} = \max\left(7000, \, 8000 + 300 \cdot W + 5000 \cdot K_j\right) \text{ ms}, \quad \tau = \frac{T_{\text{actual}}}{T_{\text{expected}}}$$

* **Rapid Guessing:** Any response completed in $T_{\text{actual}} < 4000\text{ ms}$ is flagged as low-effort rushing.
* **Cognitive Fluency:** Correct response ($X=1$) with $\tau \le 1.8$.
* **Deliberate Mastery:** Correct response ($X=1$) with $\tau > 1.8$.
* **Cognitive Struggle:** Incorrect response ($X=0$) despite adequate time ($T_{\text{actual}} \ge 4000\text{ ms}$).

### 6. Point-Biserial Item Discrimination Index ($r_{pb}$)
*File:* `backend/app/routers/teacher.py`

Calculates Pearson correlation between item score $X_{ij} \in \{0, 1\}$ and student total exam score $Y_i \in [0.0, 1.0]$:

$$r_{pb} = \frac{\sum_{i=1}^n (X_{ij} - \bar{X}_j)(Y_i - \bar{Y})}{\sqrt{\sum_{i=1}^n (X_{ij} - \bar{X}_j)^2 \cdot \sum_{i=1}^n (Y_i - \bar{Y})^2}}$$

* **$r_{pb} \ge 0.25$ (STRONG):** Top students get it right; struggling students miss it. Reliable item.
* **$0.10 \le r_{pb} < 0.25$ (FAIR):** Moderate discrimination.
* **$r_{pb} < 0.10$ or negative (REVIEW NEEDED):** Defective question, confusing wording, or incorrect answer key.

### 7. Prerequisite Debt & Cohort Root Blocker Criterion
*Files:* `backend/app/services/cognitive_analytics_service.py`, `backend/app/routers/teacher.py`

Let $W = \{c \in V \mid \bar{\alpha}_c < 0.50\}$ be the set of unmastered concepts:

$$\text{Prerequisite Debt} = \frac{\big|\{c \in W \mid \text{predecessors}(c) \cap W \neq \emptyset\}\big|}{|W|}$$

$$\text{RootBlocker}(c) \iff \left(\bar{\alpha}_c < 0.55\right) \land \left(\exists s \in \text{successors}(c) : \bar{\alpha}_s < 0.65\right)$$

* **Prerequisite Debt:** Proportion of weak concepts directly caused by unmastered upstream parents in the DAG.
* **Root Blocker:** Highlights the foundational node dragging down downstream cohort comprehension.

---

## 4. Repository & File Architecture Map

```
MCQ-analysis/
├── backend/
│   ├── app/
│   │   ├── models/                    # Database ORM Schemas (SQLAlchemy)
│   │   │   ├── user.py                # User, Roles (Teacher, Student)
│   │   │   ├── concept.py             # Concept, ConceptEdge (DAG Links)
│   │   │   ├── test.py                # Test, Question, Option, QuestionSkill (Q-Matrix)
│   │   │   ├── response.py            # Response (is_correct, response_time_ms)
│   │   │   └── diagnosis.py           # StudentConceptMastery, CognitiveDiagnosisProfile
│   │   ├── schemas/                   # Pydantic Input/Output Schemas
│   │   │   ├── concept.py             # ConceptRead, ConceptEdgeCreate
│   │   │   ├── question.py            # QuestionCreate (skill_ids), OptionCreate
│   │   │   └── agent.py               # CurriculumDraft, ClassIntervention schemas
│   │   ├── routers/                   # API Endpoints
│   │   │   ├── student.py             # POST /student/responses (Sync DB write + Async ML)
│   │   │   ├── teacher.py             # GET /teacher/tests/{id}/results (Cohort Psychometrics)
│   │   │   ├── concepts.py            # POST/DELETE /concepts/edges, GET /concepts/graph
│   │   │   ├── diagnosis.py           # GET /diagnosis/student/{id}/* (Student Dossier)
│   │   │   └── agent.py               # ReAct AI Agent Orchestration Routes
│   │   └── services/                  # Mathematical & Algorithmic Engines
│   │       ├── concept_graph.py       # Layer 1: NetworkX DAG Validation & Cycle Guards
│   │       ├── mastery_service.py     # Layer 2: Bayesian Knowledge Tracing (BKT Forward)
│   │       ├── dina_service.py        # Layer 3: Multi-Skill DINA + BFS Block Partitioning
│   │       ├── prediction_service.py  # Layer 4: Logistic Regression Slip/Guess Detector
│   │       ├── cognitive_analytics_service.py # Layer 5: Response-Time Effort (RTE) & Debt
│   │       └── agent_service.py       # ReAct AI Brain (Teaching Briefing & MCQ Synthesis)
│   ├── seed_dsa_diagnostic_test.py    # Automated seeder for sample tests and student assignment
│   └── requirements.txt               # Backend dependencies (FastAPI, SQLAlchemy, NetworkX, NumPy)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── PrerequisiteGraph.jsx  # SVG Force-Directed Prerequisite DAG Visualizer
│   │   ├── pages/
│   │   │   ├── TestBuilder.jsx        # Q-Matrix Multi-Skill Editor, DAG Controls & Bulk Import
│   │   │   ├── TakeTest.jsx           # Millisecond Client Telemetry Capture
│   │   │   ├── DiagnosticReport.jsx   # Student Dossier, Learning Roadmap & Effort Quadrants
│   │   │   └── TestResults.jsx        # Cohort Heatmap, Psychometrics & AI Intervention
│   │   └── App.jsx                    # Route Configuration
│   └── package.json                   # Frontend dependencies (React, Vite, Lucide-React, Axios)
├── advanced_ml_analytics_technical_report.tex # Formal Academic Technical Report (LaTeX)
├── advanced_ml_analytics_technical_report.pdf # Publication-Grade PDF with LaTeX Math
├── TEACHERS_PANEL_PRESENTATION_GUIDE.md       # Presentation Dossier & Defense Q&A
├── sample_15_tests_bulk_import.txt            # 15 Formatted Tests for 1-Click Bulk Import
└── ai_curriculum_15_topics_guide.md           # 15 Grounded AI Curriculum Topics
```

---

## 5. Summary of Teacher Capabilities

1. **Topological Curriculum Authoring:** Graph visualizer prevents circular dependencies and models strict prerequisites.
2. **Q-Matrix Multi-Skill Tagging:** Maps compound questions to multiple skills for fine-grained diagnosis.
3. **Cohort Mastery Heatmap:** Instant color-coded matrix of every student across all curriculum concepts.
4. **Item Psychometric Quality Badges:** Automatically identifies strong vs defective test questions using $r_{pb}$.
5. **Distractor Magnet Flags:** Discovers which wrong options acted as deceptive traps and reveals student misconceptions.
6. **Cohort Bottleneck Detection:** Isolates root blocker concepts dragging down class-wide pass rates.
7. **Agentic Closed-Loop Intervention:** AI writes teaching briefings and synthesizes editable remedial quizzes dispatched with one click to selected struggling students.

---

## 6. Installation & Local Execution

### Prerequisites
* Python 3.10+
* Node.js 18+
* PostgreSQL or Supabase account

### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend API interactive documentation is available at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend application will be accessible at `http://localhost:5173`.

---

## 7. Verification & Testing

To seed a complete sample test with multi-skill Q-matrix mappings, prerequisite DAG links, and automatic student assignment, execute:

```bash
# Inside backend directory with active virtual environment:
python seed_dsa_diagnostic_test.py
```

To run frontend production build validation:
```bash
cd frontend
npm run build
```

---

## 8. Academic Citation & Documentation References
* **De La Torre, J. (2009).** DINA Model and Parameter Estimation: A Didactic. *Journal of Educational and Behavioral Statistics*, 34(1), 115–130.
* **Corbett, A. T., & Anderson, J. R. (1995).** Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge. *User Modeling and User-Adapted Interaction*, 4(4), 253–278.
* **Wise, S. L., & Kong, X. (2005).** Response Time Effort: A New Measure of Examinee Motivation in Computer-Based Tests. *Applied Measurement in Education*, 18(2), 163–183.
* **Junker, B. W., & Sijtsma, K. (2001).** Cognitive Assessment Models with Few Assumptions: DINA and NIDA. *Applied Psychological Measurement*, 25(3), 258–272.
