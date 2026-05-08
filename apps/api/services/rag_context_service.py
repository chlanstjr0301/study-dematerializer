"""
Lightweight lexical retrieval for LLM tutor grounding context.

Gathers relevant snippets from Ground Truth Cards, STUDY.md, and representation
previews. Uses keyword overlap scoring — no embedding DB required.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass

from apps.api.services.card_service import CardNotFoundError, load_ground_truth_card
from apps.api.services.compiler_analyzer_service import KOREAN_NAMES, REPRESENTATION_PREVIEWS
from apps.api.services.study_md_service import read_study_md

logger = logging.getLogger("gonghaebun.tutor.rag")

# ---------------------------------------------------------------------------
# Korean particles for token normalization
# ---------------------------------------------------------------------------

_PARTICLES = [
    "에서", "으로", "이랑", "에게",
    "을", "를", "이", "가", "은", "는", "의", "에", "도", "과", "와",
]


def _tokenize(text: str) -> set[str]:
    """Tokenize text into a set of normalized tokens (lowercased, particles stripped)."""
    tokens: set[str] = set()
    for word in text.lower().split():
        tokens.add(word)
        for p in _PARTICLES:
            if word.endswith(p) and len(word) > len(p):
                tokens.add(word[: -len(p)])
    # Also add longer substrings for Korean compound matching
    return tokens


def _score_overlap(query_tokens: set[str], text: str) -> float:
    """Score a text snippet by keyword overlap with query tokens."""
    if not query_tokens or not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for t in query_tokens if t in text_lower and len(t) >= 2)
    return hits / max(len(query_tokens), 1)


# ---------------------------------------------------------------------------
# Context snippet model
# ---------------------------------------------------------------------------


@dataclass
class ContextSnippet:
    source_id: str
    source_type: str  # ground_truth_card | study_md | representation_preview | rubric
    title: str
    text: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Retrieval from Ground Truth Card
# ---------------------------------------------------------------------------


def _retrieve_from_card(concept_id: str, query_tokens: set[str]) -> list[ContextSnippet]:
    """Extract snippets from a Ground Truth Card."""
    snippets: list[ContextSnippet] = []
    try:
        card = load_ground_truth_card(concept_id)
    except (CardNotFoundError, Exception):
        return snippets

    # Definition
    def_text = card.definition_card.statement
    if card.definition_card.statement_kr:
        def_text = f"{card.definition_card.statement_kr}\n{card.definition_card.statement}"
    snippets.append(ContextSnippet(
        source_id=f"card:{concept_id}:definition",
        source_type="ground_truth_card",
        title=f"{KOREAN_NAMES.get(concept_id, concept_id)} 정의",
        text=def_text,
        score=_score_overlap(query_tokens, def_text) + 0.3,  # boost definitions
    ))

    # Intuitive
    intuit_text = card.intuitive_card.explanation_kr or card.intuitive_card.explanation
    snippets.append(ContextSnippet(
        source_id=f"card:{concept_id}:intuitive",
        source_type="ground_truth_card",
        title=f"{KOREAN_NAMES.get(concept_id, concept_id)} 직관적 설명",
        text=intuit_text,
        score=_score_overlap(query_tokens, intuit_text),
    ))

    # Counterexamples
    for i, ce in enumerate(card.counterexample_cards):
        ce_text = f"{ce.statement}\n{ce.explanation}"
        snippets.append(ContextSnippet(
            source_id=f"card:{concept_id}:counterexample:{ce.example_id}",
            source_type="ground_truth_card",
            title=f"반례: {ce.example_id}",
            text=ce_text,
            score=_score_overlap(query_tokens, ce_text),
        ))

    # Proof schema
    ps = card.proof_schema_card
    # proof_steps may be list[str] or list[object] depending on model version
    step_lines = []
    for i, step in enumerate(ps.proof_steps, 1):
        if isinstance(step, str):
            step_lines.append(f"{i}. {step}")
        else:
            step_lines.append(f"{getattr(step, 'step_number', i)}. {getattr(step, 'description', str(step))}")
    ps_text = f"{ps.theorem}\n" + "\n".join(step_lines)
    snippets.append(ContextSnippet(
        source_id=f"card:{concept_id}:proof_schema",
        source_type="ground_truth_card",
        title=f"증명 구조: {ps.theorem[:50]}",
        text=ps_text,
        score=_score_overlap(query_tokens, ps_text),
    ))

    # Misconceptions
    for mc in card.misconception_cards:
        mc_text = f"주장: {mc.claim}\n진위: {'참' if mc.truth_value else '거짓'}\n교정: {mc.correction}"
        snippets.append(ContextSnippet(
            source_id=f"card:{concept_id}:misconception:{mc.misconception_id}",
            source_type="ground_truth_card",
            title=f"오개념: {mc.misconception_id}",
            text=mc_text,
            score=_score_overlap(query_tokens, mc_text),
        ))

    return snippets


# ---------------------------------------------------------------------------
# Retrieval from STUDY.md
# ---------------------------------------------------------------------------


def _retrieve_from_study_md(concept_id: str | None, query_tokens: set[str]) -> list[ContextSnippet]:
    """Extract relevant lines from STUDY.md for learner state context."""
    snippets: list[ContextSnippet] = []
    content = read_study_md()
    if not content:
        return snippets

    # If concept_id is known, extract its section
    if concept_id:
        pattern = rf"## {re.escape(concept_id)}.*?(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            section = match.group(0)
            snippets.append(ContextSnippet(
                source_id=f"study_md:{concept_id}",
                source_type="study_md",
                title=f"STUDY.md — {concept_id} 학습 상태",
                text=section[:1000],  # Limit size
                score=_score_overlap(query_tokens, section) + 0.1,
            ))

    return snippets


# ---------------------------------------------------------------------------
# Retrieval from representation previews
# ---------------------------------------------------------------------------


def _retrieve_from_previews(concept_id: str, query_tokens: set[str]) -> list[ContextSnippet]:
    """Extract representation previews as context snippets."""
    snippets: list[ContextSnippet] = []
    previews = REPRESENTATION_PREVIEWS.get(concept_id)
    if not previews:
        return snippets

    for rep_type, text in previews.items():
        snippets.append(ContextSnippet(
            source_id=f"preview:{concept_id}:{rep_type}",
            source_type="representation_preview",
            title=f"{KOREAN_NAMES.get(concept_id, concept_id)} — {rep_type}",
            text=text,
            score=_score_overlap(query_tokens, text),
        ))

    return snippets


# ---------------------------------------------------------------------------
# Main retrieval function
# ---------------------------------------------------------------------------


def retrieve_context(
    concept_id: str | None,
    message: str,
    recent_messages: list[str] | None = None,
    top_k: int = 8,
) -> list[ContextSnippet]:
    """
    Gather relevant context for a learning question.

    Sources (in priority order):
    1. Ground Truth Card (if concept_id resolved)
    2. STUDY.md learner state
    3. Representation previews

    Returns top_k snippets sorted by score descending.
    """
    # Build query tokens from message + recent context
    query_text = message
    if recent_messages:
        query_text += " " + " ".join(recent_messages[-3:])
    query_tokens = _tokenize(query_text)

    all_snippets: list[ContextSnippet] = []

    if concept_id:
        all_snippets.extend(_retrieve_from_card(concept_id, query_tokens))
        all_snippets.extend(_retrieve_from_previews(concept_id, query_tokens))

    all_snippets.extend(_retrieve_from_study_md(concept_id, query_tokens))

    # Sort by score descending, take top_k
    all_snippets.sort(key=lambda s: s.score, reverse=True)

    result = all_snippets[:top_k]
    logger.info(
        "rag_retrieve",
        extra={
            "concept_id": concept_id,
            "snippet_count": len(result),
            "top_score": result[0].score if result else 0.0,
        },
    )
    return result
