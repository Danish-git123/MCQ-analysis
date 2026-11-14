from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReasoningStep(BaseModel):
    step: int
    thought: str
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    observation: str
    provider: str = "deterministic_fallback"


class DraftOption(BaseModel):
    text: str
    is_correct: bool


class DraftQuestion(BaseModel):
    source: str = "bank"  # "bank" | "ai_synthesized"
    source_question_id: Optional[int] = None
    concept_id: Optional[int] = None
    concept_name: str
    skill_names: List[str] = Field(default_factory=list)
    text: str
    options: List[DraftOption]
    misconception_note: Optional[str] = None


# ─── Workflow A: Student Diagnostic & Remedial Tutor Agent ──────────────────

class StudentTutorDraftRequest(BaseModel):
    target_concept_id: Optional[int] = None
    max_questions: int = Field(default=5, ge=1, le=10)


class StudentTutorDraftResponse(BaseModel):
    student_id: int
    engine_mode: str
    strategy_code: str
    diagnosis_summary: str
    distractor_insights: List[str] = Field(default_factory=list)
    study_coaching: List[str] = Field(default_factory=list)
    target_concepts: List[Dict[str, Any]] = Field(default_factory=list)
    draft_quiz_title: str
    draft_questions: List[DraftQuestion]
    reasoning_trace: List[ReasoningStep]


class ApproveStudentQuizRequest(BaseModel):
    title: str
    questions: List[DraftQuestion]


class ApproveQuizLaunchResponse(BaseModel):
    status: str
    test_id: int
    title: str
    question_count: int
    assigned_student_ids: List[int]


# ─── Workflow B: Teacher Curriculum & Self-Correcting DAG Agent ─────────────

class ProposedConceptEdge(BaseModel):
    from_concept: str
    to_concept: str
    reasoning: str = ""


class TeacherCurriculumRequest(BaseModel):
    topic: str = Field(..., min_length=2)
    num_questions: int = Field(default=5, ge=1, le=12)
    difficulty_level: str = "Undergraduate"
    syllabus_context: str = ""


class TeacherCurriculumDraftResponse(BaseModel):
    topic: str
    engine_mode: str
    concepts: List[Dict[str, Any]]
    validated_edges: List[ProposedConceptEdge]
    cycles_resolved: List[str] = Field(default_factory=list)
    topological_order: List[str] = Field(default_factory=list)
    draft_questions: List[DraftQuestion]
    reasoning_trace: List[ReasoningStep]


class ApproveTeacherCurriculumRequest(BaseModel):
    topic: str
    concepts: List[Dict[str, Any]]
    validated_edges: List[ProposedConceptEdge]
    draft_questions: List[DraftQuestion] = Field(default_factory=list)
    create_test: bool = False


# ─── Workflow C: Teacher Class Intervention Agent ───────────────────────────

class ClassInterventionDraftRequest(BaseModel):
    max_questions: int = Field(default=5, ge=1, le=10)


class ClassInterventionDraftResponse(BaseModel):
    test_id: int
    test_title: str
    engine_mode: str
    class_metrics: Dict[str, Any]
    teaching_briefing: str
    bottleneck_concepts: List[Dict[str, Any]]
    high_slip_alerts: List[Dict[str, Any]]
    struggling_students: List[Dict[str, Any]]
    draft_quiz_title: str
    draft_questions: List[DraftQuestion]
    reasoning_trace: List[ReasoningStep]


class ApproveClassInterventionRequest(BaseModel):
    title: str
    student_ids: List[int]
    questions: List[DraftQuestion]

