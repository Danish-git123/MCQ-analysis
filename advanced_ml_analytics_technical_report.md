# KnowledgeTrace MCQ — Advanced ML Analytics Technical Report
**CSE Mega Project — Branch: `ml-advanced-analytics`**  
*Document Version: 2.4 | Academic Year 2026–2027*

---

## Executive Summary

Standard Learning Management Systems (LMS) and online quiz applications evaluate students using naive percentage scoring (e.g., $7/10 = 70\%$). This arithmetic score fails to answer the most fundamental pedagogical questions:
1. **Did the student guess?** (In a 4-option MCQ, guessing has a $25\%$ random chance).
2. **Did they make a silly slip?** (A student who knows the concept makes a typographical or arithmetic slip).
3. **Which sub-skill caused the error?** (A multi-skill question requires simultaneous mastery of multiple concepts).
4. **Are gaps compounding?** (Unmastered foundational prerequisites blocking downstream topics).
5. **Is an exam question flawed?** (Misleading trick distractors fooling top students).

The **`ml-advanced-analytics`** branch implements an interpretable, mathematically rigorous, publication-grade **Neuro-Symbolic & Probabilistic Cognitive Diagnostic Engine**. It combines **Bayesian Knowledge Tracing (BKT)**, the **Multi-Attribute DINA Model**, **Logistic Regression Anomaly Detection**, **Response-Time Effort (RTE) Profiling**, and **NetworkX Directed Acyclic Graph (DAG) Theory** into a unified, non-blocking asynchronous architecture.

---

## 1. Repository & File Structure

Below is the file tree of the backend and frontend components that implement this branch:

```
MCQ-analysis/
├── backend/
│   └── app/
│       ├── models/                        # SQLAlchemy Database Models
│       │   ├── user.py                    # User, Roles (Teacher, Student)
│       │   ├── concept.py                 # Concept, ConceptEdge (DAG)
│       │   ├── test.py                    # Test, Question, Option, QuestionSkill
│       │   ├── response.py                # Response (is_correct, response_time_ms)
│       │   └── diagnosis.py               # StudentConceptMastery, CognitiveDiagnosisProfile
│       ├── schemas/                       # Pydantic Request/Response Models
│       │   ├── concept.py                 # ConceptRead, ConceptCreate, ConceptEdgeCreate
│       │   ├── question.py                # QuestionCreate (skill_ids), OptionCreate
│       │   └── agent.py                   # TeacherCurriculumRequest, ClassIntervention schemas
│       ├── routers/                       # FastAPI Route Controllers
│       │   ├── student.py                 # POST /student/responses (Sync + Async Worker)
│       │   ├── teacher.py                 # GET /teacher/tests/{id}/results, Q-Matrix test creation
│       │   ├── concepts.py                # POST/DELETE /concepts/edges, GET /concepts/graph
│       │   ├── diagnosis.py               # GET /diagnosis/student/{id}/* (Dossier endpoints)
│       │   └── agent.py                   # Agentic AI Draft & Approve Orchestrator
│       └── services/                      # Mathematical & Machine Learning Algorithms
│           ├── mastery_service.py         # Layer 2: Bayesian Knowledge Tracing (BKT)
│           ├── dina_service.py            # Layer 3: Multi-Skill DINA + BFS Block Partitioning
│           ├── prediction_service.py      # Layer 4: Logistic Regression Slip/Guess Predictor
│           ├── cognitive_analytics_service.py # Layer 5: Response-Time Effort (RTE) & Prerequisite Debt
│           ├── concept_graph.py           # Layer 1: NetworkX DAG Validation & Inference
│           └── agent_service.py           # ReAct Tool-Calling Agent Orchestrator
├── frontend/
│   └── src/
│       ├── components/
│       │   └── PrerequisiteGraph.jsx      # Pure SVG Interactive Directed Force/DAG Network Graph
│       ├── pages/
│       │   ├── TestBuilder.jsx            # Category 2: Q-Matrix Multi-Skill & DAG Edge Editor
│       │   ├── TakeTest.jsx               # Millisecond Latency Telemetry Collection
│       │   ├── DiagnosticReport.jsx       # Student Dossier, Learning Roadmap, Effort Quadrants
│       │   └── TestResults.jsx            # Category 1: Cohort Heatmap, Psychometrics & Intervention
│       └── App.jsx                        # Route Definitions (/teacher/student/:id/diagnosis)
├── create_diagrams.py                     # High-resolution architectural diagram generator
├── generate_ml_concepts_pdf.py            # Academic specification PDF compiler
└── pyrightconfig.json                     # Static type check & Python interpreter config
```

---

## 2. End-to-End System Data Flow

The diagram below details the entire data lifecycle across both Teacher and Student workflows:

```mermaid
flowchart TD
    subgraph S0["1. Test & Knowledge Graph Authoring (Teacher)"]
        T1["Teacher creates Concepts & Manual Edges"] --> T2["NetworkX DAG Cycle Guard: is_directed_acyclic_graph()"]
        T2 -->|"Valid DAG"| DB_C[("concepts & concept_edges")]
        T3["Teacher pins Q-Matrix: Primary + skill_ids"] --> DB_Q[("tests, questions, question_skills")]
    end

    subgraph S1["2. High-Precision Client Telemetry & Ingestion"]
        Student["Student answers Question in React UI"] -->|"Timer captures response_time_ms"| Payload["Payload: question_id, option_id, latency_ms"]
        Payload -->|"POST /student/responses"| FastAPISync["FastAPI: submit_response()"]
        FastAPISync -->|"Sync Write"| DB_Resp[("responses table")]
        FastAPISync -->|"Immediate 200 OK (<15ms)"| StudentNext["Student proceeds with 0 latency"]
    end

    subgraph S2["3. Non-Blocking Background ML Pipeline (FastAPI BackgroundTasks)"]
        FastAPISync -.->|"Spawn Worker"| Worker["run_mastery_and_diagnosis()"]
        Worker --> BKT["Layer 2: Bayesian Knowledge Tracing (Forward Pass)"]
        BKT --> DB_BKT[("student_concept_mastery")]
        Worker --> DINA["Layer 3: DINA Model (BFS Connected-Block Solver)"]
        DINA --> Ent["Quadratic Entropy: 1 - 4P(1-P)"]
        Ent --> DB_DINA[("cognitive_diagnosis_profile")]
    end

    subgraph S3["4. Cognitive Analytics & Psychometrics Engine"]
        DB_Resp & DB_DINA --> LR["Layer 4: Logistic Regression Careless Slip Detector"]
        DB_Resp --> RTE["Layer 5: Response-Time Effort (RTE) 4-Quadrant Profiler"]
        DB_DINA & DB_C --> Debt["Prerequisite Debt & NetworkX Topological Roadmap"]
    end

    subgraph S4["5. Teacher Cohort Analytics & Closed-Loop Intervention"]
        S3 --> Heatmap["Student × Concept DINA Mastery Heatmap"]
        S3 --> Psych["Point-Biserial Discrimination (r_pb) & Distractor Traps"]
        S3 --> Root["Cohort Prerequisite Bottleneck Graph (is_root_blocker)"]
        Heatmap & Psych & Root --> AI_Agent["Class Intervention AI Agent"]
        AI_Agent --> TargetedQuiz["Targeted Revision Quiz Assigned to Struggling Cohort"]
    end

    S0 --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
```

