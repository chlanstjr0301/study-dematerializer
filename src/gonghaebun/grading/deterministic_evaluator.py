"""
Card-grounded deterministic evaluator for MVP6.

Evaluates learner responses against a Ground Truth Card and rubric using
term coverage + misconception detection. No LLM calls.
"""
from __future__ import annotations

import re

from gonghaebun.models.evaluation_output import EvaluationOutput
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.rubric import ConceptRubric, MisconceptionCheck, TermCheck
from gonghaebun.study_md.writer import compute_mastery_state

# ---------------------------------------------------------------------------
# Korean particle stripping
# ---------------------------------------------------------------------------

_PARTICLES = [
    "에서", "으로", "이랑", "에게",
    "을", "를", "이", "가", "은", "는", "의", "에", "도", "과", "와",
]

_SEVERITY_PENALTIES = {
    "critical": 0.15,
    "moderate": 0.10,
    "minor": 0.05,
}

_MAPPING_RECALL_TRIGGERS = {
    "formal_to_counterexample": "open cover로 (0,1)이 compact하지 않음을 설명하라.",
    "counterexample_to_formal": "반례로부터 compact 집합의 필수 성질을 도출하라.",
    "formal_counterexample_to_proof_schema": "정의와 반례를 사용하여 Heine-Borel 증명 구조를 설명하라.",
}


