"""
Parse an existing STUDY.md into a dict of ConceptRecords.

STUDY.md format (canonical):

## {concept_id}

**domain**: real_analysis
**overall_mastery**: unknown|partial|solid
**next_review**: YYYY-MM-DD

### Representations

| type           | mastery | last_reviewed |
|----------------|---------|---------------|
| formal         | unknown | —             |
...

### Prerequisites

| concept        | mastery | note |
...

### Misconceptions Encountered

- [x] "claim" → note (date)
- [ ] "claim" → unconfirmed

### Notes

> free text

---
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RepresentationRecord:
    type: str
    mastery: str
    last_reviewed: Optional[str]


@dataclass
class PrerequisiteRecord:
    concept: str
    mastery: str
    note: str = ""


@dataclass
class MisconceptionRecord:
    claim: str
    confirmed: bool  # True = [x], False = [ ]
    note: str = ""


@dataclass
class ConfusionMappingStatus:
    mapping: str           # e.g. "formal → counterexample"
    status: str            # "passed" or "failed"
    last_session: str      # ISO date


@dataclass
class ConceptRecord:
    concept_id: str
    domain: str = "real_analysis"
    overall_mastery: str = "unknown"
    next_review: Optional[str] = None
    representations: list[RepresentationRecord] = field(default_factory=list)
    prerequisites: list[PrerequisiteRecord] = field(default_factory=list)
    misconceptions: list[MisconceptionRecord] = field(default_factory=list)
    notes: str = ""
    confusion_mapping_status: list[ConfusionMappingStatus] = field(default_factory=list)
    active_misconceptions: list[str] = field(default_factory=list)
    next_recall_trigger: Optional[str] = None


def parse_study_md(path: Path) -> dict[str, ConceptRecord]:
    """
    Parse STUDY.md and return a mapping of concept_id → ConceptRecord.
    Returns an empty dict if the file does not exist.
    """
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")
    return _parse(text)


def _parse(text: str) -> dict[str, ConceptRecord]:
    records: dict[str, ConceptRecord] = {}
    # Split on ## headings (concept sections)
    sections = re.split(r'\n(?=## )', text)
    for section in sections:
        m = re.match(r'## ([^\n]+)', section)
        if not m:
            continue
        concept_id = m.group(1).strip()
        if concept_id.lower().startswith("study"):
            continue  # skip the root heading if any
        record = _parse_section(concept_id, section)
        records[concept_id] = record
    return records


def _parse_section(concept_id: str, text: str) -> ConceptRecord:
    record = ConceptRecord(concept_id=concept_id)

    # domain
    m = re.search(r'\*\*domain\*\*:\s*(\S+)', text)
    if m:
        record.domain = m.group(1)

    # overall_mastery
    m = re.search(r'\*\*overall_mastery\*\*:\s*(\S+)', text)
    if m:
        record.overall_mastery = m.group(1)

    # next_review
    m = re.search(r'\*\*next_review\*\*:\s*(\S+)', text)
    if m:
        record.next_review = m.group(1)

    # Representations table
    rep_section = _extract_subsection(text, "Representations")
    if rep_section:
        reps_raw = _parse_table(rep_section, ["type", "mastery", "last_reviewed"])
        record.representations = [
            RepresentationRecord(
                r["type"],
                r.get("mastery", "unknown"),
                r.get("last_reviewed") if r.get("last_reviewed") not in (None, "—", "") else None,
            )
            for r in reps_raw
        ]

    # Prerequisites table
    prereq_section = _extract_subsection(text, "Prerequisites")
    if prereq_section:
        prereqs = _parse_table(prereq_section, ["concept", "mastery", "note"])
        record.prerequisites = [
            PrerequisiteRecord(r["concept"], r["mastery"], r.get("note", ""))
            for r in prereqs
        ]

    # Misconceptions
    misc_section = _extract_subsection(text, "Misconceptions Encountered")
    if misc_section:
        record.misconceptions = _parse_misconceptions(misc_section)

    # Confusion Summary
    confusion_section = _extract_subsection(text, "Confusion Summary")
    if confusion_section:
        _parse_confusion_summary(record, confusion_section)

    # Notes
    notes_section = _extract_subsection(text, "Notes")
    if notes_section:
        record.notes = notes_section.strip()

    return record


def _extract_subsection(text: str, heading: str) -> str:
    pattern = rf'### {re.escape(heading)}\n(.*?)(?=\n### |\n## |$)'
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1) if m else ""


def _parse_table(text: str, columns: list[str]) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if parts[0].lower() in (c.lower() for c in columns):
            continue  # header row
        if len(parts) >= len(columns):
            rows.append(dict(zip(columns, parts)))
    return rows


def _parse_misconceptions(text: str) -> list[MisconceptionRecord]:
    result = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'- \[(x| )\] (.+)', line)
        if m:
            confirmed = m.group(1) == "x"
            rest = m.group(2)
            result.append(MisconceptionRecord(claim=rest, confirmed=confirmed))
    return result


def _parse_confusion_summary(record: ConceptRecord, text: str) -> None:
    """Parse the Confusion Summary subsection into ConceptRecord fields."""
    # Mapping status table
    rows = _parse_table(text, ["mapping", "status", "last_session"])
    record.confusion_mapping_status = [
        ConfusionMappingStatus(
            mapping=r["mapping"],
            status=r["status"],
            last_session=r["last_session"],
        )
        for r in rows
    ]

    # Active misconceptions line
    m = re.search(r'\*\*Active misconceptions\*\*:\s*(.+)', text)
    if m:
        raw = m.group(1).strip()
        if raw and raw != "—":
            record.active_misconceptions = [t.strip() for t in raw.split(",") if t.strip()]

    # Next recall trigger line
    m = re.search(r'\*\*Next recall trigger\*\*:\s*(.+)', text)
    if m:
        raw = m.group(1).strip()
        if raw and raw != "—":
            record.next_recall_trigger = raw
