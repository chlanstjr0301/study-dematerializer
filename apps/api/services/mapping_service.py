"""
Mapping task engine service for MVP6.

Generates mapping tasks from a Ground Truth Card and evaluates mapping
submissions using the DeterministicEvaluator. No LLM calls.
"""
from __future__ import annotations

from datetime import datetime, timezone

from apps.api.services.confusion_map_service import update_from_mapping
from gonghaebun.grading.deterministic_evaluator import DeterministicEvaluator
from gonghaebun.models.confusion_map import ConfusionMap
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.mapping_models import MappingResult, MappingTask, MappingTaskType
from gonghaebun.models.rubric import ConceptRubric

# Source/target representation lookup per task type
_REP_MAP: dict[str, tuple[list[str], str]] = {
    "formal_to_counterexample": (["formal"], "counterexample"),
    "counterexample_to_formal": (["counterexample"], "formal"),
    "formal_counterexample_to_proof_schema": (
        ["formal", "counterexample"],
        "proof_schema",
    ),
}


def generate_mapping_tasks(
    session_id: str,
    concept_id: str,
    card: GroundTruthCard,
) -> list[MappingTask]:
    """Generate 3 mapping tasks from the Ground Truth Card.

    Task IDs are deterministic: ``{session_id}_{task_type}``.
    """
    tasks: list[MappingTask] = []
    for mapping_template in card.allowed_mapping_tasks:
        task_type_str = mapping_template.task_type
        source_reps, target_rep = _REP_MAP.get(
            task_type_str, (["unknown"], "unknown")
        )
        tasks.append(
            MappingTask(
                task_id=f"{session_id}_{task_type_str}",
                session_id=session_id,
                concept_id=concept_id,
                task_type=MappingTaskType(task_type_str),
                prompt=mapping_template.prompt_kr,
                required_terms=list(mapping_template.required_terms),
                grounding_notes=mapping_template.grounding_notes,
                source_representations=source_reps,
                target_representation=target_rep,
            )
        )
    return tasks


def evaluate_mapping_submission(
    task: MappingTask,
    learner_response: str,
    card: GroundTruthCard,
    rubric: ConceptRubric,
) -> MappingResult:
    """Evaluate one mapping task submission using the deterministic evaluator.

    Returns a fully populated ``MappingResult``.
    """
    evaluator = DeterministicEvaluator(card, rubric)
    task_type_str = task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type)
    evaluation = evaluator.evaluate_mapping(task_type_str, learner_response)

    return MappingResult(
        task_id=task.task_id,
        task_type=task.task_type,
        learner_response=learner_response,
        score=evaluation.score,
        passed=evaluation.passed,
        missing_elements=evaluation.missing_elements,
        incorrect_claims=evaluation.incorrect_claims,
        misconception_tags=evaluation.misconception_tags,
        mapping_failures=evaluation.mapping_failures,
        feedback=evaluation.feedback,
        next_recall_trigger=evaluation.next_recall_trigger,
        needs_human_review=evaluation.needs_human_review,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )


def update_confusion_map_from_mapping(
    confusion_map: ConfusionMap,
    result: MappingResult,
) -> ConfusionMap:
    """Update confusion map with a mapping result.

    Delegates to ``confusion_map_service.update_from_mapping``.
    """
    return update_from_mapping(confusion_map, result)
