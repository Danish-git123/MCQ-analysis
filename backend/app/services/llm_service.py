import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from groq import Groq
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models import Concept, Option, Question, QuestionSkill

logger = logging.getLogger(__name__)

GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-flash"]
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_TOOL_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "groq/compound"


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON even if wrapped in markdown fences."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {"result": parsed}
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start : end + 1])
                return parsed if isinstance(parsed, dict) else {"result": parsed}
            except Exception:
                return None
    return None


class LLMService:
    """
    Multi-Provider Cognitive Router supporting:
      1. Google Gemini (gemini-2.5-flash via async httpx REST + native function calling)
      2. Groq (llama-3.3-70b-versatile via Groq SDK + tool calling)
      3. Graceful degradation so the Agentic Brain can fall back to its local
         deterministic neuro-symbolic engine when API keys/network are unavailable.
    """

    def __init__(self):
        self.gemini_api_key = (settings.GEMINI_API_KEY or "").strip() or None
        self.groq_api_key = (settings.GROQ_API_KEY or "").strip() or None
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None

    def available_providers(self) -> List[str]:
        providers = []
        if self.gemini_api_key:
            providers.append("gemini")
        if self.groq_client:
            providers.append("groq")
        providers.append("deterministic_fallback")
        return providers

    async def _call_gemini_json(
        self, prompt: str, system_prompt: str = "", timeout: float = 18.0
    ) -> Optional[str]:
        if not self.gemini_api_key:
            return None

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                for model_name in GEMINI_MODELS:
                    endpoint = f"{GEMINI_BASE_URL}/{model_name}:generateContent"
                    resp = await client.post(
                        endpoint,
                        params={"key": self.gemini_api_key},
                        json=payload,
                    )
                    if resp.status_code in (404, 429, 503):
                        logger.info(f"Gemini model {model_name} returned HTTP {resp.status_code}, trying next...")
                        continue
                    if resp.status_code != 200:
                        logger.warning(
                            f"Gemini API ({model_name}) returned HTTP {resp.status_code}: {resp.text[:200]}"
                        )
                        return None
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return None
                    parts = candidates[0].get("content", {}).get("parts", [])
                    texts = [p.get("text", "") for p in parts if "text" in p]
                    result_text = "\n".join(texts).strip()
                    if result_text:
                        return result_text
                return None
        except Exception as exc:
            logger.warning(f"Gemini request failed, falling over: {exc}")
            return None

    async def _call_groq_json(
        self, prompt: str, system_prompt: str = ""
    ) -> Optional[str]:
        if not self.groq_client:
            return None

        def _sync_call() -> Optional[str]:
            for model_name in (GROQ_TOOL_MODEL, GROQ_FALLBACK_MODEL):
                try:
                    completion = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.2,
                        response_format={"type": "json_object"},
                    )
                    return completion.choices[0].message.content
                except Exception as exc:
                    logger.warning(f"Groq model {model_name} failed: {exc}")
            return None

        return await asyncio.to_thread(_sync_call)

    async def generate_json_with_provider(
        self, prompt: str, system_prompt: str = ""
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Attempts structured JSON generation across Gemini -> Groq.
        Returns (parsed_dict, provider_used). If both fail, returns (None, 'deterministic_fallback').
        """
        gemini_raw = await self._call_gemini_json(prompt, system_prompt)
        if gemini_raw:
            parsed = _extract_json_object(gemini_raw)
            if parsed is not None:
                return parsed, "gemini"

        groq_raw = await self._call_groq_json(prompt, system_prompt)
        if groq_raw:
            parsed = _extract_json_object(groq_raw)
            if parsed is not None:
                return parsed, "groq"

        return None, "deterministic_fallback"

    async def get_completion(self, prompt: str, system_prompt: str = "") -> str:
        """
        Backward-compatible JSON string completion across Gemini -> Groq.
        """
        data, provider = await self.generate_json_with_provider(prompt, system_prompt)
        if data is not None:
            return json.dumps(data)
        raise RuntimeError(
            "No live LLM provider succeeded (configure a valid GEMINI_API_KEY or GROQ_API_KEY)."
        )

    async def run_react_step(
        self,
        goal: str,
        history: List[Dict[str, Any]],
        tool_catalog: List[Dict[str, Any]],
        system_prompt: str,
    ) -> Dict[str, Any]:
        """
        Executes one cognitive planning step using Gemini or Groq.
        Given the goal, prior (thought, tool_name, tool_args, observation) steps, and
        available tool schemas, decides whether to call another tool or emit the final synthesis.

        Returns:
          {
            "provider": "gemini" | "groq" | "deterministic_fallback",
            "action": "call_tool" | "finish" | "fallback",
            "thought": str,
            "tool_name": Optional[str],
            "tool_args": Dict[str, Any],
            "final_output": Optional[Dict[str, Any]]
          }
        """
        planner_prompt = f"""
GOAL:
{goal}

AVAILABLE TOOLS:
{json.dumps(tool_catalog, indent=2)}

PREVIOUS STEPS & OBSERVATIONS:
{json.dumps(history, indent=2)}

Decide the single next best step.
Return ONLY valid JSON matching ONE of these two formats:

Option A — Call a tool to gather more evidence or validate/synthesize:
{{
  "action": "call_tool",
  "thought": "Brief explanation of why this tool is needed right now",
  "tool_name": "exact_tool_name_from_catalog",
  "tool_args": {{}}
}}

Option B — Finish and output the final synthesized plan once sufficient evidence has been gathered:
{{
  "action": "finish",
  "thought": "Summary of final pedagogical reasoning",
  "final_output": {{}}
}}
"""
        data, provider = await self.generate_json_with_provider(
            planner_prompt, system_prompt
        )
        if not data or provider == "deterministic_fallback":
            return {
                "provider": "deterministic_fallback",
                "action": "fallback",
                "thought": "Switching to deterministic neuro-symbolic policy engine.",
                "tool_name": None,
                "tool_args": {},
                "final_output": None,
            }

        action = str(data.get("action", "finish")).strip().lower()
        thought = str(data.get("thought", "")).strip()
        if action == "call_tool" and data.get("tool_name"):
            return {
                "provider": provider,
                "action": "call_tool",
                "thought": thought or f"Calling {data.get('tool_name')}",
                "tool_name": str(data["tool_name"]).strip(),
                "tool_args": data.get("tool_args") or {},
                "final_output": None,
            }

        return {
            "provider": provider,
            "action": "finish",
            "thought": thought or "Synthesizing final diagnostic intervention.",
            "tool_name": None,
            "tool_args": {},
            "final_output": data.get("final_output") or data,
        }

    async def infer_question_skills(self, question_ids: List[int], db: AsyncSession):
        """
        Batch infer additional prerequisite skills for a list of questions (Q-matrix enrichment).
        """
        stmt = select(Question).where(Question.id.in_(question_ids))
        res = await db.execute(stmt)
        questions = res.scalars().all()

        if not questions:
            return

        stmt_concepts = select(Concept)
        res_concepts = await db.execute(stmt_concepts)
        all_concepts = res_concepts.scalars().all()
        concept_map = {c.name.strip().lower(): c for c in all_concepts}
        concept_names = [c.name for c in all_concepts]

        questions_data = []
        for q in questions:
            stmt_opt = select(Option).where(Option.question_id == q.id)
            res_opt = await db.execute(stmt_opt)
            options = res_opt.scalars().all()

            primary_concept = next(
                (c.name for c in all_concepts if c.id == q.concept_id), "Unknown"
            )

            questions_data.append(
                {
                    "id": q.id,
                    "text": q.text,
                    "primary_concept": primary_concept,
                    "options": [o.text for o in options],
                }
            )

        system_prompt = (
            "You are an expert in educational psychometrics and cognitive diagnosis models (DINA)."
        )
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
Questions:
{json.dumps(questions_data, indent=2)}
"""

        try:
            content = await self.get_completion(prompt, system_prompt)
            data = json.loads(content)
            inferences = data.get("inferences", [])

            for inf in inferences:
                q_id = inf.get("question_id")
                additional_skills = inf.get("additional_skills", [])

                valid_skills = []
                for skill in additional_skills:
                    s_name = skill.get("name", "").strip().lower()
                    conf = skill.get("confidence", 0)
                    if s_name in concept_map and conf >= 0.6:
                        valid_skills.append((concept_map[s_name].id, conf))

                valid_skills = valid_skills[:2]

                for c_id, conf in valid_skills:
                    stmt_upsert = (
                        insert(QuestionSkill)
                        .values(
                            question_id=q_id,
                            concept_id=c_id,
                            is_primary=False,
                            source="llm_inferred",
                            llm_confidence=conf,
                        )
                        .on_conflict_do_nothing(
                            index_elements=["question_id", "concept_id"]
                        )
                    )
                    await db.execute(stmt_upsert)

            await db.commit()
            logger.info(f"Successfully inferred skills for {len(inferences)} questions.")
        except Exception as e:
            logger.error(f"Failed to infer question skills: {e}")


llm_service = LLMService()


def get_llm_service() -> LLMService:
    return llm_service
