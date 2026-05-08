"""
LLM Tutor orchestrator — RAG-grounded conversational answering.

Attempts to answer learning questions using:
1. Rule-based learning task classification
2. Lexical context retrieval from Ground Truth Cards + STUDY.md
3. LLM call with strict tutor prompt
4. Structured JSON parsing

Returns None if LLM is disabled, concept is unresolvable, or call fails.
Caller falls back to existing deterministic flow.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("gonghaebun.tutor")

# ---------------------------------------------------------------------------
# Tutor response model
# ---------------------------------------------------------------------------


@dataclass
class StudyUpdateCandidate:
    concept_id: str | None = None
    summary: str = ""
    evidence: list[str] = field(default_factory=list)
    misconception_tags: list[str] = field(default_factory=list)
    next_recall_tasks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "summary": self.summary,
            "evidence": self.evidence,
            "misconception_tags": self.misconception_tags,
            "next_recall_tasks": self.next_recall_tasks,
        }


@dataclass
class TutorResponse:
    direct_answer: str
    primary_concept: str | None
    supporting_concepts: list[str] = field(default_factory=list)
    learning_task: str = "definition_question"
    misconception_tags: list[str] = field(default_factory=list)
    missing_elements: list[str] = field(default_factory=list)
    study_update_candidate: StudyUpdateCandidate | None = None
    confidence: float = 0.5
    retrieved_context: list[dict] = field(default_factory=list)
    llm_used: bool = True
    rag_used: bool = True


# ---------------------------------------------------------------------------
# Learning task classification (rule-based)
# ---------------------------------------------------------------------------

_TASK_PATTERNS: list[tuple[str, str]] = [
    (r"증명|proof|proof schema", "proof_schema_question"),
    (r"내가 이해한|이거 맞아|이 설명 맞아|내 설명", "self_explanation_evaluation"),
    (r"STUDY\.md|정리해줘|기록|태그로|메모", "study_update_request"),
    (r"왜|어떻게|how|why|이유", "why_question"),
    (r"차이|비교|다른\s*점|vs", "comparison_question"),
    (r"뭐야|뭐임|뭐냐|뭘까|무엇|정의|define|what\s+is", "definition_question"),
    (r"다시|뭐냐고|모르겠|설명해|알려", "followup_clarification"),
]


def classify_learning_task(message: str) -> str:
    """Classify the user's learning task from message content."""
    for pattern, task in _TASK_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            return task
    return "followup_clarification"


# ---------------------------------------------------------------------------
# JSON schema for structured LLM output
# ---------------------------------------------------------------------------

