from pydantic import BaseModel


class ConceptBase(BaseModel):
    name: str


class ConceptCreate(ConceptBase):
    pass


class ConceptRead(ConceptBase):
    id: int
    created_by_teacher_id: int

    class Config:
        from_attributes = True
