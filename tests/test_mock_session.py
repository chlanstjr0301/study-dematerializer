"""End-to-end integration tests using MockLLMClient."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from gonghaebun.llm.mock import MockLLMClient
from gonghaebun.pipeline.source_loader import SourceNotFoundError
from gonghaebun.session import run_new_concept_session

SAMPLE_SOURCE = Path(__file__).parent / "data" / "sample_source.md"

EXPECTED_ARTIFACTS = [
    "source_manifest.json",
    "source_excerpt.md",
    "concept_decomposition.json",
    "prerequisite_graph.json",
    "representation_cards.md",
    "self_explanation_prompt.md",
    "diagnosis.json",
    "recall_tasks.md",
    "STUDY.patch.md",
    "session.json",
]


@pytest.fixture
def sample_source() -> Path:
    assert SAMPLE_SOURCE.exists(), f"Sample source not found: {SAMPLE_SOURCE}"
    return SAMPLE_SOURCE


@pytest.fixture
def llm() -> MockLLMClient:
    return MockLLMClient()


def test_full_session_creates_all_artifacts(tmp_path, sample_source, llm):
    output_dir = tmp_path / "runs" / "session1"
    study_md = tmp_path / "STUDY.md"

    run_new_concept_session(
        concept_input="compactness",
        source_path=sample_source,
        llm=llm,
        output_dir=output_dir,
        study_md_path=study_md,
        interactive=False,
    )

    for artifact in EXPECTED_ARTIFACTS:
        path = output_dir / artifact
        assert path.exists(), f"Missing artifact: {artifact}"


def test_session_json_contains_source_metadata(tmp_path, sample_source, llm):
    output_dir = tmp_path / "runs" / "session1"
    study_md = tmp_path / "STUDY.md"

    run_new_concept_session(
        concept_input="compactness",
        source_path=sample_source,
        llm=llm,
        output_dir=output_dir,
        study_md_path=study_md,
        interactive=False,
    )

    data = json.loads((output_dir / "session.json").read_text(encoding="utf-8"))
    assert "source_hash" in data
    assert data["source_hash"].startswith("sha256:")
    assert "grounding_mode" in data
    assert data["grounding_mode"] == "local_private_source"


def test_source_manifest_contains_required_fields(tmp_path, sample_source, llm):
    output_dir = tmp_path / "runs" / "session1"
    study_md = tmp_path / "STUDY.md"

    run_new_concept_session(
        concept_input="compactness",
        source_path=sample_source,
        llm=llm,
        output_dir=output_dir,
        study_md_path=study_md,
        interactive=False,
    )

    data = json.loads((output_dir / "source_manifest.json").read_text(encoding="utf-8"))
    assert "source_hash" in data
    assert "source_coverage" in data
    assert "keywords_found" in data
    assert isinstance(data["keywords_found"], list)
    assert len(data["keywords_found"]) >= 4


def test_representation_cards_include_grounding_section(tmp_path, sample_source, llm):
    output_dir = tmp_path / "runs" / "session1"
    study_md = tmp_path / "STUDY.md"

    run_new_concept_session(
        concept_input="compactness",
        source_path=sample_source,
        llm=llm,
        output_dir=output_dir,
        study_md_path=study_md,
        interactive=False,
    )

    cards = (output_dir / "representation_cards.md").read_text(encoding="utf-8")
    assert "Grounding" in cards
    assert "sha256:" in cards


def test_prerequisite_graph_is_valid_dag(tmp_path, sample_source, llm):
    output_dir = tmp_path / "runs" / "session1"
    study_md = tmp_path / "STUDY.md"

    run_new_concept_session(
        concept_input="compactness",
        source_path=sample_source,
        llm=llm,
        output_dir=output_dir,
        study_md_path=study_md,
        interactive=False,
    )

    from gonghaebun.models.graph import PrerequisiteEdge, PrerequisiteGraph, PrerequisiteNode
    data = json.loads((output_dir / "prerequisite_graph.json").read_text(encoding="utf-8"))
    nodes = [
        PrerequisiteNode(
            concept_id=n["concept_id"],
            canonical_name=n["canonical_name"],
            depth=n["depth"],
        )
        for n in data["nodes"]
    ]
    edges = [
        PrerequisiteEdge(from_concept=e["from_concept"], to_concept=e["to_concept"])
        for e in data["edges"]
    ]
    graph = PrerequisiteGraph(
        root_concept_id=data["root_concept_id"],
        nodes=nodes,
        edges=edges,
    )
    assert graph.has_cycle() is False


def test_mock_session_requires_source(tmp_path, llm):
    with pytest.raises(SourceNotFoundError):
        run_new_concept_session(
            concept_input="compactness",
            source_path=tmp_path / "missing.md",
            llm=llm,
            output_dir=tmp_path / "out",
            study_md_path=tmp_path / "STUDY.md",
            interactive=False,
        )


def test_study_md_created_after_session(tmp_path, sample_source, llm):
    output_dir = tmp_path / "runs" / "session1"
    study_md = tmp_path / "STUDY.md"

    run_new_concept_session(
        concept_input="compactness",
        source_path=sample_source,
        llm=llm,
        output_dir=output_dir,
        study_md_path=study_md,
        interactive=False,
    )

    assert study_md.exists()
    content = study_md.read_text(encoding="utf-8")
    assert "compactness" in content
