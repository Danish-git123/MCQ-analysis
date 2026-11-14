import json
import logging
import networkx as nx
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Concept, ConceptEdge
from .llm_service import llm_service

logger = logging.getLogger(__name__)

async def infer_llm_concept_edges(db: AsyncSession) -> Dict[str, Any]:
    """
    Fetch all concepts from DB, call LLM once to infer directed prerequisite relationships,
    enforce DAG (no cycles) using NetworkX, and persist new edges to concept_edges table.
    """
    # 1. Fetch all concepts
    stmt = select(Concept)
    res = await db.execute(stmt)
    concepts = res.scalars().all()

    if len(concepts) < 2:
        return {
            "status": "info",
            "message": "At least 2 concepts are required to infer prerequisite edges.",
            "edges_added": 0
        }

    # Map names (lowercase) to concept objects
    concept_map = {c.name.strip().lower(): c for c in concepts}
    concept_names = [c.name for c in concepts]

    # 2. Call LLM Service
    prompt = f"""You are an educational curriculum and knowledge graph expert.
Given the following list of concepts:
{json.dumps(concept_names, indent=2)}

Identify DIRECT prerequisite relationships between these concepts.
A prerequisite edge from 'Concept A' to 'Concept B' means a student MUST understand Concept A BEFORE learning Concept B.

Return ONLY a valid JSON object with a single key "edges" containing an array of objects in this exact format:
{{
  "edges": [
    {{
      "from_concept": "Concept A",
      "to_concept": "Concept B",
      "confidence": 0.90,
      "reasoning": "Explanation"
    }}
  ]
}}
If there are no clear prerequisite relationships between these concepts, return {{"edges": []}}.
"""

    try:
        content = await llm_service.get_completion(prompt, "You are a precise JSON-only knowledge graph builder.")
        data = json.loads(content)
        raw_edges = data.get("edges", [])
    except Exception as e:
        logger.error(f"Error calling LLM for concept graph inference: {e}")
        raise RuntimeError(f"Failed LLM inference: {str(e)}")

    # 3. Existing Edges & NetworkX DAG setup
    existing_edges_stmt = select(ConceptEdge)
    existing_edges_res = await db.execute(existing_edges_stmt)
    existing_edges = existing_edges_res.scalars().all()

    existing_set = {(e.from_concept_id, e.to_concept_id) for e in existing_edges}

    # Build NetworkX graph with existing edges to enforce DAG
    G = nx.DiGraph()
    for c in concepts:
        G.add_node(c.id)
    for u, v in existing_set:
        G.add_edge(u, v)

    added_edges = []

    # 4. Process LLM Inferred Edges
    for edge_info in raw_edges:
        from_name = edge_info.get("from_concept", "").strip().lower()
        to_name = edge_info.get("to_concept", "").strip().lower()
        confidence = float(edge_info.get("confidence", 0.8))

        from_c = concept_map.get(from_name)
        to_c = concept_map.get(to_name)

        if not from_c or not to_c or from_c.id == to_c.id:
            continue

        # Skip if edge already exists
        if (from_c.id, to_c.id) in existing_set:
            continue

        # Check if adding (from_c.id -> to_c.id) creates a cycle
        G.add_edge(from_c.id, to_c.id)
        if not nx.is_directed_acyclic_graph(G):
            # Remove edge to preserve DAG property
            G.remove_edge(from_c.id, to_c.id)
            logger.warning(f"Skipped edge {from_c.name} -> {to_c.name} as it would introduce a cycle.")
            continue

        # Persist new edge
        new_edge = ConceptEdge(
            from_concept_id=from_c.id,
            to_concept_id=to_c.id,
            confidence=confidence,
            source="llm_inferred"
        )
        db.add(new_edge)
        existing_set.add((from_c.id, to_c.id))
        added_edges.append({
            "from_concept": from_c.name,
            "to_concept": to_c.name,
            "confidence": confidence,
            "reasoning": edge_info.get("reasoning", "")
        })

    await db.commit()

    return {
        "status": "success",
        "message": f"Inferred {len(added_edges)} new prerequisite edge(s).",
        "added_edges": added_edges
    }

async def get_concept_graph_data(db: AsyncSession) -> Dict[str, Any]:
    """
    Return all nodes (concepts) and edges (prerequisites with source & confidence).
    """
    c_stmt = select(Concept)
    c_res = await db.execute(c_stmt)
    concepts = c_res.scalars().all()

    e_stmt = select(ConceptEdge)
    e_res = await db.execute(e_stmt)
    edges = e_res.scalars().all()

    c_dict = {c.id: c.name for c in concepts}

    nodes_list = [{"id": c.id, "name": c.name} for c in concepts]
    edges_list = [
        {
            "id": e.id,
            "from_concept_id": e.from_concept_id,
            "from_concept_name": c_dict.get(e.from_concept_id, "Unknown"),
            "to_concept_id": e.to_concept_id,
            "to_concept_name": c_dict.get(e.to_concept_id, "Unknown"),
            "confidence": e.confidence,
            "source": e.source
        }
        for e in edges
    ]

    return {
        "nodes": nodes_list,
        "edges": edges_list
    }


async def create_manual_concept_edge(
    from_concept_id: int,
    to_concept_id: int,
    confidence: float,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Manually link Prerequisite (from_concept_id) -> Dependent (to_concept_id),
    enforcing strict Directed Acyclic Graph (DAG) validity with NetworkX.
    """
    if from_concept_id == to_concept_id:
        raise ValueError("A concept cannot be a prerequisite of itself.")

    c_res = await db.execute(select(Concept))
    concepts = {c.id: c for c in c_res.scalars().all()}
    if from_concept_id not in concepts or to_concept_id not in concepts:
        raise ValueError("One or both selected concepts do not exist.")

    e_res = await db.execute(select(ConceptEdge))
    existing_edges = e_res.scalars().all()

    G = nx.DiGraph()
    for cid in concepts.keys():
        G.add_node(cid)
    for e in existing_edges:
        if e.from_concept_id == from_concept_id and e.to_concept_id == to_concept_id:
            raise ValueError(
                f"Edge '{concepts[from_concept_id].name} -> {concepts[to_concept_id].name}' already exists."
            )
        G.add_edge(e.from_concept_id, e.to_concept_id)

    G.add_edge(from_concept_id, to_concept_id)
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError(
            f"Cycle rejected by NetworkX: adding '{concepts[from_concept_id].name} -> "
            f"{concepts[to_concept_id].name}' creates a circular prerequisite dependency."
        )

    clamped_conf = max(0.1, min(1.0, float(confidence or 1.0)))
    new_edge = ConceptEdge(
        from_concept_id=from_concept_id,
        to_concept_id=to_concept_id,
        confidence=clamped_conf,
        source="manual",
    )
    db.add(new_edge)
    await db.commit()
    await db.refresh(new_edge)

    return {
        "id": new_edge.id,
        "from_concept_id": new_edge.from_concept_id,
        "from_concept_name": concepts[from_concept_id].name,
        "to_concept_id": new_edge.to_concept_id,
        "to_concept_name": concepts[to_concept_id].name,
        "confidence": new_edge.confidence,
        "source": new_edge.source,
    }


async def delete_concept_edge(edge_id: int, db: AsyncSession) -> Dict[str, Any]:
    stmt = select(ConceptEdge).where(ConceptEdge.id == edge_id)
    res = await db.execute(stmt)
    edge = res.scalars().first()
    if not edge:
        raise ValueError(f"Prerequisite edge #{edge_id} not found.")
    await db.delete(edge)
    await db.commit()
    return {"status": "deleted", "edge_id": edge_id}
