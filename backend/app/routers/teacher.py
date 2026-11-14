from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from collections import defaultdict
from typing import List, Dict, Any
import math
import networkx as nx

from ..database import get_db
from ..models import (
    User, Concept, ConceptEdge, Test, Question, Option,
    TestAssignment, Response, QuestionSkill,
    CognitiveDiagnosisProfile, StudentConceptMastery,
)
from ..schemas import ConceptCreate, ConceptRead, TestCreate, TestRead, TestAssignmentCreate, BulkQuestionImportRequest, BulkQuestionImportResponse
from ..auth import get_current_teacher
from ..services.llm_service import get_llm_service

router = APIRouter(prefix="/teacher", tags=["teacher"])

@router.get("/concepts", response_model=List[ConceptRead])
async def list_concepts(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    result = await db.execute(select(Concept))
    return result.scalars().all()

@router.post("/concepts", response_model=ConceptRead)
async def create_concept(concept: ConceptCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    clean_name = concept.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Concept name cannot be empty.")
    res = await db.execute(select(Concept))
    for existing in res.scalars().all():
        if existing.name.strip().lower() == clean_name.lower():
            return existing
    db_concept = Concept(name=clean_name, created_by_teacher_id=current_user.id)
    db.add(db_concept)
    await db.commit()
    await db.refresh(db_concept)
    return db_concept

@router.post("/tests", response_model=TestRead)
async def create_test(
    test: TestCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_teacher)
):
    db_test = Test(title=test.title, created_by_teacher_id=current_user.id)
    db.add(db_test)
    await db.flush() # flush to get test id

    new_question_ids = []
    infer_candidate_q_ids = []
    for q_idx, q_data in enumerate(test.questions):
        effective_cid = q_data.concept_id
        if effective_cid is None and q_data.skill_ids:
            effective_cid = q_data.skill_ids[0]
        db_q = Question(
            test_id=db_test.id,
            concept_id=effective_cid,
            text=q_data.text
        )
        db.add(db_q)
        await db.flush()
        new_question_ids.append(db_q.id)

        # Insert teacher-assigned primary & secondary Q-matrix skills
        teacher_skills: List[tuple] = []
        seen_cids = set()
        if db_q.concept_id:
            teacher_skills.append((db_q.concept_id, True))
            seen_cids.add(db_q.concept_id)
        for sid in (q_data.skill_ids or []):
            if sid and sid not in seen_cids:
                teacher_skills.append((sid, len(seen_cids) == 0))
                seen_cids.add(sid)

        for cid, is_prim in teacher_skills:
            await db.execute(
                pg_insert(QuestionSkill)
                .values(
                    question_id=db_q.id,
                    concept_id=cid,
                    is_primary=is_prim,
                    source='teacher',
                )
                .on_conflict_do_nothing(index_elements=["question_id", "concept_id"])
            )

        if not q_data.skill_ids:
            infer_candidate_q_ids.append(db_q.id)

        correct_opt_id = None
        for o_idx, o_data in enumerate(q_data.options):
            db_o = Option(
                question_id=db_q.id,
                text=o_data.text
            )
            db.add(db_o)
            await db.flush()
            if o_data.is_correct:
                correct_opt_id = db_o.id
        
        if correct_opt_id:
            db_q.correct_option_id = correct_opt_id

    await db.commit()
    
    # Trigger LLM Q-matrix enrichment in background for questions without explicit secondary skills
    if infer_candidate_q_ids:
        async def run_inference(q_ids: List[int]):
            from app.database import async_session
            from app.services.llm_service import get_llm_service
            async with async_session() as session:
                llm = get_llm_service()
                await llm.infer_question_skills(q_ids, session)

        background_tasks.add_task(run_inference, infer_candidate_q_ids)

    # Reload test with relationships
    stmt = select(Test).options(
        selectinload(Test.questions).selectinload(Question.options)
    ).where(Test.id == db_test.id)
    result = await db.execute(stmt)
    return result.scalars().first()

@router.post("/questions/infer-skills")
async def infer_all_question_skills(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    """
    Manually trigger LLM inference for all questions that only have a primary skill.
    """
    # Find all questions
    stmt = select(Question.id)
    res = await db.execute(stmt)
    q_ids = [r[0] for r in res.all()]

    if q_ids:
        async def run_inference(ids: List[int]):
            from app.database import async_session
            from app.services.llm_service import get_llm_service
            async with async_session() as session:
                llm = get_llm_service()
                await llm.infer_question_skills(ids, session)

        background_tasks.add_task(run_inference, q_ids)

    return {"message": f"Skill inference triggered for {len(q_ids)} questions in the background."}

@router.get("/tests", response_model=List[TestRead])
async def list_tests(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    stmt = select(Test).options(
        selectinload(Test.questions).selectinload(Question.options)
    ).where(Test.created_by_teacher_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/assign-test")
async def assign_test(assignment: TestAssignmentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    student_ids_to_assign = set(assignment.student_ids or [])

    if assignment.student_emails:
        for email in assignment.student_emails:
            clean_email = email.strip().lower()
            if not clean_email:
                continue
            stmt = select(User).where(User.email == clean_email)
            res = await db.execute(stmt)
            user = res.scalars().first()
            if user:
                student_ids_to_assign.add(user.id)
            else:
                raise HTTPException(status_code=404, detail=f"No user found with email '{clean_email}'")

    if not student_ids_to_assign:
        raise HTTPException(status_code=400, detail="No valid students selected or provided.")

    assigned_count = 0
    for s_id in student_ids_to_assign:
        stmt = select(TestAssignment).where(
            TestAssignment.test_id == assignment.test_id,
            TestAssignment.student_id == s_id
        )
        res = await db.execute(stmt)
        if not res.scalars().first():
            db_assignment = TestAssignment(test_id=assignment.test_id, student_id=s_id)
            db.add(db_assignment)
            assigned_count += 1
            
    await db.commit()
    return {"message": "Test assigned successfully", "assigned_count": assigned_count}

def _pearson_r(xs: List[float], ys: List[float]):
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs)
    den_y = sum((y - mean_y) ** 2 for y in ys)
    if den_x <= 1e-12 or den_y <= 1e-12:
        return None
    return round(num / math.sqrt(den_x * den_y), 3)


@router.get("/tests/{test_id}/results")
async def test_results(test_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    t_stmt = (
        select(Test)
        .options(selectinload(Test.questions).selectinload(Question.options))
        .where(Test.id == test_id)
    )
    t_res = await db.execute(t_stmt)
    test_obj = t_res.scalars().first()
    if not test_obj:
        raise HTTPException(status_code=404, detail="Test not found.")

    questions_sorted = sorted(test_obj.questions, key=lambda q: q.id)
    q_ids = [q.id for q in questions_sorted]

    # Fetch concepts & edges
    c_res = await db.execute(select(Concept))
    concepts_all = c_res.scalars().all()
    concept_by_id = {c.id: c.name for c in concepts_all}

    e_res = await db.execute(select(ConceptEdge))
    all_edges = e_res.scalars().all()

    # Fetch Q-matrix mappings for this test's questions
    q_skill_map: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    test_concept_ids = set()
    if q_ids:
        qs_res = await db.execute(select(QuestionSkill).where(QuestionSkill.question_id.in_(q_ids)))
        for qs in qs_res.scalars().all():
            q_skill_map[qs.question_id].append({
                "concept_id": qs.concept_id,
                "concept_name": concept_by_id.get(qs.concept_id, f"Concept #{qs.concept_id}"),
                "is_primary": qs.is_primary,
                "source": qs.source,
                "llm_confidence": qs.llm_confidence,
            })
            test_concept_ids.add(qs.concept_id)

    for q in questions_sorted:
        if q.concept_id:
            test_concept_ids.add(q.concept_id)
            if not any(s["concept_id"] == q.concept_id for s in q_skill_map[q.id]):
                q_skill_map[q.id].insert(0, {
                    "concept_id": q.concept_id,
                    "concept_name": concept_by_id.get(q.concept_id, f"Concept #{q.concept_id}"),
                    "is_primary": True,
                    "source": "teacher",
                    "llm_confidence": None,
                })

    # Fetch assignments & responses
    assign_res = await db.execute(
        select(TestAssignment, User)
        .join(User, TestAssignment.student_id == User.id)
        .where(TestAssignment.test_id == test_id)
    )
    assigned_users: Dict[int, Dict[str, Any]] = {}
    for ta, u in assign_res.all():
        assigned_users[u.id] = {"student_id": u.id, "name": u.name, "email": u.email, "assignment_status": ta.status}

    responses_rows = []
    if q_ids:
        r_stmt = (
            select(Response, User)
            .join(User, Response.student_id == User.id)
            .where(Response.question_id.in_(q_ids))
            .order_by(Response.answered_at.asc())
        )
        r_res = await db.execute(r_stmt)
        responses_rows = r_res.all()

    responses_only = [r for r, _ in responses_rows]
    total = len(responses_only)
    correct = sum(1 for r in responses_only if r.is_correct)
    rapid_guesses_total = sum(1 for r in responses_only if (r.response_time_ms or 0) < 4000)
    avg_time_total = round(
        sum((r.response_time_ms or 0) for r in responses_only) / total / 1000.0, 1
    ) if total else 0.0

    # Aggregate student-level performance on this test
    student_agg: Dict[int, Dict[str, Any]] = {}
    student_q_scores: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
    student_concept_perf: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
    concept_perf_agg: Dict[int, Dict[str, int]] = defaultdict(lambda: {"attempts": 0, "correct": 0})
    q_stats: Dict[int, Dict[str, Any]] = {}

    for r, u in responses_rows:
        if u.id not in assigned_users:
            assigned_users[u.id] = {"student_id": u.id, "name": u.name, "email": u.email, "assignment_status": "completed"}

        st = student_agg.setdefault(u.id, {
            "student_id": u.id,
            "name": u.name,
            "email": u.email,
            "answered_count": 0,
            "correct_count": 0,
            "rapid_guess_count": 0,
            "total_time_ms": 0,
        })
        st["answered_count"] += 1
        if r.is_correct:
            st["correct_count"] += 1
        if (r.response_time_ms or 0) < 4000:
            st["rapid_guess_count"] += 1
        st["total_time_ms"] += (r.response_time_ms or 0)

        student_q_scores[u.id][r.question_id].append(1 if r.is_correct else 0)

        if r.question_id not in q_stats:
            q_stats[r.question_id] = {"total": 0, "correct": 0}
        q_stats[r.question_id]["total"] += 1
        if r.is_correct:
            q_stats[r.question_id]["correct"] += 1

        for sk in q_skill_map.get(r.question_id, []):
            cid = sk["concept_id"]
            student_concept_perf[u.id][cid].append(1 if r.is_correct else 0)
            concept_perf_agg[cid]["attempts"] += 1
            if r.is_correct:
                concept_perf_agg[cid]["correct"] += 1

    # Include assigned students who haven't answered yet
    for sid, info in assigned_users.items():
        if sid not in student_agg:
            student_agg[sid] = {
                "student_id": sid,
                "name": info["name"],
                "email": info["email"],
                "answered_count": 0,
                "correct_count": 0,
                "rapid_guess_count": 0,
                "total_time_ms": 0,
            }

    all_student_ids = list(student_agg.keys())

    # Fetch DINA & BKT profiles for participating students & test concepts
    dina_lookup: Dict[tuple, CognitiveDiagnosisProfile] = {}
    bkt_lookup: Dict[tuple, StudentConceptMastery] = {}
    if all_student_ids and test_concept_ids:
        d_res = await db.execute(
            select(CognitiveDiagnosisProfile).where(
                CognitiveDiagnosisProfile.student_id.in_(all_student_ids),
                CognitiveDiagnosisProfile.concept_id.in_(list(test_concept_ids)),
            )
        )
        for prof in d_res.scalars().all():
            dina_lookup[(prof.student_id, prof.concept_id)] = prof

        b_res = await db.execute(
            select(StudentConceptMastery).where(
                StudentConceptMastery.student_id.in_(all_student_ids),
                StudentConceptMastery.concept_id.in_(list(test_concept_ids)),
            )
        )
        for bkt in b_res.scalars().all():
            bkt_lookup[(bkt.student_id, bkt.concept_id)] = bkt

    # Build Student rows & Heatmap Cells
    student_overall_scores: Dict[int, float] = {}
    heatmap_students: List[Dict[str, Any]] = []
    for sid, st in student_agg.items():
        ans = st["answered_count"]
        acc = round((st["correct_count"] / ans) * 100, 1) if ans else None
        if acc is not None:
            student_overall_scores[sid] = acc / 100.0
        avg_t = round((st["total_time_ms"] / ans) / 1000.0, 1) if ans else 0.0
        rapid_pct_s = round((st["rapid_guess_count"] / ans) * 100, 1) if ans else 0.0

        # Careless slip count: missed item whose required concepts average DINA mastery >= 0.70
        slip_count = 0
        for r, _ in responses_rows:
            if r.student_id == sid and not r.is_correct:
                req_cids = [sk["concept_id"] for sk in q_skill_map.get(r.question_id, [])]
                known_vals = [
                    dina_lookup[(sid, c)].adjusted_mastery
                    for c in req_cids
                    if (sid, c) in dina_lookup
                ]
                if known_vals and (sum(known_vals) / len(known_vals)) >= 0.70 and (r.response_time_ms or 0) >= 4000:
                    slip_count += 1

        if ans == 0:
            effort_status = "NOT_STARTED"
        elif rapid_pct_s >= 40.0 or st["rapid_guess_count"] >= 2:
            effort_status = "RAPID_GUESSING_RISK"
        elif (acc or 0) < 50.0:
            effort_status = "NEEDS_SUPPORT"
        elif (acc or 0) < 75.0:
            effort_status = "DEVELOPING"
        else:
            effort_status = "ON_TRACK"

        heatmap_students.append({
            "student_id": sid,
            "name": st["name"],
            "email": st["email"],
            "assignment_status": assigned_users.get(sid, {}).get("assignment_status", "assigned"),
            "answered_count": ans,
            "accuracy_pct": acc,
            "rapid_guess_count": st["rapid_guess_count"],
            "rapid_guessing_pct": rapid_pct_s,
            "careless_slip_count": slip_count,
            "avg_time_sec": avg_t,
            "effort_status": effort_status,
        })

    heatmap_students.sort(key=lambda s: (s["answered_count"] == 0, s["accuracy_pct"] if s["accuracy_pct"] is not None else 999))

    sorted_test_concepts = sorted(
        [{"concept_id": cid, "concept_name": concept_by_id.get(cid, f"Concept #{cid}")} for cid in test_concept_ids],
        key=lambda c: c["concept_name"]
    )

    heatmap_cells: Dict[str, Dict[str, Any]] = {}
    for st in heatmap_students:
        sid = st["student_id"]
        row_cells: Dict[str, Any] = {}
        for cinfo in sorted_test_concepts:
            cid = cinfo["concept_id"]
            prof = dina_lookup.get((sid, cid))
            bkt = bkt_lookup.get((sid, cid))
            q_scores = student_concept_perf.get(sid, {}).get(cid, [])
            test_c_acc = round((sum(q_scores) / len(q_scores)) * 100, 1) if q_scores else None
            mastery_val = (
                round(prof.adjusted_mastery, 3)
                if prof
                else (round(bkt.mastery_p, 3) if bkt else (round(test_c_acc / 100.0, 3) if test_c_acc is not None else None))
            )
            row_cells[str(cid)] = {
                "mastery": mastery_val,
                "bkt_mastery": round(bkt.mastery_p, 3) if bkt else None,
                "confidence": round(prof.confidence_score, 3) if prof else None,
                "tier": prof.reliability_tier if prof else ("OBSERVED" if test_c_acc is not None else "UNTESTED"),
                "test_accuracy_pct": test_c_acc,
            }
        heatmap_cells[str(sid)] = row_cells

    # Build Per-Question Psychometrics & Distractor Magnet Breakdown
    question_analytics: List[Dict[str, Any]] = []
    for idx, q in enumerate(questions_sorted):
        q_resps = [r for r in responses_only if r.question_id == q.id]
        q_attempts = len(q_resps)
        q_corr = sum(1 for r in q_resps if r.is_correct)
        q_acc = round((q_corr / q_attempts) * 100, 1) if q_attempts else 0.0
        q_avg_t = round(sum((r.response_time_ms or 0) for r in q_resps) / q_attempts / 1000.0, 1) if q_attempts else 0.0
        q_rapid = sum(1 for r in q_resps if (r.response_time_ms or 0) < 4000)

        # Discrimination index (Point-Biserial vs. student's overall score across test)
        xs_item: List[float] = []
        ys_total: List[float] = []
        for sid, qmap in student_q_scores.items():
            if q.id in qmap and sid in student_overall_scores:
                item_avg = sum(qmap[q.id]) / len(qmap[q.id])
                xs_item.append(item_avg)
                ys_total.append(student_overall_scores[sid])
        disc = _pearson_r(xs_item, ys_total)
        if q_attempts < 2 or disc is None:
            quality = "INSUFFICIENT_DATA"
        elif disc >= 0.25:
            quality = "STRONG"
        elif disc >= 0.10:
            quality = "FAIR"
        else:
            quality = "REVIEW_NEEDED"

        # Option distribution
        opt_counts: Dict[int, int] = defaultdict(int)
        for r in q_resps:
            if r.selected_option_id is not None:
                opt_counts[r.selected_option_id] += 1

        max_wrong_cnt = max(
            [opt_counts.get(o.id, 0) for o in q.options if o.id != q.correct_option_id],
            default=0,
        )
        option_dist = []
        for oi, opt in enumerate(q.options):
            cnt = opt_counts.get(opt.id, 0)
            is_corr_opt = opt.id == q.correct_option_id
            option_dist.append({
                "option_id": opt.id,
                "letter": chr(65 + oi) if oi < 26 else str(oi + 1),
                "text": opt.text,
                "is_correct": is_corr_opt,
                "count": cnt,
                "pct": round((cnt / q_attempts) * 100, 1) if q_attempts else 0.0,
                "is_top_distractor": (not is_corr_opt) and max_wrong_cnt > 0 and cnt == max_wrong_cnt,
            })

        question_analytics.append({
            "question_number": idx + 1,
            "question_id": q.id,
            "text": q.text,
            "concept_id": q.concept_id,
            "concept_name": concept_by_id.get(q.concept_id, "General"),
            "required_skills": q_skill_map.get(q.id, []),
            "attempts": q_attempts,
            "correct": q_corr,
            "accuracy_pct": q_acc,
            "avg_time_sec": q_avg_t,
            "rapid_guess_count": q_rapid,
            "discrimination_index": disc,
            "item_quality": quality,
            "option_distribution": option_dist,
        })

    # Build Cohort Prerequisite Bottleneck Graph (test concepts + direct DAG neighbors)
    graph_cids = set(test_concept_ids)
    relevant_edges = []
    for e in all_edges:
        if e.from_concept_id in test_concept_ids or e.to_concept_id in test_concept_ids:
            relevant_edges.append(e)
            graph_cids.add(e.from_concept_id)
            graph_cids.add(e.to_concept_id)

    # Fetch cohort DINA mastery for neighbor concepts as well
    if all_student_ids and graph_cids:
        extra_dina_res = await db.execute(
            select(CognitiveDiagnosisProfile).where(
                CognitiveDiagnosisProfile.student_id.in_(all_student_ids),
                CognitiveDiagnosisProfile.concept_id.in_(list(graph_cids)),
            )
        )
        for prof in extra_dina_res.scalars().all():
            dina_lookup[(prof.student_id, prof.concept_id)] = prof

    node_mastery_map: Dict[int, float] = {}
    node_acc_map: Dict[int, Any] = {}
    for cid in graph_cids:
        perf = concept_perf_agg.get(cid)
        c_acc = round((perf["correct"] / perf["attempts"]) * 100, 1) if perf and perf["attempts"] else None
        node_acc_map[cid] = c_acc
        d_vals = [dina_lookup[(sid, cid)].adjusted_mastery for sid in all_student_ids if (sid, cid) in dina_lookup]
        if d_vals:
            node_mastery_map[cid] = round(sum(d_vals) / len(d_vals), 3)
        elif c_acc is not None:
            node_mastery_map[cid] = round(c_acc / 100.0, 3)
        else:
            node_mastery_map[cid] = None

    G_cohort = nx.DiGraph()
    for cid in graph_cids:
        G_cohort.add_node(cid)
    for e in relevant_edges:
        G_cohort.add_edge(e.from_concept_id, e.to_concept_id)

    cohort_nodes = []
    for cid in sorted(graph_cids):
        m_val = node_mastery_map.get(cid)
        succ_weak = any((node_mastery_map.get(s) is not None and node_mastery_map[s] < 0.65) for s in G_cohort.successors(cid))
        is_root_blocker = bool(m_val is not None and m_val < 0.55 and succ_weak)
        cohort_nodes.append({
            "concept_id": cid,
            "name": concept_by_id.get(cid, f"Concept #{cid}"),
            "class_accuracy_pct": node_acc_map.get(cid),
            "avg_mastery": m_val,
            "attempts": concept_perf_agg.get(cid, {}).get("attempts", 0),
            "is_root_blocker": is_root_blocker,
        })

    cohort_edges = [
        {
            "id": e.id,
            "from_concept_id": e.from_concept_id,
            "to_concept_id": e.to_concept_id,
            "confidence": e.confidence,
            "source": e.source,
        }
        for e in relevant_edges
    ]

    return {
        "test_id": test_id,
        "test_title": test_obj.title,
        "total_responses": total,
        "total_correct": correct,
        "question_stats": q_stats,
        "summary": {
            "students_evaluated": sum(1 for s in heatmap_students if s["answered_count"] > 0),
            "assigned_count": len(assigned_users),
            "overall_accuracy_pct": round((correct / total) * 100, 1) if total else 0.0,
            "rapid_guessing_pct": round((rapid_guesses_total / total) * 100, 1) if total else 0.0,
            "avg_response_time_sec": avg_time_total,
            "concepts_covered": len(sorted_test_concepts),
        },
        "concept_heatmap": {
            "concepts": sorted_test_concepts,
            "students": heatmap_students,
            "cells": heatmap_cells,
        },
        "question_analytics": question_analytics,
        "cohort_graph": {
            "nodes": cohort_nodes,
            "edges": cohort_edges,
        },
    }

@router.get("/students")
async def list_students(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    result = await db.execute(select(User).where(User.role == "student"))
    students = result.scalars().all()
    return [{"id": s.id, "name": s.name, "email": s.email} for s in students]

import re

@router.post("/tests/parse-bulk-questions", response_model=BulkQuestionImportResponse)
async def parse_bulk_questions(
    request: BulkQuestionImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    lines = request.raw_text.splitlines()
    
    # Pre-fetch all concepts to match against
    result = await db.execute(select(Concept))
    all_db_concepts = result.scalars().all()
    concept_map = {c.name.strip().lower(): c for c in all_db_concepts}
    
    questions = []
    errors = []
    
    # State machine
    current_q_num = None
    current_concept_id = None
    current_concept_name = None
    
    current_q_text_lines = []
    current_options = []
    current_answer = None
    
    state = "SEARCHING" # SEARCHING, QUESTION_TEXT, OPTIONS
    
    def process_current_block():
        if not current_q_num:
            return
            
        q_text = " ".join(current_q_text_lines).strip()
        
        if not q_text:
            errors.append({"question_number": current_q_num, "message": "Question text is empty."})
            return
            
        if len(current_options) < 2:
            errors.append({"question_number": current_q_num, "message": "Question must have at least 2 options."})
            return
            
        if not current_answer:
            errors.append({"question_number": current_q_num, "message": "No 'Answer:' line found."})
            return
            
        # Find which option is correct based on the letter
        correct_idx = ord(current_answer.upper()) - ord('A')
        if correct_idx < 0 or correct_idx >= len(current_options):
            errors.append({"question_number": current_q_num, "message": f"Answer '{current_answer}' does not match any provided option."})
            return
            
        parsed_options = []
        for i, opt in enumerate(current_options):
            parsed_options.append({
                "text": opt,
                "is_correct": i == correct_idx
            })
            
        questions.append({
            "text": q_text,
            "concept_id": current_concept_id,
            "concept_name": current_concept_name,
            "options": parsed_options
        })

    q_pattern = re.compile(r'^Q(\d+)(?:\s*(?:[-—])\s*Concept:\s*`?([^`]+)`?)?', re.IGNORECASE)
    opt_pattern = re.compile(r'^([A-Z])\)\s*(.*)')
    ans_pattern = re.compile(r'^Answer:\s*([A-Z])', re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        q_match = q_pattern.match(stripped)
        if q_match:
            process_current_block()
            
            # Reset state for new question
            current_q_num = f"Q{q_match.group(1)}"
            raw_concept = q_match.group(2)
            
            current_concept_id = None
            current_concept_name = None
            
            if raw_concept:
                rc_clean = raw_concept.strip()
                rc_lower = rc_clean.lower()
                if rc_lower in concept_map:
                    current_concept_id = concept_map[rc_lower].id
                    current_concept_name = concept_map[rc_lower].name
                else:
                    current_concept_name = rc_clean
                    
            current_q_text_lines = []
            current_options = []
            current_answer = None
            state = "QUESTION_TEXT"
            continue
            
        if state == "SEARCHING":
            continue
            
        if state == "QUESTION_TEXT":
            opt_match = opt_pattern.match(stripped)
            ans_match = ans_pattern.match(stripped)
            if opt_match:
                state = "OPTIONS"
                current_options.append(opt_match.group(2).strip())
            elif ans_match:
                current_answer = ans_match.group(1).upper()
                state = "OPTIONS" # Technically end of options
            else:
                current_q_text_lines.append(stripped)
            continue
            
        if state == "OPTIONS":
            opt_match = opt_pattern.match(stripped)
            ans_match = ans_pattern.match(stripped)
            if opt_match:
                current_options.append(opt_match.group(2).strip())
            elif ans_match:
                current_answer = ans_match.group(1).upper()
            else:
                pass # Ignore or append? Let's ignore extra stuff in options for now
                
    # Process the last block
    process_current_block()
    
    if not questions and not errors:
        errors.append({"question_number": "All", "message": "Could not parse any questions. Make sure format matches 'Q1 — Concept: ...'"})

    return {"questions": questions, "errors": errors}
