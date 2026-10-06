from pydantic import BaseModel
from datetime import datetime


class ResponseCreate(BaseModel):
    question_id: int
    selected_option_id: int
    response_time_ms: int


class ResponseRead(ResponseCreate):
    id: int
    student_id: int
    is_correct: bool
    answered_at: datetime

    class Config:
        from_attributes = True
