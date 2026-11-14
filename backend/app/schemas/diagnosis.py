from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class CognitiveDiagnosisProfileRead(BaseModel):
    """Layer 3 — DINA cognitive diagnosis output schema."""
    concept_id: int
    concept_name: Optional[str] = None
    raw_mastery_p: Optional[float] = None
    adjusted_mastery: float
    confidence_score: float
    reliability_tier: str
    opportunity_count: int
    last_diagnosed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoadmapStep(BaseModel):
    step: int
    concept_id: int
    concept_name: str
    current_mastery: float
    confidence_score: float
    is_root_blocker: bool
    unlocks_topics: List[str]
    action_priority: str


class PrerequisiteDebtReport(BaseModel):
    debt_score: float
    debt_level: str
    debt_advice: str
    remediation_roadmap: List[RoadmapStep]


class AnomalyAnalysisResponse(BaseModel):
    student_id: int
    question_id: int
    is_correct: bool
    predicted_probability: float
    standardized_residual: float
    anomaly_type: str
    pedagogical_message: str
    feature_breakdown: Dict[str, Any]
