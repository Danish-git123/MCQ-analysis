"""
Advanced Cognitive Analytics & Prerequisite Debt Engine.
Provides unique psychometric analyses beyond standard scoring:

1. Cognitive Effort & Latency 4-Quadrant Profiler:
   - Evaluates Response-Time Effort (RTE) according to Wise & Kong (2005).
   - Classifies student behavior into 4 Cognitive Quadrants:
     * Quadrant 1: Cognitive Fluency (Fast/Adequate + Correct)
     * Quadrant 2: Deliberate Mastery (High Thinking Time + Correct)
     * Quadrant 3: Cognitive Struggle (High Effort + Incorrect)
     * Quadrant 4: Rapid Guessing (Disengaged / Guess < 4s)

2. Prerequisite Debt & Directed Topological Remediation:
   - Measures "Prerequisite Debt": The fraction of advanced concept failures
     that directly stem from unmastered upstream roots in the DAG.
   - Uses NetworkX topological sorting on the weak-concept induced subgraph
     to provide an exact sequential learning roadmap (e.g. Learn A -> Then B -> Then C).

3. Unified Tri-Model Integration:
   - Synthesizes DINA (Multi-Skill), BKT (Knowledge Trajectory), and
     Logistic Regression (Slip Anomaly Detection) into an executive diagnostic report.
"""

import math
import logging
import networkx as nx
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import (
    Response, Question, QuestionSkill, Concept, ConceptEdge, 
    CognitiveDiagnosisProfile, StudentConceptMastery, Option
)
from app.services.prediction_service import get_prediction_service
from app.services.mastery_service import get_mastery_estimator
from app.services.dina_service import get_dina_service

logger = logging.getLogger(__name__)


