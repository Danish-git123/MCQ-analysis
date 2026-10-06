from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Float, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False) # 'teacher' or 'student'

class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    created_by_teacher_id = Column(Integer, ForeignKey("app_users.id"))
    
    questions = relationship("Question", back_populates="concept")

class ConceptEdge(Base):
    __tablename__ = "concept_edges"

    id = Column(Integer, primary_key=True, index=True)
    from_concept_id = Column(Integer, ForeignKey("concepts.id"))
    to_concept_id = Column(Integer, ForeignKey("concepts.id"))
    confidence = Column(Float, default=1.0)
    source = Column(String, default="llm_inferred") # 'llm_inferred', 'statistical', 'manual'

class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_by_teacher_id = Column(Integer, ForeignKey("app_users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("Question", back_populates="test")
    assignments = relationship("TestAssignment", back_populates="test")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"))
    concept_id = Column(Integer, ForeignKey("concepts.id"))
    text = Column(String, nullable=False)
    correct_option_id = Column(Integer, nullable=True) # Will be set after options are created

    test = relationship("Test", back_populates="questions")
    concept = relationship("Concept", back_populates="questions")
    options = relationship("Option", back_populates="question")

class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    text = Column(String, nullable=False)

    question = relationship("Question", back_populates="options")

class TestAssignment(Base):
    __tablename__ = "test_assignments"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"))
    student_id = Column(Integer, ForeignKey("app_users.id"))
    status = Column(String, default="not_started") # not_started, in_progress, completed

    test = relationship("Test", back_populates="assignments")

class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("app_users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    selected_option_id = Column(Integer, ForeignKey("options.id"))
    is_correct = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

class StudentConceptMastery(Base):
    __tablename__ = "student_concept_mastery"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("app_users.id"), index=True, nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.id"), index=True, nullable=False)
    mastery_p = Column(Float, nullable=False, default=0.1) # Probability p(mastery) between 0 and 1
    opportunity_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class QuestionSkill(Base):
    """
    Maps questions to the specific concepts (skills) required to answer them.
    Supports multi-attribute Q-matrix for DINA and other models.
    """
    __tablename__ = "question_skills"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), index=True, nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.id"), index=True, nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    source = Column(String, nullable=False, default="teacher") # 'teacher', 'llm_inferred', 'graph'
    llm_confidence = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint('question_id', 'concept_id', name='uix_question_concept'),)

class CognitiveDiagnosisProfile(Base):
    """
    Layer 3 — DINA Cognitive Diagnosis Profile.
    Stores confidence-weighted mastery estimates derived from Bayesian DINA
    posterior analysis of student responses per concept.
    """
    __tablename__ = "cognitive_diagnosis_profile"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("app_users.id"), index=True, nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.id"), index=True, nullable=False)
    raw_mastery_p = Column(Float, nullable=True)          # Layer 2 BKT output (copied for reference)
    adjusted_mastery = Column(Float, nullable=False)       # DINA posterior P(α=1|X)
    confidence_score = Column(Float, nullable=False)       # 1 - 4·p·(1-p), range [0, 1]
    reliability_tier = Column(String, nullable=False)      # "LOW", "MEDIUM", or "HIGH"
    opportunity_count = Column(Integer, nullable=False, default=0)
    last_diagnosed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint('student_id', 'concept_id', name='uix_student_concept_diagnosis'),)

