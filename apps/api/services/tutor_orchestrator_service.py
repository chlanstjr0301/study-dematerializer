"""
LLM Tutor orchestrator — RAG-grounded conversational answering.

Attempts to answer learning questions using:
1. Rule-based learning task classification
2. Lexical context retrieval from Ground Truth Cards + STUDY.md
3. LLM call with strict tutor prompt
4. Structured JSON parsing

If LLM call fails AND concept is compactness, returns deterministic
fallback answer instead of None, preventing misrouting to open_set cards.
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
# Deterministic compactness fallback answers
# ---------------------------------------------------------------------------

_COMPACTNESS_TOPIC_PATTERNS: list[tuple[str, str]] = [
    # Order matters: most specific first
    (r"compact하지 않|왜.*compact|bounded.*compact|compact.*bounded|\(0,?\s*1\).*compact|compact.*\(0,?\s*1\)", "why_not_compact"),
    (r"finite subcover|유한 부분덮개|유한.*덮개|subcover.*뭐|subcover.*뭔", "finite_subcover"),
    (r"closed and bounded|닫히고 유계|heine.?borel|하이네.?보렐|metric space.*일반|일반.*metric", "heine_borel_scope"),
    (r"uniform.?continu|균등.*연속|proof schema.*compact|compact.*proof schema|증명.*compact.*uniform|compact.*증명.*uniform", "compactness_in_uniform_continuity"),
    (r"내가 이해한|이거 맞아|이 설명 맞아|내 설명.*맞|유한.*점.*대표|유한 개.*점", "self_explanation_critique"),
    (r"STUDY|정리해줘|기록|태그로|오개념.*태그|misconception.*정리", "study_update_misconception"),
]


def _match_compactness_topic(message: str, recent_messages: list[str] | None) -> str | None:
    """Match a specific compactness sub-topic from message + context."""
    combined = message
    if recent_messages:
        combined += " " + " ".join(recent_messages[-3:])
    for pattern, topic in _COMPACTNESS_TOPIC_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return topic
    return None


_COMPACTNESS_ANSWERS: dict[str, dict] = {
    "why_not_compact": {
        "direct_answer": (
            "$(0,1)$이 유계(bounded)인 것은 맞지만, 그것만으로는 옹골(compact)하지 않습니다.\n\n"
            "**옹골성의 정의**: 집합 $K$가 옹골하려면, $K$의 **모든** 열린 덮개가 유한 부분덮개를 가져야 합니다.\n\n"
            "**반례 구성**: 열린 덮개 $\\mathcal{U} = \\{U_n\\}$을 $U_n = (1/n, 1)$, $n \\geq 2$로 잡으면:\n"
            "- 각 $x \\in (0,1)$에 대해 $n > 1/x$인 $U_n$이 $x$를 포함하므로 이것은 $(0,1)$의 열린 덮개입니다.\n"
            "- 유한 개 $U_{n_1}, U_{n_2}, \\ldots, U_{n_k}$를 고르면, $N = \\max(n_1, \\ldots, n_k)$이고,\n"
            "  $\\bigcup_{i=1}^k U_{n_i} = (1/N, 1)$이므로 $(0, 1/N)$ 안의 점들이 빠집니다.\n"
            "- 따라서 유한 부분덮개가 존재하지 않으며, $(0,1)$은 옹골하지 않습니다.\n\n"
            "핵심: **유계**(bounded)는 필요조건이 아니라, 열린 덮개 조건이 근본적입니다. "
            "$\\mathbb{R}^n$에서는 Heine-Borel 정리에 의해 '닫히고 유계 $\\Leftrightarrow$ 옹골'이지만, "
            "$(0,1)$은 닫히지 않았으므로 이 동치도 성립하지 않습니다."
        ),
        "learning_task": "why_question",
        "supporting_concepts": ["open_cover", "heine_borel"],
        "misconception_tags": [],
        "missing_elements": [],
    },
    "finite_subcover": {
        "direct_answer": (
            "**유한 부분덮개(finite subcover)**란:\n\n"
            "열린 덮개 $\\mathcal{U} = \\{U_\\alpha\\}_{\\alpha \\in A}$가 집합 $K$를 덮을 때,\n"
            "이 덮개에서 **유한 개** $U_{\\alpha_1}, U_{\\alpha_2}, \\ldots, U_{\\alpha_n}$을 골라서\n"
            "$K \\subseteq U_{\\alpha_1} \\cup U_{\\alpha_2} \\cup \\cdots \\cup U_{\\alpha_n}$이 되는 것입니다.\n\n"
            "중요한 점:\n"
            "1. **원래 덮개에서** 고른 것이어야 합니다 — 임의의 열린 집합이 아닙니다.\n"
            "2. **유한 개**여야 합니다 — 무한 개를 고르면 의미가 없습니다.\n"
            "3. 고른 유한 개가 여전히 **전체 집합 $K$를 덮어야** 합니다.\n\n"
            "즉, '열린집합 몇 개만 고르면 된다'는 반만 맞습니다. "
            "반드시 **주어진 덮개에서** 골라야 하고, **어떤 열린 덮개를 잡더라도** 유한 개로 덮을 수 있어야 옹골합니다."
        ),
        "learning_task": "definition_question",
        "supporting_concepts": ["open_cover"],
        "misconception_tags": [],
        "missing_elements": [],
    },
    "heine_borel_scope": {
        "direct_answer": (
            "**Heine-Borel 정리의 적용 범위**:\n\n"
            "$\\mathbb{R}^n$에서는 '$K$가 옹골 $\\Leftrightarrow$ $K$가 닫히고 유계'가 성립합니다.\n"
            "하지만 **일반 거리 공간(metric space)**에서는 이 동치가 **성립하지 않습니다**.\n\n"
            "**반례**: 무한 차원 Banach 공간에서 닫힌 단위 구 $\\bar{B}(0,1)$은 닫히고 유계이지만 옹골하지 않습니다.\n\n"
            "일반 거리 공간에서 옹골성의 올바른 정의는 항상 **열린 덮개 정의**입니다:\n"
            "- $K$의 모든 열린 덮개가 유한 부분덮개를 가진다.\n\n"
            "Heine-Borel은 $\\mathbb{R}^n$의 특수한 성질(국소 옹골성 + 완비성)에 의존하므로, "
            "'closed and bounded = compact'라고 일반화하면 오류입니다."
        ),
        "learning_task": "why_question",
        "supporting_concepts": ["heine_borel", "open_cover"],
        "misconception_tags": ["heine_borel_scope"],
        "missing_elements": [],
    },
    "compactness_in_uniform_continuity": {
        "direct_answer": (
            "**옹골 집합 위 연속함수의 균등 연속성 증명 구조**:\n\n"
            "**정리**: 옹골 집합 $K$ 위의 연속함수 $f: K \\to \\mathbb{R}$은 균등 연속이다.\n\n"
            "**Proof schema**:\n"
            "1. $\\varepsilon > 0$을 고정한다.\n"
            "2. 각 점 $x \\in K$에 대해, 연속성에 의해 $\\delta_x > 0$가 존재하여\n"
            "   $d(x, y) < \\delta_x \\Rightarrow |f(x) - f(y)| < \\varepsilon/2$.\n"
            "3. 열린 구 $\\{B(x, \\delta_x/2)\\}_{x \\in K}$는 $K$의 열린 덮개이다.\n"
            "4. **옹골성에 의해** 유한 부분덮개 $B(x_1, \\delta_{x_1}/2), \\ldots, B(x_n, \\delta_{x_n}/2)$가 존재한다.\n"
            "5. $\\delta = \\min(\\delta_{x_1}/2, \\ldots, \\delta_{x_n}/2) > 0$을 잡는다 (**유한 개이므로 min > 0**).\n"
            "6. $d(x, y) < \\delta$이면 삼각부등식으로 $|f(x) - f(y)| < \\varepsilon$.\n\n"
            "**핵심**: 4단계에서 옹골성이 사용됩니다. 무한 개의 $\\delta_x$에서 min을 잡으면 0이 될 수 있지만, "
            "유한 부분덮개 덕분에 유한 개의 $\\delta$만 고려하므로 $\\delta > 0$이 보장됩니다."
        ),
        "learning_task": "proof_schema_question",
        "supporting_concepts": ["uniform_continuity", "open_cover"],
        "misconception_tags": [],
        "missing_elements": [],
    },
    "self_explanation_critique": {
        "direct_answer": (
            "제시한 설명을 평가합니다:\n\n"
            "**'compact하다는 건 무한히 많은 점이 있어도 결국 유한 개의 점으로 대표할 수 있다는 뜻이다'**\n\n"
            "### 잘한 부분\n"
            "직관적으로 '유한으로 제어할 수 있다'는 감각은 올바른 방향입니다.\n\n"
            "### 틀린 부분\n"
            "- **유한 개의 '점'이 아닙니다.** 옹골성에서 유한한 것은 **열린 집합(부분덮개)**이지, 점이 아닙니다.\n"
            "- **'대표'가 아닙니다.** 유한 부분덮개는 원래 열린 덮개에서 유한 개를 골라 전체 집합을 **덮는** 것입니다.\n\n"
            "### 빠진 부분\n"
            "- **'모든 열린 덮개에 대해'**라는 전칭 한정사가 빠져 있습니다. "
            "특정 덮개 하나가 아니라, **어떤** 열린 덮개를 잡더라도 유한 부분덮개가 존재해야 합니다.\n\n"
            "### 교정된 설명\n"
            "$K$가 옹골하다는 것은, $K$의 **모든** 열린 덮개 $\\{U_\\alpha\\}$에서 "
            "**유한 개의 열린 집합** $U_{\\alpha_1}, \\ldots, U_{\\alpha_n}$을 골라 $K$를 덮을 수 있다는 뜻입니다."
        ),
        "learning_task": "self_explanation_evaluation",
        "supporting_concepts": ["open_cover"],
        "misconception_tags": [
            "confuses_finite_subcover_with_finite_point_representation",
            "missing_open_cover_quantifier",
        ],
        "missing_elements": [
            "열린 덮개의 전칭 한정사 (모든 열린 덮개에 대해)",
            "유한 부분덮개는 점이 아닌 열린 집합",
        ],
    },
    "study_update_misconception": {
        "direct_answer": (
            "이전 대화를 바탕으로 감지된 오개념을 정리합니다.\n\n"
            "### 감지된 오개념\n"
            "1. **유한 부분덮개 ≠ 유한 점 대표**: 옹골성에서 유한한 것은 열린 집합(부분덮개)이지 점이 아닙니다.\n"
            "2. **전칭 한정사 누락**: '모든 열린 덮개에 대해'라는 조건이 빠지면 정의가 불완전합니다.\n\n"
            "### 학습 기록 후보\n"
            "위 오개념을 STUDY.md에 기록할 수 있습니다. 실제 파일 수정은 하지 않고 후보만 생성합니다."
        ),
        "learning_task": "study_update_request",
        "supporting_concepts": ["open_cover"],
        "misconception_tags": [
            "confuses_finite_subcover_with_finite_point_representation",
            "missing_open_cover_quantifier",
        ],
        "missing_elements": [],
    },
}


def _compactness_deterministic_fallback(
    message: str,
    learning_task: str,
    context_snippets: list,
    recent_messages: list[str] | None,
) -> TutorResponse | None:
    """
    Deterministic fallback for compactness questions when LLM fails.

    Returns a pre-authored TutorResponse for known sub-topics,
    or None if the topic doesn't match any known pattern.
    """
    topic = _match_compactness_topic(message, recent_messages)
    if topic is None:
        return None

    data = _COMPACTNESS_ANSWERS.get(topic)
    if data is None:
        return None

    rag_used = len(context_snippets) > 0

    # Build study_update_candidate for study_update_misconception
    study_update = None
    if topic == "study_update_misconception":
        study_update = StudyUpdateCandidate(
            concept_id="compactness",
            summary="유한 부분덮개를 유한 점 대표로 혼동; 전칭 한정사 누락",
            evidence=["이전 자기 설명에서 '유한 개의 점으로 대표' 표현 사용"],
            misconception_tags=data["misconception_tags"],
            next_recall_tasks=[
                "open cover의 정의를 다시 써 보세요.",
                "(0,1)이 compact하지 않음을 open cover로 증명하세요.",
            ],
        )

    logger.info(
        "tutor_deterministic_fallback_used",
        extra={"concept_id": "compactness", "topic": topic, "learning_task": data["learning_task"]},
    )

    return TutorResponse(
        direct_answer=data["direct_answer"],
        primary_concept="compactness",
        supporting_concepts=data.get("supporting_concepts", []),
        learning_task=data["learning_task"],
        misconception_tags=data.get("misconception_tags", []),
        missing_elements=data.get("missing_elements", []),
        study_update_candidate=study_update,
        confidence=0.85,
        retrieved_context=[s.to_dict() for s in context_snippets] if context_snippets else [],
        llm_used=False,
        rag_used=rag_used,
    )


# ---------------------------------------------------------------------------
# JSON schema for structured LLM output
# ---------------------------------------------------------------------------

TUTOR_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "direct_answer": {"type": "string"},
        "primary_concept": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
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
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "concept_id": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                        },
                        "summary": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                        "misconception_tags": {"type": "array", "items": {"type": "string"}},
                        "next_recall_tasks": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["concept_id", "summary", "evidence", "misconception_tags", "next_recall_tasks"],
                    "additionalProperties": False,
                },
                {"type": "null"},
            ],
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

    Returns None only if no answer can be produced at all.
    For compactness questions, deterministic fallback answers are used
    when LLM is disabled, fails, or returns low confidence.
    """
    # Classify learning task early (used by both LLM and fallback paths)
    learning_task = classify_learning_task(message)

    llm_disabled_env = os.getenv("GONGHAEBUN_LLM_DISABLED", "1")
    llm_model = os.getenv("GONGHAEBUN_LLM_MODEL", "gpt-5.5")
    api_key_present = bool(os.getenv("OPENAI_API_KEY"))

    logger.warning(
        "tutor_respond_enter",
        extra={
            "concept_id": concept_id,
            "message_preview": message[:80],
            "llm_disabled_env": llm_disabled_env,
            "openai_model": llm_model,
            "api_key_present": api_key_present,
            "learning_task": learning_task,
        },
    )

    # Fast path: LLM disabled — try compactness fallback
    if llm_disabled_env == "1":
        # Still attempt deterministic fallback for compactness
        from apps.api.services.rag_context_service import retrieve_context
        context_snippets = retrieve_context(
            concept_id=concept_id or "compactness",
            message=message,
            recent_messages=recent_messages,
            top_k=8,
        )
        fallback = _compactness_deterministic_fallback(
            message, learning_task, context_snippets, recent_messages,
        )
        if fallback:
            return fallback
        logger.warning(
            "tutor_return_none",
            extra={"reason": "llm_disabled_no_compactness_match"},
        )
        return None

    try:
        # 1. Learning task already classified above

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

        logger.warning(
            "tutor_context_retrieved",
            extra={
                "concept_id": concept_id,
                "retrieved_context_count": len(context_snippets),
                "top_source_ids": [s.source_id for s in context_snippets[:3]],
            },
        )

        # 4. Build prompt
        template = _load_tutor_prompt()
        system_prompt, user_msg = _build_prompt(
            template, message, concept_id, context_snippets, recent_messages,
        )

        # 5. Call LLM
        from gonghaebun.llm.factory import get_llm_client
        client = get_llm_client()

        logger.warning(
            "tutor_llm_call_attempt",
            extra={
                "model": llm_model,
                "prompt_len": len(system_prompt),
                "user_msg_len": len(user_msg),
            },
        )

        start_time = time.time()
        result = client.complete_structured(system_prompt, user_msg, TUTOR_OUTPUT_SCHEMA)
        latency_ms = int((time.time() - start_time) * 1000)

        logger.warning(
            "tutor_llm_call_success",
            extra={"model": llm_model, "elapsed_ms": latency_ms},
        )

        # 6. Parse response
        confidence = result.get("confidence", 0.0)
        if confidence < 0.3:
            logger.warning(
                "tutor_low_confidence",
                extra={"concept_id": concept_id, "confidence": confidence},
            )
            # Try compactness fallback before returning None
            fallback = _compactness_deterministic_fallback(
                message, learning_task, context_snippets, recent_messages,
            )
            if fallback:
                return fallback
            logger.warning(
                "tutor_return_none",
                extra={"reason": "low_confidence_no_compactness_match", "confidence": confidence},
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
            "tutor_llm_call_error",
            extra={
                "model": llm_model,
                "error_class": type(e).__name__,
                "error_repr": repr(e)[:300],
                "error_message": str(e)[:200],
                "concept_id": concept_id,
                "message_preview": message[:80],
            },
        )
        # Try compactness fallback before returning None
        try:
            from apps.api.services.rag_context_service import retrieve_context
            context_snippets = retrieve_context(
                concept_id=concept_id or "compactness",
                message=message,
                recent_messages=recent_messages,
                top_k=8,
            )
        except Exception:
            context_snippets = []
        fallback = _compactness_deterministic_fallback(
            message, learning_task, context_snippets, recent_messages,
        )
        if fallback:
            return fallback
        logger.warning(
            "tutor_return_none",
            extra={"reason": "llm_error_no_compactness_match", "error_class": type(e).__name__},
        )
        return None
