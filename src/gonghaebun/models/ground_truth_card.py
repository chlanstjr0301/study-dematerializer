"""
Ground Truth Card models for MVP6 proposal alignment.

A Ground Truth Card is a deterministic, human-authored constraint document for one
concept. It constrains LLM output, evaluator rubrics, mapping tasks, and misconception
checks. The LLM should not freely invent definitions, counterexamples, proof schemas,
or grading criteria — everything must trace back to the card.

Requires pydantic (available via the [web] extra).
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

_SLUG_RE = re.compile(r"^[A-Za-z0-9_\-]+$")

MappingTaskTypeLiteral = Literal[
    "formal_to_counterexample",
    "counterexample_to_formal",
    "formal_counterexample_to_proof_schema",
]


# ---------------------------------------------------------------------------
# Sub-cards
# ---------------------------------------------------------------------------


class DefinitionCard(BaseModel):
    """Canonical formal definition."""

    statement: str
    statement_kr: str
    source_ref: str
    required_terms: list[str]

    @field_validator("required_terms")
    @classmethod
    def _terms_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_terms must not be empty")
        return v


class IntuitiveCard(BaseModel):
    """Intuitive explanation (learning aid, not scored for mastery)."""

    explanation: str
    explanation_kr: str
    analogies: list[str]


class VisualCard(BaseModel):
    """Visual representation (learning aid, not scored for mastery)."""

    description: str
    description_kr: str
    ascii_diagram: str | None = None


class CounterexampleCard(BaseModel):
    """One specific counterexample."""

    example_id: str
    statement: str
    statement_kr: str
    explanation: str
    explanation_kr: str
    source_ref: str
    required_terms: list[str]

    @field_validator("required_terms")
    @classmethod
    def _terms_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_terms must not be empty")
        return v


class ProofSchemaCard(BaseModel):
    """Proof structure for a key theorem."""

    theorem: str
    theorem_kr: str
    proof_steps: list[str]
    source_ref: str
    required_terms: list[str]

    @field_validator("proof_steps")
    @classmethod
    def _steps_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("proof_steps must not be empty")
        return v

    @field_validator("required_terms")
    @classmethod
    def _terms_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_terms must not be empty")
        return v


class MisconceptionCard(BaseModel):
    """One known misconception (or correct statement for quiz)."""

    misconception_id: str
    claim: str
    claim_kr: str
    truth_value: bool
    correction: str
    correction_kr: str
    related_counterexample: str | None = None


class AllowedMappingTask(BaseModel):
    """One mapping task template grounded in the card."""

    task_type: MappingTaskTypeLiteral
    prompt: str
    prompt_kr: str
    required_terms: list[str]
    grounding_notes: str

    @field_validator("required_terms")
    @classmethod
    def _terms_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_terms must not be empty")
        return v


# ---------------------------------------------------------------------------
# Top-level card
# ---------------------------------------------------------------------------


class GroundTruthCard(BaseModel):
    """Complete ground truth for one concept."""

    concept_id: str
    domain: str
    source_refs: list[str]
    prerequisite_concepts: list[str]
    definition_card: DefinitionCard
    intuitive_card: IntuitiveCard
    visual_card: VisualCard
    counterexample_cards: list[CounterexampleCard]
    proof_schema_card: ProofSchemaCard
    misconception_cards: list[MisconceptionCard]
    required_terms: list[str]
    allowed_mapping_tasks: list[AllowedMappingTask]
    version: str = "1.0"
    created_at: str

    # --- validators ---

    @field_validator("concept_id")
    @classmethod
    def _concept_id_is_slug(cls, v: str) -> str:
        if not v or not _SLUG_RE.match(v):
            raise ValueError(
                f"concept_id must be a non-empty slug [A-Za-z0-9_-]. Got: {v!r}"
            )
        return v

    @field_validator("prerequisite_concepts")
    @classmethod
    def _prerequisites_are_slugs(cls, v: list[str]) -> list[str]:
        for item in v:
            if not item or not _SLUG_RE.match(item):
                raise ValueError(
                    f"prerequisite_concepts entry must be a slug. Got: {item!r}"
                )
        return v

    @field_validator("counterexample_cards")
    @classmethod
    def _min_counterexamples(cls, v: list[CounterexampleCard]) -> list[CounterexampleCard]:
        if len(v) < 2:
            raise ValueError(
                f"counterexample_cards must have >= 2 entries, got {len(v)}"
            )
        return v

    @field_validator("misconception_cards")
    @classmethod
    def _min_misconceptions(cls, v: list[MisconceptionCard]) -> list[MisconceptionCard]:
        if len(v) < 3:
            raise ValueError(
                f"misconception_cards must have >= 3 entries, got {len(v)}"
            )
        return v

    @field_validator("allowed_mapping_tasks")
    @classmethod
    def _exactly_three_mappings(cls, v: list[AllowedMappingTask]) -> list[AllowedMappingTask]:
        if len(v) != 3:
            raise ValueError(
                f"allowed_mapping_tasks must have exactly 3 entries, got {len(v)}"
            )
        return v

    @field_validator("required_terms")
    @classmethod
    def _global_terms_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_terms must not be empty")
        return v

    @model_validator(mode="after")
    def _misconception_truth_values(self) -> GroundTruthCard:
        """At least one True and at least two False among misconception_cards."""
        trues = sum(1 for m in self.misconception_cards if m.truth_value)
        falses = sum(1 for m in self.misconception_cards if not m.truth_value)
        if trues < 1:
            raise ValueError(
                "misconception_cards must contain at least one True (correct) statement"
            )
        if falses < 2:
            raise ValueError(
                "misconception_cards must contain at least two False (misconception) entries"
            )
        return self

    @model_validator(mode="after")
    def _mapping_task_types_complete(self) -> GroundTruthCard:
        """All 3 mapping task types must be present."""
        types = {t.task_type for t in self.allowed_mapping_tasks}
        expected = {
            "formal_to_counterexample",
            "counterexample_to_formal",
            "formal_counterexample_to_proof_schema",
        }
        if types != expected:
            raise ValueError(
                f"allowed_mapping_tasks must cover all 3 types. "
                f"Got: {types}, expected: {expected}"
            )
        return self
