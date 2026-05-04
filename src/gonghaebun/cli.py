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

from gonghaebun.llm.config import DEFAULT_OPENAI_MODEL


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

    # ------------------------------------------------------------------
    # review-bank subcommand
    # ------------------------------------------------------------------
    review_bank = subparsers.add_parser(
        "review-bank",
        help="Interactively review generated questions (accept / reject).",
    )
    review_bank.add_argument(
        "--questions",
        required=True,
        metavar="PATH",
        help="Path to questions.generated.json (required).",
    )
    review_bank.add_argument(
        "--output-dir",
        required=True,
        metavar="DIR",
        help="Directory to write review artifacts (required).",
    )

    # ------------------------------------------------------------------
    # recall-session subcommand
    # ------------------------------------------------------------------
    recall_session = subparsers.add_parser(
        "recall-session",
        help="Run a white-recall study session.",
    )
    recall_session.add_argument(
        "--questions",
        required=True,
        metavar="PATH",
        help="Path to questions.accepted.json (required).",
    )
    recall_session.add_argument(
        "--concept",
        required=True,
        metavar="ID",
        help="Concept ID to record in STUDY.md (required).",
    )
    recall_session.add_argument(
        "--study-md",
        default="data/gonghaebun/default/STUDY.md",
        metavar="PATH",
        help="Path to STUDY.md. (default: data/gonghaebun/default/STUDY.md)",
    )
    recall_session.add_argument(
        "--runs-dir",
        default="data/gonghaebun/default/runs",
        metavar="DIR",
        help="Directory for session run artifacts. (default: data/gonghaebun/default/runs)",
    )
    recall_session.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of questions to ask (default: all).",
    )
    recall_session.add_argument(
        "--grader",
        choices=["self", "llm", "mock"],
        default="self",
        help="Grading mode: self (default), llm, or mock.",
    )
    recall_session.add_argument(
        "--provider",
        default="openai",
        metavar="PROVIDER",
        help="LLM provider (only used with --grader llm). (default: openai)",
    )
    recall_session.add_argument(
        "--model",
        default=DEFAULT_OPENAI_MODEL,
        metavar="MODEL",
        help=f"LLM model ID (only used with --grader llm). (default: {DEFAULT_OPENAI_MODEL})",
    )
    recall_session.add_argument(
        "--no-interactive",
        action="store_true",
        default=False,
        help="Batch mode: skip input prompts (uses empty learner responses).",
    )
    recall_session.add_argument(
        "--default-score",
        type=int,
        default=2,
        metavar="0-3",
        help="Self-grader score when --no-interactive is set. (default: 2)",
    )
    recall_session.add_argument(
        "--default-answer",
        default=None,
        metavar="TEXT",
        help="Learner answer text for --no-interactive + --grader llm.",
    )

    # ------------------------------------------------------------------
    # review-due subcommand
    # ------------------------------------------------------------------
    review_due = subparsers.add_parser(
        "review-due",
        help="Review all concepts whose next_review date is today or past.",
    )
    review_due.add_argument(
        "--bank-root",
        default=None,
        metavar="DIR",
        help="Root directory; looks for {bank-root}/{concept}/questions.accepted.json.",
    )
    review_due.add_argument(
        "--questions",
        default=None,
        metavar="PATH",
        help="Explicit path to questions.accepted.json (overrides --bank-root lookup).",
    )
    review_due.add_argument(
        "--study-md",
        default="data/gonghaebun/default/STUDY.md",
        metavar="PATH",
        help="Path to STUDY.md. (default: data/gonghaebun/default/STUDY.md)",
    )
    review_due.add_argument(
        "--runs-dir",
        default="data/gonghaebun/default/runs",
        metavar="DIR",
        help="Directory for session run artifacts. (default: data/gonghaebun/default/runs)",
    )
    review_due.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum questions per concept (default: all).",
    )
    review_due.add_argument(
        "--grader",
        choices=["self", "llm", "mock"],
        default="self",
        help="Grading mode: self (default), llm, or mock.",
    )
    review_due.add_argument(
        "--provider",
        default="openai",
        metavar="PROVIDER",
        help="LLM provider (only used with --grader llm). (default: openai)",
    )
    review_due.add_argument(
        "--model",
        default=DEFAULT_OPENAI_MODEL,
        metavar="MODEL",
        help=f"LLM model ID (only used with --grader llm). (default: {DEFAULT_OPENAI_MODEL})",
    )
    review_due.add_argument(
        "--no-interactive",
        action="store_true",
        default=False,
        help="Batch mode: skip input prompts.",
    )
    review_due.add_argument(
        "--default-score",
        type=int,
        default=2,
        metavar="0-3",
        help="Self-grader score when --no-interactive is set. (default: 2)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "study":
        return _cmd_study(args)

    if args.command == "build-bank":
        return _cmd_build_bank(args)

    if args.command == "review-bank":
        return _cmd_review_bank(args)

    if args.command == "recall-session":
        return _cmd_recall_session(args)

    if args.command == "review-due":
        return _cmd_review_due(args)

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


def _cmd_review_bank(args: argparse.Namespace) -> int:
    from gonghaebun.review.review_cli import run_review_cli

    questions_path = Path(args.questions)
    output_dir = Path(args.output_dir)

    if not questions_path.exists():
        print(f"Error: questions file not found: {questions_path}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Reviewing questions from: {questions_path}")
    print(f"Output dir              : {output_dir}")
    print()

    records = run_review_cli(questions_path, output_dir)
    print(f"Review complete. {len(records)} question(s) reviewed.")
    return 0


def _make_grader(grader_type: str, model: str | None = None):
    """Instantiate the requested grader. Returns an AnswerGrader.

    Delegates to gonghaebun.grading.factory.make_grader; handles LLMAPIKeyError
    by printing to stderr and exiting (CLI-appropriate behaviour).
    """
    from gonghaebun.grading.factory import make_grader
    from gonghaebun.llm.errors import LLMAPIKeyError
    try:
        return make_grader(grader_type, model)
    except LLMAPIKeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)


