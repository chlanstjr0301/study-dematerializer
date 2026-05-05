"""
Tests for POST /api/compiler/analyze — rule-based concept analyzer.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _analyze(message: str, source_id: str | None = None):
    body: dict = {"message": message}
    if source_id is not None:
        body["source_id"] = source_id
    return client.post("/api/compiler/analyze", json=body)


# ---------------------------------------------------------------------------
# Korean alias exact match
# ---------------------------------------------------------------------------

class TestKoreanAliasMatch:
    def test_compactness_korean(self):
        r = _analyze("옹골성")
        assert r.status_code == 200
        data = r.json()
        assert data["concept_id"] == "compactness"
        assert data["canonical_name_ko"] == "옹골성"
        assert data["canonical_name_en"] == "Compactness"

    def test_connectedness_korean(self):
        r = _analyze("연결성")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "connectedness"

    def test_uniform_continuity_korean(self):
        r = _analyze("균등 연속")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "uniform_continuity"


# ---------------------------------------------------------------------------
# Korean alias in sentence with particles
# ---------------------------------------------------------------------------

class TestKoreanParticles:
    def test_particle_을(self):
        r = _analyze("옹골성을 모르겠어요")
        assert r.status_code == 200
        data = r.json()
        assert data["concept_id"] == "compactness"

    def test_particle_이(self):
        r = _analyze("연결성이 이해 안 돼요")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "connectedness"

    def test_particle_에서(self):
        r = _analyze("옹골성에서 finite subcover가 왜 중요한지")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "compactness"


# ---------------------------------------------------------------------------
# English alias and keyword match
# ---------------------------------------------------------------------------

class TestEnglishMatch:
    def test_english_alias(self):
        r = _analyze("compactness")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "compactness"

    def test_english_keyword(self):
        r = _analyze("finite subcover")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "compactness"

    def test_english_keyword_connectedness(self):
        r = _analyze("path-connected and separated sets")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "connectedness"


# ---------------------------------------------------------------------------
# Gap cue detection
# ---------------------------------------------------------------------------

class TestGapInference:
    def test_gap_모르겠(self):
        r = _analyze("옹골성 모르겠어")
        data = r.json()
        assert "정의" in data["suspected_gap"]

    def test_gap_이해안(self):
        r = _analyze("옹골성 이해 안 돼")
        data = r.json()
        assert "직관적" in data["suspected_gap"]

    def test_gap_헷갈(self):
        r = _analyze("connectedness 헷갈려")
        data = r.json()
        assert "구분" in data["suspected_gap"]

    def test_gap_증명(self):
        r = _analyze("compactness 증명 어떻게")
        data = r.json()
        assert "증명" in data["suspected_gap"]

    def test_gap_왜(self):
        r = _analyze("왜 compactness가 중요한지")
        data = r.json()
        assert "필요성" in data["suspected_gap"] or "동기" in data["suspected_gap"]

    def test_gap_default(self):
        r = _analyze("compactness")
        data = r.json()
        assert "더 깊이" in data["suspected_gap"]


# ---------------------------------------------------------------------------
# No match
# ---------------------------------------------------------------------------

class TestNoMatch:
    def test_unknown_concept(self):
        r = _analyze("양자역학")
        assert r.status_code == 200
        data = r.json()
        assert data["concept_id"] is None
        assert "옹골성" in data["suspected_gap"]
        assert "연결성" in data["suspected_gap"]
        assert "균등 연속" in data["suspected_gap"]

    def test_empty_message(self):
        r = _analyze("")
        assert r.status_code == 200
        assert r.json()["concept_id"] is None

    def test_whitespace_only(self):
        r = _analyze("   ")
        assert r.status_code == 200
        assert r.json()["concept_id"] is None


# ---------------------------------------------------------------------------
# Typo handling
# ---------------------------------------------------------------------------

class TestTypoCorrection:
    def test_compatness_typo(self):
        r = _analyze("compatness 이해 안 돼")
        data = r.json()
        assert data["concept_id"] == "compactness"
        assert data["correction"] is not None
        assert "compatness" in data["correction"]

    def test_no_correction_on_exact_match(self):
        r = _analyze("compactness")
        assert r.json()["correction"] is None


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

class TestPrerequisites:
    def test_compactness_prerequisites(self):
        r = _analyze("옹골성")
        data = r.json()
        prereqs = data["prerequisite_checks"]
        assert len(prereqs) == 5
        ids = [p["concept_id"] for p in prereqs]
        assert "metric_space" in ids
        assert "open_cover" in ids

    def test_prereq_status_미확인(self):
        r = _analyze("옹골성")
        for p in r.json()["prerequisite_checks"]:
            assert p["status"] == "미확인"

    def test_prereq_korean_names(self):
        r = _analyze("옹골성")
        prereqs = r.json()["prerequisite_checks"]
        names = {p["concept_id"]: p["name_ko"] for p in prereqs}
        assert names["metric_space"] == "거리 공간"

    def test_stub_concept_no_prerequisites(self):
        r = _analyze("거리 공간")
        data = r.json()
        assert data["concept_id"] == "metric_space"
        assert data["prerequisite_checks"] == []


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

class TestActions:
    def test_always_3_actions(self):
        r = _analyze("옹골성")
        actions = r.json()["recommended_actions"]
        assert len(actions) == 3

    def test_view_representations_route_null(self):
        r = _analyze("옹골성")
        actions = r.json()["recommended_actions"]
        rep_action = next(a for a in actions if a["action_id"] == "view_representations")
        assert rep_action["route"] is None
        assert "5가지" in rep_action["label_ko"]

    def test_recall_practice_route(self):
        r = _analyze("compactness")
        actions = r.json()["recommended_actions"]
        recall_action = next(a for a in actions if a["action_id"] == "recall_practice")
        assert recall_action["route"] == "/recall?concept=compactness"

    def test_view_prerequisites_route_null(self):
        r = _analyze("옹골성")
        actions = r.json()["recommended_actions"]
        prereq_action = next(a for a in actions if a["action_id"] == "view_prerequisites")
        assert prereq_action["route"] is None

    def test_no_actions_on_no_match(self):
        r = _analyze("양자역학")
        assert r.json()["recommended_actions"] == []


# ---------------------------------------------------------------------------
# Representations
# ---------------------------------------------------------------------------

class TestRepresentations:
    def test_seed_concept_has_representations(self):
        r = _analyze("옹골성")
        reps = r.json()["representations"]
        assert reps is not None
        assert set(reps.keys()) == {"intuitive", "formal", "example", "proof_schema", "misconception"}

    def test_stub_concept_no_representations(self):
        r = _analyze("거리 공간")
        assert r.json()["representations"] is None

    def test_connectedness_representations(self):
        r = _analyze("연결성")
        reps = r.json()["representations"]
        assert reps is not None
        assert "연결" in reps["intuitive"]


# ---------------------------------------------------------------------------
# General response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_language_always_ko(self):
        r = _analyze("compactness")
        assert r.json()["language"] == "ko"

    def test_source_id_passthrough(self):
        """source_id is accepted but doesn't change concept matching."""
        r = _analyze("옹골성", source_id="some-source")
        assert r.status_code == 200
        assert r.json()["concept_id"] == "compactness"
