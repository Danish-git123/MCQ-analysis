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


@router.post("/adaptive-quiz")
async def generate_adaptive_remedial_quiz(
    target_concept_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    """
    Generates an adaptive practice quiz specifically targeting the student's weak
    and moderate concepts, prioritizing Root Blockers from the Prerequisite DAG.
    """
    from app.models import CognitiveDiagnosisProfile, Concept, QuestionSkill, Question, Option, Test, TestAssignment
    import random

    # 1. Identify target concepts
    target_concept_ids = []
    if target_concept_id:
        target_concept_ids = [target_concept_id]
    else:
        # Pull student diagnosis sorted by lowest mastery first
        stmt = (
            select(CognitiveDiagnosisProfile)
            .where(CognitiveDiagnosisProfile.student_id == current_user.id)
            .order_by(CognitiveDiagnosisProfile.adjusted_mastery.asc())
        )
        res = await db.execute(stmt)
        profiles = res.scalars().all()

        weak = [p.concept_id for p in profiles if p.adjusted_mastery < 0.60]
        if weak:
            target_concept_ids = weak[:3] # Top 3 weakest
        elif profiles:
            target_concept_ids = [p.concept_id for p in profiles[:2]]
        else:
            # Fallback to any active concepts in the database
            c_res = await db.execute(select(Concept).limit(3))
            target_concept_ids = [c.id for c in c_res.scalars().all()]

    if not target_concept_ids:
        raise HTTPException(status_code=400, detail="No concepts available to generate an adaptive quiz.")

    # 2. Get concept names
    stmt_c = select(Concept).where(Concept.id.in_(target_concept_ids))
    res_c = await db.execute(stmt_c)
    concepts = res_c.scalars().all()
    concept_names = [c.name for c in concepts]

    # 3. Find questions from question bank matching these concepts
    stmt_q = (
        select(Question)
        .options(selectinload(Question.options))
        .join(QuestionSkill, Question.id == QuestionSkill.question_id)
        .where(QuestionSkill.concept_id.in_(target_concept_ids))
        .distinct()
    )
    res_q = await db.execute(stmt_q)
    candidate_questions = res_q.scalars().all()

    # Fallback to questions with concept_id matching if question_skills has few
    if len(candidate_questions) < 3:
        stmt_fallback = (
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.concept_id.in_(target_concept_ids))
        )
        res_fb = await db.execute(stmt_fallback)
        candidate_questions = list({q.id: q for q in (candidate_questions + list(res_fb.scalars().all()))}.values())

    if not candidate_questions:
        raise HTTPException(status_code=404, detail="No questions found for the targeted weak concepts.")

    # Select up to 5 questions
    selected_questions = candidate_questions[:5]

    # 4. Create new Remedial Test
    test_title = f"Adaptive Remedial Quiz: {concept_names[0]}"
    if len(concept_names) > 1:
        test_title += f" & {concept_names[1]}"

    # Use first teacher as creator
    t_res = await db.execute(select(User).where(User.role == "teacher"))
    teacher = t_res.scalars().first()
    creator_id = teacher.id if teacher else current_user.id

    new_test = Test(title=test_title, created_by_teacher_id=creator_id)
    db.add(new_test)
    await db.flush()

    # Clone questions into this new remedial test
    for orig_q in selected_questions:
        new_q = Question(
            test_id=new_test.id,
            concept_id=orig_q.concept_id,
            text=orig_q.text
        )
        db.add(new_q)
        await db.flush()

        correct_opt_id = None
        for orig_opt in orig_q.options:
            is_correct = (orig_q.correct_option_id == orig_opt.id)
            new_opt = Option(
                question_id=new_q.id,
                text=orig_opt.text
            )
            db.add(new_opt)
            await db.flush()
            if is_correct:
                correct_opt_id = new_opt.id

        new_q.correct_option_id = correct_opt_id

        # Copy question skills
        qs_res = await db.execute(select(QuestionSkill).where(QuestionSkill.question_id == orig_q.id))
        for orig_qs in qs_res.scalars().all():
            new_qs = QuestionSkill(
                question_id=new_q.id,
                concept_id=orig_qs.concept_id,
                is_primary=orig_qs.is_primary,
                source="adaptive_engine"
            )
            db.add(new_qs)

    # 5. Assign to the student
    assignment = TestAssignment(
        test_id=new_test.id,
        student_id=current_user.id,
        status="not_started"
    )
    db.add(assignment)
    await db.commit()

    return {
        "status": "success",
        "test_id": new_test.id,
        "title": new_test.title,
        "question_count": len(selected_questions),
        "target_concepts": concept_names
    }
