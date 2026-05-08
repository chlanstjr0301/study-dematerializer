"""
MVP6-Hotfix: Deterministic intent router for conversation-first Korean math tutor.

Classifies user intent from Korean/English messages before concept detection.
No LLM calls — pure rule-based.
"""
from __future__ import annotations

import re

from gonghaebun.knowledge.real_analysis import CONCEPTS, normalize_concept_id

from apps.api.services.compiler_analyzer_service import KOREAN_NAMES, REPRESENTATION_PREVIEWS

# ---------------------------------------------------------------------------
# Alias extensions (supplement knowledge base aliases)
# ---------------------------------------------------------------------------

_EXTRA_ALIASES: dict[str, list[str]] = {
    "compactness": ["컴팩트성", "콤팩트성"],
    "connectedness": [],
    "uniform_continuity": ["균등연속"],
}

# Build a reverse alias map including extras
_INTENT_ALIAS_MAP: dict[str, str] = {}
for _cid, _concept in CONCEPTS.items():
    for _alias in _concept.aliases:
        _INTENT_ALIAS_MAP[_alias.lower()] = _cid
    _INTENT_ALIAS_MAP[_cid.lower()] = _cid
for _cid, _extras in _EXTRA_ALIASES.items():
    for _alias in _extras:
        _INTENT_ALIAS_MAP[_alias.lower()] = _cid


# ---------------------------------------------------------------------------
# Korean particles for stripping
# ---------------------------------------------------------------------------

_PARTICLES = [
    "에서", "으로", "이랑", "에게",
    "을", "를", "이", "가", "은", "는", "의", "에", "도", "과", "와",
]


def _strip_particles(token: str) -> list[str]:
    results = [token]
    for p in _PARTICLES:
        if token.endswith(p) and len(token) > len(p):
            results.append(token[: -len(p)])
    return results


# ---------------------------------------------------------------------------
# Concept detection within sentences
# ---------------------------------------------------------------------------


def _detect_concepts_in_message(message: str) -> list[str]:
    """Find all concept_ids mentioned in the message (alias + particle stripping)."""
    found: dict[str, int] = {}
    msg_lower = message.lower()

    # Full message match
    cid = _INTENT_ALIAS_MAP.get(msg_lower.strip())
    if cid:
        found[cid] = found.get(cid, 0) + 3

    # N-gram alias matching (3-grams, 2-grams)
    words = message.split()
    for n in (3, 2):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i: i + n]).lower()
            cid = _INTENT_ALIAS_MAP.get(phrase)
            if cid:
                found[cid] = found.get(cid, 0) + 3

    # Single-token with particle stripping + punctuation stripping
    for word in words:
        for variant in _strip_particles(word):
            cleaned = variant.strip('?!.,;:()[]{}"\'"')
            for candidate in (variant, cleaned):
                cid = _INTENT_ALIAS_MAP.get(candidate.lower())
                if cid:
                    found[cid] = found.get(cid, 0) + 3

    # Also check normalize_concept_id for knowledge base coverage
    cid = normalize_concept_id(message.strip())
    if cid:
        found[cid] = found.get(cid, 0) + 1

    # Sort by score descending
    return sorted(found, key=lambda c: found[c], reverse=True)


# ---------------------------------------------------------------------------
# Intent patterns
# ---------------------------------------------------------------------------

_GREETING_PATTERNS = [
    r"^안녕", r"^하이$", r"^헬로", r"^반가", r"^hi$", r"^hello",
]
_GREETING_RE = re.compile("|".join(_GREETING_PATTERNS), re.IGNORECASE)

_EQUIVALENCE_PATTERNS = [
    r"이야\??$", r"인가\??$", r"인가요\??$", r"이에요\??$", r"맞아\??$",
    r"같은\s*(건|거)", r"같나요", r"같은가요",
    r"is\s+(the\s+)?same",
]
_EQUIVALENCE_RE = re.compile("|".join(_EQUIVALENCE_PATTERNS), re.IGNORECASE)

# Two aliases co-occurring (one Korean, one English or vice versa)
def _has_cross_language_aliases(message: str, concepts: list[str]) -> bool:
    """Check if message contains both Korean and English aliases for same concept."""
    if not concepts:
        return False
    cid = concepts[0]
    concept = CONCEPTS.get(cid)
    if not concept:
        return False
    all_aliases = list(concept.aliases) + _EXTRA_ALIASES.get(cid, []) + [cid]
    ko_found = False
    en_found = False
    msg_lower = message.lower()
    for alias in all_aliases:
        if alias.lower() in msg_lower:
            if re.search(r'[가-힣]', alias):
                ko_found = True
            elif re.search(r'[a-zA-Z]', alias):
                en_found = True
    return ko_found and en_found


