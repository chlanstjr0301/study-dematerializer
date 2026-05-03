"""
Gonghaebun CLI — entry point.

Usage:
    python -m gonghaebun.cli study <concept> --source-local <path> [options]
    python -m gonghaebun       study <concept> --source-local <path> [options]
    gonghaebun                 study <concept> --source-local <path> [options]

    python -m gonghaebun.cli build-bank --source-local <path> --bank-dir <dir> [options]
    gonghaebun                build-bank --source-local <path> --bank-dir <dir> [options]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gonghaebun",
        description="공부 해체 분석기 — AI Study Compiler",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    study = subparsers.add_parser("study", help="Run a new-concept study session.")
    study.add_argument("concept", help="Concept to study (e.g. 'compactness')")
    study.add_argument(
        "--source-local",
        required=True,
        metavar="PATH",
        help="Path to the local source Markdown file (required).",
    )
    study.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="Use the deterministic MockLLMClient (no API key needed).",
    )
    study.add_argument(
        "--no-interactive",
        action="store_true",
        default=False,
        help="Run in batch mode (no learner input collected).",
    )
    study.add_argument(
        "--runs-dir",
        default="data/gonghaebun/default/runs",
        metavar="DIR",
        help="Directory for session run artifacts. (default: data/gonghaebun/default/runs)",
    )
    study.add_argument(
        "--study-md",
        default="data/gonghaebun/default/STUDY.md",
        metavar="PATH",
        help="Path to STUDY.md. (default: data/gonghaebun/default/STUDY.md)",
    )
    study.add_argument(
        "--max-excerpt-chars",
        type=int,
        default=8000,
        metavar="N",
        help="Maximum characters in source excerpt. (default: 8000)",
    )

    # ------------------------------------------------------------------
    # build-bank subcommand
    # ------------------------------------------------------------------
    build_bank = subparsers.add_parser(
        "build-bank",
        help="Build a question bank from a source Markdown file.",
    )
    build_bank.add_argument(
        "--source-local",
        required=True,
        metavar="PATH",
        help="Path to the local source Markdown file (required).",
    )
    build_bank.add_argument(
        "--document-id",
        default=None,
        metavar="ID",
        help="Document ID slug (inferred from source filename if omitted).",
    )
    build_bank.add_argument(
        "--bank-dir",
        required=True,
        metavar="DIR",
        help="Directory for question-bank output artifacts (required).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "study":
        return _cmd_study(args)

    if args.command == "build-bank":
        return _cmd_build_bank(args)

    parser.print_help()
    return 1


def _cmd_study(args: argparse.Namespace) -> int:
    from gonghaebun.llm.mock import MockLLMClient
    from gonghaebun.pipeline.concept_resolver import ConceptNotFoundError
    from gonghaebun.pipeline.source_loader import SourceEmptyError, SourceNotFoundError
    from gonghaebun.session import run_new_concept_session

    # Validate --source-local explicitly for a clear error message
    source_path = Path(args.source_local)
    if not source_path.exists():
        print(
            f"Error: source material is required; Gonghaebun does not generate "
            f"study sessions from model prior alone. "
            f"Provide --source-local <path>.\n"
            f"(File not found: {source_path})",
            file=sys.stderr,
        )
        return 2

    if not args.mock:
        print(
            "Error: only --mock is supported in MVP 1. "
            "Real LLM providers are not yet integrated.",
            file=sys.stderr,
        )
        return 2

    llm = MockLLMClient()

    import uuid
    from pathlib import Path as _Path

    runs_dir = _Path(args.runs_dir)
    study_md_path = _Path(args.study_md)

    # Concept resolver runs inside run_new_concept_session, but we do a
    # quick pre-check here to give a clean CLI error before touching disk.
    try:
        from gonghaebun.pipeline.concept_resolver import resolve_concept
        concept = resolve_concept(args.concept)
    except ConceptNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    # Build session-specific output dir
    import uuid as _uuid
    session_id = _uuid.uuid4()
    output_dir = runs_dir / str(session_id)

    print(f"Starting session for concept: {concept.canonical_name}")
    print(f"Source: {source_path}")
    print(f"Output: {output_dir}")
    print()

    try:
        session = run_new_concept_session(
            concept_input=args.concept,
            source_path=source_path,
            llm=llm,
            output_dir=output_dir,
            study_md_path=study_md_path,
            interactive=not args.no_interactive,
        )
    except SourceNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except SourceEmptyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ConceptNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Session complete: {session.session_id}")
    print(f"Artifacts written to: {output_dir}")
    print()
    print("Artifacts:")
    for artifact in [
        "source_manifest.json",
        "source_excerpt.md",
        "concept_decomposition.json",
        "prerequisite_graph.json",
        "representation_cards.md",
        "self_explanation_prompt.md",
        "diagnosis.json",
        "recall_tasks.md",
        "STUDY.patch.md",
        "session.json",
    ]:
        path = output_dir / artifact
        status = "OK" if path.exists() else "MISSING"
        print(f"  [{status}] {artifact}")

    print()
    print(f"STUDY.md: {study_md_path}")

    return 0


def _cmd_build_bank(args: argparse.Namespace) -> int:
    from gonghaebun.bank_session import run_bank_session

    source_path = Path(args.source_local)
    if not source_path.exists():
        print(
            f"Error: source file not found: {source_path}",
            file=sys.stderr,
        )
        return 2

    document_id: str = args.document_id or source_path.stem
    bank_dir = Path(args.bank_dir)

    print(f"Building question bank from: {source_path}")
    print(f"Document ID : {document_id}")
    print(f"Output dir  : {bank_dir}")
    print()

    blocks, questions = run_bank_session(source_path, document_id, bank_dir)

    if not blocks:
        print(
            "Warning: no content blocks were parsed from the source file. "
            "The source may be empty or contain only short passages.",
            file=sys.stderr,
        )

    print(f"Blocks    : {len(blocks)}")
    print(f"Questions : {len(questions)}")
    print()
    print("Artifacts:")
    for name in ("blocks.generated.json", "questions.generated.json"):
        path = bank_dir / name
        status = "OK" if path.exists() else "MISSING"
        print(f"  [{status}] {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