class CognitiveAnalyticsService:

    async def compute_effort_quadrant_analysis(
        self,
        student_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyzes student response times against expected cognitive solving latencies
        to classify each attempt into 4 psychometric behavioral quadrants.
        """
        # Fetch all responses with question details
        stmt = (
            select(Response, Question)
            .join(Question, Response.question_id == Question.id)
            .where(Response.student_id == student_id)
            .order_by(Response.answered_at.desc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        if not rows:
            return {
                "total_responses": 0,
                "quadrants": {
                    "cognitive_fluency": 0,
                    "deliberate_mastery": 0,
                    "cognitive_struggle": 0,
                    "rapid_guessing": 0
                },
                "effort_consistency_index": 0.0,
                "detailed_attempts": []
            }

        fluency_count = 0
        deliberate_count = 0
        struggle_count = 0
        rapid_guess_count = 0
        detailed_attempts = []

        # Predictor for slip detection
        predictor = get_prediction_service()

        for resp, q in rows:
            time_ms = resp.response_time_ms
            is_correct = resp.is_correct

            # Calculate expected cognitive solving time:
            # Base 8s reading + ~0.3s per word + 5s per question skill
            word_count = len(q.text.split()) if q.text else 15
            expected_time_ms = max(7000, int(8000 + (word_count * 300) + 5000))
            latency_ratio = round(time_ms / expected_time_ms, 2)

            # 4-Quadrant Classification
            if time_ms < 4000:
                quadrant = "RAPID_GUESSING"
                quadrant_label = "Rapid Guessing (Low Effort)"
                quadrant_color = "#94A3B8" # Slate
                rapid_guess_count += 1
            elif is_correct and latency_ratio <= 1.8:
                quadrant = "COGNITIVE_FLUENCY"
                quadrant_label = "Cognitive Fluency (Automated Mastery)"
                quadrant_color = "#10B981" # Emerald
                fluency_count += 1
            elif is_correct and latency_ratio > 1.8:
                quadrant = "DELIBERATE_MASTERY"
                quadrant_label = "Deliberate Mastery (High Deliberation)"
                quadrant_color = "#3B82F6" # Royal Blue
                deliberate_count += 1
            else:
                # Incorrect + adequate/high time -> struggled with concept
                quadrant = "COGNITIVE_STRUGGLE"
                quadrant_label = "Cognitive Roadblock (Conceptual Struggle)"
                quadrant_color = "#EF4444" # Red
                struggle_count += 1

            # Check if careless slip
            anomaly = await predictor.analyze_response_anomaly(
                student_id=student_id,
                question_id=q.id,
                is_correct=is_correct,
                response_time_ms=time_ms,
                db=db
            )

            detailed_attempts.append({
                "question_id": q.id,
                "question_text": q.text,
                "is_correct": is_correct,
                "actual_time_seconds": round(time_ms / 1000.0, 1),
                "expected_time_seconds": round(expected_time_ms / 1000.0, 1),
                "latency_ratio": latency_ratio,
                "quadrant": quadrant,
                "quadrant_label": quadrant_label,
                "quadrant_color": quadrant_color,
                "anomaly_type": anomaly["anomaly_type"],
                "predicted_probability": anomaly["predicted_probability"],
                "pedagogical_message": anomaly["pedagogical_message"]
            })

        total = len(rows)
        # Effort Consistency Index (ECI): % of questions answered with genuine reading effort (non-rapid guess)
        eci = round((total - rapid_guess_count) / total, 3) if total > 0 else 0.0

        return {
            "total_responses": total,
            "quadrant_distribution": {
                "cognitive_fluency_pct": round((fluency_count / total) * 100, 1),
                "deliberate_mastery_pct": round((deliberate_count / total) * 100, 1),
                "cognitive_struggle_pct": round((struggle_count / total) * 100, 1),
                "rapid_guessing_pct": round((rapid_guess_count / total) * 100, 1),
                "counts": {
                    "cognitive_fluency": fluency_count,
                    "deliberate_mastery": deliberate_count,
                    "cognitive_struggle": struggle_count,
                    "rapid_guessing": rapid_guess_count
                }
            },
            "effort_consistency_index": eci,
            "detailed_attempts": detailed_attempts[:15] # Top 15 recent attempts
        }

    async def compute_prerequisite_debt_and_roadmap(
        self,
        student_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyzes the curriculum Prerequisite DAG to compute:
        1. Prerequisite Debt Score (% of weak concepts caused by upstream broken prerequisites).
        2. Topologically Ordered Remediation Roadmap: The exact sequence in which the
           student should study weak concepts so that fundamentals are fixed before advanced ones.
        """
        # 1. Fetch all concepts and edges
        c_res = await db.execute(select(Concept))
        all_concepts = {c.id: c.name for c in c_res.scalars().all()}

        e_res = await db.execute(select(ConceptEdge))
        edges = e_res.scalars().all()

        # Build NetworkX DiGraph
        G = nx.DiGraph()
        for cid in all_concepts.keys():
            G.add_node(cid)
        for e in edges:
            G.add_edge(e.from_concept_id, e.to_concept_id)

        # 2. Fetch student DINA mastery scores
        p_res = await db.execute(
            select(CognitiveDiagnosisProfile).where(CognitiveDiagnosisProfile.student_id == student_id)
        )
        profiles = {p.concept_id: p for p in p_res.scalars().all()}

        # Identify weak concepts (adjusted_mastery < 0.50)
        weak_concept_ids = set()
        mastered_concept_ids = set()

        for cid in all_concepts.keys():
            prof = profiles.get(cid)
            mastery = prof.adjusted_mastery if prof else 0.50
            if mastery < 0.50:
                weak_concept_ids.add(cid)
            elif mastery >= 0.70:
                mastered_concept_ids.add(cid)

        if not weak_concept_ids:
            return {
                "prerequisite_debt_score": 0.0,
                "debt_level": "ZERO_DEBT",
                "summary": "Outstanding conceptual mastery! No prerequisite debt detected.",
                "total_weak_concepts": 0,
                "remediation_roadmap": []
            }

        # 3. Calculate Prerequisite Debt
        # A weak concept is in "Debt" if at least one of its ancestors in the DAG is ALSO weak
        debt_caused_weak_concepts = 0
        root_causes = set()

        for w_cid in weak_concept_ids:
            # Check predecessors (immediate prerequisites)
            preds = list(G.predecessors(w_cid))
            unmastered_preds = [p for p in preds if p in weak_concept_ids]
            if unmastered_preds:
                debt_caused_weak_concepts += 1
                root_causes.update(unmastered_preds)

        debt_score = round(debt_caused_weak_concepts / len(weak_concept_ids), 3)

        if debt_score > 0.60:
            debt_level = "CRITICAL_FOUNDATIONAL_DEBT"
            debt_advice = (
                f"{int(debt_score*100)}% of your advanced difficulties are collateral damage from "
                "unmastered foundational prerequisites. Do not study advanced topics until root concepts are fixed."
            )
        elif debt_score > 0.20:
            debt_level = "MODERATE_PREREQUISITE_DEBT"
            debt_advice = "A moderate portion of your errors stem from specific upstream prerequisite gaps."
        else:
            debt_level = "ISOLATED_GAPS"
            debt_advice = "Your gaps are isolated to individual topics rather than cascading foundational blockers."

        # 4. Topological Sort on the Weak Concepts Induced Subgraph
        # Create subgraph containing weak concepts + their direct unmastered prerequisites
        subgraph_nodes = weak_concept_ids.union(root_causes)
        sub_G = G.subgraph(subgraph_nodes).copy()

        # Safely obtain topological order (if cycles exist despite DAG checks, fallback to in-degree)
        try:
            ordered_node_ids = list(nx.topological_sort(sub_G))
        except nx.NetworkXUnfeasible:
            # Fallback sorting by in-degree (fewer dependencies first)
            ordered_node_ids = sorted(list(subgraph_nodes), key=lambda n: sub_G.in_degree(n))

        # Build clean step-by-step remediation roadmap
        roadmap = []
        for step_num, cid in enumerate(ordered_node_ids, 1):
            prof = profiles.get(cid)
            mastery = round(prof.adjusted_mastery if prof else 0.50, 3)
            conf = round(prof.confidence_score if prof else 0.0, 3)
            
            # Find which concepts this step unlocks
            unlocks = [all_concepts[succ] for succ in G.successors(cid) if succ in weak_concept_ids]

            roadmap.append({
                "step": step_num,
                "concept_id": cid,
                "concept_name": all_concepts.get(cid, f"Concept #{cid}"),
                "current_mastery": mastery,
                "confidence_score": conf,
                "is_root_blocker": cid in root_causes,
                "unlocks_topics": unlocks,
                "action_priority": "CRITICAL_FIRST_STEP" if step_num == 1 else "FOLLOW_UP_REINFORCEMENT"
            })

        return {
            "prerequisite_debt_score": debt_score,
            "debt_level": debt_level,
            "debt_advice": debt_advice,
            "total_weak_concepts": len(weak_concept_ids),
            "root_blocker_count": len(root_causes),
            "remediation_roadmap": roadmap
        }

    async def get_comprehensive_advanced_analytics(
        self,
        student_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Synthesizes all 3 models (DINA + BKT + Logistic Regression) along with
        Cognitive Effort and Prerequisite Debt into an executive diagnostic dossier.
        """
        # 1. Effort & Latency Quadrants
        effort_data = await self.compute_effort_quadrant_analysis(student_id, db)

        # 2. Prerequisite Debt & Roadmap
        roadmap_data = await self.compute_prerequisite_debt_and_roadmap(student_id, db)

        # 3. DINA Multi-Skill Mastery
        dina_service = get_dina_service()
        dina_profiles = await dina_service.get_all_student_diagnoses(student_id, db)

        # 4. BKT Sequential Progress
        bkt_service = get_mastery_estimator()
        bkt_masteries = await bkt_service.get_all_student_masteries(student_id, db)

        # Merge DINA and BKT scores per concept
        bkt_map = {b["concept_id"]: b["mastery_p"] for b in bkt_masteries}
        integrated_concepts = []
        for d in dina_profiles:
            cid = d["concept_id"]
            dina_p = d["adjusted_mastery"]
            bkt_p = bkt_map.get(cid, 0.20)
            conf = d["confidence_score"]
            tier = d["reliability_tier"]

            # Tri-Model Convergence status
            if abs(dina_p - bkt_p) < 0.15:
                convergence = "HIGH_AGREEMENT"
            elif dina_p > bkt_p:
                convergence = "DINA_OPTIMISTIC" # multi-skill synergy
            else:
                convergence = "BKT_ACCUMULATED" # historical practice

            integrated_concepts.append({
                "concept_id": cid,
                "concept_name": d["concept_name"],
                "dina_adjusted_mastery": dina_p,
                "bkt_sequential_mastery": bkt_p,
                "model_convergence": convergence,
                "confidence_score": conf,
                "reliability_tier": tier,
                "opportunity_count": d["opportunity_count"],
                "status": "MASTERED" if dina_p >= 0.70 else ("MODERATE" if dina_p >= 0.40 else "WEAK_GAP")
            })

        return {
            "student_id": student_id,
            "executive_summary": {
                "effort_consistency_index": effort_data["effort_consistency_index"],
                "prerequisite_debt_score": roadmap_data["prerequisite_debt_score"],
                "debt_level": roadmap_data["debt_level"],
                "total_concepts_evaluated": len(integrated_concepts),
                "mastered_concepts": sum(1 for c in integrated_concepts if c["status"] == "MASTERED"),
                "moderate_concepts": sum(1 for c in integrated_concepts if c["status"] == "MODERATE"),
                "weak_concepts": sum(1 for c in integrated_concepts if c["status"] == "WEAK_GAP"),
            },
            "quadrant_distribution": effort_data["quadrant_distribution"],
            "prerequisite_debt_report": {
                "debt_score": roadmap_data["prerequisite_debt_score"],
                "debt_level": roadmap_data["debt_level"],
                "debt_advice": roadmap_data["debt_advice"],
                "remediation_roadmap": roadmap_data["remediation_roadmap"]
            },
            "integrated_concept_matrix": integrated_concepts,
            "recent_cognitive_attempts": effort_data["detailed_attempts"]
        }


# Singleton factory
_analytics_instance = None

def get_cognitive_analytics_service() -> CognitiveAnalyticsService:
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = CognitiveAnalyticsService()
    return _analytics_instance

