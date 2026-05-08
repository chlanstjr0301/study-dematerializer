"""
MVP4-R0: Rule-based concept analyzer for chat-style Korean study compiler.

Scans user messages for concept aliases and keywords, infers knowledge gaps
from Korean cue words, and returns structured Korean analysis with
representation previews and prerequisite checks.

No LLM calls — deterministic only.
"""
from __future__ import annotations

from gonghaebun.knowledge.real_analysis import (
    CONCEPTS,
    CONCEPT_KEYWORDS,
    PREREQUISITE_EDGES,
    normalize_concept_id,
)

# ---------------------------------------------------------------------------
# Korean canonical names (extracted from existing aliases)
# ---------------------------------------------------------------------------

KOREAN_NAMES: dict[str, str] = {
    "compactness": "옹골성",
    "connectedness": "연결성",
    "uniform_continuity": "균등 연속",
    "metric_space": "거리 공간",
    "open_set": "열린 집합",
    "open_cover": "열린 덮개",
    "heine_borel": "하이네-보렐 정리",
    "sequential_compactness": "수열 옹골성",
    "continuity": "연속",
    "path_connected": "경로 연결",
}

# ---------------------------------------------------------------------------
# Gap inference cues
# ---------------------------------------------------------------------------

GAP_CUES: list[tuple[str, str]] = [
    ("모르겠", "개념의 정의를 아직 파악하지 못한 것 같습니다."),
    ("이해가 안", "개념의 직관적 이해가 부족한 것 같습니다."),
    ("이해 안", "개념의 직관적 이해가 부족한 것 같습니다."),
    ("헷갈", "유사 개념과의 구분이 명확하지 않은 것 같습니다."),
    ("증명", "증명 구조를 파악하지 못한 것 같습니다."),
    ("어떻게", "개념의 적용 방법을 모르는 것 같습니다."),
    ("왜", "개념의 필요성과 동기를 이해하지 못한 것 같습니다."),
]

DEFAULT_GAP = "이 개념에 대해 더 깊이 공부할 필요가 있습니다."

# ---------------------------------------------------------------------------
# Korean particles to strip during tokenization
# ---------------------------------------------------------------------------

_PARTICLES = [
    "에서", "으로", "이랑", "에게",
    "을", "를", "이", "가", "은", "는", "의", "에", "도", "과", "와",
]

# ---------------------------------------------------------------------------
# Representation previews (seed concepts only)
# ---------------------------------------------------------------------------

REPRESENTATION_PREVIEWS: dict[str, dict[str, str]] = {
    "compactness": {
        "intuitive": (
            "옹골 집합은 '빠져나갈 틈이 없는' 집합입니다. "
            "모든 열린 덮개에서 유한 개만 골라도 전체를 덮을 수 있습니다."
        ),
        "formal": (
            "위상 공간 X의 부분집합 K가 옹골(compact)하다 "
            "\u27FA K의 모든 열린 덮개가 유한 부분덮개를 갖는다."
        ),
        "example": (
            "반례: (0,1)은 옹골이 아닙니다. "
            "열린 덮개 {(1/n, 1) : n\u22652}은 유한 부분덮개를 갖지 않습니다."
        ),
        "proof_schema": (
            "옹골성 증명의 전형적 구조: "
            "임의의 열린 덮개를 잡고 \u2192 유한 부분덮개를 구성하거나 모순을 유도합니다."
        ),
        "misconception": (
            "흔한 오개념: '옹골 = 닫힌 + 유계'는 \u211D\u207F에서만 성립합니다 "
            "(하이네-보렐 정리). 일반 위상 공간에서는 거짓입니다."
        ),
    },
    "connectedness": {
        "intuitive": (
            "연결 집합은 '한 덩어리'인 집합입니다. "
            "두 개의 분리된 열린 집합으로 쪼갤 수 없습니다."
        ),
        "formal": (
            "위상 공간 X가 연결(connected)이다 "
            "\u27FA X를 두 개의 공집합이 아닌 분리된 열린 집합의 합집합으로 "
            "나타낼 수 없다."
        ),
        "example": (
            "반례: (0,1) \u222A (2,3)은 연결이 아닙니다. "
            "\u211D에서 구간 [0,1]은 연결입니다 (중간값 정리)."
        ),
        "proof_schema": (
            "연결성 증명의 전형적 구조: "
            "분리가 존재한다고 가정하고 \u2192 모순을 유도합니다."
        ),
        "misconception": (
            "흔한 오개념: '경로 연결 = 연결'은 거짓입니다. "
            "경로 연결은 연결보다 강한 성질이지만, "
            "위상수학자의 사인 곡선은 연결이지만 경로 연결이 아닙니다."
        ),
    },
    "uniform_continuity": {
        "intuitive": (
            "균등 연속은 '모든 점에서 같은 정도로 연속'인 것입니다. "
            "\u03B4가 점에 의존하지 않고 \u03B5에만 의존합니다."
        ),
        "formal": (
            "함수 f: X \u2192 Y가 균등 연속이다 \u27FA "
            "\u2200\u03B5>0, \u2203\u03B4>0 s.t. d(x,y)<\u03B4 \u21D2 d(f(x),f(y))<\u03B5 "
            "(\u03B4가 x,y에 무관)."
        ),
        "example": (
            "반례: f(x)=1/x는 (0,1)에서 연속이지만 균등 연속이 아닙니다. "
            "f(x)=x\u00B2는 [0,1]에서 균등 연속입니다 (옹골 집합 위 연속함수)."
        ),
        "proof_schema": (
            "균등 연속 증명의 전형적 구조: "
            "옹골 집합 위의 연속함수가 균등 연속임을 보이려면 "
            "열린 덮개 논증 또는 수열 논증을 사용합니다."
        ),
        "misconception": (
            "흔한 오개념: '연속 = 균등 연속'은 거짓입니다. "
            "핵심 차이: 연속에서 \u03B4는 점 x에 의존할 수 있지만, "
            "균등 연속에서 \u03B4는 \u03B5에만 의존해야 합니다."
        ),
    },
}

