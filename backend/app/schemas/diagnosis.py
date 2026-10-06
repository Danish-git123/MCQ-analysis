from pydantic import BaseModel
from typing import Optional
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