TUTOR_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "direct_answer": {"type": "string"},
        "primary_concept": {"type": ["string", "null"]},
        "supporting_concepts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "learning_task": {"type": "string"},
        "misconception_tags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "missing_elements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "study_update_candidate": {
            "type": ["object", "null"],
            "properties": {
                "concept_id": {"type": ["string", "null"]},
                "summary": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "misconception_tags": {"type": "array", "items": {"type": "string"}},
                "next_recall_tasks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["concept_id", "summary", "evidence", "misconception_tags", "next_recall_tasks"],
        },
        "confidence": {"type": "number"},
    },
    "required": [
        "direct_answer",
        "primary_concept",
        "supporting_concepts",
        "learning_task",
        "misconception_tags",
        "missing_elements",
        "study_update_candidate",
        "confidence",
    ],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def _load_tutor_prompt() -> str:
    """Load the learning tutor prompt template."""
    prompt_path = Path(__file__).parent.parent.parent.parent / "src" / "gonghaebun" / "prompts" / "learning_tutor.txt"
    if not prompt_path.exists():
        # Fallback: try installed package
        try:
            from gonghaebun.prompts import load_prompt
            return load_prompt("learning_tutor")
        except Exception:
            raise FileNotFoundError(f"Tutor prompt not found at {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _build_prompt(
    template: str,
    message: str,
    primary_concept: str | None,
    context_snippets: list,
    recent_messages: list[str] | None,
) -> tuple[str, str]:
    """Build (system_prompt, user_message) for the LLM call."""
    # Format retrieved context
    context_text = ""
    for i, snippet in enumerate(context_snippets, 1):
        context_text += f"\n[{i}] {snippet.title}\n{snippet.text}\n"
    if not context_text:
        context_text = "(검색된 문맥 없음)"

    # Format recent messages
    recent_text = ""
    if recent_messages:
        for msg in recent_messages[-5:]:
            recent_text += f"- {msg}\n"
    if not recent_text:
        recent_text = "(이전 대화 없음)"

    # Fill template
    system_prompt = template.replace("{retrieved_context}", context_text)
    system_prompt = system_prompt.replace("{recent_messages}", recent_text)
    system_prompt = system_prompt.replace("{message}", message)
    system_prompt = system_prompt.replace("{primary_concept}", primary_concept or "(미확인)")

    return system_prompt, message


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def tutor_respond(
    message: str,
    recent_messages: list[str] | None = None,
    concept_id: str | None = None,
    source_id: str | None = None,
) -> TutorResponse | None:
    """
    Attempt LLM tutor response.

    Returns None if:
    - LLM is disabled (GONGHAEBUN_LLM_DISABLED=1)
    - LLM call fails
    - Confidence below threshold (0.3)

    Caller should fall back to deterministic flow on None.
    """
    # Fast path: LLM disabled
    if os.getenv("GONGHAEBUN_LLM_DISABLED", "1") == "1":
        return None

    logger.info(
        "tutor_overlay_attempt",
        extra={"concept_id": concept_id, "message_len": len(message)},
    )

    try:
        # 1. Classify learning task
        learning_task = classify_learning_task(message)

        # 2. Resolve concept if not provided
        if not concept_id:
            from apps.api.services.intent_router import _detect_concepts_in_message
            concepts = _detect_concepts_in_message(message)
            if concepts:
                concept_id = concepts[0]
            elif recent_messages:
                # Try recent messages
                for prev in reversed(recent_messages):
                    prev_concepts = _detect_concepts_in_message(prev)
                    if prev_concepts:
                        concept_id = prev_concepts[0]
                        break

        # 3. Retrieve context
        from apps.api.services.rag_context_service import retrieve_context
        context_snippets = retrieve_context(
            concept_id=concept_id,
            message=message,
            recent_messages=recent_messages,
            top_k=8,
        )
        rag_used = len(context_snippets) > 0

        # 4. Build prompt
        template = _load_tutor_prompt()
        system_prompt, user_msg = _build_prompt(
            template, message, concept_id, context_snippets, recent_messages,
        )

        # 5. Call LLM
        from gonghaebun.llm.factory import get_llm_client
        client = get_llm_client()

        start_time = time.time()
        result = client.complete_structured(system_prompt, user_msg, TUTOR_OUTPUT_SCHEMA)
        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "llm_call_success",
            extra={"concept_id": concept_id, "latency_ms": latency_ms},
        )

        # 6. Parse response
        confidence = result.get("confidence", 0.0)
        if confidence < 0.3:
            logger.info(
                "tutor_overlay_low_confidence",
                extra={"concept_id": concept_id, "confidence": confidence},
            )
            return None

        # Build study_update_candidate if present
        suc_data = result.get("study_update_candidate")
        study_update = None
        if suc_data and isinstance(suc_data, dict):
            study_update = StudyUpdateCandidate(
                concept_id=suc_data.get("concept_id"),
                summary=suc_data.get("summary", ""),
                evidence=suc_data.get("evidence", []),
                misconception_tags=suc_data.get("misconception_tags", []),
                next_recall_tasks=suc_data.get("next_recall_tasks", []),
            )

        tutor_response = TutorResponse(
            direct_answer=result.get("direct_answer", ""),
            primary_concept=result.get("primary_concept") or concept_id,
            supporting_concepts=result.get("supporting_concepts", []),
            learning_task=result.get("learning_task", learning_task),
            misconception_tags=result.get("misconception_tags", []),
            missing_elements=result.get("missing_elements", []),
            study_update_candidate=study_update,
            confidence=confidence,
            retrieved_context=[s.to_dict() for s in context_snippets],
            llm_used=True,
            rag_used=rag_used,
        )

        logger.info(
            "tutor_overlay_success",
            extra={
                "concept_id": concept_id,
                "confidence": confidence,
                "context_count": len(context_snippets),
                "learning_task": tutor_response.learning_task,
            },
        )

        return tutor_response

    except Exception as e:
        logger.warning(
            "tutor_overlay_fallback",
            extra={"error": str(e), "concept_id": concept_id},
        )
        return None