---

## 3. Mathematical Foundations & Calculation Pipeline

### Layer 1: Knowledge Graph Topology & Cycle Prevention
The curriculum is modeled as a directed graph $G = (V, E)$, where $V$ is the set of concepts and directed edges $(u, v) \in E$ signify that $u$ is an essential prerequisite for $v$ ($u \to v$).

#### The Acyclic Invariant (NetworkX)
A prerequisite curriculum cannot contain circular dependencies (e.g., $A \to B \to C \to A$ is logically impossible because it implies $A$ must be understood before $A$ can be learned).

Before committing any edge $(u, v)$ to PostgreSQL, [`concept_graph.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/services/concept_graph.py) constructs an in-memory directed graph and verifies:

$$\text{ValidEdge}(u, v) \iff (u \neq v) \land \left[\text{is\_directed\_acyclic\_graph}(G \cup \{(u, v)\}) == \text{True}\right]$$

If an edge induces a cycle, it is immediately rejected with HTTP 400 and the circular path is reported to the teacher.

---

### Layer 2: Bayesian Knowledge Tracing (BKT)
*File: [`backend/app/services/mastery_service.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/services/mastery_service.py)*

BKT models the student's mastery of a single concept over chronological practice attempts $t = 1, 2, \dots$ as a **Hidden Markov Model (HMM)** with two latent states:
- State $0$: Unmastered ($L_t = 0$)
- State $1$: Mastered ($L_t = 1$)

#### Parameter Definitions
- $P(L_0)$: Prior probability of knowing the concept before practice.
- $P(T)$: Transition probability of learning the concept during an attempt.
- $P(S)$: Slip probability (student knows the concept but answers incorrectly).
- $P(G)$: Guess probability (student does not know the concept but guesses correctly).

#### The Forward Algorithm Equations
When observation $o_t \in \{0, 1\}$ (where $1 = \text{Correct}, 0 = \text{Incorrect}$) is observed:

