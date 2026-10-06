from pydantic import BaseModel
from typing import List, Optional


class OptionBase(BaseModel):
    text: str


class OptionCreate(OptionBase):
    is_correct: bool = False


class OptionRead(OptionBase):
    id: int
    question_id: int

    class Config:
        from_attributes = True


class QuestionBase(BaseModel):
    text: str
    concept_id: Optional[int] = None


class QuestionCreate(QuestionBase):
    options: List[OptionCreate]


class QuestionRead(QuestionBase):
    id: int
    test_id: int
    correct_option_id: Optional[int]
    options: List[OptionRead] = []

    class Config:
        from_attributes = True


class QuestionStudentRead(QuestionBase):
    id: int
    test_id: int
    options: List[OptionRead] = []
    # Not including correct_option_id for students

    class Config:
        from_attributes = True
