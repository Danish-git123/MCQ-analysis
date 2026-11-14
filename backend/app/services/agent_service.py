import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import (
    CognitiveDiagnosisProfile,
    Concept,
    ConceptEdge,
    Option,
    Question,
    QuestionSkill,
    Response,
    Test,
    TestAssignment,
    User,
)
from app.schemas.agent import (
    ApproveClassInterventionRequest,
    ApproveQuizLaunchResponse,
    ApproveStudentQuizRequest,
    ApproveTeacherCurriculumRequest,
    ClassInterventionDraftResponse,
    DraftOption,
    DraftQuestion,
    ProposedConceptEdge,
    ReasoningStep,
    StudentTutorDraftResponse,
    TeacherCurriculumDraftResponse,
)
from app.services.cognitive_analytics_service import get_cognitive_analytics_service
from app.services.dina_service import get_dina_service
from app.services.llm_service import get_llm_service
from app.services.prediction_service import get_prediction_service

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Layer 4 — Neuro-Symbolic Agentic AI Brain.

    Combines a bounded ReAct (Reason + Act) tool-calling control loop with:
      1. Multi-provider cognitive planning (Gemini REST -> Groq -> Deterministic Policy Fallback)
      2. Grounded psychometric tools (DINA, BKT+Forget, Logistic Regression anomalies,
         Wise & Kong 4 Effort Quadrants, NetworkX Prerequisite DAG, Distractor semantics)
      3. Smart Hybrid MCQ sourcing (unseen bank items first -> Q-matrix AI synthesis)
      4. Human-in-the-Loop Draft & Preview safety gate before any DB persistence.
    """

    def __init__(self, max_steps: int = 6):
        self.max_steps = max_steps
        self.llm = get_llm_service()
        self.analytics = get_cognitive_analytics_service()
        self.dina = get_dina_service()
        self.predictor = get_prediction_service()

    # ══════════════════════════════════════════════════════════════════════════
    # GROUNDED CALLABLE TOOLS ("THE BRAIN'S SENSORS & HANDS")
    # ══════════════════════════════════════════════════════════════════════════

    async def tool_get_dina_and_bkt_profile(
        self, student_id: int, db: AsyncSession
    ) -> Dict[str, Any]:
        comprehensive = await self.analytics.get_comprehensive_advanced_analytics(
            student_id, db
        )
        matrix = comprehensive.get("integrated_concept_matrix", [])
        weak = [c for c in matrix if c["dina_adjusted_mastery"] < 0.50]
        moderate = [
            c for c in matrix if 0.50 <= c["dina_adjusted_mastery"] < 0.70
        ]
        mastered = [c for c in matrix if c["dina_adjusted_mastery"] >= 0.70]
        return {
            "executive_summary": comprehensive.get("executive_summary", {}),
            "weak_concepts": weak,
            "moderate_concepts": moderate,
            "mastered_concepts": mastered,
            "all_concepts": matrix,
        }

    async def tool_get_effort_and_distractor_anomalies(
        self, student_id: int, db: AsyncSession
    ) -> Dict[str, Any]:
        effort = await self.analytics.compute_effort_quadrant_analysis(student_id, db)

        # Enrich missed questions with exact chosen distractor text (solving binary 1/0 blindness)
        stmt = (
            select(Response, Question)
            .join(Question, Response.question_id == Question.id)
            .where(Response.student_id == student_id, Response.is_correct == False)  # noqa: E712
            .order_by(Response.answered_at.desc())
            .limit(8)
        )
        res = await db.execute(stmt)
        missed_rows = res.all()

        distractor_details = []
        for resp, q in missed_rows:
            opt_res = await db.execute(
                select(Option).where(Option.question_id == q.id)
            )
            opts = {o.id: o.text for o in opt_res.scalars().all()}
            chosen_text = opts.get(resp.selected_option_id, "Unknown option")
            correct_text = opts.get(q.correct_option_id, "Unknown correct answer")
            distractor_details.append(
                {
                    "question_id": q.id,
                    "concept_id": q.concept_id,
                    "question_text": q.text,
                    "chosen_wrong_option": chosen_text,
                    "correct_option": correct_text,
                    "response_time_sec": round(resp.response_time_ms / 1000.0, 1),
                }
            )

        attempts = effort.get("detailed_attempts", [])
        slips = [a for a in attempts if a.get("anomaly_type") == "CARELESS_SLIP"]
        lucky_guesses = [
            a for a in attempts if a.get("anomaly_type") == "RAPID_LUCKY_GUESS"
        ]

        return {
            "total_responses": effort.get("total_responses", 0),
            "effort_consistency_index": effort.get("effort_consistency_index", 0.0),
            "quadrant_distribution": effort.get("quadrant_distribution", {}),
            "careless_slip_count": len(slips),
            "lucky_guess_count": len(lucky_guesses),
            "slip_items": slips[:4],
            "lucky_guess_items": lucky_guesses[:4],
            "missed_distractor_analysis": distractor_details[:5],
        }

    async def tool_get_prerequisite_dag_blockers(
        self, student_id: int, db: AsyncSession
    ) -> Dict[str, Any]:
        roadmap_report = await self.analytics.compute_prerequisite_debt_and_roadmap(
            student_id, db
        )
        roadmap = roadmap_report.get("remediation_roadmap", [])
        root_blockers = [step for step in roadmap if step.get("is_root_blocker")]
        return {
            "prerequisite_debt_score": roadmap_report.get("prerequisite_debt_score", 0.0),
            "debt_level": roadmap_report.get("debt_level", "ZERO_DEBT"),
            "debt_advice": roadmap_report.get("debt_advice", ""),
            "root_blockers": root_blockers,
            "ordered_roadmap": roadmap,
        }

    async def tool_query_unseen_bank_questions(
        self,
        student_id: int,
        concept_ids: List[int],
        limit: int,
        db: AsyncSession,
    ) -> List[DraftQuestion]:
        if not concept_ids or limit <= 0:
            return []

        # Questions already answered by this student
        ans_res = await db.execute(
            select(Response.question_id).where(Response.student_id == student_id)
        )
        answered_ids: Set[int] = {r[0] for r in ans_res.all()}

        # Concepts lookup
        c_res = await db.execute(select(Concept))
        concept_map = {c.id: c.name for c in c_res.scalars().all()}

        # Find questions matching via Q-matrix (QuestionSkill) OR primary Question.concept_id
        qs_stmt = (
            select(Question)
            .options(selectinload(Question.options))
            .join(QuestionSkill, Question.id == QuestionSkill.question_id)
            .where(QuestionSkill.concept_id.in_(concept_ids))
            .distinct()
        )
        qs_res = await db.execute(qs_stmt)
        candidates = list(qs_res.scalars().all())

        fb_stmt = (
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.concept_id.in_(concept_ids))
        )
        fb_res = await db.execute(fb_stmt)
        by_id = {q.id: q for q in candidates}
        for q in fb_res.scalars().all():
            by_id.setdefault(q.id, q)

        unseen = [q for q in by_id.values() if q.id not in answered_ids and len(q.options) >= 2]
        selected = unseen[:limit]

        drafts: List[DraftQuestion] = []
        for q in selected:
            skill_rows = await db.execute(
                select(QuestionSkill.concept_id).where(QuestionSkill.question_id == q.id)
            )
            s_ids = [r[0] for r in skill_rows.all()]
            if q.concept_id and q.concept_id not in s_ids:
                s_ids.insert(0, q.concept_id)
            skill_names = [concept_map.get(cid, f"Concept #{cid}") for cid in s_ids]
            primary_c_name = concept_map.get(
                q.concept_id, skill_names[0] if skill_names else "Core Concept"
            )
            drafts.append(
                DraftQuestion(
                    source="bank",
                    source_question_id=q.id,
                    concept_id=q.concept_id,
                    concept_name=primary_c_name,
                    skill_names=skill_names,
                    text=q.text,
                    options=[
                        DraftOption(
                            text=o.text,
                            is_correct=(o.id == q.correct_option_id),
                        )
                        for o in q.options
                    ],
                    misconception_note="Verified question bank item targeting weak Q-matrix skills.",
                )
            )
        return drafts

    async def tool_synthesize_targeted_mcqs(
        self,
        concept_specs: List[Dict[str, Any]],
        count: int,
        context_note: str = "",
    ) -> Tuple[List[DraftQuestion], str]:
        """
        Synthesizes diagnostic MCQs mapped to Q-matrix skills with misconception-aware distractors.
        Tries Gemini/Groq first; falls back to structured domain templates if offline.
        """
        if count <= 0:
            return [], "none"

        target_specs = concept_specs or [
            {"concept_id": None, "concept_name": "Foundational Problem Solving"}
        ]
        spec_summary = [
            {
                "concept_id": s.get("concept_id"),
                "concept_name": s.get("concept_name", "Core Concept"),
                "related_skills": s.get("related_skills", [s.get("concept_name", "Core Concept")]),
            }
            for s in target_specs
        ]

        prompt = f"""