# ---------------------------------------------------------------------------
# Levenshtein edit distance (inline, no dependency)
# ---------------------------------------------------------------------------


def _edit_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return _edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[len(b)]


# ---------------------------------------------------------------------------
# Tokenization with Korean particle stripping
# ---------------------------------------------------------------------------


def _strip_particles(token: str) -> list[str]:
    """Return the token plus variants with common Korean particles stripped."""
    results = [token]
    for p in _PARTICLES:
        if token.endswith(p) and len(token) > len(p):
            results.append(token[: -len(p)])
    return results


def _tokenize(message: str) -> list[str]:
    """Split message into tokens with Korean particle variants."""
    raw_tokens = message.split()
    tokens: list[str] = []
    for t in raw_tokens:
        tokens.extend(_strip_particles(t))
    return tokens


# ---------------------------------------------------------------------------
# Concept scoring
# ---------------------------------------------------------------------------


def _score_concepts(message: str) -> dict[str, int]:
    """Score each concept_id by alias and keyword matches in the message."""
    scores: dict[str, int] = {}

    # Try full message as alias first
    full_cid = normalize_concept_id(message)
    if full_cid is not None:
        scores[full_cid] = scores.get(full_cid, 0) + 3

    # Try contiguous n-grams (bigrams, trigrams) for multi-word aliases
    raw_words = message.split()
    for n in (3, 2):
        for i in range(len(raw_words) - n + 1):
            phrase = " ".join(raw_words[i : i + n])
            cid = normalize_concept_id(phrase)
            if cid is not None:
                scores[cid] = scores.get(cid, 0) + 3

    # Single-token alias matching (with particle stripping)
    tokens = _tokenize(message)
    for token in tokens:
        cid = normalize_concept_id(token)
        if cid is not None:
            scores[cid] = scores.get(cid, 0) + 3

    # Keyword matching (low weight)
    msg_lower = message.lower()
    for cid, keywords in CONCEPT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in msg_lower:
                scores[cid] = scores.get(cid, 0) + 1

    return scores


def _fuzzy_match(message: str) -> tuple[str | None, str | None]:
    """
    Attempt fuzzy matching when exact matching fails.

    Returns (concept_id, correction_note) or (None, None).
    """
    tokens = _tokenize(message)
    # Build candidate list: all aliases + concept_ids
    candidates: dict[str, str] = {}  # alias_lower → concept_id
    for cid, concept in CONCEPTS.items():
        candidates[cid.lower()] = cid
        for alias in concept.aliases:
            candidates[alias.lower()] = cid

    best_cid: str | None = None
    best_dist = 999
    best_typo = ""
    best_correction = ""

    for token in tokens:
        t_lower = token.lower()
        if len(t_lower) < 5:
            continue
        for alias, cid in candidates.items():
            if len(alias) < 5:
                continue
            dist = _edit_distance(t_lower, alias)
            if dist <= 2 and dist < best_dist:
                best_dist = dist
                best_cid = cid
                best_typo = token
                best_correction = alias

    if best_cid is not None:
        # Find the canonical form for the correction note
        canonical = CONCEPTS[best_cid].canonical_name.lower()
        # Use concept_id if the correction alias matches it, otherwise use the alias
        display = best_cid if best_correction == best_cid else best_correction
        note = f"{best_typo}\ub294 {display}\ub85c \ud574\uc11d\ud588\uc5b4\uc694."
        return best_cid, note

    return None, None


