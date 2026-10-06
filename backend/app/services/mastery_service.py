from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models import Response, Question, StudentConceptMastery, Concept

logger = logging.getLogger(__name__)

# Standard BKT Default Parameters for 4-option MCQs
DEFAULT_P_INIT = 0.20  # P(L0) - prior knowledge
DEFAULT_P_TRANS = 0.15 # P(T)  - probability of learning transition per item
DEFAULT_P_SLIP = 0.10  # P(S)  - slip probability (knows concept but makes mistake)
DEFAULT_P_GUESS = 0.25 # P(G)  - guess probability (1 out of 4 options = 25%)

class BaseMasteryEstimator(ABC):
    """
    Abstract Base Class defining the contract for Sequential Mastery Estimation.
    Allows seamlessly swapping pyBKT for AKT, DKT, or NeuralCD without breaking downstream APIs.
    """

    @abstractmethod
    async def update_mastery(self, student_id: int, concept_id: int, db: AsyncSession) -> float:
        """Calculate and update the sequential mastery estimate for a student on a concept."""
        pass

    @abstractmethod
    async def get_mastery(self, student_id: int, concept_id: int, db: AsyncSession) -> float:
        """Return the current p(mastery) probability between 0.0 and 1.0."""
        pass

    @abstractmethod
    async def get_all_student_masteries(self, student_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """Return all concept mastery scores for a specific student."""
        pass


class PYBKTMasteryEstimator(BaseMasteryEstimator):
    """
    Bayesian Knowledge Tracing (pyBKT) implementation for sequential mastery estimation.
    Uses BKT forward algorithm to update p(L_t) after each response sequence.
    """

    def __init__(self, p_init=DEFAULT_P_INIT, p_trans=DEFAULT_P_TRANS, p_slip=DEFAULT_P_SLIP, p_guess=DEFAULT_P_GUESS):
        self.p_init = p_init
        self.p_trans = p_trans
        self.p_slip = p_slip
        self.p_guess = p_guess

    def compute_bkt_sequence(self, responses_is_correct: List[bool]) -> float:
        """
        Calculates p(mastery) for a sequence of true/false responses in chronological order.
        """
        p_curr = self.p_init
        for is_correct in responses_is_correct:
            if is_correct:
                # Observation = Correct
                p_obs = (p_curr * (1 - self.p_slip)) / (p_curr * (1 - self.p_slip) + (1 - p_curr) * self.p_guess)
            else:
                # Observation = Incorrect
                p_obs = (p_curr * self.p_slip) / (p_curr * self.p_slip + (1 - p_curr) * (1 - self.p_guess))
            
            # Transition step: P(L_t+1) = P(L_t|obs) + (1 - P(L_t|obs)) * P(T)
            p_curr = p_obs + (1 - p_obs) * self.p_trans

        return round(float(p_curr), 4)

    async def update_mastery(self, student_id: int, concept_id: int, db: AsyncSession) -> float:
        """
        Fetch all historical responses for this student and concept in chronological order,
        run pyBKT algorithm, and persist updated mastery to student_concept_mastery table.
        """
        stmt = (
            select(Response.is_correct)
            .join(Question, Response.question_id == Question.id)
            .where(Response.student_id == student_id, Question.concept_id == concept_id)
            .order_by(Response.answered_at.asc())
        )
        res = await db.execute(stmt)
        responses = res.scalars().all()

        if not responses:
            new_p = self.p_init
            opp_count = 0
        else:
            new_p = self.compute_bkt_sequence(responses)
            opp_count = len(responses)

        # Check existing record in DB
        mastery_stmt = select(StudentConceptMastery).where(
            StudentConceptMastery.student_id == student_id,
            StudentConceptMastery.concept_id == concept_id
        )
        mastery_res = await db.execute(mastery_stmt)
        record = mastery_res.scalars().first()

        if record:
            record.mastery_p = new_p
            record.opportunity_count = opp_count
        else:
            record = StudentConceptMastery(
                student_id=student_id,
                concept_id=concept_id,
                mastery_p=new_p,
                opportunity_count=opp_count
            )
            db.add(record)

        await db.commit()
        return new_p

    async def get_mastery(self, student_id: int, concept_id: int, db: AsyncSession) -> float:
        """
        Retrieve stored mastery probability from database or compute if missing.
        """
        stmt = select(StudentConceptMastery).where(
            StudentConceptMastery.student_id == student_id,
            StudentConceptMastery.concept_id == concept_id
        )
        res = await db.execute(stmt)
        record = res.scalars().first()

        if record:
            return record.mastery_p

        # If no record exists, trigger computation
        return await self.update_mastery(student_id, concept_id, db)

    async def get_all_student_masteries(self, student_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Retrieve list of all concepts and the student's mastery score for each.
        """
        c_stmt = select(Concept)
        c_res = await db.execute(c_stmt)
        concepts = c_res.scalars().all()

        m_stmt = select(StudentConceptMastery).where(StudentConceptMastery.student_id == student_id)
        m_res = await db.execute(m_stmt)
        masteries = {m.concept_id: m for m in m_res.scalars().all()}

        result = []
        for c in concepts:
            m_record = masteries.get(c.id)
            mastery_p = m_record.mastery_p if m_record else self.p_init
            opp_count = m_record.opportunity_count if m_record else 0

            result.append({
                "concept_id": c.id,
                "concept_name": c.name,
                "mastery_p": mastery_p,
                "opportunity_count": opp_count,
                "last_updated": m_record.last_updated if m_record else None
            })

        return result


# Global Factory for swapping estimators cleanly
def get_mastery_estimator() -> BaseMasteryEstimator:
    """
    Returns the active Mastery Estimator instance.
    Can be configured via env or settings to switch between BKT, AKT, DKT, etc.
    """
    return PYBKTMasteryEstimator()