_DEFINITION_PATTERNS = [
    r"뭐야", r"뭐지", r"뭐예요", r"뭐에요", r"뭐임", r"뭐냐", r"뭘까", r"무엇",
    r"무슨\s*(뜻|의미)", r"정의", r"what\s+is", r"define",
    r"설명해", r"설명을?\s*해", r"설명\s*좀", r"알려줘", r"알려\s*주",
]
_DEFINITION_RE = re.compile("|".join(_DEFINITION_PATTERNS), re.IGNORECASE)

_DIFFERENCE_PATTERNS = [
    r"차이", r"다른\s*(점|거|건)", r"구별", r"구분", r"비교",
    r"differ", r"vs\.?", r"versus",
]
_DIFFERENCE_RE = re.compile("|".join(_DIFFERENCE_PATTERNS), re.IGNORECASE)

_FOLLOWUP_PATTERNS = [
    r"물어보잖아", r"질문이잖아", r"대답해", r"답해",
    r"그게\s*맞", r"맞냐", r"맞아\?", r"아니야\?",
    r"다시\s*(설명|말)", r"제대로", r"좀\s*더",
    r"왜\??$", r"왜요\??$",
    r"뭐냐고", r"뭐라고", r"모르겠는데", r"더\s*자세히",
]
_FOLLOWUP_RE = re.compile("|".join(_FOLLOWUP_PATTERNS), re.IGNORECASE)

_START_STUDY_PATTERNS = [
    r"공부\s*시작", r"학습\s*시작", r"세션\s*시작", r"start\s*stud",
]
_START_STUDY_RE = re.compile("|".join(_START_STUDY_PATTERNS), re.IGNORECASE)

