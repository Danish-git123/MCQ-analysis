"""
Pydantic schemas package — domain-organized.

All schemas are re-exported here so that existing imports like
    from app.schemas import UserRead, TestCreate, ...
continue to work without modification.
"""

# User & Auth
from .user import UserBase, UserCreate, UserRead, Token, TokenData

# Concepts
from .concept import ConceptBase, ConceptCreate, ConceptRead

# Questions & Options
from .question import (
    OptionBase, OptionCreate, OptionRead,
    QuestionBase, QuestionCreate, QuestionRead, QuestionStudentRead,
)

# Tests & Assignments
from .test import TestBase, TestCreate, TestRead, TestAssignmentCreate, TestAssignmentRead

# Responses
from .response import ResponseCreate, ResponseRead

# Layer 3 — Cognitive Diagnosis
from .diagnosis import CognitiveDiagnosisProfileRead

# Bulk Import
from .bulk_import import (
    BulkQuestionImportRequest, BulkQuestionImportError,
    BulkQuestionImportQuestion, BulkQuestionImportResponse,
)
