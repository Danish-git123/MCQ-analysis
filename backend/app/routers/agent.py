from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_teacher, get_current_user
from app.database import get_db
from app.models import User
from app.schemas.agent import (
    ApproveClassInterventionRequest,
    ApproveQuizLaunchResponse,
    ApproveStudentQuizRequest,
    ApproveTeacherCurriculumRequest,
    ClassInterventionDraftRequest,
    ClassInterventionDraftResponse,
    StudentTutorDraftRequest,
    StudentTutorDraftResponse,
    TeacherCurriculumDraftResponse,
    TeacherCurriculumRequest,
)
from app.services.agent_service import get_agent_orchestrator
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/agent", tags=["Agentic AI Brain"])


@router.get("/status")
async def get_agent_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    llm = get_llm_service()
    return {
        "status": "active",
        "architecture": "Neuro-Symbolic ReAct Tool-Calling Orchestrator",
        "available_providers": llm.available_providers(),
        "human_in_the_loop": True,
    }


@router.post("/student/{student_id}/diagnose-draft", response_model=StudentTutorDraftResponse)
async def generate_student_tutor_draft(
    student_id: int,
    req: StudentTutorDraftRequest = StudentTutorDraftRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Cannot run tutor agent for another student.")

    agent = get_agent_orchestrator()
    return await agent.run_student_tutor_agent(
        student_id=student_id,
        db=db,
        target_concept_id=req.target_concept_id,
        max_questions=req.max_questions,
    )


@router.post("/student/{student_id}/approve-quiz", response_model=ApproveQuizLaunchResponse)
async def approve_student_tutor_quiz(
    student_id: int,
    req: ApproveStudentQuizRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Cannot approve quiz for another student.")

    agent = get_agent_orchestrator()
    try:
        return await agent.approve_and_launch_student_quiz(
            student_id=student_id, req=req, db=db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/teacher/curriculum-draft", response_model=TeacherCurriculumDraftResponse)
async def generate_teacher_curriculum_draft(
    req: TeacherCurriculumRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    agent = get_agent_orchestrator()
    return await agent.run_teacher_curriculum_agent(
        topic=req.topic,
        num_questions=req.num_questions,
        difficulty_level=req.difficulty_level,
        db=db,
        syllabus_context=req.syllabus_context,
    )


@router.post("/teacher/curriculum-approve")
async def approve_teacher_curriculum_draft(
    req: ApproveTeacherCurriculumRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
) -> Dict[str, Any]:
    agent = get_agent_orchestrator()
    return await agent.approve_teacher_curriculum(
        teacher_id=current_user.id, req=req, db=db
    )


@router.post(
    "/teacher/tests/{test_id}/intervention-draft",
    response_model=ClassInterventionDraftResponse,
)
async def generate_class_intervention_draft(
    test_id: int,
    req: ClassInterventionDraftRequest = ClassInterventionDraftRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    agent = get_agent_orchestrator()
    try:
        return await agent.run_class_intervention_agent(
            test_id=test_id, db=db, max_questions=req.max_questions
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/teacher/tests/{test_id}/intervention-approve",
    response_model=ApproveQuizLaunchResponse,
)
async def approve_class_intervention_draft(
    test_id: int,
    req: ApproveClassInterventionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    agent = get_agent_orchestrator()
    try:
        return await agent.approve_class_intervention(
            teacher_id=current_user.id, req=req, db=db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