def _cmd_recall_session(args: argparse.Namespace) -> int:
    import uuid
    from datetime import datetime, timezone

    from gonghaebun.study_loop.question_loader import load_recall_questions
    from gonghaebun.study_loop.session_writer import build_study_session, write_session_artifacts
    from gonghaebun.study_loop.white_recall import run_white_recall_session

    questions_path = Path(args.questions)
    if not questions_path.exists():
        print(f"Error: questions file not found: {questions_path}", file=sys.stderr)
        return 2

    # --no-interactive + --grader llm guard
    if args.no_interactive and args.grader == "llm" and not args.default_answer:
        print(
            "Warning: --no-interactive with --grader llm will grade empty answers. "
            "Proceed with caution.",
            file=sys.stderr,
        )

    grader = _make_grader(args.grader, getattr(args, "model", DEFAULT_OPENAI_MODEL))

    questions = load_recall_questions(questions_path, limit=args.limit)
    if not questions:
        print("No questions found in the question bank.")
        return 0

    started_at = datetime.now(timezone.utc).isoformat()
    session_id = str(uuid.uuid4())

    print(f"Recall session: {session_id}")
    print(f"Concept       : {args.concept}")
    print(f"Questions     : {len(questions)}")
    print(f"Grader        : {args.grader}")
    print()

    default_answer: str = args.default_answer or ""

    attempt_results = run_white_recall_session(
        questions,
        grader,
        no_interactive=args.no_interactive,
        default_answer=default_answer,
    )

    ended_at = datetime.now(timezone.utc).isoformat()

    session = build_study_session(
        session_id=session_id,
        concept_id=args.concept,
        source_path=str(questions_path),
        attempt_results=attempt_results,
        started_at=started_at,
        ended_at=ended_at,
        grader_type=args.grader,
    )

    output_dir = write_session_artifacts(
        session=session,
        attempt_results=attempt_results,
        runs_dir=Path(args.runs_dir),
        study_md_path=Path(args.study_md),
        grader_type=args.grader,
    )

    print(f"Session complete.")
    print(f"Artifacts : {output_dir}")
    print(f"STUDY.md  : {args.study_md}")
    return 0


def _cmd_review_due(args: argparse.Namespace) -> int:
    import uuid
    from datetime import datetime, timezone

    from gonghaebun.study_loop.question_loader import load_recall_questions
    from gonghaebun.study_loop.review_due import find_question_bank, get_due_concepts
    from gonghaebun.study_loop.session_writer import build_study_session, write_session_artifacts
    from gonghaebun.study_loop.white_recall import run_white_recall_session

    study_md_path = Path(args.study_md)
    runs_dir = Path(args.runs_dir)

    due_concepts = get_due_concepts(study_md_path)

    if not due_concepts:
        print("No concepts are due for review.")
        return 0

    print(f"Due concepts: {', '.join(due_concepts)}")
    print()

    grader = _make_grader(args.grader, getattr(args, "model", DEFAULT_OPENAI_MODEL))

    for concept_id in due_concepts:
        # Resolve question bank path
        if args.questions:
            questions_path = Path(args.questions)
            if not questions_path.exists():
                print(
                    f"Error: questions file not found: {questions_path}",
                    file=sys.stderr,
                )
                return 2
        else:
            if not args.bank_root:
                print(
                    "Error: --bank-root or --questions is required.",
                    file=sys.stderr,
                )
                return 2
            try:
                questions_path = find_question_bank(Path(args.bank_root), concept_id)
            except FileNotFoundError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 2

        questions = load_recall_questions(questions_path, limit=args.limit)
        if not questions:
            print(f"  [{concept_id}] No questions found — skipping.")
            continue

        started_at = datetime.now(timezone.utc).isoformat()
        session_id = str(uuid.uuid4())

        print(f"  [{concept_id}] {len(questions)} question(s), grader={args.grader}")

        attempt_results = run_white_recall_session(
            questions,
            grader,
            no_interactive=args.no_interactive,
            default_answer="",
        )

        ended_at = datetime.now(timezone.utc).isoformat()

        session = build_study_session(
            session_id=session_id,
            concept_id=concept_id,
            source_path=str(questions_path),
            attempt_results=attempt_results,
            started_at=started_at,
            ended_at=ended_at,
            grader_type=args.grader,
        )

        output_dir = write_session_artifacts(
            session=session,
            attempt_results=attempt_results,
            runs_dir=runs_dir,
            study_md_path=study_md_path,
            grader_type=args.grader,
        )

        print(f"  [{concept_id}] artifacts → {output_dir}")

    print()
    print(f"STUDY.md: {study_md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
