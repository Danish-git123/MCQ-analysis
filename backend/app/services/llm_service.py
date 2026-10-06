import logging
import json
from typing import List, Dict, Any, Optional
from groq import Groq
from app.core.config import settings
from app.models import Concept, Question, QuestionSkill
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        # Gemini can be added here if needed in the future

    async def get_completion(self, prompt: str, system_prompt: str = "") -> str:
        if not self.groq_client:
            raise ValueError("GROQ_API_KEY is not configured")
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="groq/compound",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise RuntimeError(f"Failed LLM inference: {str(e)}")

    async def infer_question_skills(self, question_ids: List[int], db: AsyncSession):
        """
        Batch infer additional prerequisite skills for a list of questions.
        """
        # 1. Fetch questions and their options
        stmt = select(Question).where(Question.id.in_(question_ids))
        res = await db.execute(stmt)
        questions = res.scalars().all()
        
        if not questions:
            return

        # 2. Fetch all existing concepts to match against
        stmt_concepts = select(Concept)
        res_concepts = await db.execute(stmt_concepts)
        all_concepts = res_concepts.scalars().all()
        concept_map = {c.name.strip().lower(): c for c in all_concepts}
        concept_names = [c.name for c in all_concepts]

        # 3. Prepare prompt
        questions_data = []
        for q in questions:
            # We need to fetch options for each question
            from app.models import Option
            stmt_opt = select(Option).where(Option.question_id == q.id)
            res_opt = await db.execute(stmt_opt)
            options = res_opt.scalars().all()
            
            # Fetch primary concept name
            primary_concept = next((c.name for c in all_concepts if c.id == q.concept_id), "Unknown")
            
            questions_data.append({
                "id": q.id,
                "text": q.text,
                "primary_concept": primary_concept,
                "options": [o.text for o in options]
            })

        system_prompt = "You are an expert in educational psychometrics and cognitive diagnosis models (DINA)."
        prompt = f"""
Given a list of questions and their primary concepts, identify up to 2 ADDITIONAL prerequisite skills 
needed to answer each question correctly. 

Choose ONLY from this existing concept list:
{json.dumps(concept_names, indent=2)}

Return ONLY a valid JSON object with a single key "inferences" containing an array of objects:
{{
  "inferences": [
    {{
      "question_id": 123,
      "additional_skills": [
        {{"name": "Concept A", "confidence": 0.85}},
        {{"name": "Concept B", "confidence": 0.70}}
      ]
    }}
  ]
}}

Keep only skills with confidence >= 0.6. Max 3 skills per question in total (including primary).
If no additional skills are needed, return an empty list for additional_skills.
"""
        prompt += f"\nQuestions:\n{json.dumps(questions_data, indent=2)}"

        try:
            content = await self.get_completion(prompt, system_prompt)
            data = json.loads(content)
            inferences = data.get("inferences", [])
            
            for inf in inferences:
                q_id = inf.get("question_id")
                additional_skills = inf.get("additional_skills", [])
                
                # Filter by confidence and existence
                valid_skills = []
                for skill in additional_skills:
                    s_name = skill.get("name", "").strip().lower()
                    conf = skill.get("confidence", 0)
                    if s_name in concept_map and conf >= 0.6:
                        valid_skills.append((concept_map[s_name].id, conf))
                
                # Limit to 2 additional skills
                valid_skills = valid_skills[:2]
                
                for c_id, conf in valid_skills:
                    # Upsert on unique constraint
                    from sqlalchemy.dialects.postgresql import insert
                    from app.models import QuestionSkill
                    
                    # SQLAlchemy insert with on_conflict_do_update
                    stmt_upsert = insert(QuestionSkill).values(
                        question_id=q_id,
                        concept_id=c_id,
                        is_primary=False,
                        source='llm_inferred',
                        llm_confidence=conf
                    ).on_conflict_do_update(
                        index_elements=['question_id', 'concept_id'],
                        set_=dict(llm_confidence=conf, source='llm_inferred')
                    )
                    await db.execute(stmt_upsert)
            
            await db.commit()
            logger.info(f"Successfully inferred skills for {len(inferences)} questions.")
        except Exception as e:
            logger.error(f"Failed to infer question skills: {e}")
            # Do not raise, background task should fail silently/log only

llm_service = LLMService()

def get_llm_service() -> LLMService:
    return llm_service
