# -*- coding: utf-8 -*-
"""
Generate high-resolution flowcharts and conceptual diagrams for KnowledgeTrace MCQ
using Matplotlib with crisp modern tech styling.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

def create_dataflow_diagram(output_path="ml_dataflow_diagram.png"):
    fig, ax = plt.subplots(figsize=(12, 15), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 126)
    ax.axis('off')

    # Color palette
    c_client = "#2563EB"      # Royal Blue
    c_router = "#7C3AED"      # Purple
    c_bg_task = "#DB2777"     # Dark Pink
    c_bkt = "#059669"         # Emerald Green
    c_dina = "#D97706"        # Amber
    c_db = "#0F172A"          # Slate Dark
    c_diag = "#0284C7"        # Sky Blue
    
    # Title
    ax.text(50, 122, "KnowledgeTrace MCQ — End-to-End ML Data Flow Architecture", 
            ha='center', va='center', fontsize=16, fontweight='bold', color='#0F172A')
    ax.text(50, 118.5, "Detailed trace showing Exact Functions, Services, Database Tables, and Diagnostic Algorithms", 
            ha='center', va='center', fontsize=9.8, color='#64748B')

    def draw_box(x, y, w, h, bg_color, border_color, title, subtitle, items=None):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1.5",
                             facecolor=bg_color, edgecolor=border_color, linewidth=2, zorder=2)
        ax.add_patch(box)
        
        ax.text(x + 2.5, y + h - 2.8, title, fontsize=10.5, fontweight='bold', color=border_color, zorder=3)
        if subtitle:
            ax.text(x + 2.5, y + h - 5.4, subtitle, fontsize=8.2, fontstyle='italic', color='#475569', zorder=3)
        
        if items:
            curr_y = y + h - 8.2
            for item in items:
                ax.text(x + 3.2, curr_y, item, fontsize=8.0, color='#1E293B', zorder=3)
                curr_y -= 2.6

    def draw_arrow(x1, y1, x2, y2, label="", color="#64748B"):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6",
                                    color=color, lw=2.2, shrinkA=2, shrinkB=2), zorder=4)
        if label:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            ax.text(mid_x + 1.2, mid_y, label, fontsize=7.6, fontweight='bold', color=color,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=color, lw=0.9), zorder=5)

    # 1. Client / Student UI Box
    draw_box(10, 103, 80, 12, "#EFF6FF", c_client, 
             "1. Student Frontend (React Client)", 
             "File: frontend/src/pages/StudentTestView.jsx",
             ["• Action: Student selects option & clicks 'Submit Answer'",
              "• High-precision millisecond latency logged via client timers",
              "• Payload: { question_id: 101, selected_option_id: 402, response_time_ms: 4520 }"])

    draw_arrow(50, 103, 50, 93, "HTTP POST /student/responses", c_client)

    # 2. FastAPI Router
    draw_box(10, 80, 80, 13, "#F5F3FF", c_router,
             "2. API Gateway & Synchronous Recording (FastAPI Router)",
             "Function: submit_response() | File: backend/app/routers/student.py",
             ["• Checks correctness: is_correct = (question.correct_option_id == resp.selected_option_id)",
              "• Persists immediate interaction into PostgreSQL 'responses' table",
              "• Spawns asynchronous non-blocking worker: background_tasks.add_task(run_mastery_and_diagnosis)"])

    draw_arrow(50, 80, 50, 71, "Async Background Task", c_bg_task)

    # 3. Background Task Container
    box_bg = FancyBboxPatch((8, 16), 84, 55, boxstyle="round,pad=1.2,rounding_size=2.0",
                            facecolor="#FDF2F8", edgecolor=c_bg_task, linewidth=1.5, linestyle="--", zorder=1)
    ax.add_patch(box_bg)
    ax.text(11, 68, "3. Asynchronous Pipeline Worker: run_mastery_and_diagnosis(student_id, concept_id)", 
            fontsize=9.8, fontweight='bold', color=c_bg_task, zorder=3)

    # 4. Layer 2 - BKT Box
    draw_box(12, 48, 76, 17, "#ECFDF5", c_bkt,
             "Layer 2 — Sequential Mastery Estimation: Bayesian Knowledge Tracing (BKT)",
             "Service: PYBKTMasteryEstimator.update_mastery() | File: backend/app/services/mastery_service.py",
             ["• Algorithm: compute_bkt_sequence(responses) [Hidden Markov Model (HMM) Forward Algorithm]",
              "• Step 1 (Bayes Rule): P(Lt | Correct) = P(Lt)*(1 - P(S)) / [ P(Lt)*(1 - P(S)) + (1 - P(Lt))*P(G) ]",
              "• Step 2 (Transition): P(Lt+1) = P(Lt | obs) + (1 - P(Lt | obs)) * P(T)",
              "• Database Upsert: Writes updated 'mastery_p' and 'opportunity_count' to 'student_concept_mastery' table"])

    draw_arrow(50, 48, 50, 41, "Feeds Primary Mastery", c_bkt)

    # 5. Layer 3 - DINA Box
    draw_box(12, 19, 76, 22, "#FFFBEB", c_dina,
             "Layer 3 — Multi-Attribute Cognitive Diagnosis: DINA Model",
             "Service: DINADiagnosisService.update_diagnosis() | File: backend/app/services/dina_service.py",
             ["• Step A: Reads Q-Matrix mapping questions to skills from 'question_skills' table",
              "• Step B: Graph Partitioning: Breadth-First Search (BFS) extracts isolated connected skill block",
              "• Step C: Vectorized Likelihood: Evaluates 2^K profiles in parallel using NumPy broadcasting & Log-Sum-Exp",
              "• Step D: Marginalization: Integrates posteriors to obtain single-skill probability P(alpha_k = 1 | X)",
              "• Step E: Epistemic Confidence: Confidence = 1 - 4 * P * (1 - P)  --> Tiers: [LOW, MEDIUM, HIGH]",
              "• Database Upsert: Persists to 'cognitive_diagnosis_profile' table (adjusted_mastery, confidence_score)"])

    # 6. Database and Downstream Consumers (Height 12, plenty of space for 3 bullets)
    draw_box(10, 2, 38, 12, "#F1F5F9", c_db,
             "Database Persistence",
             "PostgreSQL Tables",
             ["• responses (Raw telemetry log)",
              "• student_concept_mastery (BKT state)",
              "• cognitive_diagnosis_profile (DINA)"])

    draw_box(52, 2, 38, 12, "#F0F9FF", c_diag,
             "Diagnostic Intelligence (WHY)",
             "Function: get_question_why()",
             ["• Triggered when student answers incorrectly",
              "• Identifies required concepts with P < 0.50",
              "• Flags 'Likely Missing Prerequisite' in UI"])

    draw_arrow(36, 19, 29, 14, "SQL Commit", c_db)
    draw_arrow(64, 19, 71, 14, "Query Diagnostics", c_diag)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Data flow diagram successfully saved to: {output_path}")


def create_models_diagram(output_path="ml_models_diagram.png"):
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 16), dpi=300)
    
    # ── PANEL 1: Layer 1 Concept Prerequisite DAG ──
    ax1.set_xlim(0, 100)
    ax1.set_ylim(0, 42)
    ax1.axis('off')
    
    box1 = FancyBboxPatch((2, 1), 96, 40, boxstyle="round,pad=0.5,rounding_size=1.2",
                          facecolor="#F8FAFC", edgecolor="#475569", linewidth=1.5)
    ax1.add_patch(box1)
    ax1.text(4, 38, "Layer 1: LLM Prerequisite Graph & Directed Acyclic Graph (DAG) Validation", 
             fontsize=11.5, fontweight='bold', color="#0F172A")
    ax1.text(4, 34.5, "Algorithm: infer_llm_concept_edges() with NetworkX nx.is_directed_acyclic_graph(G)", 
             fontsize=8.8, fontstyle='italic', color="#475569")
    
    # Draw 4 Concept Nodes: A -> B -> C -> D
    nodes = [
        ("Concept A\n(e.g., Vectors)", 15, 23, "#3B82F6"),
        ("Concept B\n(e.g., Force / Newton)", 40, 23, "#3B82F6"),
        ("Concept C\n(e.g., Friction & Work)", 65, 23, "#3B82F6"),
        ("Concept D\n(e.g., Energy Cons.)", 90, 23, "#3B82F6"),
    ]
    for name, nx_, ny, col in nodes:
        node_box = FancyBboxPatch((nx_ - 8.5, ny - 5), 17, 10, boxstyle="round,pad=0.4,rounding_size=1.0",
                                  facecolor="#EFF6FF", edgecolor=col, linewidth=2)
        ax1.add_patch(node_box)
        ax1.text(nx_, ny, name, ha='center', va='center', fontsize=8.4, fontweight='bold', color="#1E3A8A")
        
    # Valid forward arrows
    for i in range(len(nodes) - 1):
        x_start = nodes[i][1] + 8.5
        x_end = nodes[i+1][1] - 8.5
        ax1.annotate('', xy=(x_end, 23), xytext=(x_start, 23),
                     arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6", color="#059669", lw=2.4))
        ax1.text((x_start + x_end)/2, 25.5, "Valid Prereq", ha='center', fontsize=7.5, fontweight='bold', color="#059669")

    # Invalid cycle attempt (D -> B) curved arc dipping cleanly below
    ax1.annotate('', xy=(40, 17.5), xytext=(90, 17.5),
                 arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6",
                                 connectionstyle="arc3,rad=0.35", color="#DC2626", lw=2.2, linestyle="--"))
    ax1.text(65, 4.5, "REJECTED: Circular Prerequisite Loop (D -> B) creates Cycle!\nDetected & revoked by nx.is_directed_acyclic_graph(G) == False", 
             ha='center', fontsize=8.0, fontweight='bold', color="#DC2626",
             bbox=dict(boxstyle="round,pad=0.35", fc="#FEF2F2", ec="#DC2626", lw=1.2))

    # ── PANEL 2: Layer 2 BKT Hidden Markov Model ──
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 38)
    ax2.axis('off')
    
    box2 = FancyBboxPatch((2, 1), 96, 36, boxstyle="round,pad=0.5,rounding_size=1.2",
                          facecolor="#F8FAFC", edgecolor="#059669", linewidth=1.5)
    ax2.add_patch(box2)
    ax2.text(4, 34, "Layer 2: Bayesian Knowledge Tracing (BKT) — 2-State Hidden Markov Model (HMM)", 
             fontsize=11.5, fontweight='bold', color="#0F172A")
    ax2.text(4, 30.5, "Algorithm: compute_bkt_sequence() | Tracks Latent State: Lt in {0 (Unmastered), 1 (Mastered)}", 
             fontsize=8.8, fontstyle='italic', color="#047857")

    # Latent State Nodes
    # State 0
    s0 = FancyBboxPatch((12, 13), 22, 13, boxstyle="round,pad=0.5,rounding_size=1.2",
                        facecolor="#FEF2F2", edgecolor="#DC2626", linewidth=2.2)
    ax2.add_patch(s0)
    ax2.text(23, 21, "State 0: Unmastered", ha='center', fontsize=9.8, fontweight='bold', color="#991B1B")
    ax2.text(23, 16.5, "Prior Knowledge\nP(L0) = 0.20", ha='center', fontsize=8.3, color="#7F1D1D")

    # State 1
    s1 = FancyBboxPatch((66, 13), 22, 13, boxstyle="round,pad=0.5,rounding_size=1.2",
                        facecolor="#ECFDF5", edgecolor="#059669", linewidth=2.2)
    ax2.add_patch(s1)
    ax2.text(77, 21, "State 1: Mastered", ha='center', fontsize=9.8, fontweight='bold', color="#065F46")
    ax2.text(77, 16.5, "Target State\nP(Lt) -> 1.0", ha='center', fontsize=8.3, color="#047857")

    # Transition Arrow (Learning)
    ax2.annotate('', xy=(66, 20), xytext=(34, 20),
                 arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.65", color="#2563EB", lw=2.6))
    ax2.text(50, 22.8, "Learning Transition: P(T) = 0.15", ha='center', fontsize=8.8, fontweight='bold', color="#1D4ED8")
    ax2.text(50, 17.5, "(Cannot unlearn: P(unmaster) = 0)", ha='center', fontsize=7.5, fontstyle='italic', color="#64748B")

    # Emission probabilities
    ax2.text(23, 9.2, "Observations (State 0):", ha='center', fontsize=8.0, fontweight='bold', color="#475569")
    ax2.text(23, 5.8, "• Lucky Guess: P(G) = 0.25\n• Normal Wrong: 1 - P(G) = 0.75", 
             ha='center', fontsize=7.5, color="#1E293B", bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#CBD5E1", lw=0.7))

    ax2.text(77, 9.2, "Observations (State 1):", ha='center', fontsize=8.0, fontweight='bold', color="#475569")
    ax2.text(77, 5.8, "• Careless Slip: P(S) = 0.10\n• Normal Correct: 1 - P(S) = 0.90", 
             ha='center', fontsize=7.5, color="#1E293B", bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#CBD5E1", lw=0.7))

    # ── PANEL 3: Layer 3 Multi-Skill DINA Model & Connected Blocks ──
    ax3.set_xlim(0, 100)
    ax3.set_ylim(0, 42)
    ax3.axis('off')
    
    box3 = FancyBboxPatch((2, 1), 96, 40, boxstyle="round,pad=0.5,rounding_size=1.2",
                          facecolor="#F8FAFC", edgecolor="#D97706", linewidth=1.5)
    ax3.add_patch(box3)
    ax3.text(4, 38, "Layer 3: Multi-Attribute Cognitive Diagnosis (DINA) & BFS Connected-Block Partitioning", 
             fontsize=11.5, fontweight='bold', color="#0F172A")
    ax3.text(4, 34.5, "Algorithm: _compute_block_exact() with Vectorized NumPy Broadcasting & Quadratic Entropy", 
             fontsize=8.8, fontstyle='italic', color="#B45309")

    # Q-Matrix Illustration
    q_box = FancyBboxPatch((5, 5), 42, 27, boxstyle="round,pad=0.4,rounding_size=1.0",
                           facecolor="#FFFBEB", edgecolor="#F59E0B", linewidth=1.5)
    ax3.add_patch(q_box)
    ax3.text(26, 29, "Q-Matrix Conjunctive Logic", ha='center', fontsize=9.2, fontweight='bold', color="#92400E")
    ax3.text(7, 24.5, "• Question j requires: {Skill 1, Skill 2}", fontsize=8.0, color="#1E293B")
    ax3.text(7, 21.0, "• Latent Ideal: ξj(α) = α1 × α2", fontsize=8.5, fontweight='bold', color="#B45309")
    ax3.text(7, 17.5, "• Student needs ALL required skills = 1", fontsize=7.8, color="#1E293B")
    ax3.text(7, 14.0, "• Missing even ONE skill drops chance to Guessing:", fontsize=7.8, color="#1E293B")
    ax3.text(7, 10.2, "  P(Correct | ξ=1) = 1 - Slip = 0.90", fontsize=8.0, fontweight='bold', color="#059669")
    ax3.text(7, 6.8, "  P(Correct | ξ=0) = Guess = 0.25", fontsize=8.0, fontweight='bold', color="#DC2626")

    # Connected Block Graph
    b_box = FancyBboxPatch((51, 5), 45, 27, boxstyle="round,pad=0.4,rounding_size=1.0",
                           facecolor="#EFF6FF", edgecolor="#3B82F6", linewidth=1.5)
    ax3.add_patch(b_box)
    ax3.text(73.5, 29, "Connected-Block Graph Partitioning (BFS)", ha='center', fontsize=9.2, fontweight='bold', color="#1E40AF")
    ax3.text(53, 24.5, "• Problem: 2^K profiles explodes for 30 skills (2^30 > 10^9)!", fontsize=7.8, color="#DC2626")
    ax3.text(53, 20.5, "• Solution: Build skill co-occurrence graph from questions", fontsize=7.8, color="#1E293B")
    ax3.text(53, 16.8, "• BFS isolates connected block: K <= 12 (<= 4,096 states)", fontsize=7.8, fontweight='bold', color="#059669")
    ax3.text(53, 13.0, "• Vectorized NumPy execution (< 10 ms runtime)", fontsize=7.8, color="#1E293B")
    ax3.text(53, 9.5, "• Epistemic Confidence: Conf = 1 - 4·p·(1 - p)", fontsize=7.8, fontweight='bold', color="#2563EB")
    ax3.text(53, 6.5, "  Tiers: LOW (<0.40) | MEDIUM (0.40-0.75) | HIGH (>=0.75)", fontsize=7.4, color="#475569")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Models diagram successfully saved to: {output_path}")

if __name__ == "__main__":
    create_dataflow_diagram()
    create_models_diagram()
