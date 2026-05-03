"""
Stage 7: Study Writer pipeline module.

Thin wrapper around gonghaebun.study_md.writer that writes both the
STUDY.patch.md and updates STUDY.md for a completed session.

No LLM calls.
"""
from __future__ import annotations

from pathlib import Path

from gonghaebun.models.session_models import StudySession
from gonghaebun.study_md.writer import apply_patch, generate_patch


def write_study_artifacts(
    session: StudySession,
    output_dir: Path,
    study_md_path: Path,
) -> tuple[Path, Path]:
    """
    Write STUDY.patch.md to output_dir and update STUDY.md at study_md_path.

    Returns (patch_path, study_md_path).
    """
    patch_content = generate_patch(session)
    patch_path = output_dir / "STUDY.patch.md"
    patch_path.write_text(patch_content, encoding="utf-8")

    apply_patch(study_md_path, session)

    return patch_path, study_md_path
