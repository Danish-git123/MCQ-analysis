from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Any, List

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Concept
from app.services.mastery_service import get_mastery_estimator

router = APIRouter(prefix="/mastery", tags=["Sequential Mastery Estimation"])

@router.get("/student/{student_id}", response_model=List[Dict[str, Any]])
async def get_student_mastery_profile(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get sequential pyBKT mastery profile for a student across all concepts.
    """
    estimator = get_mastery_estimator()
    return await estimator.get_all_student_masteries(student_id, db)

@router.get("/student/{student_id}/concept/{concept_id}")
async def get_single_concept_mastery(
    student_id: int,
    concept_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get sequential pyBKT mastery probability p(mastery) for a specific student and concept.
    """
    estimator = get_mastery_estimator()
    mastery_p = await estimator.get_mastery(student_id, concept_id, db)
    return {
        "student_id": student_id,
        "concept_id": concept_id,
        "mastery_p": mastery_p
    }

@router.post("/recompute/{student_id}")
async def recompute_student_mastery(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger full recomputation of pyBKT mastery probabilities across all concepts for a student.
    """
    c_stmt = select(Concept)
    c_res = await db.execute(c_stmt)
    concepts = c_res.scalars().all()

    estimator = get_mastery_estimator()
    results = {}
    for c in concepts:
        p = await estimator.update_mastery(student_id, c.id, db)
        results[c.name] = p

    return {
        "status": "success",
        "student_id": student_id,
        "updated_masteries": results
    }
