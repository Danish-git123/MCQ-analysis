from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from .question import QuestionCreate, QuestionRead


class TestBase(BaseModel):
    title: str


class TestCreate(TestBase):
    questions: List[QuestionCreate]


class TestRead(TestBase):
    id: int
    created_by_teacher_id: int
    created_at: datetime
    questions: List[QuestionRead] = []

    class Config:
        from_attributes = True


class TestAssignmentCreate(BaseModel):
    test_id: int
    student_ids: Optional[List[int]] = []
    student_emails: Optional[List[str]] = []


class TestAssignmentRead(BaseModel):
    id: int
    test_id: int
    student_id: int
    status: str
    test: Optional[TestRead] = None

    class Config:
        from_attributes = True
