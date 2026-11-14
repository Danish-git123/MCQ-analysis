from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.dina_service import get_dina_service
from app.services.prediction_service import get_prediction_service
from app.services.cognitive_analytics_service import get_cognitive_analytics_service

router = APIRouter(prefix="/diagnosis", tags=["Cognitive Diagnosis & Advanced Analytics"])


@router.get("/student/{student_id}", response_model=List[Dict[str, Any]])
async def get_student_cognitive_profile(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the full DINA cognitive diagnosis profile for a student across all concepts.
    Returns adjusted_mastery, confidence_score, and reliability_tier per concept.
    """
    service = get_dina_service()
    return await service.get_all_student_diagnoses(student_id, db)


@router.get("/student/{student_id}/concept/{concept_id}")
async def get_single_concept_diagnosis(
    student_id: int,
    concept_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get DINA cognitive diagnosis for a specific (student, concept) pair.
    """
    service = get_dina_service()
    result = await service.get_diagnosis(student_id, concept_id, db)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No diagnosis profile found for student {student_id}, concept {concept_id}",
        )
    return result


@router.get("/student/{student_id}/question/{question_id}/why")
async def get_question_why_explanation(
    student_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    For a specific question, explain why the student might have missed it
    based on their current DINA mastery profile.
    """
    service = get_dina_service()
    return await service.get_question_why(student_id, question_id, db)


@router.get("/student/{student_id}/report")
async def get_student_report(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a full diagnostic report for a student, showing incorrectly answered
    questions and their required skills ranked by likelihood of being missing.
    """
    service = get_dina_service()
    return await service.get_student_diagnostic_report(student_id, db)


# ══════════════════════════════════════════════════════════════════════════════
# NEW UNIQUE ANALYTICS ENDPOINTS (Branch: ml-advanced-analytics)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/student/{student_id}/advanced-analytics")
async def get_student_advanced_analytics(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Synthesizes Tri-Model results (DINA + BKT + Logistic Regression),
    4-Quadrant Cognitive Effort profiling, and Prerequisite Debt into an executive dossier.
    """
    analytics = get_cognitive_analytics_service()
    return await analytics.get_comprehensive_advanced_analytics(student_id, db)


@router.get("/student/{student_id}/effort-quadrants")
async def get_student_effort_quadrants(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns Response-Time Effort (RTE) distribution across the 4 cognitive quadrants:
    Fluency, Deliberate Mastery, Struggle, and Rapid Guessing.
    """
    analytics = get_cognitive_analytics_service()
    return await analytics.compute_effort_quadrant_analysis(student_id, db)


@router.get("/student/{student_id}/learning-roadmap")
async def get_student_learning_roadmap(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes Prerequisite Debt score and outputs a topologically ordered
    step-by-step remediation path for weak concepts.
    """
    analytics = get_cognitive_analytics_service()
    return await analytics.compute_prerequisite_debt_and_roadmap(student_id, db)


@router.get("/student/{student_id}/question/{question_id}/predict")
async def predict_question_performance(
    student_id: int,
    question_id: int,
    response_time_ms: int = Query(default=15000, description="Hypothetical or actual latency"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Uses the Logistic Regression model (Equation 3) to predict P(Correct | features)
    and analyze whether an answer is expected or a careless slip anomaly.
    """
    predictor = get_prediction_service()
    features, breakdown = await predictor.extract_features(student_id, question_id, response_time_ms, db)
    p_pred = predictor.predict_probability(features)
    return {
        "student_id": student_id,
        "question_id": question_id,
        "predicted_probability": p_pred,
        "feature_breakdown": breakdown
    }
