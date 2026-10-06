# Phase 2 Development Log

## Layer 1 — Concept Graph Construction
**Date Completed**: 2026-08-30

### What Was Built
1. **Schema Enhancements**:
   - Added `confidence` (Float, default=1.0) and `source` (String, default='llm_inferred') to `ConceptEdge` table in `backend/app/models.py`.
   - Executed asynchronous database schema migration adding `confidence` and `source` columns to PostgreSQL `concept_edges` table on Supabase.
2. **LLM-based Prerequisite Inference Service (`app/services/concept_graph.py`)**:
   - Built single-prompt batch inference utilizing Groq API (`groq/compound` model).
   - Designed prompt expecting structured JSON with prerequisite pairs, confidence scores (0.0 to 1.0), and pedagogical reasoning.
   - Integrated **NetworkX (`nx.DiGraph`)** in-memory DAG validation to automatically detect and discard any cycle-inducing candidate edges before persisting to the database.
3. **Concept Graph Endpoints (`app/routers/concepts.py`)**:
   - `POST /concepts/infer-graph`: Triggers LLM concept edge inference (Teacher restricted).
   - `GET /concepts/graph`: Returns current nodes and directed edges with confidence ratings and source tags (`llm_inferred`, `statistical`, `manual`).

---

## Layer 2 — Sequential Mastery Estimation
**Date Completed**: 2026-08-31

### What Was Built
1. **Persistence Schema (`student_concept_mastery` table)**:
   - Added PostgreSQL `student_concept_mastery` table with columns: `id`, `student_id`, `concept_id`, `mastery_p` (Float), `opportunity_count` (Integer), `last_updated` (Timestamp).
2. **Abstract Estimator Interface & pyBKT Service (`app/services/mastery_service.py`)**:
   - Implemented `BaseMasteryEstimator` abstract base class defining `update_mastery`, `get_mastery`, and `get_all_student_masteries`.
   - Built `PYBKTMasteryEstimator` following Bayesian Knowledge Tracing parameters: $P(L_0)=0.20$, $P(T)=0.15$, $P(S)=0.10$, $P(G)=0.25$.
   - Swappable provider pattern (`get_mastery_estimator()`) allowing future substitution of DKT/AKT models without breaking existing contracts.
3. **Automated Submission Trigger (`app/routers/student.py`)**:
   - Connected student `POST /student/responses` to automatically compute and persist updated concept mastery upon each answer submission.
4. **Mastery API Endpoints (`app/routers/mastery.py`)**:
   - `GET /mastery/student/{student_id}`: Retrieves full concept mastery profile for a student.
   - `GET /mastery/student/{student_id}/concept/{concept_id}`: Retrieves concept-specific mastery probability.
   - `POST /mastery/recompute/{student_id}`: Recalculates mastery scores for a student across all historical responses.

### Decisions Made & Rationale
- **Decoupled ML Module Architecture**: Isolated mastery calculation into `BaseMasteryEstimator` class hierarchy in `app/services/mastery_service.py` to allow clean ML model swaps.
- **Persistence Strategy**: Created `student_concept_mastery` table for O(1) query lookups across student dashboards.

### Verified Results (Real DB Execution)
- Verified sequence math evolution over 4 consecutive attempts: $0.20 \rightarrow 0.55 \rightarrow 0.27 \rightarrow 0.63 \rightarrow 0.88$.
- Tested persistence and profile lookups against real Supabase DB.
