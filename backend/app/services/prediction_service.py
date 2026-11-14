"""
Layer 4 — Logistic Regression Performance Prediction & Careless Slip Detection Service.
Implements Equation (3) from the Project Phase-I Report (Group G23):
    P(X = 1 | x) = 1 / (1 + exp[-(β0 + β1*x1 + β2*x2 + ... + βm*xm)])

Features used:
    x1: Student's cumulative historical accuracy
    x2: DINA/BKT concept mastery for the question's required skills
    x3: Question empirical difficulty (historical pass rate across students)
    x4: Question skill complexity (number of required skills in Q-matrix)
    x5: Normalized response latency ratio (actual time / expected reading time)

Unique Capabilities:
    1. Predicts probability of correct answer before/during test.
    2. Identifies Careless Slips (High predicted P > 0.80, but answered incorrectly).
    3. Identifies Rapid Lucky Guesses (Low predicted P < 0.25, but answered correctly in rapid time).
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models import Response, Question, QuestionSkill, CognitiveDiagnosisProfile, Option

logger = logging.getLogger(__name__)

# Default weights if cold-start (prior to empirical logistic regression calibration)
# Derived from psychometric calibration: high weight on skill mastery (β2) and question pass rate (β3)
DEFAULT_INTERCEPT = -0.40  # β0
DEFAULT_WEIGHTS = np.array([
    0.85,   # β1: Student historical accuracy
    1.80,   # β2: Concept mastery level
    1.25,   # β3: Question pass rate / empirical ease
   -0.45,   # β4: Question skill complexity (more skills = harder)
    0.35    # β5: Normalized latency (adequate thinking time = higher chance)
])

# Slip / Guess Anomaly Thresholds
SLIP_PROBABILITY_THRESHOLD = 0.78       # Predicted P >= 78% but got wrong -> Careless Slip
RAPID_GUESS_TIME_MS = 4000              # Less than 4 seconds on complex item -> Rapid Guess
LUCKY_GUESS_PROBABILITY_THRESHOLD = 0.28 # Predicted P <= 28% but got right quickly -> Lucky Guess


class LogisticRegressionPredictor:
    """
    Vectorized Logistic Regression model for answer prediction and psychometric anomaly detection.
    """

    def __init__(self, intercept: float = DEFAULT_INTERCEPT, weights: np.ndarray = None):
        self.intercept = intercept
        self.weights = weights if weights is not None else DEFAULT_WEIGHTS.copy()

    def sigmoid(self, z: float) -> float:
        """Numerically stable sigmoid function."""
        if z >= 0:
            ez = math.exp(-z)
            return 1.0 / (1.0 + ez)
        else:
            ez = math.exp(z)
            return ez / (1.0 + ez)

    def predict_probability(self, feature_vector: np.ndarray) -> float:
        """
        Calculates P(X = 1 | x) = 1 / (1 + exp(-(β0 + β^T * x)))
        """
        z = float(self.intercept + np.dot(self.weights, feature_vector))
        return round(self.sigmoid(z), 4)

    async def extract_features(
        self,
        student_id: int,
        question_id: int,
        response_time_ms: int,
        db: AsyncSession
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Extracts the 5 feature dimensions for a given (student, question, latency) tuple.
        """
        # Feature 1: Student Cumulative Accuracy
        stmt_acc = select(
            func.count(Response.id),
            func.sum(func.cast(Response.is_correct, func.Integer if db.bind.dialect.name != 'postgresql' else Response.is_correct.type))
        ).where(Response.student_id == student_id)
        
        # Safe query for boolean sum across postgres/sqlite
        stmt_responses = select(Response.is_correct).where(Response.student_id == student_id)
        res_r = await db.execute(stmt_responses)
        hist_answers = res_r.scalars().all()
        
        if hist_answers:
            x1_accuracy = sum(1 for a in hist_answers if a) / len(hist_answers)
        else:
            x1_accuracy = 0.50  # Neutral prior if first attempt

        # Feature 2 & 4: Required Skills & Concept Mastery Level
        stmt_skills = select(QuestionSkill.concept_id).where(QuestionSkill.question_id == question_id)
        res_skills = await db.execute(stmt_skills)
        skill_ids = res_skills.scalars().all()
        x4_complexity = float(len(skill_ids)) if skill_ids else 1.0

        if skill_ids:
            stmt_mastery = select(CognitiveDiagnosisProfile.adjusted_mastery).where(
                CognitiveDiagnosisProfile.student_id == student_id,
                CognitiveDiagnosisProfile.concept_id.in_(skill_ids)
            )
            res_mastery = await db.execute(stmt_mastery)
            masteries = res_mastery.scalars().all()
            if masteries:
                x2_mastery = float(np.mean(masteries))
            else:
                x2_mastery = 0.50  # Prior
        else:
            x2_mastery = 0.50

        # Feature 3: Question Empirical Pass Rate (Difficulty index p_val)
        stmt_q_perf = select(Response.is_correct).where(Response.question_id == question_id)
        res_q = await db.execute(stmt_q_perf)
        q_history = res_q.scalars().all()
        if q_history and len(q_history) >= 2:
            x3_difficulty = sum(1 for a in q_history if a) / len(q_history)
        else:
            x3_difficulty = 0.60  # Average default pass rate

        # Feature 5: Normalized Latency Ratio
        # Estimate expected reading & solving time: ~12s base + 8s per required skill
        expected_time_ms = max(8000, int(10000 + (x4_complexity * 8000)))
        latency_ratio = min(3.0, response_time_ms / expected_time_ms)
        x5_latency = float(latency_ratio)

        feature_vector = np.array([x1_accuracy, x2_mastery, x3_difficulty, x4_complexity, x5_latency])
        
        feature_breakdown = {
            "student_accuracy": round(x1_accuracy, 3),
            "concept_mastery": round(x2_mastery, 3),
            "question_pass_rate": round(x3_difficulty, 3),
            "skill_complexity": int(x4_complexity),
            "expected_time_ms": expected_time_ms,
            "actual_time_ms": response_time_ms,
            "latency_ratio": round(latency_ratio, 2)
        }

        return feature_vector, feature_breakdown

    async def analyze_response_anomaly(
        self,
        student_id: int,
        question_id: int,
        is_correct: bool,
        response_time_ms: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Runs Logistic Regression prediction and detects whether an error was a Careless Slip
        or a correct answer was a Rapid Lucky Guess.
        """
        features, breakdown = await self.extract_features(student_id, question_id, response_time_ms, db)
        p_predicted = self.predict_probability(features)

        # Standardized residual: r = (Actual - Predicted) / sqrt(P * (1 - P))
        denom = math.sqrt(max(0.01, p_predicted * (1.0 - p_predicted)))
        actual_val = 1.0 if is_correct else 0.0
        residual = (actual_val - p_predicted) / denom

        anomaly_type = "STANDARD"
        pedagogical_message = "Performance matches expected latent ability."

        if not is_correct and p_predicted >= SLIP_PROBABILITY_THRESHOLD:
            anomaly_type = "CARELESS_SLIP"
            pedagogical_message = (
                f"Careless Slip Detected: Student had a {int(p_predicted*100)}% statistical probability "
                "of answering correctly given high skill mastery. This indicates an accidental typo, "
                "misread option, or arithmetic error rather than a conceptual deficiency."
            )
        elif is_correct and p_predicted <= LUCKY_GUESS_PROBABILITY_THRESHOLD and response_time_ms <= RAPID_GUESS_TIME_MS:
            anomaly_type = "RAPID_LUCKY_GUESS"
            pedagogical_message = (
                f"Rapid Guess Alert: Question was answered correctly in only {response_time_ms/1000:.1f}s "
                f"despite a low predicted likelihood ({int(p_predicted*100)}%). Verification recommended."
            )
        elif not is_correct and response_time_ms <= RAPID_GUESS_TIME_MS:
            anomaly_type = "RAPID_INCORRECT_GUESS"
            pedagogical_message = "Question missed with minimal reading effort (< 4s). Indicates disengagement or blind rushing."

        return {
            "student_id": student_id,
            "question_id": question_id,
            "is_correct": is_correct,
            "predicted_probability": p_predicted,
            "standardized_residual": round(residual, 3),
            "anomaly_type": anomaly_type,
            "pedagogical_message": pedagogical_message,
            "feature_breakdown": breakdown
        }


# Singleton factory
_predictor_instance = None

def get_prediction_service() -> LogisticRegressionPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = LogisticRegressionPredictor()
    return _predictor_instance