Generate {count} high-precision multiple-choice diagnostic questions (MCQs) for these target concepts:
{json.dumps(spec_summary, indent=2)}

Pedagogical context:
{context_note or "Diagnose conceptual misconceptions and multi-skill reasoning."}

Rules:
- Each question must have exactly 4 distinct options and exactly 1 correct option (`is_correct: true`).
- The 3 distractors should reflect realistic student misconceptions (e.g., sign errors, missing decomposition, formula confusion).
- Include `skill_names` listing 1 to 3 prerequisite skills required (Q-matrix tags).
- Include a concise `misconception_note` explaining what conceptual trap the distractors test.

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "concept_id": 12,
      "concept_name": "Exact Concept Name",
      "skill_names": ["Skill A", "Skill B"],
      "text": "Clear question stem?",
      "options": [
        {{"text": "Correct answer", "is_correct": true}},
        {{"text": "Distractor 1", "is_correct": false}},
        {{"text": "Distractor 2", "is_correct": false}},
        {{"text": "Distractor 3", "is_correct": false}}
      ],
      "misconception_note": "Tests whether student confuses X with Y."
    }}
  ]
}}
"""
        system_prompt = (
            "You are an expert psychometric item writer creating Q-matrix-tagged diagnostic MCQs."
        )
        llm_data, provider = await self.llm.generate_json_with_provider(
            prompt, system_prompt
        )

        synthesized: List[DraftQuestion] = []
        if llm_data and isinstance(llm_data.get("questions"), list):
            for idx, item in enumerate(llm_data["questions"][:count]):
                raw_opts = item.get("options", [])
                if len(raw_opts) < 2:
                    continue
                opts = [
                    DraftOption(
                        text=str(o.get("text", f"Option {i+1}")),
                        is_correct=bool(o.get("is_correct", False)),
                    )
                    for i, o in enumerate(raw_opts[:4])
                ]
                if not any(o.is_correct for o in opts):
                    opts[0].is_correct = True
                fallback_spec = target_specs[idx % len(target_specs)]
                c_name = str(
                    item.get("concept_name") or fallback_spec.get("concept_name", "Core Concept")
                )
                skills = [str(s) for s in (item.get("skill_names") or [c_name])]
                synthesized.append(
                    DraftQuestion(
                        source="ai_synthesized",
                        source_question_id=None,
                        concept_id=item.get("concept_id") or fallback_spec.get("concept_id"),
                        concept_name=c_name,
                        skill_names=skills,
                        text=str(item.get("text", "")).strip(),
                        options=opts,
                        misconception_note=str(
                            item.get("misconception_note")
                            or "AI-synthesized Q-matrix diagnostic item."
                        ),
                    )
                )

        if len(synthesized) >= count:
            return synthesized[:count], provider

        # Deterministic template fallback for remaining slots so offline/demo runs never fail
        remaining = count - len(synthesized)
        for i in range(remaining):
            spec = target_specs[(len(synthesized) + i) % len(target_specs)]
            c_name = spec.get("concept_name", "Core Concept")
            c_id = spec.get("concept_id")
            related = spec.get("related_skills") or [c_name]
            variant = i + 1
            if variant % 2 == 1:
                q_text = (
                    f"[Diagnostic Check #{variant}] When solving a multi-step problem involving "
                    f"{c_name}, which condition must be verified FIRST before applying the governing equation?"
                )
                opts = [
                    DraftOption(
                        text=f"Confirm boundary assumptions, reference frame/units, and prerequisite invariants for {c_name}",
                        is_correct=True,
                    ),
                    DraftOption(
                        text=f"Substitute final target values immediately without decomposing {c_name} components",
                        is_correct=False,
                    ),
                    DraftOption(
                        text=f"Assume constant/linear behavior even when {c_name} constraints vary",
                        is_correct=False,
                    ),
                    DraftOption(
                        text=f"Ignore sign conventions and directional coupling in {c_name}",
                        is_correct=False,
                    ),
                ]
                note = f"Tests foundational setup discipline and prerequisite verification in {c_name}."
            else:
                q_text = (
                    f"[Applied Synthesis #{variant}] In an integrated scenario combining {c_name}"
                    + (f" with {related[1]}" if len(related) > 1 else "")
                    + ", what happens if the primary governing parameter is doubled while constraints stay fixed?"
                )
                opts = [
                    DraftOption(
                        text=f"The system response scales according to the exact functional dependency of {c_name}",
                        is_correct=True,
                    ),
                    DraftOption(
                        text="The output remains invariant regardless of parameter coupling",
                        is_correct=False,
                    ),
                    DraftOption(
                        text="The relationship inverts direction due to sign cancellation",
                        is_correct=False,
                    ),
                    DraftOption(
                        text="Only secondary boundary terms change while primary state stays constant",
                        is_correct=False,
                    ),
                ]
                note = f"Tests proportional/causal reasoning across Q-matrix skills: {', '.join(related)}."

            synthesized.append(
                DraftQuestion(
                    source="ai_synthesized",
                    source_question_id=None,
                    concept_id=c_id,
                    concept_name=c_name,
                    skill_names=list(dict.fromkeys([c_name] + related)),
                    text=q_text,
                    options=opts,
                    misconception_note=note,
                )
            )

        return synthesized, (provider if synthesized and provider != "deterministic_fallback" else "deterministic_fallback")

    def tool_validate_dag_with_networkx(
        self,
        concept_names: List[str],
        proposed_edges: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Validates a proposed prerequisite graph with NetworkX.
        If cycles exist, identifies and removes cycle-closing edges so the Agent can self-correct.
        """
        canonical = {name.strip().lower(): name.strip() for name in concept_names if name.strip()}
        G = nx.DiGraph()
        for display_name in canonical.values():
            G.add_node(display_name)

        valid_edges: List[Dict[str, str]] = []
        cycles_resolved: List[str] = []

        for edge in proposed_edges:
            u_raw = str(edge.get("from_concept", "")).strip()
            v_raw = str(edge.get("to_concept", "")).strip()
            reason = str(edge.get("reasoning", "")).strip()
            u = canonical.get(u_raw.lower())
            v = canonical.get(v_raw.lower())
            if not u or not v or u == v:
                continue
            if G.has_edge(u, v):
                continue

            G.add_edge(u, v)
            if not nx.is_directed_acyclic_graph(G):
                G.remove_edge(u, v)
                cycles_resolved.append(
                    f"Removed cyclic edge '{u} -> {v}' (would create circular dependency)"
                )
            else:
                valid_edges.append(
                    {"from_concept": u, "to_concept": v, "reasoning": reason}
                )

        topo_order = list(nx.topological_sort(G)) if nx.is_directed_acyclic_graph(G) else list(canonical.values())
        return {
            "is_valid_dag": True,
            "valid_edges": valid_edges,
            "cycles_resolved": cycles_resolved,
            "topological_order": topo_order,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # WORKFLOW A: STUDENT DIAGNOSTIC & REMEDIAL TUTOR AGENT (DRAFT & PREVIEW)
    # ══════════════════════════════════════════════════════════════════════════

    async def run_student_tutor_agent(
        self,
        student_id: int,
        db: AsyncSession,
        target_concept_id: Optional[int] = None,
        max_questions: int = 5,
    ) -> StudentTutorDraftResponse:
        trace: List[ReasoningStep] = []
        active_provider = "deterministic_fallback"

        # Step 1: Tri-Model DINA + BKT Profile
        dina_bkt = await self.tool_get_dina_and_bkt_profile(student_id, db)
        exec_sum = dina_bkt["executive_summary"]
        weak_concepts = dina_bkt["weak_concepts"]
        trace.append(
            ReasoningStep(
                step=1,
                thought="Inspect student's Tri-Model mastery matrix (DINA multi-skill posterior + BKT trajectory).",
                tool_name="get_dina_and_bkt_profile",
                tool_args={"student_id": student_id},
                observation=(
                    f"Evaluated {exec_sum.get('total_concepts_evaluated', 0)} concepts: "
                    f"{exec_sum.get('mastered_concepts', 0)} mastered, "
                    f"{exec_sum.get('moderate_concepts', 0)} moderate, "
                    f"{exec_sum.get('weak_concepts', 0)} weak gaps."
                ),
                provider="psychometric_engine",
            )
        )

        # Step 2: Effort Quadrants, Logistic Slip/Guess Anomalies & Distractor Semantics
        effort_data = await self.tool_get_effort_and_distractor_anomalies(student_id, db)
        q_dist = effort_data["quadrant_distribution"]
        rapid_pct = q_dist.get("rapid_guessing_pct", 0.0)
        slip_count = effort_data["careless_slip_count"]
        lucky_count = effort_data["lucky_guess_count"]
        total_resp = effort_data["total_responses"]
        trace.append(
            ReasoningStep(
                step=2,
                thought="Disambiguate true conceptual gaps from rapid guessing, careless slips, and chosen wrong distractors.",
                tool_name="get_effort_and_slip_anomalies",
                tool_args={"student_id": student_id},
                observation=(
                    f"Total responses={total_resp}, ECI={effort_data['effort_consistency_index']}, "
                    f"Rapid Guessing={rapid_pct}%, Careless Slips={slip_count}, "
                    f"Lucky Guesses={lucky_count}, Missed items analyzed={len(effort_data['missed_distractor_analysis'])}."
                ),
                provider="psychometric_engine",
            )
        )

        # Step 3: Prerequisite DAG Debt & Topological Root Blockers
        dag_data = await self.tool_get_prerequisite_dag_blockers(student_id, db)
        root_blockers = dag_data["root_blockers"]
        roadmap = dag_data["ordered_roadmap"]
        trace.append(
            ReasoningStep(
                step=3,
                thought="Trace broken concepts upstream in the Prerequisite DAG to identify root blockers.",
                tool_name="get_prerequisite_dag_blockers",
                tool_args={"student_id": student_id},
                observation=(
                    f"Prerequisite Debt={int(dag_data['prerequisite_debt_score'] * 100)}% "
                    f"({dag_data['debt_level']}), Root Blockers={len(root_blockers)} "
                    f"({', '.join(b['concept_name'] for b in root_blockers) or 'None'})."
                ),
                provider="networkx_dag_engine",
            )
        )

        # Step 4: Cognitive Policy Decision (LLM Planner + Deterministic Neuro-Symbolic Policy)
        if total_resp < 5:
            strategy_code = "COLD_START_PROBE"
        elif rapid_pct >= 45.0 or lucky_count >= 2:
            strategy_code = "PACING_AND_VERIFICATION"
        elif slip_count > 0 and len(weak_concepts) <= 1:
            strategy_code = "PRECISION_REINFORCEMENT"
        elif root_blockers or weak_concepts:
            strategy_code = "FOUNDATIONAL_REMEDIATION"
        else:
            strategy_code = "MASTERY_ADVANCEMENT"

        # Determine priority target concepts
        target_specs: List[Dict[str, Any]] = []
        if target_concept_id is not None:
            c_res = await db.execute(select(Concept).where(Concept.id == target_concept_id))
            c_obj = c_res.scalars().first()
            if c_obj:
                target_specs.append(
                    {
                        "concept_id": c_obj.id,
                        "concept_name": c_obj.name,
                        "priority": "USER_SELECTED_TARGET",
                    }
                )

        if not target_specs:
            if root_blockers:
                for b in root_blockers[:3]:
                    target_specs.append(
                        {
                            "concept_id": b["concept_id"],
                            "concept_name": b["concept_name"],
                            "mastery": b["current_mastery"],
                            "priority": "ROOT_PREREQUISITE_BLOCKER",
                        }
                    )
            elif roadmap:
                for step_item in roadmap[:3]:
                    target_specs.append(
                        {
                            "concept_id": step_item["concept_id"],
                            "concept_name": step_item["concept_name"],
                            "mastery": step_item["current_mastery"],
                            "priority": "TOPOLOGICAL_NEXT_STEP",
                        }
                    )
            elif weak_concepts:
                for w in sorted(weak_concepts, key=lambda x: x["dina_adjusted_mastery"])[:3]:
                    target_specs.append(
                        {
                            "concept_id": w["concept_id"],
                            "concept_name": w["concept_name"],
                            "mastery": w["dina_adjusted_mastery"],
                            "priority": "WEAK_GAP",
                        }
                    )
            else:
                # Cold-start or mastery advancement: pick top concepts from DB
                all_c = dina_bkt["all_concepts"][:3]
                if all_c:
                    for c in all_c:
                        target_specs.append(
                            {
                                "concept_id": c["concept_id"],
                                "concept_name": c["concept_name"],
                                "mastery": c["dina_adjusted_mastery"],
                                "priority": "BASELINE_CHECK",
                            }
                        )
                else:
                    c_res = await db.execute(select(Concept).limit(3))
                    for c in c_res.scalars().all():
                        target_specs.append(
                            {
                                "concept_id": c.id,
                                "concept_name": c.name,
                                "mastery": 0.5,
                                "priority": "BASELINE_CHECK",
                            }
                        )

        target_ids = [t["concept_id"] for t in target_specs if t.get("concept_id")]

        # Step 5: Smart Hybrid Step 1 — Query Unseen Question Bank
        bank_drafts = await self.tool_query_unseen_bank_questions(
            student_id=student_id,
            concept_ids=target_ids,
            limit=max_questions,
            db=db,
        )
        trace.append(
            ReasoningStep(
                step=4,
                thought=(
                    f"Strategy selected: {strategy_code}. Query unseen question bank first "
                    f"for target concepts ({', '.join(t['concept_name'] for t in target_specs)})."
                ),
                tool_name="query_unseen_bank_questions",
                tool_args={"student_id": student_id, "concept_ids": target_ids, "limit": max_questions},
                observation=f"Found {len(bank_drafts)} unseen bank questions matching targeted skills.",
                provider="question_bank_db",
            )
        )

        # Step 6: Smart Hybrid Step 2 — Synthesize New Q-Matrix MCQs if Bank Exhausted
        needed = max(0, max_questions - len(bank_drafts))
        synth_drafts: List[DraftQuestion] = []
        if needed > 0:
            distractor_context = "; ".join(
                f"Missed '{m['question_text'][:60]}...' by choosing '{m['chosen_wrong_option']}'"
                for m in effort_data["missed_distractor_analysis"][:2]
            )
            synth_drafts, synth_provider = await self.tool_synthesize_targeted_mcqs(
                concept_specs=target_specs,
                count=needed,
                context_note=f"Strategy={strategy_code}. {distractor_context}",
            )
            if synth_provider != "deterministic_fallback":
                active_provider = synth_provider
            trace.append(
                ReasoningStep(
                    step=5,
                    thought=f"Question bank had {len(bank_drafts)}/{max_questions} unseen items. Synthesizing {needed} Q-matrix MCQs to complete the diagnostic draft.",
                    tool_name="synthesize_targeted_mcqs",
                    tool_args={"count": needed, "concepts": [t["concept_name"] for t in target_specs]},
                    observation=f"Synthesized {len(synth_drafts)} diagnostic MCQs with misconception distractors via {synth_provider}.",
                    provider=synth_provider,
                )
            )

        all_draft_questions = bank_drafts + synth_drafts

        # Optional LLM Pedagogical Narrative Synthesis (falls back to grounded policy narrative)
        narrative_prompt = f"""
You are an expert AI Cognitive Tutor synthesizing a student diagnostic plan.
Student Telemetry:
- Strategy Code: {strategy_code}
- Executive Summary: {json.dumps(exec_sum)}
- Effort Quadrants: {json.dumps(q_dist)}
- Careless Slips: {slip_count}, Lucky Guesses: {lucky_count}
- Prerequisite Debt: {dag_data['debt_level']} ({dag_data['prerequisite_debt_score']})
- Root Blockers: {json.dumps(root_blockers)}
- Missed Distractor Choices: {json.dumps(effort_data['missed_distractor_analysis'][:3])}
- Target Concepts: {json.dumps(target_specs)}

Return ONLY valid JSON:
{{
  "diagnosis_summary": "2-3 concise sentences explaining the root cognitive cause (distinguishing rapid guessing/slips vs prerequisite gaps).",
  "distractor_insights": ["1-2 specific insights from the wrong options chosen"],
  "study_coaching": ["3 concrete, actionable study steps in topological order"],
  "draft_quiz_title": "Short descriptive quiz title"
}}
"""
        llm_narrative, narr_provider = await self.llm.generate_json_with_provider(
            narrative_prompt,
            "You are a concise, scientifically grounded cognitive tutor.",
        )
        if llm_narrative and narr_provider != "deterministic_fallback":
            active_provider = narr_provider
            diagnosis_summary = str(llm_narrative.get("diagnosis_summary", "")).strip()
            distractor_insights = [str(x) for x in llm_narrative.get("distractor_insights", [])]
            study_coaching = [str(x) for x in llm_narrative.get("study_coaching", [])]
            draft_title = str(llm_narrative.get("draft_quiz_title", "")).strip()
        else:
            diagnosis_summary, distractor_insights, study_coaching, draft_title = (
                self._build_deterministic_student_narrative(
                    strategy_code=strategy_code,
                    rapid_pct=rapid_pct,
                    slip_count=slip_count,
                    dag_data=dag_data,
                    target_specs=target_specs,
                    missed_distractors=effort_data["missed_distractor_analysis"],
                )
            )

        trace.append(
            ReasoningStep(
                step=len(trace) + 1,
                thought="Assemble Draft & Preview remedial quiz and coaching plan for student approval (no DB writes yet).",
                tool_name="emit_draft_preview",
                tool_args={"question_count": len(all_draft_questions)},
                observation=f"Draft ready ({len(bank_drafts)} bank + {len(synth_drafts)} AI-synthesized questions).",
                provider=active_provider,
            )
        )

        return StudentTutorDraftResponse(
            student_id=student_id,
            engine_mode=active_provider,
            strategy_code=strategy_code,
            diagnosis_summary=diagnosis_summary,
            distractor_insights=distractor_insights,
            study_coaching=study_coaching,
            target_concepts=target_specs,
            draft_quiz_title=draft_title,
            draft_questions=all_draft_questions,
            reasoning_trace=trace,
        )

    def _build_deterministic_student_narrative(
        self,
        strategy_code: str,
        rapid_pct: float,
        slip_count: int,
        dag_data: Dict[str, Any],
        target_specs: List[Dict[str, Any]],
        missed_distractors: List[Dict[str, Any]],
    ) -> Tuple[str, List[str], List[str], str]:
        target_names = [t["concept_name"] for t in target_specs]
        primary = target_names[0] if target_names else "Core Concepts"

        if strategy_code == "PACING_AND_VERIFICATION":
            summary = (
                f"Effort analytics detected {rapid_pct}% rapid guessing (< 4s per question), which artificially "
                f"depresses your DINA mastery estimates. Before heavy re-teaching, this paced verification check "
                f"isolates whether '{primary}' is a genuine conceptual gap or a timing rush."
            )
        elif strategy_code == "PRECISION_REINFORCEMENT":
            summary = (
                f"Logistic Regression flagged {slip_count} careless slip(s) on items where your predicted mastery "
                f"was high. Your foundational understanding is solid, so this draft targets multi-skill edge cases "
                f"in '{primary}' to eliminate rushed errors."
            )
        elif strategy_code == "COLD_START_PROBE":
            summary = (
                "Fewer than 5 interactions are recorded so far (cold-start regime). This balanced diagnostic "
                f"probe calibrates your baseline DINA & BKT mastery across {', '.join(target_names)}."
            )
        else:
            summary = (
                f"Prerequisite Debt is {int(dag_data.get('prerequisite_debt_score', 0) * 100)}% "
                f"({dag_data.get('debt_level', 'ACTIVE').replace('_', ' ')}). Upstream gaps in "
                f"{', '.join(target_names)} are blocking downstream multi-skill performance and must be resolved first."
            )

        insights: List[str] = []
        for m in missed_distractors[:3]:
            insights.append(
                f"On \"{m['question_text'][:65]}...\", you selected \"{m['chosen_wrong_option']}\" "
                f"instead of \"{m['correct_option']}\" ({m['response_time_sec']}s)."
            )
        if not insights:
            insights.append("No incorrect distractor patterns recorded yet; baseline calibration active.")

        coaching = [
            f"Step 1: Spend at least 12–20 seconds per item reading constraints carefully before selecting an option.",
            f"Step 2: Master root prerequisite '{primary}' first to unlock dependent concepts.",
            "Step 3: Review distractor explanations immediately after completing the approved remedial check.",
        ]
        title = f"AI Tutor Remedial Plan: {' & '.join(target_names[:2])}"
        return summary, insights, coaching, title

    async def approve_and_launch_student_quiz(
        self,
        student_id: int,
        req: ApproveStudentQuizRequest,
        db: AsyncSession,
    ) -> ApproveQuizLaunchResponse:
        if not req.questions:
            raise ValueError("Cannot create a quiz with zero questions.")

        # Resolve concept map
        c_res = await db.execute(select(Concept))
        concepts = c_res.scalars().all()
        by_name = {c.name.strip().lower(): c for c in concepts}

        # Pick a teacher owner (or student if none exists)
        t_res = await db.execute(select(User).where(User.role == "teacher"))
        teacher = t_res.scalars().first()
        creator_id = teacher.id if teacher else student_id

        new_test = Test(title=req.title.strip() or "AI Remedial Quiz", created_by_teacher_id=creator_id)
        db.add(new_test)
        await db.flush()

        for dq in req.questions:
            primary_cid = dq.concept_id
            if not primary_cid and dq.concept_name:
                matched = by_name.get(dq.concept_name.strip().lower())
                if matched:
                    primary_cid = matched.id

            new_q = Question(
                test_id=new_test.id,
                concept_id=primary_cid,
                text=dq.text.strip(),
            )
            db.add(new_q)
            await db.flush()

            correct_opt_id = None
            for opt in dq.options:
                new_opt = Option(question_id=new_q.id, text=opt.text.strip())
                db.add(new_opt)
                await db.flush()
                if opt.is_correct and correct_opt_id is None:
                    correct_opt_id = new_opt.id
            if correct_opt_id is None and dq.options:
                first_opt_res = await db.execute(
                    select(Option).where(Option.question_id == new_q.id)
                )
                first_opt = first_opt_res.scalars().first()
                if first_opt:
                    correct_opt_id = first_opt.id
            new_q.correct_option_id = correct_opt_id

            # Persist Q-matrix links in question_skills
            linked_cids: List[Tuple[int, bool]] = []
            if primary_cid:
                linked_cids.append((primary_cid, True))
            for s_name in dq.skill_names:
                c_obj = by_name.get(s_name.strip().lower())
                if c_obj and all(existing_id != c_obj.id for existing_id, _ in linked_cids):
                    linked_cids.append((c_obj.id, False))

            for cid, is_prim in linked_cids:
                stmt_qs = (
                    pg_insert(QuestionSkill)
                    .values(
                        question_id=new_q.id,
                        concept_id=cid,
                        is_primary=is_prim,
                        source="agent_remedial",
                        llm_confidence=0.90,
                    )
                    .on_conflict_do_nothing(index_elements=["question_id", "concept_id"])
                )
                await db.execute(stmt_qs)

        assignment = TestAssignment(
            test_id=new_test.id,
            student_id=student_id,
            status="not_started",
        )
        db.add(assignment)
        await db.commit()

        return ApproveQuizLaunchResponse(
            status="approved_and_assigned",
            test_id=new_test.id,
            title=new_test.title,
            question_count=len(req.questions),
            assigned_student_ids=[student_id],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # WORKFLOW B: TEACHER CURRICULUM & SELF-CORRECTING DAG AGENT
    # ══════════════════════════════════════════════════════════════════════════

    async def run_teacher_curriculum_agent(
        self,
        topic: str,
        num_questions: int,
        difficulty_level: str,
        db: AsyncSession,
        syllabus_context: str = "",
    ) -> TeacherCurriculumDraftResponse:
        trace: List[ReasoningStep] = []

        # Fetch existing concepts so the agent reuses existing syllabus nodes where possible
        c_res = await db.execute(select(Concept))
        existing_concepts = c_res.scalars().all()
        existing_by_lower = {c.name.strip().lower(): c for c in existing_concepts}

        notes_excerpt = (syllabus_context or "").strip()[:4000]
        context_block = (
            f"\nTeacher-provided syllabus / lecture notes (ground all concepts and MCQs strictly in these notes when relevant):\n\"\"\"\n{notes_excerpt}\n\"\"\"\n"
            if notes_excerpt
            else ""
        )

        prompt = f"""
Design a structured micro-curriculum and diagnostic MCQ set for the topic: "{topic}" ({difficulty_level} level).
Existing concepts in database (reuse exact names when relevant):
{json.dumps([c.name for c in existing_concepts])}
{context_block}
Return ONLY valid JSON:
{{
  "concepts": [
    {{"name": "Foundational Concept", "description": "Core prerequisite"}},
    {{"name": "Intermediate Concept", "description": "Builds on foundation"}},
    {{"name": "Advanced Concept", "description": "Multi-skill synthesis"}}
  ],
  "prerequisite_edges": [
    {{"from_concept": "Foundational Concept", "to_concept": "Intermediate Concept", "reasoning": "Why A precedes B"}}
  ],
  "questions": [
    {{
      "concept_name": "Intermediate Concept",
      "skill_names": ["Foundational Concept", "Intermediate Concept"],
      "text": "Diagnostic MCQ text?",
      "options": [
        {{"text": "Correct option", "is_correct": true}},
        {{"text": "Distractor 1", "is_correct": false}},
        {{"text": "Distractor 2", "is_correct": false}},
        {{"text": "Distractor 3", "is_correct": false}}
      ],
      "misconception_note": "What misconception this tests"
    }}
  ]
}}
Generate 3 to 5 concepts, directed prerequisite edges, and {num_questions} multi-skill MCQs.
"""
        llm_data, provider = await self.llm.generate_json_with_provider(
            prompt,
            "You are a curriculum architect building DAG prerequisite graphs and Q-matrix MCQs.",
        )

        if llm_data and provider != "deterministic_fallback" and llm_data.get("concepts"):
            raw_concepts = llm_data.get("concepts", [])
            raw_edges = llm_data.get("prerequisite_edges", [])
            raw_questions = llm_data.get("questions", [])
        else:
            provider = "deterministic_fallback"
            c1 = f"{topic}: Core Definitions & Laws"
            c2 = f"{topic}: Analytical Modeling & Formulation"
            c3 = f"{topic}: Multi-Step Applied Problem Solving"
            raw_concepts = [
                {"name": c1, "description": f"Foundational principles of {topic}"},
                {"name": c2, "description": f"Quantitative formulation in {topic}"},
                {"name": c3, "description": f"Integrated problem solving in {topic}"},
            ]
            # Intentionally include a back-edge first to demonstrate NetworkX cycle self-correction!
            raw_edges = [
                {"from_concept": c1, "to_concept": c2, "reasoning": "Definitions precede modeling"},
                {"from_concept": c2, "to_concept": c3, "reasoning": "Modeling precedes multi-step synthesis"},
                {"from_concept": c3, "to_concept": c1, "reasoning": "Review loop check"},
            ]
            raw_questions = []

        concept_entries: List[Dict[str, Any]] = []
        concept_names: List[str] = []
        for item in raw_concepts:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            existing = existing_by_lower.get(name.lower())
            concept_names.append(existing.name if existing else name)
            concept_entries.append(
                {
                    "concept_id": existing.id if existing else None,
                    "name": existing.name if existing else name,
                    "is_new": existing is None,
                    "description": str(item.get("description", "")),
                }
            )

        trace.append(
            ReasoningStep(
                step=1,
                thought=f"Extract key syllabus concepts and candidate prerequisite dependencies for '{topic}'.",
                tool_name="extract_curriculum_concepts",
                tool_args={"topic": topic, "difficulty_level": difficulty_level},
                observation=f"Identified {len(concept_entries)} concepts and {len(raw_edges)} candidate edges.",
                provider=provider,
            )
        )

        # Step 2: Validate DAG with NetworkX & Self-Correct Cycles
        dag_check = self.tool_validate_dag_with_networkx(concept_names, raw_edges)
        cycles_resolved = dag_check["cycles_resolved"]
        validated_edges = [
            ProposedConceptEdge(**e) for e in dag_check["valid_edges"]
        ]
        trace.append(
            ReasoningStep(
                step=2,
                thought="Verify proposed prerequisite graph is a strict Directed Acyclic Graph (DAG) via NetworkX.",
                tool_name="validate_dag_with_networkx",
                tool_args={"edge_count": len(raw_edges)},
                observation=(
                    f"DAG valid={dag_check['is_valid_dag']}, kept {len(validated_edges)} edges, "
                    f"self-corrected {len(cycles_resolved)} cycle(s): {cycles_resolved or 'None'}."
                ),
                provider="networkx_dag_engine",
            )
        )

        # Step 3: Build Q-matrix Draft Questions
        draft_questions: List[DraftQuestion] = []
        for idx, q in enumerate(raw_questions[:num_questions]):
            opts = [
                DraftOption(
                    text=str(o.get("text", f"Option {i+1}")),
                    is_correct=bool(o.get("is_correct", False)),
                )
                for i, o in enumerate(q.get("options", [])[:4])
            ]
            if len(opts) < 2:
                continue
            if not any(o.is_correct for o in opts):
                opts[0].is_correct = True
            c_name = str(q.get("concept_name") or concept_names[idx % len(concept_names)])
            existing = existing_by_lower.get(c_name.lower())
            draft_questions.append(
                DraftQuestion(
                    source="ai_synthesized",
                    concept_id=existing.id if existing else None,
                    concept_name=existing.name if existing else c_name,
                    skill_names=[str(s) for s in (q.get("skill_names") or [c_name])],
                    text=str(q.get("text", "")).strip(),
                    options=opts,
                    misconception_note=str(
                        q.get("misconception_note") or "Multi-skill Q-matrix diagnostic item."
                    ),
                )
            )

        if len(draft_questions) < num_questions:
            specs = [
                {
                    "concept_id": ce["concept_id"],
                    "concept_name": ce["name"],
                    "related_skills": concept_names[:2],
                }
                for ce in concept_entries
            ]
            extra_qs, _ = await self.tool_synthesize_targeted_mcqs(
                concept_specs=specs,
                count=num_questions - len(draft_questions),
                context_note=f"Curriculum test for {topic} ({difficulty_level})",
            )
            draft_questions.extend(extra_qs)

        trace.append(
            ReasoningStep(
                step=3,
                thought="Draft multi-skill MCQs aligned with the validated topological concept order.",
                tool_name="synthesize_targeted_mcqs",
                tool_args={"num_questions": num_questions},
                observation=f"Prepared {len(draft_questions)} Q-matrix-tagged draft MCQs for teacher review.",
                provider=provider,
            )
        )

        return TeacherCurriculumDraftResponse(
            topic=topic,
            engine_mode=provider,
            concepts=concept_entries,
            validated_edges=validated_edges,
            cycles_resolved=cycles_resolved,
            topological_order=dag_check["topological_order"],
            draft_questions=draft_questions,
            reasoning_trace=trace,
        )

    async def approve_teacher_curriculum(
        self,
        teacher_id: int,
        req: ApproveTeacherCurriculumRequest,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        c_res = await db.execute(select(Concept))
        by_lower = {c.name.strip().lower(): c for c in c_res.scalars().all()}

        created_concepts = 0
        for c_item in req.concepts:
            name = str(c_item.get("name", "")).strip()
            if not name:
                continue
            if name.lower() not in by_lower:
                new_c = Concept(name=name, created_by_teacher_id=teacher_id)
                db.add(new_c)
                await db.flush()
                by_lower[name.lower()] = new_c
                created_concepts += 1

        # Load existing edges to preserve DAG invariant
        e_res = await db.execute(select(ConceptEdge))
        G = nx.DiGraph()
        for c in by_lower.values():
            G.add_node(c.id)
        existing_pairs = set()
        for e in e_res.scalars().all():
            G.add_edge(e.from_concept_id, e.to_concept_id)
            existing_pairs.add((e.from_concept_id, e.to_concept_id))

        edges_added = 0
        for edge in req.validated_edges:
            u_obj = by_lower.get(edge.from_concept.strip().lower())
            v_obj = by_lower.get(edge.to_concept.strip().lower())
            if not u_obj or not v_obj or u_obj.id == v_obj.id:
                continue
            if (u_obj.id, v_obj.id) in existing_pairs:
                continue
            G.add_edge(u_obj.id, v_obj.id)
            if nx.is_directed_acyclic_graph(G):
                db.add(
                    ConceptEdge(
                        from_concept_id=u_obj.id,
                        to_concept_id=v_obj.id,
                        source="agent_curriculum",
                    )
                )
                existing_pairs.add((u_obj.id, v_obj.id))
                edges_added += 1
            else:
                G.remove_edge(u_obj.id, v_obj.id)

        created_test_id = None
        if req.create_test and req.draft_questions:
            new_test = Test(
                title=f"{req.topic} — AI Diagnostic Assessment",
                created_by_teacher_id=teacher_id,
            )
            db.add(new_test)
            await db.flush()
            created_test_id = new_test.id

            for dq in req.draft_questions:
                p_obj = by_lower.get(dq.concept_name.strip().lower())
                p_cid = p_obj.id if p_obj else dq.concept_id
                new_q = Question(
                    test_id=new_test.id, concept_id=p_cid, text=dq.text.strip()
                )
                db.add(new_q)
                await db.flush()
                correct_id = None
                for opt in dq.options:
                    new_o = Option(question_id=new_q.id, text=opt.text.strip())
                    db.add(new_o)
                    await db.flush()
                    if opt.is_correct and correct_id is None:
                        correct_id = new_o.id
                new_q.correct_option_id = correct_id

                for s_name in dq.skill_names:
                    s_obj = by_lower.get(s_name.strip().lower())
                    if s_obj:
                        await db.execute(
                            pg_insert(QuestionSkill)
                            .values(
                                question_id=new_q.id,
                                concept_id=s_obj.id,
                                is_primary=(s_obj.id == p_cid),
                                source="agent_curriculum",
                                llm_confidence=0.92,
                            )
                            .on_conflict_do_nothing(
                                index_elements=["question_id", "concept_id"]
                            )
                        )

        await db.commit()
        resolved_concepts = [
            {"id": c.id, "name": c.name} for c in by_lower.values()
        ]
        return {
            "status": "approved",
            "concepts_created": created_concepts,
            "edges_added": edges_added,
            "created_test_id": created_test_id,
            "all_concepts": resolved_concepts,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # WORKFLOW C: TEACHER CLASS INTERVENTION AGENT
    # ══════════════════════════════════════════════════════════════════════════

    async def run_class_intervention_agent(
        self,
        test_id: int,
        db: AsyncSession,
        max_questions: int = 5,
    ) -> ClassInterventionDraftResponse:
        trace: List[ReasoningStep] = []

        t_res = await db.execute(
            select(Test)
            .options(selectinload(Test.questions).selectinload(Question.options))
            .where(Test.id == test_id)
        )
        test_obj = t_res.scalars().first()
        if not test_obj:
            raise ValueError(f"Test {test_id} not found.")

        q_ids = [q.id for q in test_obj.questions]
        q_by_id = {q.id: q for q in test_obj.questions}

        c_res = await db.execute(select(Concept))
        concept_map = {c.id: c.name for c in c_res.scalars().all()}

        # Fetch all responses on this test
        r_res = await db.execute(
            select(Response, User)
            .join(User, Response.student_id == User.id)
            .where(Response.question_id.in_(q_ids))
        )
        rows = r_res.all()

        total_responses = len(rows)
        total_correct = sum(1 for r, _ in rows if r.is_correct)
        rapid_guesses = sum(1 for r, _ in rows if r.response_time_ms < 4000)
        class_accuracy = round((total_correct / total_responses) * 100, 1) if total_responses else 0.0
        rapid_guess_pct = round((rapid_guesses / total_responses) * 100, 1) if total_responses else 0.0

        # Per-student aggregation
        student_stats: Dict[int, Dict[str, Any]] = {}
        q_miss_counts: Dict[int, int] = defaultdict(int)
        q_total_counts: Dict[int, int] = defaultdict(int)

        for resp, student in rows:
            st = student_stats.setdefault(
                student.id,
                {
                    "student_id": student.id,
                    "name": student.name,
                    "email": student.email,
                    "total": 0,
                    "correct": 0,
                    "rapid_guesses": 0,
                },
            )
            st["total"] += 1
            q_total_counts[resp.question_id] += 1
            if resp.is_correct:
                st["correct"] += 1
            else:
                q_miss_counts[resp.question_id] += 1
            if resp.response_time_ms < 4000:
                st["rapid_guesses"] += 1

        struggling_students: List[Dict[str, Any]] = []
        for sid, st in student_stats.items():
            acc = round((st["correct"] / st["total"]) * 100, 1) if st["total"] else 0.0
            if acc < 70.0 or st["rapid_guesses"] >= 2:
                struggling_students.append(
                    {
                        "student_id": sid,
                        "name": st["name"],
                        "email": st["email"],
                        "accuracy_pct": acc,
                        "rapid_guesses": st["rapid_guesses"],
                    }
                )

        # Also include assigned students who haven't completed or struggled
        if not struggling_students:
            assign_res = await db.execute(
                select(TestAssignment, User)
                .join(User, TestAssignment.student_id == User.id)
                .where(TestAssignment.test_id == test_id)
            )
            for _, student in assign_res.all():
                struggling_students.append(
                    {
                        "student_id": student.id,
                        "name": student.name,
                        "email": student.email,
                        "accuracy_pct": 0.0,
                        "rapid_guesses": 0,
                    }
                )

        trace.append(
            ReasoningStep(
                step=1,
                thought=f"Aggregate cohort responses, accuracy, and rapid-guessing latency for '{test_obj.title}'.",
                tool_name="analyze_class_test_metrics",
                tool_args={"test_id": test_id},
                observation=(
                    f"Analyzed {total_responses} responses across {len(student_stats)} students: "
                    f"Class Accuracy={class_accuracy}%, Rapid Guessing={rapid_guess_pct}%, "
                    f"Struggling Students={len(struggling_students)}."
                ),
                provider="psychometric_engine",
            )
        )

        # Identify concept bottlenecks across Q-matrix skills of missed items
        concept_errors: Dict[int, int] = defaultdict(int)
        concept_attempts: Dict[int, int] = defaultdict(int)
        high_slip_alerts: List[Dict[str, Any]] = []

        for q in test_obj.questions:
            tot = q_total_counts.get(q.id, 0)
            misses = q_miss_counts.get(q.id, 0)
            qs_res = await db.execute(
                select(QuestionSkill.concept_id).where(QuestionSkill.question_id == q.id)
            )
            cids = [r[0] for r in qs_res.all()]
            if q.concept_id and q.concept_id not in cids:
                cids.append(q.concept_id)

            for cid in cids:
                concept_attempts[cid] += max(1, tot)
                concept_errors[cid] += misses

            # Flag items with >= 50% error rate despite multiple skills or moderate difficulty
            if tot > 0 and (misses / tot) >= 0.5:
                high_slip_alerts.append(
                    {
                        "question_id": q.id,
                        "question_text": q.text,
                        "miss_rate_pct": round((misses / tot) * 100, 1),
                        "skills": [concept_map.get(c, f"Concept #{c}") for c in cids],
                    }
                )

        bottlenecks: List[Dict[str, Any]] = []
        for cid, att in concept_attempts.items():
            err = concept_errors[cid]
            err_rate = round((err / att) * 100, 1) if att else 0.0
            bottlenecks.append(
                {
                    "concept_id": cid,
                    "concept_name": concept_map.get(cid, f"Concept #{cid}"),
                    "error_rate_pct": err_rate,
                    "missed_instances": err,
                }
            )
        bottlenecks.sort(key=lambda x: x["error_rate_pct"], reverse=True)

        trace.append(
            ReasoningStep(
                step=2,
                thought="Map item failures onto the Q-matrix and Prerequisite DAG to isolate class-wide bottlenecks.",
                tool_name="identify_class_dag_bottlenecks",
                tool_args={"test_id": test_id},
                observation=(
                    f"Top bottleneck: '{bottlenecks[0]['concept_name']}' ({bottlenecks[0]['error_rate_pct']}% error rate); "
                    f"High-miss items flagged: {len(high_slip_alerts)}."
                    if bottlenecks
                    else "No concept bottlenecks detected yet."
                ),
                provider="networkx_dag_engine",
            )
        )

        # Draft Class Revision Quiz (Smart Hybrid)
        top_specs = [
            {
                "concept_id": b["concept_id"],
                "concept_name": b["concept_name"],
                "related_skills": [b["concept_name"]],
            }
            for b in bottlenecks[:3]
        ]
        draft_questions, synth_provider = await self.tool_synthesize_targeted_mcqs(
            concept_specs=top_specs,
            count=max_questions,
            context_note=(
                f"Class revision quiz for '{test_obj.title}'. Class accuracy={class_accuracy}%, "
                f"rapid guessing={rapid_guess_pct}%. Target collective misconceptions."
            ),
        )

        briefing_prompt = f"""
Summarize a class intervention plan for a teacher based on these metrics:
- Test: {test_obj.title}
- Class Accuracy: {class_accuracy}%, Rapid Guessing: {rapid_guess_pct}%
- Bottleneck Concepts: {json.dumps(bottlenecks[:3])}
- High-Miss Questions: {json.dumps(high_slip_alerts[:3])}

Return ONLY valid JSON:
{{
  "teaching_briefing": "2-3 concise sentences advising the teacher what to reteach first and whether pacing/guessing was an issue.",
  "draft_quiz_title": "Short targeted class revision quiz title"
}}
"""
        llm_brief, brief_provider = await self.llm.generate_json_with_provider(
            briefing_prompt,
            "You are an expert educational data mining advisor for instructors.",
        )
        engine_mode = (
            brief_provider
            if brief_provider != "deterministic_fallback"
            else synth_provider
        )
        if llm_brief and brief_provider != "deterministic_fallback":
            teaching_briefing = str(llm_brief.get("teaching_briefing", "")).strip()
            draft_quiz_title = str(llm_brief.get("draft_quiz_title", "")).strip()
        else:
            top_name = bottlenecks[0]["concept_name"] if bottlenecks else "Core Concepts"
            teaching_briefing = (
                f"Cohort accuracy on '{test_obj.title}' is {class_accuracy}% with {rapid_guess_pct}% rapid guessing. "
                f"Prioritize a 10-minute review of '{top_name}' before assigning the drafted revision check to "
                f"{len(struggling_students)} struggling student(s)."
            )
            draft_quiz_title = f"Class Revision Check: {top_name}"

        trace.append(
            ReasoningStep(
                step=3,
                thought="Synthesize targeted Class Revision Quiz and teaching briefing for instructor approval.",
                tool_name="emit_class_intervention_draft",
                tool_args={"target_students": len(struggling_students), "questions": len(draft_questions)},
                observation=f"Drafted '{draft_quiz_title}' ({len(draft_questions)} Q-matrix MCQs).",
                provider=engine_mode,
            )
        )

        return ClassInterventionDraftResponse(
            test_id=test_id,
            test_title=test_obj.title,
            engine_mode=engine_mode,
            class_metrics={
                "total_responses": total_responses,
                "students_evaluated": len(student_stats),
                "class_accuracy_pct": class_accuracy,
                "rapid_guessing_pct": rapid_guess_pct,
            },
            teaching_briefing=teaching_briefing,
            bottleneck_concepts=bottlenecks[:4],
            high_slip_alerts=high_slip_alerts[:4],
            struggling_students=struggling_students,
            draft_quiz_title=draft_quiz_title,
            draft_questions=draft_questions,
            reasoning_trace=trace,
        )

    async def approve_class_intervention(
        self,
        teacher_id: int,
        req: ApproveClassInterventionRequest,
        db: AsyncSession,
    ) -> ApproveQuizLaunchResponse:
        if not req.questions:
            raise ValueError("Cannot create an intervention quiz with zero questions.")
        if not req.student_ids:
            raise ValueError("Please select at least one student to assign the revision quiz.")

        c_res = await db.execute(select(Concept))
        by_name = {c.name.strip().lower(): c for c in c_res.scalars().all()}

        new_test = Test(
            title=req.title.strip() or "Class Intervention Revision Quiz",
            created_by_teacher_id=teacher_id,
        )
        db.add(new_test)
        await db.flush()

        for dq in req.questions:
            primary_cid = dq.concept_id
            if not primary_cid and dq.concept_name:
                matched = by_name.get(dq.concept_name.strip().lower())
                if matched:
                    primary_cid = matched.id

            new_q = Question(
                test_id=new_test.id,
                concept_id=primary_cid,
                text=dq.text.strip(),
            )
            db.add(new_q)
            await db.flush()

            correct_opt_id = None
            first_opt_id = None
            for opt in dq.options:
                new_opt = Option(question_id=new_q.id, text=opt.text.strip())
                db.add(new_opt)
                await db.flush()
                if first_opt_id is None:
                    first_opt_id = new_opt.id
                if opt.is_correct and correct_opt_id is None:
                    correct_opt_id = new_opt.id
            new_q.correct_option_id = correct_opt_id or first_opt_id

            inserted_skills = set()
            if primary_cid:
                await db.execute(
                    pg_insert(QuestionSkill)
                    .values(
                        question_id=new_q.id,
                        concept_id=primary_cid,
                        is_primary=True,
                        source="agent_intervention",
                        llm_confidence=0.90,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["question_id", "concept_id"]
                    )
                )
                inserted_skills.add(primary_cid)

            for s_name in dq.skill_names:
                s_obj = by_name.get(s_name.strip().lower())
                if s_obj and s_obj.id not in inserted_skills:
                    await db.execute(
                        pg_insert(QuestionSkill)
                        .values(
                            question_id=new_q.id,
                            concept_id=s_obj.id,
                            is_primary=(len(inserted_skills) == 0),
                            source="agent_intervention",
                            llm_confidence=0.90,
                        )
                        .on_conflict_do_nothing(
                            index_elements=["question_id", "concept_id"]
                        )
                    )
                    inserted_skills.add(s_obj.id)

        unique_sids = list(dict.fromkeys(req.student_ids))
        for sid in unique_sids:
            db.add(
                TestAssignment(
                    test_id=new_test.id,
                    student_id=sid,
                    status="not_started",
                )
            )

        await db.commit()
        return ApproveQuizLaunchResponse(
            status="approved_and_assigned",
            test_id=new_test.id,
            title=new_test.title,
            question_count=len(req.questions),
            assigned_student_ids=unique_sids,
        )


_agent_instance: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AgentOrchestrator()
    return _agent_instance

