from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from ..database import get_db
from ..models import User, Concept, Test, Question, Option, TestAssignment, Response, QuestionSkill
from ..schemas import ConceptCreate, ConceptRead, TestCreate, TestRead, TestAssignmentCreate, BulkQuestionImportRequest, BulkQuestionImportResponse
from ..auth import get_current_teacher
from ..services.llm_service import get_llm_service

router = APIRouter(prefix="/teacher", tags=["teacher"])

@router.get("/concepts", response_model=List[ConceptRead])
async def list_concepts(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    result = await db.execute(select(Concept))
    return result.scalars().all()

@router.post("/concepts", response_model=ConceptRead)
async def create_concept(concept: ConceptCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    db_concept = Concept(name=concept.name, created_by_teacher_id=current_user.id)
    db.add(db_concept)
    await db.commit()
    await db.refresh(db_concept)
    return db_concept

@router.post("/tests", response_model=TestRead)
async def create_test(
    test: TestCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_teacher)
):
    db_test = Test(title=test.title, created_by_teacher_id=current_user.id)
    db.add(db_test)
    await db.flush() # flush to get test id

    new_question_ids = []
    for q_idx, q_data in enumerate(test.questions):
        db_q = Question(
            test_id=db_test.id,
            concept_id=q_data.concept_id,
            text=q_data.text
        )
        db.add(db_q)
        await db.flush()
        new_question_ids.append(db_q.id)

        # Insert primary skill into question_skills
        if db_q.concept_id:
            qs = QuestionSkill(
                question_id=db_q.id,
                concept_id=db_q.concept_id,
                is_primary=True,
                source='teacher'
            )
            db.add(qs)

        correct_opt_id = None
        for o_idx, o_data in enumerate(q_data.options):
            db_o = Option(
                question_id=db_q.id,
                text=o_data.text
            )
            db.add(db_o)
            await db.flush()
            if o_data.is_correct:
                correct_opt_id = db_o.id
        
        if correct_opt_id:
            db_q.correct_option_id = correct_opt_id

    await db.commit()
    
    # Trigger LLM inference for new questions in background
    if new_question_ids:
        async def run_inference(q_ids: List[int]):
            from app.database import async_session
            from app.services.llm_service import get_llm_service
            async with async_session() as session:
                llm = get_llm_service()
                await llm.infer_question_skills(q_ids, session)

        background_tasks.add_task(run_inference, new_question_ids)

    # Reload test with relationships
    stmt = select(Test).options(
        selectinload(Test.questions).selectinload(Question.options)
    ).where(Test.id == db_test.id)
    result = await db.execute(stmt)
    return result.scalars().first()

@router.post("/questions/infer-skills")
async def infer_all_question_skills(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    """
    Manually trigger LLM inference for all questions that only have a primary skill.
    """
    # Find all questions
    stmt = select(Question.id)
    res = await db.execute(stmt)
    q_ids = [r[0] for r in res.all()]

    if q_ids:
        async def run_inference(ids: List[int]):
            from app.database import async_session
            from app.services.llm_service import get_llm_service
            async with async_session() as session:
                llm = get_llm_service()
                await llm.infer_question_skills(ids, session)

        background_tasks.add_task(run_inference, q_ids)

    return {"message": f"Skill inference triggered for {len(q_ids)} questions in the background."}

@router.get("/tests", response_model=List[TestRead])
async def list_tests(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    stmt = select(Test).options(
        selectinload(Test.questions).selectinload(Question.options)
    ).where(Test.created_by_teacher_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/assign-test")
async def assign_test(assignment: TestAssignmentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    student_ids_to_assign = set(assignment.student_ids or [])

    if assignment.student_emails:
        for email in assignment.student_emails:
            clean_email = email.strip().lower()
            if not clean_email:
                continue
            stmt = select(User).where(User.email == clean_email)
            res = await db.execute(stmt)
            user = res.scalars().first()
            if user:
                student_ids_to_assign.add(user.id)
            else:
                raise HTTPException(status_code=404, detail=f"No user found with email '{clean_email}'")

    if not student_ids_to_assign:
        raise HTTPException(status_code=400, detail="No valid students selected or provided.")

    assigned_count = 0
    for s_id in student_ids_to_assign:
        stmt = select(TestAssignment).where(
            TestAssignment.test_id == assignment.test_id,
            TestAssignment.student_id == s_id
        )
        res = await db.execute(stmt)
        if not res.scalars().first():
            db_assignment = TestAssignment(test_id=assignment.test_id, student_id=s_id)
            db.add(db_assignment)
            assigned_count += 1
            
    await db.commit()
    return {"message": "Test assigned successfully", "assigned_count": assigned_count}

@router.get("/tests/{test_id}/results")
async def test_results(test_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    # simple aggregation for phase 1
    stmt = select(Response).join(Question).where(Question.test_id == test_id)
    result = await db.execute(stmt)
    responses = result.scalars().all()
    
    total = len(responses)
    correct = sum(1 for r in responses if r.is_correct)
    
    q_stats = {}
    for r in responses:
        if r.question_id not in q_stats:
            q_stats[r.question_id] = {"total": 0, "correct": 0}
        q_stats[r.question_id]["total"] += 1
        if r.is_correct:
            q_stats[r.question_id]["correct"] += 1
            
    return {
        "test_id": test_id,
        "total_responses": total,
        "total_correct": correct,
        "question_stats": q_stats
    }

@router.get("/students")
async def list_students(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    result = await db.execute(select(User).where(User.role == "student"))
    students = result.scalars().all()
    return [{"id": s.id, "name": s.name, "email": s.email} for s in students]

import re

@router.post("/tests/parse-bulk-questions", response_model=BulkQuestionImportResponse)
async def parse_bulk_questions(
    request: BulkQuestionImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    lines = request.raw_text.splitlines()
    
    # Pre-fetch all concepts to match against
    result = await db.execute(select(Concept))
    all_db_concepts = result.scalars().all()
    concept_map = {c.name.strip().lower(): c for c in all_db_concepts}
    
    questions = []
    errors = []
    
    # State machine
    current_q_num = None
    current_concept_id = None
    current_concept_name = None
    
    current_q_text_lines = []
    current_options = []
    current_answer = None
    
    state = "SEARCHING" # SEARCHING, QUESTION_TEXT, OPTIONS
    
    def process_current_block():
        if not current_q_num:
            return
            
        q_text = " ".join(current_q_text_lines).strip()
        
        if not q_text:
            errors.append({"question_number": current_q_num, "message": "Question text is empty."})
            return
            
        if len(current_options) < 2:
            errors.append({"question_number": current_q_num, "message": "Question must have at least 2 options."})
            return
            
        if not current_answer:
            errors.append({"question_number": current_q_num, "message": "No 'Answer:' line found."})
            return
            
        # Find which option is correct based on the letter
        correct_idx = ord(current_answer.upper()) - ord('A')
        if correct_idx < 0 or correct_idx >= len(current_options):
            errors.append({"question_number": current_q_num, "message": f"Answer '{current_answer}' does not match any provided option."})
            return
            
        parsed_options = []
        for i, opt in enumerate(current_options):
            parsed_options.append({
                "text": opt,
                "is_correct": i == correct_idx
            })
            
        questions.append({
            "text": q_text,
            "concept_id": current_concept_id,
            "concept_name": current_concept_name,
            "options": parsed_options
        })

    q_pattern = re.compile(r'^Q(\d+)(?:\s*(?:[-—])\s*Concept:\s*`?([^`]+)`?)?', re.IGNORECASE)
    opt_pattern = re.compile(r'^([A-Z])\)\s*(.*)')
    ans_pattern = re.compile(r'^Answer:\s*([A-Z])', re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        q_match = q_pattern.match(stripped)
        if q_match:
            process_current_block()
            
            # Reset state for new question
            current_q_num = f"Q{q_match.group(1)}"
            raw_concept = q_match.group(2)
            
            current_concept_id = None
            current_concept_name = None
            
            if raw_concept:
                rc_clean = raw_concept.strip()
                rc_lower = rc_clean.lower()
                if rc_lower in concept_map:
                    current_concept_id = concept_map[rc_lower].id
                    current_concept_name = concept_map[rc_lower].name
                else:
                    current_concept_name = rc_clean
                    
            current_q_text_lines = []
            current_options = []
            current_answer = None
            state = "QUESTION_TEXT"
            continue
            
        if state == "SEARCHING":
            continue
            
        if state == "QUESTION_TEXT":
            opt_match = opt_pattern.match(stripped)
            ans_match = ans_pattern.match(stripped)
            if opt_match:
                state = "OPTIONS"
                current_options.append(opt_match.group(2).strip())
            elif ans_match:
                current_answer = ans_match.group(1).upper()
                state = "OPTIONS" # Technically end of options
            else:
                current_q_text_lines.append(stripped)
            continue
            
        if state == "OPTIONS":
            opt_match = opt_pattern.match(stripped)
            ans_match = ans_pattern.match(stripped)
            if opt_match:
                current_options.append(opt_match.group(2).strip())
            elif ans_match:
                current_answer = ans_match.group(1).upper()
            else:
                pass # Ignore or append? Let's ignore extra stuff in options for now
                
    # Process the last block
    process_current_block()
    
    if not questions and not errors:
        errors.append({"question_number": "All", "message": "Could not parse any questions. Make sure format matches 'Q1 — Concept: ...'"})

    return {"questions": questions, "errors": errors}
