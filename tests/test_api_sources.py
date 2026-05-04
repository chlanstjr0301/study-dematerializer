"""
Tests for GET /api/sources and POST /api/sources/upload.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.source_service as source_svc

client = TestClient(app)

_MD_CONTENT = b"# Sample\n\nSome valid UTF-8 markdown content.\n"
_TXT_CONTENT = b"Some plain text content.\n"


@pytest.fixture()
def sources_env(tmp_path: Path, monkeypatch):
    """Patch source_service.config.SOURCES_DIR to tmp_path."""
    import apps.api.config as cfg
    monkeypatch.setattr(cfg, "SOURCES_DIR", tmp_path / "sources")
    return tmp_path / "sources"


class TestListSources:
    def test_empty_list_when_dir_absent(self, sources_env):
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lists_uploaded_files(self, sources_env):
        sources_env.mkdir(parents=True)
        (sources_env / "sample.md").write_bytes(_MD_CONTENT)
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["filename"] == "sample.md"
        assert data[0]["relative_path"] == "sources/sample.md"


class TestUploadSource:
    def _upload(self, sources_env, filename: str, content: bytes,
                concept_id: str = "compactness", document_id: str | None = None):
        files = {"file": (filename, content, "text/plain")}
        data: dict = {"concept_id": concept_id}
        if document_id:
            data["document_id"] = document_id
        return client.post("/api/sources/upload", files=files, data=data)

    def test_upload_md_returns_201(self, sources_env):
        resp = self._upload(sources_env, "sample.md", _MD_CONTENT)
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"].endswith(".md")
        assert data["source_path"].startswith("sources/")
        assert "document_id" in data

    def test_upload_txt_returns_201(self, sources_env):
        resp = self._upload(sources_env, "notes.txt", _TXT_CONTENT)
        assert resp.status_code == 201

    def test_upload_pdf_returns_400(self, sources_env):
        resp = self._upload(sources_env, "paper.pdf", b"%PDF-1.4 fake")
        assert resp.status_code == 400

    def test_upload_empty_file_returns_400(self, sources_env):
        resp = self._upload(sources_env, "empty.md", b"")
        assert resp.status_code == 400

    def test_upload_non_utf8_returns_400(self, sources_env):
        resp = self._upload(sources_env, "bad.md", b"\xff\xfe binary garbage")
        assert resp.status_code == 400

    def test_upload_bad_concept_id_dotdot_returns_400(self, sources_env):
        resp = self._upload(sources_env, "sample.md", _MD_CONTENT, concept_id="../evil")
        assert resp.status_code == 400

    def test_upload_bad_concept_id_slash_returns_400(self, sources_env):
        resp = self._upload(sources_env, "sample.md", _MD_CONTENT, concept_id="compactness/evil")
        assert resp.status_code == 400

    def test_upload_bad_document_id_returns_400(self, sources_env):
        resp = self._upload(sources_env, "sample.md", _MD_CONTENT, document_id="../evil")
        assert resp.status_code == 400

    def test_file_stored_under_sources_dir(self, sources_env):
        resp = self._upload(sources_env, "sample.md", _MD_CONTENT)
        assert resp.status_code == 201
        filename = resp.json()["filename"]
        assert (sources_env / filename).exists()
        # Confirm file did NOT escape sources dir
        assert (sources_env / filename).is_relative_to(sources_env)

    def test_document_id_returned(self, sources_env):
        resp = self._upload(sources_env, "myfile.md", _MD_CONTENT, document_id="chapter1")
        assert resp.status_code == 201
        assert resp.json()["document_id"] == "chapter1"

    def test_document_id_defaults_to_stem(self, sources_env):
        resp = self._upload(sources_env, "myfile.md", _MD_CONTENT)
        assert resp.status_code == 201
        assert resp.json()["document_id"] == "myfile"
