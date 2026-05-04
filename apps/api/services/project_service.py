"""
Service: project bootstrap — create data directories and skeleton STUDY.md.
"""
from __future__ import annotations

import apps.api.config as config


def get_status() -> dict:
    return {
        "project_root":      str(config.DATA_ROOT.resolve()),
        "study_md_exists":   config.STUDY_MD.exists(),
        "banks_dir_exists":  config.BANK_ROOT.exists(),
        "runs_dir_exists":   config.RUNS_DIR.exists(),
        "sources_dir_exists": config.SOURCES_DIR.exists(),
    }


def bootstrap(overwrite: bool = False) -> dict:
    created: list[str] = []
    skipped: list[str] = []

    for path, name in [
        (config.BANK_ROOT,    "banks"),
        (config.RUNS_DIR,     "runs"),
        (config.SOURCES_DIR,  "sources"),
    ]:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(name)
        else:
            skipped.append(name)

    # STUDY.md skeleton — validate_study_md() is NOT called here.
    # It requires concept records that don't exist yet; parse_study_md() returns {}
    # on this skeleton without error.
    if not config.STUDY_MD.exists() or overwrite:
        from datetime import date
        config.STUDY_MD.parent.mkdir(parents=True, exist_ok=True)
        skeleton = (
            "# STUDY.md\n\n"
            f"_Bootstrapped {date.today().isoformat()}. "
            "Concept records appear after recall sessions._\n"
        )
        config.STUDY_MD.write_text(skeleton, encoding="utf-8")
        created.append("STUDY.md")
    else:
        skipped.append("STUDY.md")

    return {"created": created, "skipped": skipped}
