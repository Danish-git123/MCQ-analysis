from pydantic import BaseModel
from typing import List, Optional

from .question import OptionCreate


class BulkQuestionImportRequest(BaseModel):
    raw_text: str


class BulkQuestionImportError(BaseModel):
    question_number: str
    message: str


class BulkQuestionImportQuestion(BaseModel):
    text: str
    concept_id: Optional[int] = None
    concept_name: Optional[str] = None
    options: List[OptionCreate]


class BulkQuestionImportResponse(BaseModel):
    questions: List[BulkQuestionImportQuestion]
    errors: List[BulkQuestionImportError]
