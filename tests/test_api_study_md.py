"""
Tests for GET /api/due and GET /api/study-md.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.study_md_service as study_md_svc

client = TestClient(app)


@pytest.fixture()
def tmp_study_md(tmp_path: Path) -> Path:
    """Write a minimal STUDY.md and patch the service to use it."""
    content = """\
# STUDY.md

## compactness

- mastery: solid
- next_review: 2020-01-01
- representations:
  - definition: solid
  - theorem: partial

## connectedness

- mastery: unknown
- next_review: null
"""
    path = tmp_path / "STUDY.md"
    path.write_text(content, encoding="utf-8")
    return path


class TestGetDue:
    def test_returns_empty_when_no_study_md(self, tmp_path, monkeypatch):
        monkeypatch.setattr(study_md_svc.config, "STUDY_MD", tmp_path / "nonexistent.md")
        resp = client.get("/api/due")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_due_concepts(self, tmp_study_md, monkeypatch):
        monkeypatch.setattr(study_md_svc.config, "STUDY_MD", tmp_study_md)
        resp = client.get("/api/due")
        assert resp.status_code == 200
        data = resp.json()
        concept_ids = [item["concept_id"] for item in data]
        # Both are due (next_review in the past or null)
        assert "compactness" in concept_ids
        assert "connectedness" in concept_ids

    def test_item_schema(self, tmp_study_md, monkeypatch):
        monkeypatch.setattr(study_md_svc.config, "STUDY_MD", tmp_study_md)
        resp = client.get("/api/due")
        item = resp.json()[0]
        assert "concept_id" in item
        assert "next_review" in item
        assert "overdue" in item

    def test_overdue_flag_set_for_past_date(self, tmp_study_md, monkeypatch):
        monkeypatch.setattr(study_md_svc.config, "STUDY_MD", tmp_study_md)
        resp = client.get("/api/due")
        compactness = next(i for i in resp.json() if i["concept_id"] == "compactness")
        assert compactness["overdue"] is True


class TestGetStudyMd:
    def test_returns_empty_string_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(study_md_svc.config, "STUDY_MD", tmp_path / "nonexistent.md")
        resp = client.get("/api/study-md")
        assert resp.status_code == 200
        assert resp.json() == {"content": ""}

    def test_returns_file_content(self, tmp_study_md, monkeypatch):
        monkeypatch.setattr(study_md_svc.config, "STUDY_MD", tmp_study_md)
        resp = client.get("/api/study-md")
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "compactness" in content
        assert "STUDY.md" in content
