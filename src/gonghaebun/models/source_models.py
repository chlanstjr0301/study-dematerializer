from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

SourceCoverage = Literal["sufficient", "partial", "insufficient"]


@dataclass
class SourceWindow:
    start_char: int
    end_char: int
    text: str


@dataclass
class SourceManifest:
    source_path: str
    source_hash: str              # "sha256:..."
    source_size_chars: int
    concept_id: str
    keywords_searched: list[str] = field(default_factory=list)
    keywords_found: list[str] = field(default_factory=list)
    windows_extracted: int = 0
    source_coverage: SourceCoverage = "insufficient"
    excerpt_chars: int = 0
    excerpt_capped: bool = False
    grounding_mode: str = "local_private_source"
    extracted_at: str = ""       # ISO 8601
