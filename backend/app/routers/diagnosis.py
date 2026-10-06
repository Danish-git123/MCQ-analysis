from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.dina_service import get_dina_service

router = APIRouter(prefix="/diagnosis", tags=["Layer 3 — Cognitive Diagnosis (DINA)"])


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
