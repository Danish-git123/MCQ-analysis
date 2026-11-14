"""
Seed script to create a realistic Multi-Skill Sample Test in the database.
Creates:
1. Core Concepts with Prerequisite Relationships (DAG).
2. A comprehensive 6-Question Diagnostic Test testing single-skill and multi-skill questions.
3. Automatically maps Question-Skills (Q-Matrix).
4. Automatically assigns the test to all registered students.
"""

import asyncio
from sqlalchemy.future import select
from app.database import async_session
from app.models import User, Concept, ConceptEdge, Test, Question, Option, QuestionSkill, TestAssignment

SAMPLE_CONCEPTS = [
    "Trigonometric Vectors",
    "Newtonian Laws of Motion",
    "Kinetic & Static Friction",
    "Work & Energy Conservation"
]

SAMPLE_EDGES = [
    ("Trigonometric Vectors", "Newtonian Laws of Motion"),
    ("Newtonian Laws of Motion", "Kinetic & Static Friction"),
    ("Newtonian Laws of Motion", "Work & Energy Conservation")
]

SAMPLE_QUESTIONS = [
    {
        "text": "A 100 N force acts at an angle of 30° above the horizontal. What is its horizontal component?",
        "primary_concept": "Trigonometric Vectors",
        "skills": ["Trigonometric Vectors"],
        "options": [
            ("86.6 N", True),
            ("50.0 N", False),
            ("100.0 N", False),
            ("70.7 N", False)
        ]
    },
    {
        "text": "A 5 kg block accelerates at 4 m/s² on a frictionless surface. What is the net horizontal force acting on it?",
        "primary_concept": "Newtonian Laws of Motion",
        "skills": ["Newtonian Laws of Motion"],
        "options": [
            ("20 N", True),
            ("1.25 N", False),
            ("9.8 N", False),
            ("45 N", False)
        ]
    },
    {
        "text": "A 10 kg mass rests on a frictionless ramp inclined at 30° to the horizontal. What is the acceleration down the incline? (g = 9.8 m/s²)",
        "primary_concept": "Newtonian Laws of Motion",
        "skills": ["Trigonometric Vectors", "Newtonian Laws of Motion"],
        "options": [
            ("4.9 m/s²", True),
            ("8.5 m/s²", False),
            ("9.8 m/s²", False),
            ("2.45 m/s²", False)
        ]
    },
    {
        "text": "A 10 kg crate rests on a horizontal floor with coefficient of kinetic friction μk = 0.20. What frictional force opposes its motion? (g = 9.8 m/s²)",
        "primary_concept": "Kinetic & Static Friction",
        "skills": ["Newtonian Laws of Motion", "Kinetic & Static Friction"],
        "options": [
            ("19.6 N", True),
            ("98.0 N", False),
            ("49.0 N", False),
            ("2.0 N", False)
        ]
    },
    {
        "text": "A block slides down a 37° rough ramp (sin 37° ≈ 0.6, cos 37° ≈ 0.8) with μk = 0.25. What is the net acceleration down the incline? (g = 10 m/s²)",
        "primary_concept": "Kinetic & Static Friction",
        "skills": ["Trigonometric Vectors", "Newtonian Laws of Motion", "Kinetic & Static Friction"],
        "options": [
            ("4.0 m/s²", True),
            ("6.0 m/s²", False),
            ("2.0 m/s²", False),
            ("8.0 m/s²", False)
        ]
    },
    {
        "text": "A 2 kg pendulum bob is released from a height of 1.25 m above its lowest point. Ignoring air resistance, what is its speed at the lowest point? (g = 10 m/s²)",
        "primary_concept": "Work & Energy Conservation",
        "skills": ["Newtonian Laws of Motion", "Work & Energy Conservation"],
        "options": [
            ("5.0 m/s", True),
            ("25.0 m/s", False),
            ("2.5 m/s", False),
            ("10.0 m/s", False)
        ]
    }
]


async def seed():
    async with async_session() as session:
        print("🌱 Seeding Sample Test into Database...")

        # 1. Find or create a teacher
        res_t = await session.execute(select(User).where(User.role == "teacher"))
        teacher = res_t.scalars().first()
        if not teacher:
            print("⚠️ No teacher account found. Please register as a teacher in the UI first.")
            return

        # 2. Seed Concepts
        concept_map = {}
        for cname in SAMPLE_CONCEPTS:
            stmt = select(Concept).where(Concept.name == cname)
            res = await session.execute(stmt)
            c = res.scalars().first()
            if not c:
                c = Concept(name=cname, created_by_teacher_id=teacher.id)
                session.add(c)
                await session.flush()
                print(f"  + Created concept: {cname}")
            concept_map[cname] = c

        # 3. Seed Prerequisite Edges
        for from_name, to_name in SAMPLE_EDGES:
            c1 = concept_map[from_name]
            c2 = concept_map[to_name]
            stmt = select(ConceptEdge).where(
                ConceptEdge.from_concept_id == c1.id,
                ConceptEdge.to_concept_id == c2.id
            )
            res = await session.execute(stmt)
            if not res.scalars().first():
                edge = ConceptEdge(
                    from_concept_id=c1.id,
                    to_concept_id=c2.id,
                    confidence=0.95,
                    source="manual"
                )
                session.add(edge)
                print(f"  + Created prerequisite: {from_name} -> {to_name}")

        # 4. Create the Test
        test_title = "Engineering Mechanics & Vector Dynamics Diagnostic Test"
        stmt_test = select(Test).where(Test.title == test_title)
        res_test = await session.execute(stmt_test)
        test = res_test.scalars().first()
        if not test:
            test = Test(title=test_title, created_by_teacher_id=teacher.id)
            session.add(test)
            await session.flush()
            print(f"  + Created Test: '{test_title}'")

            # 5. Add Questions, Options & Q-Matrix Skills
            for q_idx, q_info in enumerate(SAMPLE_QUESTIONS, 1):
                prim_concept = concept_map[q_info["primary_concept"]]
                q = Question(
                    test_id=test.id,
                    concept_id=prim_concept.id,
                    text=q_info["text"]
                )
                session.add(q)
                await session.flush()

                # Add options
                correct_id = None
                for opt_text, is_corr in q_info["options"]:
                    opt = Option(question_id=q.id, text=opt_text)
                    session.add(opt)
                    await session.flush()
                    if is_corr:
                        correct_id = opt.id

                q.correct_option_id = correct_id

                # Populate Q-Matrix (question_skills)
                for skill_name in q_info["skills"]:
                    s_concept = concept_map[skill_name]
                    qs = QuestionSkill(
                        question_id=q.id,
                        concept_id=s_concept.id,
                        is_primary=(skill_name == q_info["primary_concept"]),
                        source="teacher"
                    )
                    session.add(qs)

                print(f"    - Added Q{q_idx} with {len(q_info['skills'])} skills mapped in Q-Matrix")

        # 6. Assign the test to all students
        res_students = await session.execute(select(User).where(User.role == "student"))
        students = res_students.scalars().all()
        for s in students:
            stmt_a = select(TestAssignment).where(
                TestAssignment.test_id == test.id,
                TestAssignment.student_id == s.id
            )
            res_a = await session.execute(stmt_a)
            if not res_a.scalars().first():
                assign = TestAssignment(
                    test_id=test.id,
                    student_id=s.id,
                    status="not_started"
                )
                session.add(assign)
                print(f"  + Assigned test to student: {s.name or s.email}")

        await session.commit()
        print("\n✅ Sample Test Successfully Seeded & Ready to Take!")


if __name__ == "__main__":
    asyncio.run(seed())