def _normalize(text: str) -> str:
    """Lowercase, strip Korean particles, normalize whitespace.

    Keeps mathematical notation (ε, δ, ∈, ⊂, etc.) intact.
    """
    # Lowercase English text (Korean is case-insensitive by nature)
    text = text.lower()
    # Strip Korean particles from token boundaries
    for particle in _PARTICLES:
        # Replace particle at word boundary (after Korean char) with space
        text = re.sub(rf"({particle})(?=\s|$|[^가-힣])", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _check_terms(
    normalized_response: str,
    required_terms: list[TermCheck],
) -> tuple[float, list[str]]:
    """Return (coverage_score, missing_terms)."""
    total_weight = 0.0
    matched_weight = 0.0
    missing: list[str] = []

    for tc in required_terms:
        total_weight += tc.weight
        found = any(
            alias.lower() in normalized_response
            for alias in [tc.term] + tc.aliases
        )
        if found:
            matched_weight += tc.weight
        else:
            missing.append(tc.term)

    coverage = matched_weight / total_weight if total_weight > 0 else 0.0
    return coverage, missing


def _detect_misconceptions(
    normalized_response: str,
    misconception_checks: list[MisconceptionCheck],
    card: GroundTruthCard,
) -> tuple[float, list[str], list[str]]:
    """Return (penalty, matched_ids, incorrect_claims)."""
    penalty = 0.0
    matched_ids: list[str] = []
    incorrect_claims: list[str] = []

    # Build a claim lookup from the card
    claim_by_id = {m.misconception_id: m.claim for m in card.misconception_cards}

    for check in misconception_checks:
        for pattern in check.trigger_patterns:
            if re.search(pattern, normalized_response, re.IGNORECASE):
                matched_ids.append(check.misconception_id)
                incorrect_claims.append(
                    claim_by_id.get(check.misconception_id, check.misconception_id)
                )
                penalty += _SEVERITY_PENALTIES.get(check.severity, 0.10)
                break  # One match per misconception

    return min(penalty, 0.50), matched_ids, incorrect_claims


def _compute_score(coverage: float, misconception_penalty: float) -> float:
    """Final score = coverage * (1 - penalty), clamped to [0.0, 1.0]."""
    return max(0.0, min(1.0, coverage * (1.0 - misconception_penalty)))


def _needs_human_review(
    coverage: float,
    misconception_ids: list[str],
    has_critical: bool,
    response_len: int,
) -> bool:
    """Determine if the result needs human review.

    Triggers:
    1. Coverage 0.40–0.60 with no misconceptions → ambiguous
    2. Very short response (< 20 chars) → insufficient
    3. Very long response (> 2000 chars) → may be incidental
    4. High coverage + critical misconception → mixed signals
    """
    # Condition 1: ambiguous coverage with no misconceptions
    if 0.40 <= coverage <= 0.60 and not misconception_ids:
        return True
    # Condition 2: very short (but not empty — empty is just score 0)
    if 0 < response_len < 20:
        return True
    # Condition 3: very long
    if response_len > 2000:
        return True
    # Condition 4: high coverage but critical misconception
    if coverage >= 0.70 and has_critical:
        return True
    return False


def _generate_feedback(
    passed: bool,
    missing_terms: list[str],
    misconception_ids: list[str],
) -> str:
    """Generate Korean feedback text."""
    parts: list[str] = []
    if passed:
        parts.append("잘 설명했습니다.")
    else:
        if missing_terms:
            terms_kr = ", ".join(missing_terms[:3])
            parts.append(f"다음 용어가 누락되었습니다: {terms_kr}")
        if misconception_ids:
            parts.append("일부 오개념이 감지되었습니다.")
    if not parts:
        parts.append("다시 시도해 보세요.")
    return " ".join(parts)


def _generate_recall_trigger(
    task_type: str,
    missing_terms: list[str],
    misconception_ids: list[str],
) -> str:
    """Generate targeted recall prompt (Korean) for failed tasks."""
    if not missing_terms and not misconception_ids:
        return ""
    return _MAPPING_RECALL_TRIGGERS.get(task_type, "이 개념을 다시 설명하라.")


# ---------------------------------------------------------------------------
# Main evaluator class
# ---------------------------------------------------------------------------


class DeterministicEvaluator:
    """Card-grounded deterministic evaluation. No LLM calls."""

    def __init__(self, card: GroundTruthCard, rubric: ConceptRubric) -> None:
        self.card = card
        self.rubric = rubric

    # -- helpers --

    def _get_combined_checks(
        self, task_key: str
    ) -> tuple[list[TermCheck], list[MisconceptionCheck], float]:
        """Return (required_terms, all misconception_checks, pass_threshold)."""
        task_rubric = self.rubric.task_rubrics.get(task_key)
        if task_rubric is None:
            return [], list(self.rubric.global_misconception_checks), 0.70

        # Combine task-level + global misconception checks (deduplicate by id)
        seen_ids: set[str] = set()
        combined_mc: list[MisconceptionCheck] = []
        for mc in task_rubric.misconception_checks:
            if mc.misconception_id not in seen_ids:
                combined_mc.append(mc)
                seen_ids.add(mc.misconception_id)
        for mc in self.rubric.global_misconception_checks:
            if mc.misconception_id not in seen_ids:
                combined_mc.append(mc)
                seen_ids.add(mc.misconception_id)

        return task_rubric.required_terms, combined_mc, task_rubric.pass_threshold

    def _evaluate_core(
        self,
        task_key: str,
        learner_response: str,
        is_mapping: bool = False,
        mapping_task_type: str = "",
    ) -> EvaluationOutput:
        """Shared evaluation pipeline for term-based tasks."""
        # Empty answer → immediate 0
        if not learner_response.strip():
            return EvaluationOutput(
                score=0.0,
                mastery="unknown",
                passed=False,
                missing_elements=[],
                incorrect_claims=[],
                misconception_tags=[],
                mapping_failures=[mapping_task_type] if is_mapping and mapping_task_type else [],
                needs_human_review=False,
                feedback="답변이 비어 있습니다.",
                next_recall_trigger="",
            )

        normalized = _normalize(learner_response)
        terms, mc_checks, threshold = self._get_combined_checks(task_key)

        coverage, missing = _check_terms(normalized, terms)
        penalty, mc_ids, incorrect = _detect_misconceptions(normalized, mc_checks, self.card)
        score = _compute_score(coverage, penalty)
        passed = score >= threshold

        has_critical = any(
            mc.severity == "critical"
            for mc in mc_checks
            if mc.misconception_id in mc_ids
        )

        review = _needs_human_review(
            coverage, mc_ids, has_critical, len(learner_response.strip()),
        )

        mapping_failures: list[str] = []
        if is_mapping and not passed and mapping_task_type:
            mapping_failures = [mapping_task_type]

        trigger_key = mapping_task_type if is_mapping else task_key
        recall_trigger = _generate_recall_trigger(trigger_key, missing, mc_ids)

        feedback = _generate_feedback(passed, missing, mc_ids)

        return EvaluationOutput(
            score=round(score, 4),
            mastery=compute_mastery_state(score),
            passed=passed,
            missing_elements=missing,
            incorrect_claims=incorrect,
            misconception_tags=mc_ids,
            mapping_failures=mapping_failures,
            needs_human_review=review,
            feedback=feedback,
            next_recall_trigger=recall_trigger,
        )

    # -- public API --

    def evaluate_self_explanation(
        self,
        representation_type: str,
        learner_response: str,
    ) -> EvaluationOutput:
        """Evaluate a self-explanation against card content.

        representation_type: "formal", "counterexample", "proof_schema",
                             "intuitive", "visual"
        Note: intuitive/visual are evaluated but NOT scored for mastery by the caller.
        """
        task_key = f"self_explain_{representation_type}"
        return self._evaluate_core(task_key, learner_response)

    def evaluate_mapping(
        self,
        task_type: str,
        learner_response: str,
    ) -> EvaluationOutput:
        """Evaluate a mapping task submission.

        task_type: "formal_to_counterexample", "counterexample_to_formal",
                   "formal_counterexample_to_proof_schema"
        """
        task_key = f"mapping_{task_type}"
        return self._evaluate_core(
            task_key, learner_response,
            is_mapping=True, mapping_task_type=task_type,
        )

    def evaluate_recall(
        self,
        learner_response: str,
        targeted_triggers: list[str] | None = None,
    ) -> EvaluationOutput:
        """Evaluate white recall response."""
        return self._evaluate_core("recall", learner_response)

    def evaluate_misconception_quiz(
        self,
        results: list[dict],
    ) -> EvaluationOutput:
        """Evaluate misconception T/F quiz results.

        Each result dict: {"misconception_id": str, "learner_answer": bool}
        Deterministic: compare against card truth_values.
        """
        if not results:
            return EvaluationOutput(
                score=0.0,
                mastery="unknown",
                passed=False,
                missing_elements=[],
                incorrect_claims=[],
                misconception_tags=[],
                mapping_failures=[],
                needs_human_review=False,
                feedback="퀴즈 결과가 없습니다.",
                next_recall_trigger="",
            )

        truth_by_id = {m.misconception_id: m.truth_value for m in self.card.misconception_cards}
        claim_by_id = {m.misconception_id: m.claim for m in self.card.misconception_cards}

        correct_count = 0
        total = len(results)
        mc_tags: list[str] = []
        incorrect_claims: list[str] = []

        for r in results:
            mid = r["misconception_id"]
            learner_answer = r["learner_answer"]
            expected = truth_by_id.get(mid)
            if expected is not None and learner_answer == expected:
                correct_count += 1
            else:
                mc_tags.append(mid)
                incorrect_claims.append(claim_by_id.get(mid, mid))

        score = correct_count / total if total > 0 else 0.0
        threshold = self.rubric.task_rubrics.get(
            "misconception_quiz",
        )
        pass_threshold = threshold.pass_threshold if threshold else 0.70
        passed = score >= pass_threshold

        feedback = _generate_feedback(passed, [], mc_tags)

        return EvaluationOutput(
            score=round(score, 4),
            mastery=compute_mastery_state(score),
            passed=passed,
            missing_elements=[],
            incorrect_claims=incorrect_claims,
            misconception_tags=mc_tags,
            mapping_failures=[],
            needs_human_review=False,  # Purely deterministic
            feedback=feedback,
            next_recall_trigger="",
        )