# ---------------------------------------------------------------------------
# Gap inference
# ---------------------------------------------------------------------------


def _infer_gap(message: str) -> str:
    """Detect learning gap from Korean cue words in the message."""
    for cue, gap_text in GAP_CUES:
        if cue in message:
            return gap_text
    return DEFAULT_GAP


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


import logging as _logging

_tutor_logger = _logging.getLogger("gonghaebun.tutor")

# Patterns that indicate a question-like message (should try tutor overlay)
_QUESTION_LIKE_RE = __import__("re").compile(
    r"(\?|뭐|왜|어떻게|설명|알려|모르|증명|proof|맞아|이해|차이|비교|정리해|기록|태그|STUDY)",
    __import__("re").IGNORECASE,
)


def _is_question_like(message: str) -> bool:
    """Return True if message looks like a learning question (should try tutor)."""
    return bool(_QUESTION_LIKE_RE.search(message))


def _build_tutor_response(tutor_result) -> dict:
    """Convert a TutorResponse into the AnalyzeResponse dict format."""
    from apps.api.services.compiler_analyzer_service import KOREAN_NAMES
    concept_id = tutor_result.primary_concept
    ko_name = KOREAN_NAMES.get(concept_id, concept_id) if concept_id else None

    return {
        "language": "ko",
        "concept_id": concept_id,
        "canonical_name_ko": ko_name,
        "canonical_name_en": concept_id,
        "suspected_gap": "",
        "correction": None,
        "prerequisite_checks": [],
        "recommended_actions": [],
        "representations": None,
        "intent": "tutor_response",
        "direct_answer": tutor_result.direct_answer,
        "render_mode": "bubble",
        "llm_used": tutor_result.llm_used,
        "rag_used": tutor_result.rag_used,
        "retrieved_context": tutor_result.retrieved_context,
        "learning_task": tutor_result.learning_task,
        "misconception_tags": tutor_result.misconception_tags,
        "missing_elements": tutor_result.missing_elements,
        "study_update_candidate": (
            tutor_result.study_update_candidate.to_dict()
            if tutor_result.study_update_candidate
            else None
        ),
    }


def _resolve_active_concept(recent_messages: list[str] | None) -> str | None:
    """Find the most recent concept_id from conversation history."""
    if not recent_messages:
        return None
    for prev in reversed(recent_messages):
        scores = _score_concepts(prev)
        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        cid, _ = _fuzzy_match(prev)
        if cid:
            return cid
    return None


