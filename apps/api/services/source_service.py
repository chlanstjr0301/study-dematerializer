"""
Service: source file management — list and upload source files.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import apps.api.config as config

_ALLOWED = {".md", ".txt"}
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


def list_sources() -> list[dict]:
    d = config.SOURCES_DIR
    if not d.exists():
        return []
    items = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix.lower() in _ALLOWED:
            stat = p.stat()
            items.append({
                "source_id":     p.stem,
                "filename":      p.name,
                "relative_path": f"sources/{p.name}",
                "size_bytes":    stat.st_size,
                "created_at":    datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            })
    return items


def save_source(
    file_bytes: bytes,
    filename: str,
    concept_id: str,
    document_id: str | None = None,
) -> dict:
    from apps.api.services.path_utils import sanitize_filename_stem, validate_slug

    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED:
        raise ValueError(f"Unsupported type {suffix!r}. Only .md and .txt are allowed.")
    if len(file_bytes) == 0:
        raise ValueError("File is empty.")
    if len(file_bytes) > _MAX_BYTES:
        raise ValueError("File exceeds 2 MB limit.")

    # Validate UTF-8
    try:
        file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("File must be valid UTF-8 text.")

    # Validate concept_id and document_id slugs (strict — rejects invalid)
    validate_slug(concept_id, field_name="concept_id")
    safe_doc_id = validate_slug(document_id, field_name="document_id") if document_id else None

    # Sanitize filename stem (lenient — replaces unsafe chars with '_')
    stem = sanitize_filename_stem(Path(filename).stem)
    safe_name = f"{stem}{suffix}"

    config.SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.SOURCES_DIR / safe_name
    dest.write_bytes(file_bytes)

    return {
        "source_path": f"sources/{safe_name}",
        "filename":    safe_name,
        "size_bytes":  len(file_bytes),
        "document_id": safe_doc_id or stem,
    }