_START_RECALL_PATTERNS = [
    r"인출\s*연습", r"인출\s*시작", r"recall", r"quiz",
]
_START_RECALL_RE = re.compile("|".join(_START_RECALL_PATTERNS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


def classify_intent(
    message: str,
    recent_messages: list[str] | None = None,
) -> dict:
    """
    Classify user intent and detect concepts.

    Returns:
        {
            "intent": str,
            "concept_id": str | None,
            "all_concepts": list[str],
        }
    """
    msg = message.strip()

    # 0. Greeting (check BEFORE concept detection)
    if _GREETING_RE.search(msg):
        return {"intent": "greeting", "concept_id": None, "all_concepts": []}

    concepts = _detect_concepts_in_message(msg)
    primary_concept = concepts[0] if concepts else None

    # 1. Start study session
    if _START_STUDY_RE.search(msg):
        return {"intent": "start_study_session", "concept_id": primary_concept, "all_concepts": concepts}

    # 2. Start recall
    if _START_RECALL_RE.search(msg):
        return {"intent": "start_recall", "concept_id": primary_concept, "all_concepts": concepts}

    # 3. Alias equivalence question (cross-language or explicit question pattern)
    if primary_concept and (
        _has_cross_language_aliases(msg, concepts)
        or _EQUIVALENCE_RE.search(msg)
    ):
        return {"intent": "alias_equivalence_question", "concept_id": primary_concept, "all_concepts": concepts}

    # 4. Difference question (2+ concepts)
    if len(concepts) >= 2 and _DIFFERENCE_RE.search(msg):
        return {"intent": "difference_question", "concept_id": primary_concept, "all_concepts": concepts}

    # 5. Definition question (concept found in current message)
    if primary_concept and _DEFINITION_RE.search(msg):
        return {"intent": "definition_question", "concept_id": primary_concept, "all_concepts": concepts}

    # 6. Followup repair (no concept but repair cue + recent context)
    #    Checked BEFORE definition-from-context to handle "뭐냐고", "다시 설명" etc.
    if not primary_concept and _FOLLOWUP_RE.search(msg) and recent_messages:
        # Try to recover concept from recent messages
        for prev in reversed(recent_messages):
            prev_concepts = _detect_concepts_in_message(prev)
            if prev_concepts:
                return {
                    "intent": "followup_repair",
                    "concept_id": prev_concepts[0],
                    "all_concepts": prev_concepts,
                }
        return {"intent": "followup_repair", "concept_id": None, "all_concepts": []}

    # 7. Definition question without concept in message → resolve from context
    #    (after followup check so "뭐냐고" is handled as followup, not definition)
    if not primary_concept and _DEFINITION_RE.search(msg) and recent_messages:
        for prev in reversed(recent_messages):
            prev_concepts = _detect_concepts_in_message(prev)
            if prev_concepts:
                return {
                    "intent": "definition_question",
                    "concept_id": prev_concepts[0],
                    "all_concepts": prev_concepts,
                }

    # 8. Pure concept lookup (alias found, no special intent pattern)
    if primary_concept:
        return {"intent": "concept_lookup", "concept_id": primary_concept, "all_concepts": concepts}

    # 8. Unsupported
    return {"intent": "unsupported", "concept_id": None, "all_concepts": []}


# ---------------------------------------------------------------------------
# Direct answer generation
# ---------------------------------------------------------------------------

# Short Korean definitions for direct answers
_DEFINITIONS_KR: dict[str, str] = {
    "compactness": (
        "거리 공간 X의 부분집합 K가 옹골(compact)이란, "
        "K의 모든 열린 덮개가 유한 부분덮개를 가지는 것입니다. "
        "ℝⁿ에서는 Heine-Borel 정리에 의해 닫히고 유계인 것과 동치이지만, "
        "일반 공간에서는 열린 덮개 정의가 우선입니다."
    ),
    "connectedness": (
        "위상 공간 X가 연결(connected)이란, "
        "X를 두 개의 공집합이 아닌 분리된 열린 집합의 합집합으로 "
        "나타낼 수 없는 것입니다."
    ),
    "uniform_continuity": (
        "함수 f: X → Y가 균등 연속이란, "
        "∀ε>0, ∃δ>0 s.t. d(x,y)<δ ⇒ d(f(x),f(y))<ε이고, "
        "이때 δ가 x,y에 무관하게 ε에만 의존하는 것입니다."
    ),
}

_KOREAN_ALIAS_NAMES: dict[str, list[str]] = {
    "compactness": ["옹골성", "컴팩트성", "콤팩트성"],
    "connectedness": ["연결성"],
    "uniform_continuity": ["균등 연속", "균등연속"],
}


def generate_direct_answer(
    intent: str,
    concept_id: str | None,
    message: str,
    recent_messages: list[str] | None = None,
) -> str | None:
    """
    Generate a Korean direct answer for conversational intents.
    Returns None for concept_lookup / start_* / unsupported (handled by existing flow).
    """
    if intent == "greeting":
        return (
            "안녕하세요! 공해분입니다. "
            "개념 이름이나 질문을 입력하면 학습을 도와드릴게요. "
            "예: \"옹골성이 뭐야?\", \"compactness 공부 시작\""
        )

    if intent == "alias_equivalence_question" and concept_id:
        concept = CONCEPTS.get(concept_id)
        if not concept:
            return None
        ko_names = _KOREAN_ALIAS_NAMES.get(concept_id, [])
        ko_str = ", ".join(ko_names) if ko_names else KOREAN_NAMES.get(concept_id, concept_id)
        en_name = concept.canonical_name.lower()
        definition = _DEFINITIONS_KR.get(concept_id, "")
        return (
            f"네. {en_name}는 보통 한국어로 {ko_str}이라고 부릅니다. "
            f"핵심 정의: {definition}"
        )

    if intent == "definition_question" and concept_id:
        definition = _DEFINITIONS_KR.get(concept_id, "")
        ko_name = KOREAN_NAMES.get(concept_id, concept_id)
        if definition:
            return f"{ko_name}의 정의: {definition}"
        return None

    if intent == "difference_question" and concept_id:
        # Basic difference answer — could be extended with card data
        return None  # Fall through to concept_lookup behavior with both concepts shown

    if intent == "followup_repair":
        if concept_id:
            ko_name = KOREAN_NAMES.get(concept_id, concept_id)
            definition = _DEFINITIONS_KR.get(concept_id, "")
            if definition:
                return (
                    f"죄송합니다. 질문에 바로 답변하겠습니다. "
                    f"{ko_name}: {definition}"
                )
        return "죄송합니다. 이전 질문에 제대로 답하지 못했습니다. 질문을 다시 말씀해 주세요."

    return None