def analyze_message(
    message: str,
    source_id: str | None = None,
    recent_messages: list[str] | None = None,
) -> dict:
    """
    Rule-based concept analysis from a Korean/English user message.

    Returns dict matching AnalyzeResponse schema.
    """
    from apps.api.services.intent_router import classify_intent, generate_direct_answer

    message = message.strip()
    if not message:
        resp = _no_match_response(correction=None)
        resp["intent"] = "unsupported"
        resp["direct_answer"] = None
        resp["render_mode"] = "card"
        return resp

    # 0. Classify intent first (conversation-first)
    intent_result = classify_intent(message, recent_messages)
    intent = intent_result["intent"]
    intent_concept_id = intent_result["concept_id"]

    # Greeting → immediate bubble response (no concept search needed)
    if intent == "greeting":
        direct_answer = generate_direct_answer(intent, None, message, recent_messages)
        resp = _no_match_response(correction=None)
        resp["intent"] = "greeting"
        resp["direct_answer"] = direct_answer
        resp["render_mode"] = "bubble"
        return resp

    # LLM Tutor overlay: for question-like messages, try LLM first
    if _is_question_like(message):
        try:
            from apps.api.services.tutor_orchestrator_service import tutor_respond
            tutor_result = tutor_respond(
                message=message,
                recent_messages=recent_messages,
                concept_id=intent_concept_id,
                source_id=source_id,
            )
            if tutor_result and tutor_result.confidence >= 0.5:
                _tutor_logger.info(
                    "tutor_overlay_success_in_analyzer",
                    extra={"concept_id": tutor_result.primary_concept},
                )
                return _build_tutor_response(tutor_result)
        except Exception as e:
            _tutor_logger.warning(
                "tutor_overlay_fallback_in_analyzer",
                extra={"error": str(e)},
            )

    # Generate direct answer for conversational intents
    direct_answer = generate_direct_answer(intent, intent_concept_id, message, recent_messages)

    # 1. Score concepts by alias + keyword matches
    scores = _score_concepts(message)
    correction: str | None = None

    if scores:
        concept_id = max(scores, key=scores.get)  # type: ignore[arg-type]
    else:
        # 2. Fuzzy fallback
        concept_id, correction = _fuzzy_match(message)

    # Use intent router's concept if scorer didn't find one
    if concept_id is None and intent_concept_id is not None:
        concept_id = intent_concept_id

    if concept_id is None:
        resp = _no_match_response(correction=None)
        resp["intent"] = intent
        resp["direct_answer"] = direct_answer
        resp["render_mode"] = "bubble" if direct_answer else "card"
        return resp

    # 3. Build response
    concept = CONCEPTS[concept_id]
    korean_name = KOREAN_NAMES.get(concept_id, concept.canonical_name)

    # Prerequisites
    prereq_ids = PREREQUISITE_EDGES.get(concept_id, [])
    prereq_checks = []
    for pid in prereq_ids:
        prereq_concept = CONCEPTS.get(pid)
        if prereq_concept is None:
            continue
        prereq_checks.append({
            "concept_id": pid,
            "name_ko": KOREAN_NAMES.get(pid, prereq_concept.canonical_name),
            "name_en": prereq_concept.canonical_name,
            "status": "\ubbf8\ud655\uc778",
        })

    # Representations (seed concepts only)
    representations = REPRESENTATION_PREVIEWS.get(concept_id)

    # Recommended actions
    actions = [
        {
            "action_id": "view_representations",
            "label_ko": "5\uac00\uc9c0 \ud45c\ud604 \ubcf4\uae30",
            "description_ko": f"{korean_name}\uc758 \uc9c1\uad00\xb7\uc815\uc758\xb7\uc608\uc2dc\xb7\uc99d\uba85\uad6c\uc870\xb7\uc624\uac1c\ub150\uc744 \ud655\uc778\ud569\ub2c8\ub2e4.",
            "route": None,
        },
        {
            "action_id": "recall_practice",
            "label_ko": "\uc778\ucd9c \uc5f0\uc2b5 \uc2dc\uc791",
            "description_ko": f"{korean_name}\uc5d0 \ub300\ud55c \uc778\ucd9c \uc5f0\uc2b5\uc744 \uc2dc\uc791\ud569\ub2c8\ub2e4.",
            "route": f"/recall?concept={concept_id}",
        },
        {
            "action_id": "view_prerequisites",
            "label_ko": "\uc120\ud589\uac1c\ub150 \ubaa9\ub85d \ubcf4\uae30",
            "description_ko": f"{korean_name}\uc744(\ub97c) \uc774\ud574\ud558\uae30 \uc704\ud574 \ud544\uc694\ud55c \uc120\ud589\uac1c\ub150\uc785\ub2c8\ub2e4.",
            "route": None,
        },
    ]

    # Determine render mode: bubble for direct-answer intents, card for concept_lookup
    if intent in ("definition_question", "alias_equivalence_question", "followup_repair") and direct_answer:
        render_mode = "bubble"
    else:
        render_mode = "card"

    return {
        "language": "ko",
        "concept_id": concept_id,
        "canonical_name_ko": korean_name,
        "canonical_name_en": concept.canonical_name,
        "suspected_gap": _infer_gap(message),
        "correction": correction,
        "prerequisite_checks": prereq_checks,
        "recommended_actions": actions,
        "representations": representations,
        "intent": intent,
        "direct_answer": direct_answer,
        "render_mode": render_mode,
    }


def _no_match_response(correction: str | None) -> dict:
    """Build response when no concept could be matched."""
    return {
        "language": "ko",
        "concept_id": None,
        "canonical_name_ko": None,
        "canonical_name_en": None,
        "suspected_gap": (
            "\ud574\ub2f9 \uac1c\ub150\uc744 \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. "
            "\ud604\uc7ac \uc9c0\uc6d0\ud558\ub294 \uac1c\ub150: "
            "\uc639\uace8\uc131(compactness), "
            "\uc5f0\uacb0\uc131(connectedness), "
            "\uade0\ub4f1 \uc5f0\uc18d(uniform continuity)"
        ),
        "correction": correction,
        "prerequisite_checks": [],
        "recommended_actions": [],
        "representations": None,
    }
