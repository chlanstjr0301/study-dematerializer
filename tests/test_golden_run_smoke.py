"""
Golden Run Smoke Test (Step 19).

End-to-end test that simulates the demo golden run scenario (doc 10):
create session → diagnose → self-explain → mapping (with known failure) →
recall → complete.

Verifies:
- Mapping task evaluation produces expected failure
- Misconception tags match expected set
- Confusion map has expected structure
- STUDY.md updated with confusion summary
- All artifacts written
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def golden_env(tmp_path: Path, monkeypatch):
    """Isolated environment for golden run smoke test."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    bank_root = tmp_path / "banks"
    bank_root.mkdir()
    study_md = tmp_path / "STUDY.md"
    study_md.write_text("# Study Progress\n", encoding="utf-8")
    data_root = tmp_path

    # Copy test source
    sample_source = Path("tests/data/sample_source.md")
    (sources_dir / "test_source.md").write_text(
        sample_source.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Monkeypatch config
    import apps.api.config as cfg
    import apps.api.services.study_session_service as svc_mod
    monkeypatch.setattr(svc_mod.config, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(svc_mod.config, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(svc_mod.config, "BANK_ROOT", bank_root)
    monkeypatch.setattr(svc_mod.config, "STUDY_MD", study_md)
    monkeypatch.setattr(svc_mod.config, "DATA_ROOT", data_root)

    # Mapping router uses config.RUNS_DIR directly
    monkeypatch.setattr(cfg, "RUNS_DIR", runs_dir)

    # Ensure MockLLMClient finds fixtures
    monkeypatch.setenv("GONGHAEBUN_FIXTURE_DIR", str(Path("tests/fixtures").resolve()))

    # Clear card/rubric caches so they're loaded fresh each test
    from apps.api.services.card_service import clear_cache
    clear_cache()

    return {
        "runs_dir": runs_dir,
        "sources_dir": sources_dir,
        "bank_root": bank_root,
        "study_md": study_md,
        "data_root": data_root,
    }


# ---------------------------------------------------------------------------
# Golden answers (from doc 10)
# ---------------------------------------------------------------------------

# THE KEY DIAGNOSTIC ANSWER: Uses Heine-Borel shortcut instead of open cover
DIAGNOSTIC_ANSWER = "(0,1)은 닫혀 있지 않아서 compact하지 않습니다."

# Correct counterexample → formal mapping
CORRECT_CE_TO_FORMAL = (
    "(0,1)이 compact하지 않으므로, compact 집합은 모든 열린 덮개에 대해 "
    "유한 부분덮개가 존재해야 합니다. R^n에서는 닫혀 있고 유계여야 합니다."
)

# Weak proof schema answer
WEAK_PROOF_ANSWER = (
    "Heine-Borel은 closed and bounded이면 compact라는 것인데, "
    "증명 구조는 잘 모르겠습니다."
)


# ---------------------------------------------------------------------------
# Main golden run test
# ---------------------------------------------------------------------------


class TestGoldenRunCompactness:
    """Full compactness golden run: doc 10 scenario."""

    def test_golden_run(self, golden_env):
        """
        Full demo flow: create → diagnose → self-explain → mapping → recall → complete.

        The learner knows what compactness is, but uses the Heine-Borel shortcut
        for the formal → counterexample mapping instead of constructing an open
        cover argument. This is the diagnostic failure scenario.
        """
        study_md = golden_env["study_md"]
        runs_dir = golden_env["runs_dir"]

        # ---------------------------------------------------------------
        # Step 1: Create session
        # ---------------------------------------------------------------
        resp = client.post("/api/study-session", json={"concept_id": "compactness"})
        assert resp.status_code == 201
        session = resp.json()
        session_id = session["session_id"]
        assert session["concept_id"] == "compactness"
        assert "representations" in session
        assert isinstance(session["prerequisites"], list)
        assert isinstance(session["misconceptions"], list)

        session_dir = runs_dir / session_id
        assert (session_dir / "study_session_state.json").exists()
        assert (session_dir / "confusion_map.json").exists()
        assert (session_dir / "mapping_tasks.json").exists()

        # ---------------------------------------------------------------
        # Step 2: Diagnosis
        # ---------------------------------------------------------------
        resp = client.post(f"/api/study-session/{session_id}/diagnose", json={
            "prior_knowledge": "compact가 뭔지는 대충 아는데, 왜 (0,1)이 compact가 아닌지 증명을 못 하겠어요.",
            "gap_description": "open cover 개념이 잘 안 와닿아요.",
        })
        assert resp.status_code == 200
        diag = resp.json()
        assert diag["initial_mastery_estimate"] == "partial"

        # ---------------------------------------------------------------
        # Step 3: Self-explain (formal + proof_schema — minimum required)
        # ---------------------------------------------------------------
        resp = client.post(f"/api/study-session/{session_id}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "compact 집합은 모든 열린 덮개에 대해 유한 부분덮개가 존재하는 거리 공간의 부분집합이다.",
        })
        assert resp.status_code == 200

        resp = client.post(f"/api/study-session/{session_id}/self-explain", json={
            "representation_type": "proof_schema",
            "learner_explanation": "Heine-Borel: closed and bounded이면 compact이다. 증명은 잘 모르겠다.",
        })
        assert resp.status_code == 200

        # ---------------------------------------------------------------
        # Step 4: Advance prerequisites + representations
        # ---------------------------------------------------------------
        for step in ["prerequisites", "representations"]:
            resp = client.post(f"/api/study-session/{session_id}/advance", json={
                "completed_step": step,
            })
            assert resp.status_code == 200

        # ---------------------------------------------------------------
        # Step 5: Mapping — THE KEY DEMO MOMENT
        # ---------------------------------------------------------------

        # 5a. Get mapping tasks
        resp = client.get(f"/api/study-session/{session_id}/mapping-tasks")
        assert resp.status_code == 200
        tasks_data = resp.json()
        assert len(tasks_data["tasks"]) == 3

        # Find task by type
        tasks_by_type = {t["task_type"]: t for t in tasks_data["tasks"]}
        assert "formal_to_counterexample" in tasks_by_type
        assert "counterexample_to_formal" in tasks_by_type
        assert "formal_counterexample_to_proof_schema" in tasks_by_type

        # 5b. Submit Task 1 — DIAGNOSTIC FAILURE
        task1 = tasks_by_type["formal_to_counterexample"]
        resp = client.post(f"/api/study-session/{session_id}/mapping-submit", json={
            "task_id": task1["task_id"],
            "learner_response": DIAGNOSTIC_ANSWER,
        })
        assert resp.status_code == 200
        r1 = resp.json()
        assert r1["passed"] is False
        assert r1["score"] < 0.50, f"Score should be < 0.50 for diagnostic failure, got {r1['score']}"
        assert "missing_open_cover_argument" in r1["misconception_tags"]
        assert "formal_to_counterexample" in r1["mapping_failures"]
        assert r1["next_recall_trigger"] != ""

        # Confusion map should be updated inline
        assert "confusion_map" in r1
        cmap_inline = r1["confusion_map"]
        assert any(
            e["task_type"] == "formal_to_counterexample" and not e["passed"]
            for e in cmap_inline["mapping_edges"]
        )

        # 5c. Submit Task 2 — correct answer
        task2 = tasks_by_type["counterexample_to_formal"]
        resp = client.post(f"/api/study-session/{session_id}/mapping-submit", json={
            "task_id": task2["task_id"],
            "learner_response": CORRECT_CE_TO_FORMAL,
        })
        assert resp.status_code == 200
        r2 = resp.json()
        assert r2["passed"] is True
        assert r2["score"] >= 0.70

        # 5d. Submit Task 3 — weak proof answer
        task3 = tasks_by_type["formal_counterexample_to_proof_schema"]
        resp = client.post(f"/api/study-session/{session_id}/mapping-submit", json={
            "task_id": task3["task_id"],
            "learner_response": WEAK_PROOF_ANSWER,
        })
        assert resp.status_code == 200
        r3 = resp.json()
        assert r3["passed"] is False
        assert r3["score"] < 0.50

        # ---------------------------------------------------------------
        # Step 5 verification: Confusion Map structure
        # ---------------------------------------------------------------
        resp = client.get(f"/api/study-session/{session_id}/confusion-map")
        assert resp.status_code == 200
        cmap = resp.json()

        assert cmap["concept_id"] == "compactness"
        assert len(cmap["mapping_edges"]) == 3

        # Verify edge pass/fail status
        edges_by_type = {e["task_type"]: e for e in cmap["mapping_edges"]}
        assert edges_by_type["formal_to_counterexample"]["passed"] is False
        assert edges_by_type["counterexample_to_formal"]["passed"] is True
        assert edges_by_type["formal_counterexample_to_proof_schema"]["passed"] is False

        # Misconception tags present
        assert "missing_open_cover_argument" in cmap["misconception_tags"]

        # Next recall triggers present
        assert len(cmap["next_recall_triggers"]) >= 1

        # Evidence snippets present
        assert len(cmap["evidence_snippets"]) >= 1

        # ---------------------------------------------------------------
        # Step 6: Advance mapping + misconceptions
        # ---------------------------------------------------------------
        resp = client.post(f"/api/study-session/{session_id}/advance", json={
            "completed_step": "mapping",
        })
        assert resp.status_code == 200

        resp = client.post(f"/api/study-session/{session_id}/advance", json={
            "completed_step": "misconceptions",
        })
        assert resp.status_code == 200

        # ---------------------------------------------------------------
        # Step 7: Recall
        # ---------------------------------------------------------------
        resp = client.post(f"/api/study-session/{session_id}/recall", json={
            "learner_response": (
                "옹골성은 모든 열린 덮개에 대해 유한 부분덮개가 존재하는 성질이다. "
                "(0,1)은 닫혀 있지 않아서 compact하지 않다. "
                "Heine-Borel에 의해 R에서 compact는 닫히고 유계인 것이다."
            ),
        })
        assert resp.status_code == 200
        recall_data = resp.json()
        assert "accuracy_score" in recall_data

        # ---------------------------------------------------------------
        # Step 8: Complete
        # ---------------------------------------------------------------
        resp = client.post(f"/api/study-session/{session_id}/complete")
        assert resp.status_code == 200
        completion = resp.json()

        assert completion["completed"] is True
        assert completion["study_md_updated"] is True
        assert len(completion["mastery_updates"]) >= 2  # at least formal + proof_schema
        assert completion["next_review_date"]  # non-empty

        # ---------------------------------------------------------------
        # Post-completion: Verify STUDY.md
        # ---------------------------------------------------------------
        study_text = study_md.read_text(encoding="utf-8")
        assert "compactness" in study_text

        # Confusion Summary section should exist
        assert "### Confusion Summary" in study_text
        assert "formal" in study_text.lower()

        # Active misconceptions
        assert "missing_open_cover_argument" in study_text

        # Next recall trigger
        assert "Next recall trigger" in study_text

        # ---------------------------------------------------------------
        # Post-completion: Verify artifacts
        # ---------------------------------------------------------------
        assert (session_dir / "confusion_map.json").exists()
        assert (session_dir / "mapping_results.json").exists()
        assert (session_dir / "mapping_tasks.json").exists()
        assert (session_dir / "study_session_state.json").exists()
        assert (session_dir / "STUDY.patch.md").exists()

        # Validate confusion_map.json structure
        final_cmap = json.loads(
            (session_dir / "confusion_map.json").read_text(encoding="utf-8")
        )
        assert final_cmap["concept_id"] == "compactness"
        assert final_cmap["last_updated_step"] == "complete"
        assert len(final_cmap["mapping_edges"]) == 3

        # Validate mapping_results.json
        results = json.loads(
            (session_dir / "mapping_results.json").read_text(encoding="utf-8")
        )
        assert len(results) == 3
        task1_result = next(r for r in results if "formal_to_counterexample" in r["task_id"])
        assert task1_result["passed"] is False
        assert task1_result["score"] < 0.50

        # Validate final state
        state = json.loads(
            (session_dir / "study_session_state.json").read_text(encoding="utf-8")
        )
        assert state["completed"] is True
        assert state["recall_completed"] is True
        assert state["confusion_map_initialized"] is True


class TestGoldenRunMappingFailureDiagnosis:
    """Focused tests on the mapping failure diagnosis scenario."""

    def test_diagnostic_answer_gets_zero_coverage(self, golden_env):
        """The Heine-Borel shortcut answer has zero required-term coverage."""
        from gonghaebun.grading.deterministic_evaluator import DeterministicEvaluator
        from apps.api.services.card_service import load_ground_truth_card, load_rubric

        card = load_ground_truth_card("compactness", use_cache=False)
        rubric = load_rubric("compactness", use_cache=False)
        ev = DeterministicEvaluator(card, rubric)

        result = ev.evaluate_mapping("formal_to_counterexample", DIAGNOSTIC_ANSWER)

        assert result.score < 0.50
        assert result.passed is False
        assert "missing_open_cover_argument" in result.misconception_tags
        assert "formal_to_counterexample" in result.mapping_failures
        assert len(result.missing_elements) >= 3  # open cover, finite subcover, (1/n,1)

    def test_correct_ce_to_formal_passes(self, golden_env):
        """Enriched answer with all required terms passes."""
        from gonghaebun.grading.deterministic_evaluator import DeterministicEvaluator
        from apps.api.services.card_service import load_ground_truth_card, load_rubric

        card = load_ground_truth_card("compactness", use_cache=False)
        rubric = load_rubric("compactness", use_cache=False)
        ev = DeterministicEvaluator(card, rubric)

        result = ev.evaluate_mapping("counterexample_to_formal", CORRECT_CE_TO_FORMAL)

        assert result.score >= 0.70
        assert result.passed is True
        assert result.mapping_failures == []

    def test_weak_proof_answer_fails(self, golden_env):
        """Weak proof answer fails with missing terms."""
        from gonghaebun.grading.deterministic_evaluator import DeterministicEvaluator
        from apps.api.services.card_service import load_ground_truth_card, load_rubric

        card = load_ground_truth_card("compactness", use_cache=False)
        rubric = load_rubric("compactness", use_cache=False)
        ev = DeterministicEvaluator(card, rubric)

        result = ev.evaluate_mapping(
            "formal_counterexample_to_proof_schema", WEAK_PROOF_ANSWER,
        )

        assert result.score < 0.50
        assert result.passed is False
        assert len(result.missing_elements) >= 2


class TestGoldenRunConfusionMapStructure:
    """Verify confusion map structure after the golden run mapping steps."""

    def test_confusion_map_after_all_mappings(self, golden_env):
        """Submit all 3 mapping tasks and verify confusion map structure."""
        runs_dir = golden_env["runs_dir"]

        # Create session + diagnose
        resp = client.post("/api/study-session", json={"concept_id": "compactness"})
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        resp = client.post(f"/api/study-session/{session_id}/diagnose", json={
            "prior_knowledge": "compact 알아",
            "gap_description": "증명 못 해",
        })
        assert resp.status_code == 200

        # Get tasks
        resp = client.get(f"/api/study-session/{session_id}/mapping-tasks")
        tasks_by_type = {t["task_type"]: t for t in resp.json()["tasks"]}

        # Submit all 3
        for task_type, answer in [
            ("formal_to_counterexample", DIAGNOSTIC_ANSWER),
            ("counterexample_to_formal", CORRECT_CE_TO_FORMAL),
            ("formal_counterexample_to_proof_schema", WEAK_PROOF_ANSWER),
        ]:
            resp = client.post(f"/api/study-session/{session_id}/mapping-submit", json={
                "task_id": tasks_by_type[task_type]["task_id"],
                "learner_response": answer,
            })
            assert resp.status_code == 200

        # Verify confusion map
        resp = client.get(f"/api/study-session/{session_id}/confusion-map")
        assert resp.status_code == 200
        cmap = resp.json()

        # 3 edges
        assert len(cmap["mapping_edges"]) == 3

        # Pass/fail distribution: 1 pass, 2 fails
        passed = [e for e in cmap["mapping_edges"] if e["passed"]]
        failed = [e for e in cmap["mapping_edges"] if not e["passed"]]
        assert len(passed) == 1
        assert len(failed) == 2

        # The passed edge is counterexample→formal
        assert passed[0]["task_type"] == "counterexample_to_formal"

        # Misconception tags populated
        assert len(cmap["misconception_tags"]) >= 1

        # Evidence snippets for failed mappings
        assert len(cmap["evidence_snippets"]) >= 2  # 2 failures

        # Next recall triggers
        assert len(cmap["next_recall_triggers"]) >= 1


class TestGoldenRunArtifacts:
    """Verify all expected artifacts are produced."""

    def test_session_artifacts_complete(self, golden_env):
        """All expected artifacts exist after session completion."""
        runs_dir = golden_env["runs_dir"]

        # Create + diagnose + self-explain + advance + mapping + recall + complete
        resp = client.post("/api/study-session", json={"concept_id": "compactness"})
        session_id = resp.json()["session_id"]
        session_dir = runs_dir / session_id

        client.post(f"/api/study-session/{session_id}/diagnose", json={
            "prior_knowledge": "조금 알아",
            "gap_description": "열린 덮개 어려워",
        })

        for rep in ["formal", "proof_schema"]:
            client.post(f"/api/study-session/{session_id}/self-explain", json={
                "representation_type": rep,
                "learner_explanation": f"설명: {rep}...",
            })

        for step in ["prerequisites", "representations"]:
            client.post(f"/api/study-session/{session_id}/advance", json={
                "completed_step": step,
            })

        # Submit mapping tasks
        resp = client.get(f"/api/study-session/{session_id}/mapping-tasks")
        for task in resp.json()["tasks"]:
            client.post(f"/api/study-session/{session_id}/mapping-submit", json={
                "task_id": task["task_id"],
                "learner_response": "테스트 응답입니다.",
            })

        for step in ["mapping", "misconceptions"]:
            client.post(f"/api/study-session/{session_id}/advance", json={
                "completed_step": step,
            })

        client.post(f"/api/study-session/{session_id}/recall", json={
            "learner_response": "Compactness recall...",
        })

        resp = client.post(f"/api/study-session/{session_id}/complete")
        assert resp.status_code == 200

        # Verify artifact files
        expected_artifacts = [
            "study_session_state.json",
            "confusion_map.json",
            "mapping_tasks.json",
            "mapping_results.json",
            "STUDY.patch.md",
            # Pipeline artifacts from session creation
            "concept_decomposition.json",
            "prerequisite_graph.json",
            "representation_set.json",
            "diagnosis.json",
            "recall_tasks.json",
        ]

        for artifact in expected_artifacts:
            assert (session_dir / artifact).exists(), f"Missing artifact: {artifact}"
