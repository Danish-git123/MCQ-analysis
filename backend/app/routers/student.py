from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from ..database import get_db
from ..models import User, Test, Question, Option, TestAssignment, Response
from ..schemas import TestAssignmentRead, QuestionStudentRead, ResponseCreate
from ..auth import get_current_student

router = APIRouter(prefix="/student", tags=["student"])

@router.get("/assignments", response_model=List[TestAssignmentRead])
async def list_assignments(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_student)):
    stmt = select(TestAssignment).options(
        selectinload(TestAssignment.test).selectinload(Test.questions).selectinload(Question.options)
    ).where(TestAssignment.student_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/tests/{test_id}/questions", response_model=List[QuestionStudentRead])
async def get_test_questions(test_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_student)):
    # Verify assignment
    stmt = select(TestAssignment).where(TestAssignment.test_id == test_id, TestAssignment.student_id == current_user.id)
    result = await db.execute(stmt)
    assignment = result.scalars().first()
    if not assignment:
        raise HTTPException(status_code=403, detail="Not assigned to this test")
        
    stmt = select(Question).options(selectinload(Question.options)).where(Question.test_id == test_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/responses")
async def submit_response(
    resp: ResponseCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    # Check if correct
    stmt = select(Question).where(Question.id == resp.question_id)
    result = await db.execute(stmt)
    question = result.scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    is_correct = (question.correct_option_id == resp.selected_option_id)
    
    db_response = Response(
        student_id=current_user.id,
        question_id=resp.question_id,
        selected_option_id=resp.selected_option_id,
        is_correct=is_correct,
        response_time_ms=resp.response_time_ms
    )
    db.add(db_response)
    await db.commit()

    # Trigger Layer 2 (BKT) → Layer 3 (DINA) pipeline if question has a concept tag
    # Runs in the background so we don't block the student's request
    mastery_p = None
    if question.concept_id:
        async def run_mastery_and_diagnosis(student_id: int, concept_id: int):
            from app.database import async_session
            from app.services.mastery_service import get_mastery_estimator
            from app.services.dina_service import get_dina_service
            from app.models import CognitiveDiagnosisProfile
            from sqlalchemy.future import select

            async with async_session() as session:
                # Layer 2 — BKT sequential mastery update
                estimator = get_mastery_estimator()
                raw_mastery_p = await estimator.update_mastery(student_id, concept_id, session)

                # Layer 3 — DINA cognitive diagnosis (uses same session)
                # This now updates the whole connected block of skills
                dina = get_dina_service()
                await dina.update_diagnosis(student_id, concept_id, session)
                
                # Update the raw_mastery_p for the primary concept in the DINA profile
                stmt = select(CognitiveDiagnosisProfile).where(
                    CognitiveDiagnosisProfile.student_id == student_id,
                    CognitiveDiagnosisProfile.concept_id == concept_id
                )
                res = await session.execute(stmt)
                profile = res.scalars().first()
                if profile:
                    profile.raw_mastery_p = raw_mastery_p
                    await session.commit()

        background_tasks.add_task(run_mastery_and_diagnosis, current_user.id, question.concept_id)

    return {
        "status": "recorded",
        "is_correct": is_correct,
        "concept_id": question.concept_id,
        "updated_mastery_p": mastery_p
    }

@router.post("/tests/{test_id}/complete")
async def complete_test(test_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_student)):
    stmt = select(TestAssignment).where(TestAssignment.test_id == test_id, TestAssignment.student_id == current_user.id)
    result = await db.execute(stmt)
    assignment = result.scalars().first()
    if assignment:
        assignment.status = "completed"
        await db.commit()
    return {"status": "completed"}
