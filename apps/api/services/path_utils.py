"""
Shared path-validation helpers.

- validate_slug: strict validation for concept_id / document_id (rejects invalid, never silently rewrites)
- sanitize_filename_stem: lenient sanitization for uploaded filenames (replaces unsafe chars with '_')
"""
from __future__ import annotations

import re

_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")
_MAX_LEN = 80


def validate_slug(value: str, *, field_name: str) -> str:
    """
    Strictly validate a concept_id or document_id slug.
    Rejects — does NOT silently rewrite — invalid values.

    Rules:
    - strip() leading/trailing whitespace
    - replace spaces with underscores (only whitespace normalisation allowed)
    - reject empty
    - reject ".", "..", values containing "/", "\\", or "."
    - reject anything not matching ^[A-Za-z0-9_-]+$
    - enforce max length 80
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name!r} must not be empty.")
    value = value.strip().replace(" ", "_")
    if "." in value or "/" in value or "\\" in value:
        raise ValueError(
            f"{field_name!r} contains disallowed characters ('.', '/', '\\\\')."
        )
    if not _SLUG_PATTERN.match(value):
        raise ValueError(
            f"{field_name!r} must contain only letters, digits, hyphens, and underscores. "
            f"Got: {value!r}"
        )
    if len(value) > _MAX_LEN:
        raise ValueError(f"{field_name!r} exceeds maximum length of {_MAX_LEN}.")
    return value


def sanitize_filename_stem(value: str) -> str:
    """
    Sanitize an uploaded filename stem for safe storage.
    May replace unsafe characters with '_'; still rejects empty / traversal.
    Used only for the uploaded file's own name, not for concept_id / document_id.
    """
    if not value or not value.strip():
        raise ValueError("Filename stem must not be empty.")
    value = value.strip()
    if value in (".", "..") or "/" in value or "\\" in value:
        raise ValueError("Filename contains path traversal characters.")
    safe = re.sub(r"[^\w\-]", "_", value)[:_MAX_LEN]
    if not safe:
        raise ValueError("Filename is empty after sanitization.")
    return safe
