from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.database import get_db
from app.auth import get_current_user, get_current_teacher
from app.models import User
from app.schemas import ConceptEdgeCreate
from app.services.concept_graph import (
    infer_llm_concept_edges,
    get_concept_graph_data,
    create_manual_concept_edge,
    delete_concept_edge,
)

router = APIRouter(prefix="/concepts", tags=["Concepts & Knowledge Graph"])

@router.post("/infer-graph")
async def infer_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
) -> Dict[str, Any]:
    """
    Trigger LLM-based prerequisite graph inference across all existing concepts.
    Enforces DAG using NetworkX and attaches confidence + source metadata.
    """
    try:
        result = await infer_llm_concept_edges(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph")
async def get_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get graph representation (nodes and directed prerequisite edges)
    including confidence score and source ('llm_inferred', 'statistical', 'manual').
    """
    try:
        data = await get_concept_graph_data(db)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edges")
async def add_manual_edge(
    req: ConceptEdgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
) -> Dict[str, Any]:
    try:
        return await create_manual_concept_edge(
            from_concept_id=req.from_concept_id,
            to_concept_id=req.to_concept_id,
            confidence=req.confidence,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/edges/{edge_id}")
async def remove_concept_edge(
    edge_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
) -> Dict[str, Any]:
    try:
        return await delete_concept_edge(edge_id=edge_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
