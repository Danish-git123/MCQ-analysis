"""
Layer 3 — DINA (Deterministic Inputs, Noisy AND) Cognitive Diagnosis Service.

Implements a Multi-Attribute DINA model using fixed slip/guess parameters (cold-start mode).
Constructs a Q-matrix graph per student to marginalize over joint probability profiles
for interconnected skills (blocks).
"""

from typing import List, Tuple, Dict, Any, Optional, Set
import logging
import math
import numpy as np
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Response, Question, CognitiveDiagnosisProfile, Concept, QuestionSkill

logger = logging.getLogger(__name__)

# ─── Fixed DINA Parameters (cold-start informative priors) ───────────────────
DEFAULT_SLIP = 0.10   # P(incorrect | mastered)
DEFAULT_GUESS = 0.25  # P(correct  | not mastered)
DEFAULT_PRIOR = 0.50  # Uninformative prior P(α=1) for DINA

# ─── Reliability Tier Thresholds ───────────────
RELIABILITY_LOW_UPPER = 0.40
RELIABILITY_MEDIUM_UPPER = 0.75
K_MAX = 12 # Maximum block size before falling back to single-skill


def get_item_parameters(question_id: int) -> Tuple[float, float]:
    """Return (slip, guess) for a given question. (Current: Fixed)."""
    return DEFAULT_SLIP, DEFAULT_GUESS


def _reliability_tier(confidence: float) -> str:
    if confidence < RELIABILITY_LOW_UPPER:
        return "LOW"
    elif confidence < RELIABILITY_MEDIUM_UPPER:
        return "MEDIUM"
    else:
        return "HIGH"


