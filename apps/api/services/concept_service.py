"""
Service: concept compiler — list concepts and run the full 8-stage compiler.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import apps.api.config as config
from apps.api.services.bank_service import safe_resolve_under
from apps.api.services.path_utils import validate_slug
from gonghaebun.knowledge.real_analysis import CONCEPTS
from gonghaebun.llm.factory import get_llm_client
from gonghaebun.pipeline.concept_resolver import ConceptNotFoundError, resolve_concept
from gonghaebun.pipeline.io import save_questions
from gonghaebun.pipeline.recall_orchestrator import convert_tasks_to_questions
from gonghaebun.session import run_new_concept_session
from gonghaebun.study_md.writer import apply_concept_compiler_patch


def list_concepts() -> list[dict]:
    """Return all CONCEPTS entries as dicts with concept_id, canonical_name, domain, prerequisites."""
    results = []
    for concept_id, concept in CONCEPTS.items():
        results.append(
            {
                "concept_id": concept_id,
                "canonical_name": concept.canonical_name,
                "domain": concept.domain,
                "prerequisites": concept.prerequisites,
            }
        )
    return sorted(results, key=lambda c: c["concept_id"])


def compile_concept(
    concept_id: str,
    source_relative_path: str,
    document_id: str,
    grader: str = "mock",
    *,
    bank_root: Path | None = None,
    runs_dir: Path | None = None,
    study_md: Path | None = None,
    data_root: Path | None = None,
) -> dict:
    """
    Run the full 8-stage concept compiler for the given concept_id.

    1. Validate concept_id slug and resolve concept.
    2. Validate and resolve source file path.
    3. Run run_new_concept_session() with mock LLM.
    4. Convert recall tasks + representations → Question bank.
    5. Write questions.generated.json + representation_set.json to bank dir.
    6. Apply prerequisites + misconceptions to STUDY.md.
    7. Return summary dict.

    Raises:
        ValueError: invalid slug or source path outside sources/
        ConceptNotFoundError: unknown concept_id
    """
    _bank_root = bank_root or config.BANK_ROOT
    _runs_dir = runs_dir or config.RUNS_DIR
    _study_md = study_md or config.STUDY_MD
    _data_root = data_root or config.DATA_ROOT

    validate_slug(concept_id, field_name="concept_id")
    validate_slug(document_id, field_name="document_id")

    # Source path must be under sources/
    if not source_relative_path.startswith("sources/"):
        raise ValueError(
            f"source_relative_path must start with 'sources/'. Got: {source_relative_path!r}"
        )
    source_path = safe_resolve_under(_data_root, source_relative_path)
    if not source_path.exists():
        raise ValueError(f"Source file not found: {source_relative_path!r}")

    # Resolve concept — raises ConceptNotFoundError if unknown
    resolve_concept(concept_id)

    # Pre-generate session_id so artifacts are discoverable via GET /api/sessions/{id}
    session_id = str(uuid4())
    output_dir = _runs_dir / session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    llm = get_llm_client()
    run_new_concept_session(
        concept_input=concept_id,
        source_path=source_path,
        llm=llm,
        output_dir=output_dir,
        study_md_path=_study_md,
        session_id=session_id,
    )

    # Load artifacts written by the pipeline
    tasks_data: dict = json.loads((output_dir / "recall_tasks.json").read_text(encoding="utf-8"))
    rep_set_data: dict = json.loads((output_dir / "representation_set.json").read_text(encoding="utf-8"))
    graph_data: dict = json.loads((output_dir / "prerequisite_graph.json").read_text(encoding="utf-8"))
    diagnosis_data: dict = json.loads((output_dir / "diagnosis.json").read_text(encoding="utf-8"))

    # Convert to question bank and persist
    questions = convert_tasks_to_questions(tasks_data, rep_set_data, concept_id)
    bank_dir = _bank_root / concept_id
    bank_dir.mkdir(parents=True, exist_ok=True)
    save_questions(bank_dir / "questions.generated.json", questions)
    shutil.copy2(output_dir / "representation_set.json", bank_dir / "representation_set.json")

    # Persist prerequisites + misconceptions to STUDY.md
    apply_concept_compiler_patch(_study_md, concept_id, graph_data, diagnosis_data)

    prerequisite_count = len(
        [n for n in graph_data.get("nodes", []) if n.get("concept_id") != concept_id]
    )
    misconception_count = len(diagnosis_data.get("misconceptions", []))

    return {
        "session_id": session_id,
        "concept_id": concept_id,
        "representation_count": 5,
        "prerequisite_count": prerequisite_count,
        "misconception_count": misconception_count,
        "question_count": len(questions),
        "bank_dir": str(bank_dir.relative_to(_data_root)),
    }