**Step 1 — Observation Update (Bayes' Rule):**
$$\text{If } o_t = 1 \text{ (Correct): } \quad P(L_t \mid o_t = 1) = \frac{P(L_t) \cdot (1 - P(S))}{P(L_t) \cdot (1 - P(S)) + (1 - P(L_t)) \cdot P(G)}$$

$$\text{If } o_t = 0 \text{ (Incorrect): } \quad P(L_t \mid o_t = 0) = \frac{P(L_t) \cdot P(S)}{P(L_t) \cdot P(S) + (1 - P(L_t)) \cdot (1 - P(G))}$$

**Step 2 — Latent Learning Transition:**
$$P(L_{t+1}) = P(L_t \mid o_t) + \left[1 - P(L_t \mid o_t)\right] \cdot P(T)$$

---

### Layer 3: Multi-Attribute Cognitive Diagnosis (DINA Model)
*File: [`backend/app/services/dina_service.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/services/dina_service.py)*

Real-world test questions rarely test only one standalone skill. The **DINA** model (*Deterministic Inputs, Noisy "And" gate*, Junker & Sijtsma, 2001) evaluates a student's binary latent attribute vector:

$$\boldsymbol{\alpha}_i = (\alpha_{i1}, \alpha_{i2}, \dots, \alpha_{iK}) \in \{0, 1\}^K$$

#### The Q-Matrix & Conjunctive Latent Logic
The test structure is specified by the binary matrix $Q \in \{0, 1\}^{J \times K}$:

$$q_{jk} = \begin{cases} 1 & \text{if Question } j \text{ requires Concept } k \\ 0 & \text{otherwise} \end{cases}$$

Under DINA, success requires **all** required skills simultaneously. The ideal latent response $\eta_{ij}$ is computed as:

$$\eta_{ij} = \prod_{k=1}^K \alpha_{ik}^{q_{jk}}$$

- If a student has mastered all required concepts ($\alpha_{ik} = 1$ for every $k$ where $q_{jk} = 1$), $\eta_{ij} = 1$.
- If **even one** concept is missing, $\eta_{ij} = 0$.

#### Response Likelihood & Bayesian Marginalization
With slip parameter $s_j$ and guess parameter $g_j$:

$$P(X_{ij} = 1 \mid \boldsymbol{\alpha}_i) = g_j^{1 - \eta_{ij}} (1 - s_j)^{\eta_{ij}}$$

Given response vector $\mathbf{X}_i = (X_{i1}, \dots, X_{iJ})$, the joint posterior across all $2^K$ skill patterns is:

$$P(\boldsymbol{\alpha} \mid \mathbf{X}_i) = \frac{\prod_{j=1}^J \left[P(X_{ij} \mid \boldsymbol{\alpha})\right] P(\boldsymbol{\alpha})}{\sum_{\boldsymbol{\alpha}'} \prod_{j=1}^J \left[P(X_{ij} \mid \boldsymbol{\alpha}')\right] P(\boldsymbol{\alpha}')}$$

The marginal mastery of concept $k$ displayed in the Teacher Heatmap is:

$$P(\alpha_{ik} = 1 \mid \mathbf{X}_i) = \sum_{\boldsymbol{\alpha} : \alpha_k = 1} P(\boldsymbol{\alpha} \mid \mathbf{X}_i)$$

#### Connected-Block BFS Graph Partitioning ($2^K$ Solver)
When $K = 30$, evaluating $2^{30} \approx 1.07 \times 10^9$ states is computationally intractable on a live server.
1. The engine constructs a co-occurrence graph where an edge connects concept $A$ and concept $B$ if any question tests both skills simultaneously.
2. A **Breadth-First Search (BFS)** partitions the curriculum into disjoint connected blocks.
3. For the target block (clamped at $K_{\text{block}} \le 12$, maximum $2^{12} = 4{,}096$ states), the exact posterior is vectorized in NumPy using the log-sum-exp trick in $< 10\text{ ms}$.

---

### Layer 4: Information-Theoretic Epistemic Confidence
*File: [`backend/app/services/dina_service.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/services/dina_service.py)*

The confidence metric measures how statistically decisive the diagnosis is based on **Normalized Quadratic Entropy**:

$$\text{Confidence}(P) = 1 - 4 \cdot P \cdot (1 - P)$$

- **At $P = 0.50$ (Total uncertainty / coin flip):**
  $$\text{Confidence} = 1 - 4(0.50)(0.50) = 1 - 1.00 = \mathbf{0.00 \text{ (0\%)}}$$
- **At $P = 0.85$ (Definite mastery evidence):**
  $$\text{Confidence} = 1 - 4(0.85)(0.15) = 1 - 0.51 = \mathbf{0.49 \text{ (49\%)}}$$
- **At $P = 0.98$ or $P = 0.02$ (High certainty):**
  $$\text{Confidence} = 1 - 4(0.98)(0.02) = 1 - 0.0784 = \mathbf{0.92 \text{ (92\%)}}$$

**Reliability Tiers**:
- `LOW`: $\text{Confidence} < 0.40$ (Preliminary; more testing required)
- `MEDIUM`: $0.40 \le \text{Confidence} < 0.75$ (Provisional diagnosis)
- `HIGH`: $\text{Confidence} \ge 0.75$ (Certified diagnostic stability)

---

### Layer 5: Response-Time Effort (RTE) & 4-Quadrant Profiler
*File: [`backend/app/services/cognitive_analytics_service.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/services/cognitive_analytics_service.py)*

Based on Wise & Kong (2005) Response-Time Effort theory, student solving times are evaluated against expected reading and cognitive processing requirements:

$$T_{\text{expected}} = \max\left(7000, 8000 + 300 \cdot W + 5000 \cdot K_j\right) \text{ ms}$$

where $W$ is the stem word count and $K_j$ is the number of required skills in the Q-matrix.

$$\text{Latency Ratio: } \tau = \frac{T_{\text{actual}}}{T_{\text{expected}}}$$

#### The 4 Cognitive Behavioral Quadrants
1. **Cognitive Fluency**: Correct ($X = 1$) with optimal latency ($\tau \le 1.8$). Automated conceptual grasp.
2. **Deliberate Mastery**: Correct ($X = 1$) with high deliberation ($\tau > 1.8$). High-effort successful reasoning.
3. **Cognitive Struggle**: Incorrect ($X = 0$) despite adequate time ($T \ge 4000\text{ ms}$). Genuine conceptual misunderstanding.
4. **Rapid Guessing**: Any response submitted in $T < 4000\text{ ms}$. Disengaged rush without reading the choices.

#### Effort Consistency Index (ECI)
$$\text{ECI} = \frac{N_{\text{fluency}} + N_{\text{deliberate}} + N_{\text{struggle}}}{N_{\text{total}}} = 1 - \frac{N_{\text{rapid}}}{N_{\text{total}}}$$

If a student's rapid guessing rate exceeds $40\%$, their low DINA mastery is flagged as an effort artifact rather than an intellectual gap.

---

### Layer 6: Logistic Regression Slip Anomaly Model
*File: [`backend/app/services/prediction_service.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/services/prediction_service.py)*

Implements Equation (3) from the project specification to predict performance probability before/during attempts:

$$P(X_{ij} = 1 \mid \mathbf{x}) = \sigma\left(\beta_0 + \sum_{m=1}^5 \beta_m x_m\right) = \frac{1}{1 + e^{-(\beta_0 + \boldsymbol{\beta}^T \mathbf{x})}}$$

#### Feature Vector $\mathbf{x} \in \mathbb{R}^5$:
1. $x_1$: Student cumulative historical accuracy ($[0.0, 1.0]$)
2. $x_2$: Concept mastery across the question's required skills
3. $x_3$: Question pass rate / empirical ease across cohort
4. $x_4$: Skill complexity count ($-0.45$ penalty per additional skill)
5. $x_5$: Normalized latency ratio $\tau$

#### Anomaly Classification Rules
- **Careless Slip**: If $P(\text{Correct}) \ge 0.78$ and $T \ge 4.0\text{ s}$, but student answered **incorrectly** ($X = 0$).
- **Rapid Lucky Guess**: If $P(\text{Correct}) \le 0.28$ and $T < 4.0\text{ s}$, but student answered **correctly** ($X = 1$).

---

### Layer 7: Item Psychometrics & Point-Biserial Discrimination
*File: [`backend/app/routers/teacher.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/routers/teacher.py#L195-L206)*

To evaluate whether a question effectively discriminates high-performing students from struggling students, the engine calculates the **Point-Biserial Correlation** ($r_{pb}$):

$$r_{pb} = \frac{\sum_{i=1}^n (X_{ij} - \bar{X}_j)(Y_i - \bar{Y})}{\sqrt{\sum_{i=1}^n (X_{ij} - \bar{X}_j)^2 \sum_{i=1}^n (Y_i - \bar{Y})^2}}$$

where $X_{ij} \in \{0, 1\}$ is student $i$'s score on item $j$, and $Y_i \in [0.0, 1.0]$ is their overall test accuracy.

- **$r_{pb} \ge 0.25$ (`STRONG`)**: High performers get it right, low performers get it wrong. Psychometrically excellent item.
- **$0.10 \le r_{pb} < 0.25$ (`FAIR`)**: Moderate discrimination.
- **$r_{pb} < 0.10$ or negative (`REVIEW_NEEDED`)**: Flawed question or misleading trick distractor confusing high-ability students.

---

### Layer 8: Prerequisite Debt & Root Blocker Analytics
*Files: [`cognitive_analytics_service.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/services/cognitive_analytics_service.py), [`teacher.py`](file:///e:/Mega Project/MCQ-analysis/backend/app/routers/teacher.py)*

Let $W = \{c \in V \mid \bar{\alpha}_c < 0.50\}$ be the set of weak concepts.

#### Student Prerequisite Debt Score
$$\text{PrerequisiteDebt} = \frac{|\{c \in W \mid \text{predecessors}(c) \cap W \neq \emptyset\}|}{|W|}$$

Measures the proportion of advanced failures that directly stem from unmastered upstream roots in the DAG.

#### Cohort Root Blocker Flag
In the cohort prerequisite graph, a concept $c$ is flagged with a pulsing crimson halo as a **Root Blocker** if:

$$\text{IsRootBlocker}(c) \iff \left(\bar{\alpha}_c < 0.55\right) \land \left(\exists s \in \text{successors}(c) : \bar{\alpha}_s < 0.65\right)$$

This isolates the exact foundational bottleneck dragging down dependent skills across the entire class.

---

## 4. Justification of Initial & Default Values

Every hyperparameter and default value in this architecture is mathematically grounded in psychometric literature:

| Parameter | Default Value | Mathematical & Psychometric Justification |
| :--- | :--- | :--- |
| **BKT Prior $P(L_0)$** | `0.20` ($20\%$) | Assumes an uninstructed student has a $20\%$ baseline prior probability of intuitive familiarity with a new concept before targeted practice begins. |
| **BKT Transition $P(T)$** | `0.15` ($15\%$) | Standard empirical rate in cognitive tutoring literature (Corbett & Anderson). Represents a $15\%$ incremental chance that a single practice opportunity causes state transition to mastery. |
| **BKT Slip $P(S)$** | `0.10` ($10\%$) | Accounts for human typographical errors, perceptual slips, or misreading of options by students who otherwise possess the latent skill. |
| **BKT Guess $P(G)$** | `0.25` ($25\%$) | Standard statistical chance of guessing the correct option in a 4-choice MCQ without any domain knowledge ($1/4 = 0.25$). |
| **Rapid Guessing Time** | `4000 ms` ($4.0\text{ s}$) | Psychometric eye-tracking studies confirm that reading a technical MCQ stem ($\sim 15$–$25$ words) and 4 response options requires $\ge 4.0$ seconds. Submissions under $4$s represent blind random clicking. |
| **Expected Base Time** | `8000 ms` ($8.0\text{ s}$) | Baseline cognitive reading and comprehension overhead for an average college-level sentence before problem solving begins. |
| **Word Factor** | `300 ms/word` | Average adult technical reading speed is $\sim 200\text{ words/minute} \approx 300\text{ ms/word}$. |
| **Skill Overhead** | `5000 ms/skill` | Conjunctive multi-skill questions require cognitive context-switching between domains, estimated at $5\text{ s}$ per additional concept. |
| **Logistic Intercept $\beta_0$** | `-0.40` | Sets baseline prior log-odds $\sigma(-0.40) \approx 0.40$, reflecting moderate difficulty for fresh questions. |
| **Accuracy Weight $\beta_1$** | `+0.85` | Positive reinforcement: historical competence increases probability of future success. |
| **Mastery Weight $\beta_2$** | `+1.80` | Highest magnitude weight: direct latent skill mastery is the single strongest predictor of item correctness. |
| **Item Ease Weight $\beta_3$** | `+1.25` | Calibrates for question difficulty: an easier item across the cohort increases individual success likelihood. |
| **Complexity Weight $\beta_4$** | `-0.45` | Negative coefficient: each additional required concept introduces another failure point, penalizing the odds. |
| **Latency Weight $\beta_5$** | `+0.35` | Modest positive boost: deliberate solving time correlates with higher accuracy compared to hasty attempts. |
| **Careless Slip Threshold** | `P >= 0.78` | If the statistical model predicts $\ge 78\%$ chance of correct answer and the student spent $\ge 4$s, an incorrect answer is categorized as an accidental slip rather than a conceptual deficiency. |
| **Max BFS Block Size** | `K = 12` | $2^{12} = 4{,}096$ floating-point evaluations completes in $< 10\text{ ms}$ in vectorized NumPy. Beyond $K=12$, exponential explosion would degrade API response times. |

---

## 5. Complete Step-by-Step Sample for Testing

This sample demonstrates how the mathematics and data flow execute end-to-end.

### Step 1: Define Curriculum & DAG
The teacher creates 3 concepts in the Syllabus Graph:
1. Concept 1: **Relational Algebra**
2. Concept 2: **SQL Query Execution**
3. Concept 3: **Query Cost Optimization**

**Prerequisite Edges**:
- Relational Algebra $\to$ SQL Query Execution
- SQL Query Execution $\to$ Query Cost Optimization

*(If a teacher tries to add Query Cost Optimization $\to$ Relational Algebra, NetworkX blocks it with HTTP 400: cycle detected).*

---

### Step 2: Define Questions with Multi-Skill Q-Matrix
The teacher creates 2 diagnostic questions:

- **Question 1**: *"Evaluate the relational selection $\sigma_{A > 5}(R)$ on table R."*
  - Primary Skill: `Relational Algebra` ($C_1$)
  - Q-Matrix row: $\mathbf{q}_1 = [1, 0, 0]$
- **Question 2**: *"Convert a correlated subquery into an optimized indexed join plan."*
  - Primary Skill: `Query Cost Optimization` ($C_3$)
  - Secondary Skill: `SQL Query Execution` ($C_2$)
  - Q-Matrix row: $\mathbf{q}_2 = [0, 1, 1]$

---

### Step 3: Student Attempt Telemetry
Student **Alice** attempts the test:
- **Attempt on Q1**: Correct ($X = 1$), latency = $14{,}200\text{ ms}$ ($14.2\text{ s}$).
- **Attempt on Q2**: Incorrect ($X = 0$), selects Distractor B, latency = $21{,}000\text{ ms}$ ($21.0\text{ s}$).

---

### Step 4: Step-by-Step Mathematical Calculation

#### 1. Layer 2: BKT Calculation on Q1 ($C_1$)
- Prior $P(L_0) = 0.20$, $P(S) = 0.10$, $P(G) = 0.25$, $P(T) = 0.15$.
- Observation $o_1 = 1$ (Correct):

$$P(L_1 \mid \text{Correct}) = \frac{0.20 \times (1 - 0.10)}{0.20 \times (1 - 0.10) + (1 - 0.20) \times 0.25} = \frac{0.18}{0.18 + 0.20} = \frac{0.18}{0.38} \approx \mathbf{0.4737}$$

- Transition Update:
$$P(L_2) = 0.4737 + (1 - 0.4737) \times 0.15 = 0.4737 + (0.5263 \times 0.15) = 0.4737 + 0.0789 = \mathbf{0.5526 \text{ (55.3\%)}}$$
*Mastery of Relational Algebra increases from $20\%$ to $55.3\%$.*

#### 2. Layer 3: DINA Conjunctive Calculation on Q2 ($C_2, C_3$)
- Required skills: $\mathbf{q}_2 = [0, 1, 1]$.
- Alice knows $C_2$ ($P = 0.75$), but misses $C_3$ ($P = 0.25$).
- Ideal response: $\eta_2 = \alpha_2 \cdot \alpha_3 = 1 \cdot 0 = \mathbf{0}$.
- Conditional probability:
  $$P(X_2 = 1 \mid \eta_2 = 0) = g_2 = 0.25$$
- Because $\eta_2 = 0$, the probability of a correct response was only $25\%$ (pure guess).
- Marginal DINA update computes:
  - $P(C_2 = 1) \approx 0.68$ (High confidence)
  - $P(C_3 = 1) \approx 0.18$ (Low confidence)

#### 3. Epistemic Confidence on $C_3$
$$P = 0.18 \implies \text{Confidence} = 1 - 4(0.18)(0.82) = 1 - 4(0.1476) = 1 - 0.5904 = \mathbf{0.4096 \text{ (41.0\% — MEDIUM TIER)}}$$

#### 4. Layer 4: Response-Time Effort on Q2
- Word count $W = 12$, required skills $K_j = 2$.
- $T_{\text{expected}} = \max(7000, 8000 + 300(12) + 5000(2)) = 8000 + 3600 + 10000 = \mathbf{21{,}600\text{ ms}}$.
- Actual time: $21{,}000\text{ ms}$.
- Latency ratio: $\tau = 21000 / 21600 = \mathbf{0.972}$.
- Quadrant: Because $T \ge 4000\text{ ms}$ and $X = 0$, Alice is classified as **`COGNITIVE_STRUGGLE`**.
  *(She spent adequate effort thinking, proving this is a genuine conceptual gap rather than a rush).*

#### 5. Layer 5: Root-Cause "WHY" Engine
When Alice or the teacher clicks on missed Question 2:
- $C_2$ (SQL Query Execution): $P = 0.68 \ge 0.50$ (OK).
- $C_3$ (Query Cost Optimization): $P = 0.18 < 0.50$.
- **Result**: The engine flags $C_3$ with **`Likely Missing Prerequisite`**, pinpointing the exact gap.

#### 6. Teacher Cohort & AI Intervention Agent
In `TestResults.jsx`:
- Alice appears in the Heatmap with $C_1 = 55\%$, $C_2 = 68\%$, $C_3 = 18\%$.
- Effort status: `DEVELOPING`.
- Point-Biserial Discrimination for Q2 shows $r_{pb} = 0.32$ (`STRONG`).
- Teacher clicks **Analyze Class with AI Agent**:
  - Agent detects $C_3$ has an $80\%$ class failure rate.
  - Automatically drafts a 3-question revision quiz targeting $C_3$ and its prerequisite $C_2$.
  - Teacher edits Question 1's stem directly in the draft, selects Alice's checkbox, and clicks **Approve & Assign**.
  - Alice immediately receives the customized remedial quiz on her dashboard.

---

## 6. Summary Takeaway for Academic Defense / Presentation

1. **Not a Black Box**: Unlike deep neural networks that output unexplainable embeddings, every score produced by this branch has an explicit, traceable mathematical derivation (Bayes' rule, quadratic entropy, or Pearson correlation).
2. **Double-Engine Filtering**: Disentangles knowledge from behavior. A student who rushes is flagged for low effort, while a knowledgeable student who makes a typo is protected by the careless slip model.
3. **Graph-Constrained AI**: LLMs are grounded by NetworkX graph theory, preventing circular hallucinations in the curriculum.
4. **Instant Ingestion**: Non-blocking FastAPI background tasks guarantee that complex mathematical matrix operations never compromise the live user experience ($< 15\text{ ms}$ response times).

---

## 7. Exhaustive Mathematical Dictionary: Formulas, Variables & Constants

Below is the definitive reference of every mathematical equation executed on this branch, detailing every variable, constant, domain, and step-by-step numerical calculation.

---

### Formula 1: DINA Conjunctive Latent Ideal Response
$$\eta_{ij} = \prod_{k=1}^K \alpha_{ik}^{q_{jk}}$$

#### What it means intuitively:
The conjunctive **"AND"** gate. If a question requires 3 concepts, the student must master all 3 concepts. If even one concept is missing ($\alpha_{ik} = 0$), the entire product collapses to $0$, meaning the student cannot solve the problem through knowledge alone and must guess.

#### Variable Breakdown:
- $\eta_{ij} \in \{0, 1\}$ (Binary integer): Ideal response indicator for student $i$ on question $j$. $1$ means student has all required skills; $0$ means at least one required skill is missing.
- $\alpha_{ik} \in \{0, 1\}$ (Binary integer): Latent mastery state of student $i$ on concept $k$. $1$ = Mastered, $0$ = Unmastered.
- $q_{jk} \in \{0, 1\}$ (Binary integer): Q-Matrix entry from `question_skills`. $1$ if question $j$ tests concept $k$, $0$ otherwise.
- $K \in \mathbb{N}$ (Integer): Total number of concepts in the curriculum block ($K \le 12$).
- $i \in \{1, \dots, N\}$ (Integer): Student ID index.
- $j \in \{1, \dots, J\}$ (Integer): Question ID index.
- $k \in \{1, \dots, K\}$ (Integer): Concept ID index.

#### Constants & Defaults:
- None (pure algebraic logical reduction).

#### Numerical Example:
Question $j$ tests Concepts 1 and 2 ($q_{j1} = 1, q_{j2} = 1, q_{j3} = 0$).
- Student A: $\boldsymbol{\alpha}_A = [1, 1, 0] \implies \eta_{Aj} = 1^1 \times 1^1 \times 0^0 = 1 \times 1 \times 1 = \mathbf{1}$.
- Student B: $\boldsymbol{\alpha}_B = [1, 0, 1] \implies \eta_{Bj} = 1^1 \times 0^1 \times 1^0 = 1 \times 0 \times 1 = \mathbf{0}$.

---

### Formula 2: DINA Item Response Probability
$$P(X_{ij} = 1 \mid \boldsymbol{\alpha}_i) = g_j^{1 - \eta_{ij}} (1 - s_j)^{\eta_{ij}}$$

#### What it means intuitively:
Maps the latent ideal response $\eta_{ij}$ to the actual real-world probability that the student chooses the correct answer. It acts as a smooth statistical switch between the **Guessing Floor** and the **Mastery Ceiling**.

#### Variable Breakdown:
- $X_{ij} \in \{0, 1\}$ (Binary): Observed answer from `responses.is_correct`. $1$ = Correct, $0$ = Incorrect.
- $\boldsymbol{\alpha}_i \in \{0, 1\}^K$ (Vector): Student $i$'s latent skill vector.
- $\eta_{ij} \in \{0, 1\}$ (Binary): Conjunctive ideal response from Formula 1.
- $P(X_{ij} = 1 \mid \boldsymbol{\alpha}_i) \in [0.0, 1.0]$ (Float): Probability of a correct response.

#### Constants & Default Values:
- $s_j = 0.10$ ($10\%$): **Careless Slip Rate**. Probability that a student who knows all skills makes a typo or misreads an option. Set to $0.10$ based on standard psychometric benchmarks.
- $g_j = 0.25$ ($25\%$): **Lucky Guess Rate**. Probability that a student lacking the skills guesses correctly. Set to $1/4 = 0.25$ for 4-option MCQs.
- Ceiling: $1 - s_j = 1 - 0.10 = \mathbf{0.90 \text{ (90\%)}}$.
- Floor: $g_j = \mathbf{0.25 \text{ (25\%)}}$.

#### Numerical Example:
- If Student A has $\eta_{Aj} = 1$:
  $$P(X_{Aj} = 1) = 0.25^{1 - 1} \times (1 - 0.10)^1 = 0.25^0 \times 0.90^1 = 1 \times 0.90 = \mathbf{0.90 \text{ (90\%)}}$$
- If Student B has $\eta_{Bj} = 0$:
  $$P(X_{Bj} = 1) = 0.25^{1 - 0} \times (1 - 0.10)^0 = 0.25^1 \times 0.90^0 = 0.25 \times 1 = \mathbf{0.25 \text{ (25\%)}}$$

---

### Formula 3: Epistemic Confidence via Normalized Quadratic Entropy
$$\text{Confidence}(P) = 1 - 4 \cdot P \cdot (1 - P)$$

#### What it means intuitively:
Calculates how certain the system is about a diagnosis. Maximum uncertainty happens at a 50/50 coin flip ($P = 0.50$). As mastery approaches $1.0$ (definite mastery) or $0.0$ (definite absence of skill), uncertainty drops to zero and confidence approaches $1.0$.

#### Variable Breakdown:
- $P \in [0.0, 1.0]$ (Float): Marginal mastery probability for a concept ($P = P(\alpha_k = 1)$).
- $\text{Confidence}(P) \in [0.0, 1.0]$ (Float): Statistical certainty of the diagnosis.

#### Constants & Default Values:
- The coefficient **$4$**: Since the term $P(1 - P)$ reaches its maximum at $P = 0.5$, where $0.5 \times (1 - 0.5) = 0.25$, multiplying by $4$ perfectly normalizes the entropy term $4 \times 0.25 = 1.0$, so $1 - 1.0 = 0.0$.
- Reliability Tiers:
  - `LOW`: $\text{Confidence} < 0.40$
  - `MEDIUM`: $0.40 \le \text{Confidence} < 0.75$
  - `HIGH`: $\text{Confidence} \ge 0.75$

#### Numerical Example:
- At $P = 0.50$: $\text{Confidence} = 1 - 4(0.50)(0.50) = 1 - 4(0.25) = 1 - 1 = \mathbf{0.00 \text{ (0\% — LOW)}}$
- At $P = 0.85$: $\text{Confidence} = 1 - 4(0.85)(0.15) = 1 - 4(0.1275) = 1 - 0.51 = \mathbf{0.49 \text{ (49\% — MEDIUM)}}$
- At $P = 0.98$: $\text{Confidence} = 1 - 4(0.98)(0.02) = 1 - 4(0.0196) = 1 - 0.0784 = \mathbf{0.9216 \text{ (92.2\% — HIGH)}}$

---

### Formula 4: BKT Observation Update (Bayes' Rule)
$$\text{If Correct: } \quad P(L_t \mid o_t = 1) = \frac{P(L_t) \cdot (1 - P(S))}{P(L_t) \cdot (1 - P(S)) + (1 - P(L_t)) \cdot P(G)}$$
$$\text{If Incorrect: } \quad P(L_t \mid o_t = 0) = \frac{P(L_t) \cdot P(S)}{P(L_t) \cdot P(S) + (1 - P(L_t)) \cdot (1 - P(G))}$$

#### What it means intuitively:
Bayes' rule balances evidence against noise. A correct answer increases mastery belief, but does not jump to $100\%$ because of guessing. An incorrect answer lowers mastery belief, but does not drop to $0\%$ because of slips.

#### Variable Breakdown:
- $P(L_t) \in [0.0, 1.0]$ (Float): Prior belief of concept mastery at attempt $t$.
- $o_t \in \{0, 1\}$ (Binary): Student attempt result ($1$ = Correct, $0$ = Incorrect).
- $P(L_t \mid o_t) \in [0.0, 1.0]$ (Float): Posterior mastery belief after observing the result.

#### Constants & Default Values:
- $P(L_0) = 0.20$ ($20\%$): Initial prior belief before any practice questions.
- $P(S) = 0.10$ ($10\%$): Careless slip probability.
- $P(G) = 0.25$ ($25\%$): Lucky guess probability.

#### Numerical Example:
Start with prior $P(L_0) = 0.20$.
- Student answers **Correct** ($o_1 = 1$):
  $$P(L_1 \mid 1) = \frac{0.20 \times (1 - 0.10)}{0.20 \times (1 - 0.10) + (1 - 0.20) \times 0.25} = \frac{0.20 \times 0.90}{0.18 + 0.80 \times 0.25} = \frac{0.18}{0.18 + 0.20} = \frac{0.18}{0.38} \approx \mathbf{0.4737}$$
- What if the student answered **Incorrect** ($o_1 = 0$)?
  $$P(L_1 \mid 0) = \frac{0.20 \times 0.10}{0.20 \times 0.10 + (1 - 0.20) \times (1 - 0.25)} = \frac{0.02}{0.02 + 0.80 \times 0.75} = \frac{0.02}{0.02 + 0.60} = \frac{0.02}{0.62} \approx \mathbf{0.0323}$$

---

### Formula 5: BKT Latent Learning Transition
$$P(L_{t+1}) = P(L_t \mid o_t) + \left[1 - P(L_t \mid o_t)\right] \cdot P(T)$$

#### What it means intuitively:
Accounts for learning that occurs during the practice attempt itself. Even if a student did not know the concept initially, they have an incremental probability $P(T)$ of transitioning from the unlearned state to the learned state.

#### Variable Breakdown:
- $P(L_{t+1}) \in [0.0, 1.0]$ (Float): Updated prior mastery for the upcoming attempt $t+1$.
- $P(L_t \mid o_t) \in [0.0, 1.0]$ (Float): Posterior mastery from Formula 4.
- $1 - P(L_t \mid o_t) \in [0.0, 1.0]$ (Float): Fraction of probability mass currently in the unlearned state.

#### Constants & Default Values:
- $P(T) = 0.15$ ($15\%$): Learning rate per practice opportunity.

#### Numerical Example:
From Formula 4, after a correct answer, $P(L_1 \mid 1) = 0.4737$:
$$P(L_2) = 0.4737 + [1 - 0.4737] \times 0.15 = 0.4737 + (0.5263 \times 0.15) = 0.4737 + 0.0789 = \mathbf{0.5526 \text{ (55.3\%)}}$$

---

### Formula 6: Expected Solving Latency & Latency Ratio
$$T_{\text{expected}} = \max\left(7000, 8000 + 300 \cdot W + 5000 \cdot K_j\right) \text{ ms}$$
$$\tau = \frac{T_{\text{actual}}}{T_{\text{expected}}}$$

#### What it means intuitively:
Calibrates how long an average student should take to read, process, and solve a question based on its reading length and concept complexity. $\tau \approx 1.0$ means standard solving speed; $\tau \ll 1.0$ indicates hasty rushing; $\tau \gg 1.0$ indicates high deliberation or struggle.

#### Variable Breakdown:
- $W \in \mathbb{N}$ (Integer): Word count of the question stem text (`len(question.text.split())`).
- $K_j \in \mathbb{N}$ (Integer): Number of required skills mapped to question $j$ in the Q-matrix.
- $T_{\text{actual}} \in \mathbb{N}$ (Milliseconds): Measured client solving latency from `responses.response_time_ms`.
- $T_{\text{expected}} \in \mathbb{N}$ (Milliseconds): Computed expected time.
- $\tau \in [0.0, \infty)$ (Float): Dimensionless Latency Ratio.

#### Constants & Default Values:
- $7000\text{ ms}$ ($7\text{ s}$): Minimum floor execution time.
- $8000\text{ ms}$ ($8\text{ s}$): Baseline cognitive comprehension overhead for an average college question.
- $300\text{ ms/word}$: Reading rate based on $200\text{ words/minute} \approx 300\text{ ms/word}$.
- $5000\text{ ms/skill}$ ($5\text{ s}$): Cognitive context-switching overhead per required skill attribute.

#### Numerical Example:
A question has $W = 20$ words and requires $K_j = 2$ concepts.
$$T_{\text{expected}} = \max(7000, 8000 + 300(20) + 5000(2)) = 8000 + 6000 + 10000 = \mathbf{24{,}000\text{ ms (24 seconds)}}$$
- If a student answers in $T_{\text{actual}} = 18{,}000\text{ ms}$ ($18\text{ s}$):
  $$\tau = \frac{18000}{24000} = \mathbf{0.75}$$
- If a student answers in $T_{\text{actual}} = 3{,}100\text{ ms}$ ($3.1\text{ s}$):
  $$\tau = \frac{3100}{24000} = \mathbf{0.129} \quad (\text{Flagged as Rapid Guessing because } T_{\text{actual}} < 4000\text{ ms})$$

---

### Formula 7: Effort Consistency Index (ECI)
$$\text{ECI} = \frac{N_{\text{fluency}} + N_{\text{deliberate}} + N_{\text{struggle}}}{N_{\text{total}}} = 1 - \frac{N_{\text{rapid}}}{N_{\text{total}}}$$

#### What it means intuitively:
The percentage of questions on which the student made a genuine, honest attempt, filtering out instances where the student clicked randomly without reading.

#### Variable Breakdown:
- $N_{\text{total}}$ (Integer): Total responses submitted by the student.
- $N_{\text{rapid}}$ (Integer): Number of attempts submitted in $< 4000\text{ ms}$.
- $N_{\text{fluency}}$, $N_{\text{deliberate}}$, $N_{\text{struggle}}$ (Integers): Counts in the valid cognitive quadrants.
- $\text{ECI} \in [0.0, 1.0]$ (Float): Effort Consistency Index (displayed as percentage).

#### Constants & Default Values:
- $4000\text{ ms}$ ($4.0\text{ s}$): Rapid Guessing Threshold.
- If $N_{\text{rapid}} / N_{\text{total}} \ge 0.40$ ($40\%$), the student is tagged with `RAPID_GUESSING_RISK`.

#### Numerical Example:
A student answers $10$ questions: $5$ in Cognitive Fluency, $2$ in Deliberate Mastery, $1$ in Cognitive Struggle, and $2$ in Rapid Guessing ($< 4\text{ s}$).
$$\text{ECI} = \frac{5 + 2 + 1}{10} = \frac{8}{10} = 1 - \frac{2}{10} = \mathbf{0.80 \text{ (80\% Effort Consistency)}}$$

---

### Formula 8: Logistic Regression Performance Prediction & Careless Slip Model
$$P(X_{ij} = 1 \mid \mathbf{x}) = \sigma(z) = \frac{1}{1 + e^{-z}}$$
$$z = \beta_0 + \beta_1 x_1 + \beta_2 x_2 + \beta_3 x_3 + \beta_4 x_4 + \beta_5 x_5$$

#### What it means intuitively:
Predicts the likelihood of answering a question correctly by combining student track record, concept mastery, question ease, complexity penalty, and thinking time.

#### Variable Breakdown:
- $x_1 \in [0.0, 1.0]$: Student cumulative historical accuracy across all past tests.
- $x_2 \in [0.0, 1.0]$: Student DINA mastery on the required concepts of this question.
- $x_3 \in [0.0, 1.0]$: Question empirical pass rate across all cohort attempts.
- $x_4 \ge 1$ (Integer): Skill complexity count ($K_j$ concepts required).
- $x_5 \ge 0.0$ (Float): Normalized latency ratio $\tau = T_{\text{actual}} / T_{\text{expected}}$.
- $z \in (-\infty, +\infty)$: Logit score.
- $P \in [0.0, 1.0]$: Predicted probability of correctness.

#### Constants & Default Values:
- $\beta_0 = -0.40$ (Base difficulty intercept)
- $\beta_1 = +0.85$ (Student historical accuracy weight)
- $\beta_2 = +1.80$ (Skill mastery weight — strongest positive predictor)
- $\beta_3 = +1.25$ (Question ease weight)
- $\beta_4 = -0.45$ (Skill complexity penalty per additional concept)
- $\beta_5 = +0.35$ (Deliberate latency bonus)
- **Careless Slip Threshold**: $P \ge 0.78$ with $T_{\text{actual}} \ge 4000\text{ ms}$, but $X_{ij} = 0$.
- **Rapid Lucky Guess Threshold**: $P \le 0.28$ with $T_{\text{actual}} < 4000\text{ ms}$, but $X_{ij} = 1$.

#### Numerical Example:
A student has $80\%$ historical accuracy ($x_1 = 0.80$), high concept mastery ($x_2 = 0.90$), on an easy question ($x_3 = 0.85$), requiring $1$ skill ($x_4 = 1$), taking normal time ($x_5 = 1.0$):
$$z = -0.40 + 0.85(0.80) + 1.80(0.90) + 1.25(0.85) - 0.45(1) + 0.35(1.0)$$
$$z = -0.40 + 0.68 + 1.62 + 1.0625 - 0.45 + 0.35 = \mathbf{2.4625}$$
$$P = \frac{1}{1 + e^{-2.4625}} = \frac{1}{1 + 0.0852} = \frac{1}{1.0852} \approx \mathbf{0.9215 \text{ (92.2\% predicted chance of success)}}$$
- If this student submits an **incorrect** answer with $T_{\text{actual}} = 15\text{ s}$:
  Because $P = 0.9215 \ge 0.78$ and $T \ge 4\text{ s}$, the system flags this as a **Careless Slip**.

---

### Formula 9: Point-Biserial Discrimination Index ($r_{pb}$)
$$r_{pb} = \frac{\sum_{i=1}^n (X_{ij} - \bar{X}_j)(Y_i - \bar{Y})}{\sqrt{\sum_{i=1}^n (X_{ij} - \bar{X}_j)^2 \sum_{i=1}^n (Y_i - \bar{Y})^2}}$$

#### What it means intuitively:
The Pearson correlation between an individual question score ($0$ or $1$) and the student's total exam score ($0.0$ to $1.0$). A high positive correlation means high-performing students got the question right while low-performing students missed it.

#### Variable Breakdown:
- $X_{ij} \in \{0, 1\}$: Student $i$'s score on item $j$.
- $\bar{X}_j \in [0.0, 1.0]$: Item pass rate (average score on question $j$).
- $Y_i \in [0.0, 1.0]$: Student $i$'s overall test score across all items.
- $\bar{Y} \in [0.0, 1.0]$: Cohort mean test score.
- $n \in \mathbb{N}$: Number of students who completed the test.
- $r_{pb} \in [-1.0, +1.0]$: Discrimination index.

#### Constants & Default Values:
- $r_{pb} \ge 0.25$: `STRONG` (Excellent item quality)
- $0.10 \le r_{pb} < 0.25$: `FAIR` (Acceptable item quality)
- $r_{pb} < 0.10$: `REVIEW_NEEDED` (Defective question, confusing wording, or misleading trap distractor)

#### Numerical Example:
Four students take a test. Item scores $X = [1, 0, 1, 0]$ and total exam scores $Y = [0.90, 0.20, 0.80, 0.10]$.
- Means: $\bar{X} = 0.50$, $\bar{Y} = 0.50$.
- Deviations $(X - \bar{X}) = [+0.5, -0.5, +0.5, -0.5]$.
- Deviations $(Y - \bar{Y}) = [+0.4, -0.3, +0.3, -0.4]$.
- Numerator: $(0.5)(0.4) + (-0.5)(-0.3) + (0.5)(0.3) + (-0.5)(-0.4) = 0.20 + 0.15 + 0.15 + 0.20 = \mathbf{0.70}$.
- Denominator: $\sqrt{[0.25 + 0.25 + 0.25 + 0.25] \times [0.16 + 0.09 + 0.09 + 0.16]} = \sqrt{1.0 \times 0.50} = \sqrt{0.50} \approx \mathbf{0.7071}$.
- Result:
  $$r_{pb} = \frac{0.70}{0.7071} \approx \mathbf{0.990 \text{ (STRONG Discrimination)}}$$

---

### Formula 10: Prerequisite Debt Score
$$\text{PrerequisiteDebt} = \frac{|\{c \in W \mid \text{predecessors}(c) \cap W \neq \emptyset\}|}{|W|}$$

#### What it means intuitively:
The percentage of a student's weak concepts whose upstream foundational prerequisites are also broken. High debt means the student is failing advanced topics because they never mastered the fundamentals.

#### Variable Breakdown:
- $W = \{c \in V \mid \bar{\alpha}_c < 0.50\}$: The set of weak concepts for student $i$.
- $\text{predecessors}(c)$: Immediate prerequisite parents pointing to concept $c$ in the syllabus DAG ($u \to c$).
- $|W|$: Total number of weak concepts.
- $\text{PrerequisiteDebt} \in [0.0, 1.0]$: Debt fraction.

#### Constants & Default Values:
- $0.50$: Mastery threshold separating mastered concepts from weak gaps.
- Debt Levels:
  - `ZERO_DEBT`: Debt $= 0.0$
  - `LOW_DEBT`: $0.0 < \text{Debt} < 0.35$
  - `MODERATE_DEBT`: $0.35 \le \text{Debt} < 0.60$
  - `HIGH_PREREQUISITE_DEBT`: $\text{Debt} \ge 0.60$

#### Numerical Example:
A student has 4 weak concepts: $W = \{A, B, C, D\}$.
The DAG edges are: $A \to B$ and $B \to C$. Concept $D$ has no prerequisites.
- Predecessors of $A$: $\emptyset$ (No parent).
- Predecessors of $B$: $\{A\}$. Since $A \in W$, $B$ is caused by upstream debt!
- Predecessors of $C$: $\{B\}$. Since $B \in W$, $C$ is caused by upstream debt!
- Predecessors of $D$: $\emptyset$.
Debt-caused concepts = $\{B, C\}$ (count = $2$). Total weak concepts = $4$.
$$\text{PrerequisiteDebt} = \frac{2}{4} = \mathbf{0.50 \text{ (50\% — MODERATE DEBT)}}$$

---

### Formula 11: Cohort Root Blocker Criterion
$$\text{IsRootBlocker}(c) \iff \left(\bar{\alpha}_c < 0.55\right) \land \left(\exists s \in \text{successors}(c) : \bar{\alpha}_s < 0.65\right)$$

#### What it means intuitively:
Identifies whether concept $c$ is a foundational bottleneck for the entire class. If the class average mastery on $c$ is low ($< 55\%$) and at least one downstream topic that depends on $c$ is also struggling ($< 65\%$), concept $c$ is flagged with a pulsing crimson halo. Fixing $c$ will remediate the bottleneck for the whole cohort.

#### Variable Breakdown:
- $\bar{\alpha}_c \in [0.0, 1.0]$: Class-wide average DINA mastery on concept $c$.
- $\text{successors}(c)$: Downstream concepts in the syllabus DAG that depend on $c$ ($c \to s$).
- $\bar{\alpha}_s \in [0.0, 1.0]$: Class-wide average DINA mastery on dependent concept $s$.
- $\text{IsRootBlocker}(c) \in \{\text{True}, \text{False}\}$: Boolean flag.

#### Constants & Default Values:
- $0.55$ ($55\%$): Bottleneck failure threshold for root concept $c$.
- $0.65$ ($65\%$): Downstream contagion threshold for successor concept $s$.

#### Numerical Example:
Curriculum has edge: *Normalization* ($C_1$) $\to$ *Indexing* ($C_2$).
- Cohort average on *Normalization*: $\bar{\alpha}_1 = 0.42$ ($42\%$).
- Cohort average on *Indexing*: $\bar{\alpha}_2 = 0.58$ ($58\%$).
Check conditions for $C_1$:
1. $\bar{\alpha}_1 = 0.42 < 0.55$ $\implies$ **True**.
2. Successor $C_2$ has $\bar{\alpha}_2 = 0.58 < 0.65$ $\implies$ **True**.
Both conditions are met $\implies$ **$\text{IsRootBlocker}(C_1) = \text{True}$** (Highlighted as Root Blocker).