class DINADiagnosisService:

    async def update_diagnosis(
        self,
        student_id: int,
        concept_id: int, # the primary concept that triggered this update
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Recompute DINA cognitive diagnosis profiles for the connected block of skills
        containing `concept_id`.
        """
        # 1. Fetch all responses by the student
        stmt_resp = (
            select(Response.question_id, Response.is_correct)
            .where(Response.student_id == student_id)
        )
        res_resp = await db.execute(stmt_resp)
        student_responses = res_resp.all()
        
        if not student_responses:
            return []

        response_dict = {r[0]: r[1] for r in student_responses}
        answered_q_ids = list(response_dict.keys())

        # 2. Fetch Q-matrix for these questions from question_skills
        stmt_q_skills = (
            select(QuestionSkill.question_id, QuestionSkill.concept_id)
            .where(QuestionSkill.question_id.in_(answered_q_ids))
        )
        res_q_skills = await db.execute(stmt_q_skills)
        q_skills = res_q_skills.all()

        # Build Q-matrix dict: question_id -> set of concept_ids
        Q_matrix = defaultdict(set)
        for q_id, c_id in q_skills:
            Q_matrix[q_id].add(c_id)

        if concept_id not in [c for q, c in q_skills]:
            # If the triggering concept is not in the Q-matrix of answered questions, 
            # we can't update its diagnosis based on new responses.
            return []

        # 3. Build graph of concepts and find the connected block containing `concept_id`
        adj_list = defaultdict(set)
        for q_id, c_ids in Q_matrix.items():
            c_list = list(c_ids)
            for i in range(len(c_list)):
                for j in range(i + 1, len(c_list)):
                    adj_list[c_list[i]].add(c_list[j])
                    adj_list[c_list[j]].add(c_list[i])

        # BFS to find block
        visited = set()
        queue = [concept_id]
        visited.add(concept_id)
        block_concepts = []

        while queue:
            curr = queue.pop(0)
            block_concepts.append(curr)
            for neighbor in adj_list[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        K = len(block_concepts)
        results = []

        if K > K_MAX:
            logger.warning(f"Block size {K} exceeds K_MAX {K_MAX}. Falling back to single-skill exact for student {student_id}.")
            # Fallback to single-skill (primary-only) for each concept in the block
            # For simplicity, we just compute it for the triggering concept here, 
            # or we could loop through all in block.
            for c_id in block_concepts:
                # Find questions where this concept is present
                relevant_q_ids = [q_id for q_id, c_ids in Q_matrix.items() if c_id in c_ids]
                results.append(self._compute_single_skill_exact(c_id, relevant_q_ids, response_dict))
        else:
            results = self._compute_block_exact(block_concepts, Q_matrix, response_dict)

        # 4. Upsert results into cognitive_diagnosis_profile
        stmt_existing = select(CognitiveDiagnosisProfile).where(
            CognitiveDiagnosisProfile.student_id == student_id,
            CognitiveDiagnosisProfile.concept_id.in_(block_concepts)
        )
        res_existing = await db.execute(stmt_existing)
        existing_profiles = {p.concept_id: p for p in res_existing.scalars().all()}

        updated_data = []
        for res in results:
            c_id = res['concept_id']
            p_post = res['adjusted_mastery']
            opp_count = res['opportunity_count']
            
            # confidence_score = 1 - 4*p*(1-p)
            confidence = 1.0 - 4.0 * p_post * (1.0 - p_post)
            confidence = max(0.0, min(1.0, confidence))
            tier = _reliability_tier(confidence)

            if c_id in existing_profiles:
                p = existing_profiles[c_id]
                p.adjusted_mastery = p_post
                p.confidence_score = confidence
                p.reliability_tier = tier
                p.opportunity_count = opp_count
            else:
                p = CognitiveDiagnosisProfile(
                    student_id=student_id,
                    concept_id=c_id,
                    adjusted_mastery=p_post,
                    confidence_score=confidence,
                    reliability_tier=tier,
                    opportunity_count=opp_count
                )
                db.add(p)
            
            updated_data.append({
                "concept_id": c_id,
                "adjusted_mastery": round(p_post, 4),
                "confidence_score": round(confidence, 4),
                "reliability_tier": tier,
                "opportunity_count": opp_count,
            })

        await db.commit()
        return updated_data

    def _compute_single_skill_exact(
        self, 
        concept_id: int, 
        relevant_q_ids: List[int], 
        response_dict: Dict[int, bool]
    ) -> Dict[str, Any]:
        """Single attribute DINA (Special Case)."""
        responses = [response_dict[q_id] for q_id in relevant_q_ids if q_id in response_dict]
        
        if not responses:
            return {
                "concept_id": concept_id,
                "adjusted_mastery": DEFAULT_PRIOR,
                "opportunity_count": 0
            }

        # Vectorized single skill
        s, g = DEFAULT_SLIP, DEFAULT_GUESS
        log_lik_1 = 0.0
        log_lik_0 = 0.0
        
        for correct in responses:
            if correct:
                log_lik_1 += math.log(1.0 - s)
                log_lik_0 += math.log(g)
            else:
                log_lik_1 += math.log(s)
                log_lik_0 += math.log(1.0 - g)

        log_prior_1 = math.log(DEFAULT_PRIOR)
        log_prior_0 = math.log(1.0 - DEFAULT_PRIOR)

        log_joint_1 = log_lik_1 + log_prior_1
        log_joint_0 = log_lik_0 + log_prior_0

        # Log-Sum-Exp for normalization
        max_log = max(log_joint_1, log_joint_0)
        log_denom = max_log + math.log(math.exp(log_joint_1 - max_log) + math.exp(log_joint_0 - max_log))
        
        p_post = math.exp(log_joint_1 - log_denom)
        return {
            "concept_id": concept_id,
            "adjusted_mastery": p_post,
            "opportunity_count": len(responses)
        }

    def _compute_block_exact(
        self, 
        block_concepts: List[int], 
        Q_matrix: Dict[int, Set[int]], 
        response_dict: Dict[int, bool]
    ) -> List[Dict[str, Any]]:
        """Exact marginalization using vectorized numpy for multi-attribute DINA."""
        K = len(block_concepts)
        concept_to_idx = {c_id: i for i, c_id in enumerate(block_concepts)}
        
        # 1. Enumerate all 2^K profiles
        # profiles shape: (2^K, K)
        profiles = np.array(np.meshgrid(*[[0, 1]] * K)).T.reshape(-1, K)
        num_profiles = len(profiles)

        # 2. Prior: independent, P(alpha_k=1)=0.5
        # log_prior per profile = K * log(0.5)
        log_prior = K * math.log(DEFAULT_PRIOR)
        log_posteriors = np.full(num_profiles, log_prior)

        # 3. Likelihood calculation
        # Filter questions that require at least one concept in this block
        block_q_ids = [q_id for q_id, c_ids in Q_matrix.items() 
                      if any(c in concept_to_idx for c in c_ids) and q_id in response_dict]
        
        opp_counts = defaultdict(int)
        for q_id in block_q_ids:
            correct = response_dict[q_id]
            s, g = get_item_parameters(q_id)
            
            # Required skill indices in this block
            req_indices = [concept_to_idx[c] for c in Q_matrix[q_id] if c in concept_to_idx]
            for c_id in Q_matrix[q_id]:
                if c_id in concept_to_idx:
                    opp_counts[c_id] += 1
            
            # xi_j(alpha) = 1 if ALL required skills mastered
            # xi shape: (2^K,)
            if req_indices:
                xi = np.all(profiles[:, req_indices] == 1, axis=1)
            else:
                xi = np.ones(num_profiles, dtype=bool)

            # P(correct | alpha)
            prob_correct = np.where(xi, 1.0 - s, g)
            
            if correct:
                log_posteriors += np.log(prob_correct)
            else:
                log_posteriors += np.log(1.0 - prob_correct)

        # 4. Normalization (Log-Sum-Exp)
        max_log = np.max(log_posteriors)
        log_denom = max_log + np.log(np.sum(np.exp(log_posteriors - max_log)))
        
        # Normalize joint log-probabilities to get profile posteriors
        profile_posteriors = np.exp(log_posteriors - log_denom)

        # 5. Marginalization for each concept
        results = []
        for c_id in block_concepts:
            idx = concept_to_idx[c_id]
            # Sum posteriors of profiles where this concept is mastered
            p_post = np.sum(profile_posteriors[profiles[:, idx] == 1])
            results.append({
                "concept_id": c_id,
                "adjusted_mastery": float(p_post),
                "opportunity_count": opp_counts[c_id]
            })

        return results

    async def get_diagnosis(self, student_id: int, concept_id: int, db: AsyncSession) -> Optional[Dict[str, Any]]:
        stmt = select(CognitiveDiagnosisProfile).where(
            CognitiveDiagnosisProfile.student_id == student_id,
            CognitiveDiagnosisProfile.concept_id == concept_id,
        )
        res = await db.execute(stmt)
        profile = res.scalars().first()
        if not profile:
            return None
        return {
            "student_id": profile.student_id,
            "concept_id": profile.concept_id,
            "adjusted_mastery": profile.adjusted_mastery,
            "confidence_score": profile.confidence_score,
            "reliability_tier": profile.reliability_tier,
            "opportunity_count": profile.opportunity_count,
            "last_diagnosed_at": profile.last_diagnosed_at,
        }

    async def get_all_student_diagnoses(self, student_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        c_res = await db.execute(select(Concept))
        concepts = c_res.scalars().all()
        p_res = await db.execute(
            select(CognitiveDiagnosisProfile).where(CognitiveDiagnosisProfile.student_id == student_id)
        )
        profiles = {p.concept_id: p for p in p_res.scalars().all()}
        result = []
        for c in concepts:
            p = profiles.get(c.id)
            if p:
                result.append({
                    "concept_id": c.id, "concept_name": c.name,
                    "adjusted_mastery": p.adjusted_mastery,
                    "confidence_score": p.confidence_score, "reliability_tier": p.reliability_tier,
                    "opportunity_count": p.opportunity_count, "last_diagnosed_at": p.last_diagnosed_at,
                })
            else:
                prior_conf = 1.0 - 4.0 * DEFAULT_PRIOR * (1.0 - DEFAULT_PRIOR)
                result.append({
                    "concept_id": c.id, "concept_name": c.name,
                    "adjusted_mastery": DEFAULT_PRIOR,
                    "confidence_score": round(prior_conf, 4), "reliability_tier": _reliability_tier(prior_conf),
                    "opportunity_count": 0, "last_diagnosed_at": None,
                })
        return result

    async def get_question_why(self, student_id: int, question_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Explain WHY a student might have missed a question by listing required skills
        and their current mastery status.
        """
        # 1. Get skills required for this question
        stmt = select(QuestionSkill.concept_id).where(QuestionSkill.question_id == question_id)
        res = await db.execute(stmt)
        req_concept_ids = [r[0] for r in res.all()]
        
        if not req_concept_ids:
            return []

        # 2. Get student diagnosis for these concepts
        stmt_diag = select(CognitiveDiagnosisProfile, Concept.name).join(Concept).where(
            CognitiveDiagnosisProfile.student_id == student_id,
            CognitiveDiagnosisProfile.concept_id.in_(req_concept_ids)
        )
        res_diag = await db.execute(stmt_diag)
        diags = res_diag.all()
        
        diag_map = {d[0].concept_id: (d[0], d[1]) for d in diags}
        
        results = []
        for c_id in req_concept_ids:
            if c_id in diag_map:
                profile, name = diag_map[c_id]
                results.append({
                    "concept_id": c_id,
                    "concept_name": name,
                    "adjusted_mastery": profile.adjusted_mastery,
                    "confidence_score": profile.confidence_score,
                    "reliability_tier": profile.reliability_tier,
                    "opportunity_count": profile.opportunity_count,
                    "likely_missing": profile.adjusted_mastery < 0.5
                })
            else:
                # Concept exists but no profile yet (student hasn't encountered it)
                stmt_c = select(Concept.name).where(Concept.id == c_id)
                res_c = await db.execute(stmt_c)
                name = res_c.scalar()
                prior_conf = 1.0 - 4.0 * DEFAULT_PRIOR * (1.0 - DEFAULT_PRIOR)
                results.append({
                    "concept_id": c_id,
                    "concept_name": name,
                    "adjusted_mastery": DEFAULT_PRIOR,
                    "confidence_score": prior_conf,
                    "reliability_tier": _reliability_tier(prior_conf),
                    "opportunity_count": 0,
                    "likely_missing": False # At 0.5, it's neutral
                })
        
        # Sort by mastery weakest first
        results.sort(key=lambda x: x['adjusted_mastery'])
        return results

    async def get_student_diagnostic_report(self, student_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Return a report of all incorrectly answered questions with their required skills
        ranked by likelihood of being missing.
        """
        # 1. Find all incorrect responses
        stmt_resp = select(Response.question_id, Question.text).join(Question).where(
            Response.student_id == student_id,
            Response.is_correct == False
        )
        res_resp = await db.execute(stmt_resp)
        incorrect_responses = res_resp.all()
        
        report = []
        for q_id, q_text in incorrect_responses:
            why = await self.get_question_why(student_id, q_id, db)
            if why:
                report.append({
                    "question_id": q_id,
                    "question_text": q_text,
                    "required_skills": why
                })
        
        return report

def get_dina_service() -> DINADiagnosisService:
    return DINADiagnosisService()
