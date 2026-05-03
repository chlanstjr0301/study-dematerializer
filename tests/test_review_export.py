"""Tests for review/review_cli.py (MVP2 Step 6)."""
from __future__ import annotations

import pytest

from gonghaebun.models.question_bank import Evidence, Question, ReviewRecord
from gonghaebun.pipeline.io import export_accepted, load_questions, save_questions
from gonghaebun.review.review_cli import (
    apply_review_action,
    review_questions,
    run_review_cli,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEXT = (
    "A subset K of a metric space X is compact if every open cover has a "
    "finite subcover. Standard definition in real analysis."
)
_REVIEWED_AT = "2026-01-01T00:00:00+00:00"


def make_question(
    question_id: str = "q_doc_b000001_R01",
    status: str = "candidate",
    question_text: str = "State the definition of compactness.",
    expected_answer: str = _TEXT,
) -> Question:
    return Question(
        question_id=question_id,
        document_id="doc",
        source_block_id="doc_b000001",
        question_type="definition_recall",
        difficulty="medium",
        question=question_text,
        expected_answer=expected_answer,
        evidence=Evidence(
            source_text=_TEXT,
            source_file="doc.md",
            start_line=5,
            end_line=7,
            text_hash="deadbeef",
        ),
        rule_id="R01_definition_recall",
        status=status,  # type: ignore[arg-type]
        created_at=_REVIEWED_AT,
        updated_at=_REVIEWED_AT,
    )


# ---------------------------------------------------------------------------
# apply_review_action — accept
# ---------------------------------------------------------------------------


class TestApplyReviewActionAccept:
    def test_status_becomes_accepted(self):
        q = make_question()
        apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert q.status == "accepted"

    def test_shorthand_a_accepted(self):
        q = make_question()
        apply_review_action(q, "a", 0, reviewed_at=_REVIEWED_AT)
        assert q.status == "accepted"

    def test_returns_review_record(self):
        q = make_question()
        record = apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert isinstance(record, ReviewRecord)

    def test_record_action_is_accept(self):
        q = make_question()
        record = apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert record.action == "accept"

    def test_record_before_question_preserved(self):
        q = make_question()
        original_text = q.question
        record = apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert record.before_question == original_text

    def test_record_after_question_is_none(self):
        q = make_question()
        record = apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert record.after_question is None

    def test_record_after_expected_answer_is_none(self):
        q = make_question()
        record = apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert record.after_expected_answer is None


# ---------------------------------------------------------------------------
# apply_review_action — reject
# ---------------------------------------------------------------------------


class TestApplyReviewActionReject:
    def test_status_becomes_rejected(self):
        q = make_question()
        apply_review_action(q, "reject", 0, reviewed_at=_REVIEWED_AT)
        assert q.status == "rejected"

    def test_shorthand_r_rejected(self):
        q = make_question()
        apply_review_action(q, "r", 0, reviewed_at=_REVIEWED_AT)
        assert q.status == "rejected"

    def test_record_action_is_reject(self):
        q = make_question()
        record = apply_review_action(q, "r", 0, reviewed_at=_REVIEWED_AT)
        assert record.action == "reject"


# ---------------------------------------------------------------------------
# apply_review_action — skip
# ---------------------------------------------------------------------------


class TestApplyReviewActionSkip:
    def test_status_becomes_skipped(self):
        q = make_question()
        apply_review_action(q, "skip", 0, reviewed_at=_REVIEWED_AT)
        assert q.status == "skipped"

    def test_shorthand_s_skipped(self):
        q = make_question()
        apply_review_action(q, "s", 0, reviewed_at=_REVIEWED_AT)
        assert q.status == "skipped"

    def test_record_action_is_skip(self):
        q = make_question()
        record = apply_review_action(q, "s", 0, reviewed_at=_REVIEWED_AT)
        assert record.action == "skip"


# ---------------------------------------------------------------------------
# apply_review_action — edit
# ---------------------------------------------------------------------------


class TestApplyReviewActionEdit:
    def test_status_becomes_edited(self):
        q = make_question()
        apply_review_action(q, "edit", 0, edited_question="New Q", reviewed_at=_REVIEWED_AT)
        assert q.status == "edited"

    def test_shorthand_e_edited(self):
        q = make_question()
        apply_review_action(q, "e", 0, edited_question="New Q", reviewed_at=_REVIEWED_AT)
        assert q.status == "edited"

    def test_question_text_updated(self):
        q = make_question()
        apply_review_action(q, "edit", 0, edited_question="Updated question text", reviewed_at=_REVIEWED_AT)
        assert q.question == "Updated question text"

    def test_expected_answer_updated(self):
        q = make_question()
        apply_review_action(q, "edit", 0, edited_expected_answer="Updated answer", reviewed_at=_REVIEWED_AT)
        assert q.expected_answer == "Updated answer"

    def test_after_question_in_record(self):
        q = make_question()
        record = apply_review_action(q, "edit", 0, edited_question="New Q", reviewed_at=_REVIEWED_AT)
        assert record.after_question == "New Q"

    def test_after_expected_answer_in_record(self):
        q = make_question()
        record = apply_review_action(q, "edit", 0, edited_expected_answer="New A", reviewed_at=_REVIEWED_AT)
        assert record.after_expected_answer == "New A"

    def test_before_fields_capture_original_values(self):
        original_q = "State the definition of compactness."
        original_a = _TEXT
        q = make_question(question_text=original_q, expected_answer=original_a)
        record = apply_review_action(
            q, "edit", 0,
            edited_question="New Q",
            edited_expected_answer="New A",
            reviewed_at=_REVIEWED_AT,
        )
        assert record.before_question == original_q
        assert record.before_expected_answer == original_a

    def test_edit_without_changes_leaves_text_unchanged(self):
        original_q = q_text = "State the definition of compactness."
        q = make_question(question_text=q_text)
        apply_review_action(q, "edit", 0, reviewed_at=_REVIEWED_AT)
        # No edited_question provided — text must remain unchanged
        assert q.question == original_q


# ---------------------------------------------------------------------------
# apply_review_action — unknown action
# ---------------------------------------------------------------------------


class TestApplyReviewActionUnknown:
    def test_unknown_action_raises(self):
        q = make_question()
        with pytest.raises(ValueError, match="Unknown review action"):
            apply_review_action(q, "approve", 0)

    def test_empty_string_raises(self):
        q = make_question()
        with pytest.raises(ValueError):
            apply_review_action(q, "", 0)


# ---------------------------------------------------------------------------
# review_id determinism
# ---------------------------------------------------------------------------


class TestReviewId:
    def test_review_id_format(self):
        q = make_question()
        record = apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert record.review_id == f"rev_{q.question_id}_000000"

    def test_review_id_zero_padded_index(self):
        q = make_question()
        record = apply_review_action(q, "accept", 7, reviewed_at=_REVIEWED_AT)
        assert record.review_id == f"rev_{q.question_id}_000007"

    def test_reviewed_at_injected(self):
        q = make_question()
        record = apply_review_action(q, "accept", 0, reviewed_at=_REVIEWED_AT)
        assert record.reviewed_at == _REVIEWED_AT

    def test_reviewed_at_defaults_to_now(self):
        q = make_question()
        record = apply_review_action(q, "accept", 0)
        assert record.reviewed_at  # non-empty
        assert "T" in record.reviewed_at  # ISO 8601


# ---------------------------------------------------------------------------
# review_questions
# ---------------------------------------------------------------------------


class TestReviewQuestions:
    def _make_pair(self):
        questions = [
            make_question("q_a"),
            make_question("q_b"),
        ]
        return questions

    def test_applies_multiple_actions(self):
        questions = self._make_pair()
        actions = [
            {"question_id": "q_a", "action": "accept", "reviewed_at": _REVIEWED_AT},
            {"question_id": "q_b", "action": "reject", "reviewed_at": _REVIEWED_AT},
        ]
        _, records = review_questions(questions, actions)
        assert len(records) == 2
        assert records[0].action == "accept"
        assert records[1].action == "reject"

    def test_status_updated_on_questions(self):
        questions = self._make_pair()
        actions = [
            {"question_id": "q_a", "action": "accept", "reviewed_at": _REVIEWED_AT},
        ]
        updated, _ = review_questions(questions, actions)
        accepted = next(q for q in updated if q.question_id == "q_a")
        assert accepted.status == "accepted"

    def test_original_order_preserved(self):
        questions = self._make_pair()  # q_a, q_b
        actions = [
            {"question_id": "q_b", "action": "accept", "reviewed_at": _REVIEWED_AT},
            {"question_id": "q_a", "action": "reject", "reviewed_at": _REVIEWED_AT},
        ]
        updated, _ = review_questions(questions, actions)
        assert updated[0].question_id == "q_a"
        assert updated[1].question_id == "q_b"

    def test_unknown_question_id_raises(self):
        questions = [make_question("q_a")]
        actions = [{"question_id": "q_nonexistent", "action": "accept"}]
        with pytest.raises(ValueError, match="question_id"):
            review_questions(questions, actions)

    def test_empty_actions_returns_unchanged_questions(self):
        questions = self._make_pair()
        updated, records = review_questions(questions, [])
        assert records == []
        assert all(q.status == "candidate" for q in updated)

    def test_edit_action_with_new_text(self):
        questions = [make_question("q_a")]
        actions = [
            {
                "question_id": "q_a",
                "action": "edit",
                "edited_question": "Revised question",
                "reviewed_at": _REVIEWED_AT,
            }
        ]
        updated, records = review_questions(questions, actions)
        assert updated[0].question == "Revised question"
        assert records[0].after_question == "Revised question"

    def test_review_index_increments_per_action(self):
        questions = self._make_pair()
        actions = [
            {"question_id": "q_a", "action": "accept", "reviewed_at": _REVIEWED_AT},
            {"question_id": "q_b", "action": "reject", "reviewed_at": _REVIEWED_AT},
        ]
        _, records = review_questions(questions, actions)
        assert records[0].review_id.endswith("_000000")
        assert records[1].review_id.endswith("_000001")


# ---------------------------------------------------------------------------
# export_accepted after review
# ---------------------------------------------------------------------------


class TestExportAfterReview:
    def test_export_accepted_after_review(self, tmp_path):
        questions = [
            make_question("q_a"),
            make_question("q_b"),
            make_question("q_c"),
        ]
        actions = [
            {"question_id": "q_a", "action": "accept", "reviewed_at": _REVIEWED_AT},
            {"question_id": "q_b", "action": "reject", "reviewed_at": _REVIEWED_AT},
            {"question_id": "q_c", "action": "skip",   "reviewed_at": _REVIEWED_AT},
        ]
        updated, _ = review_questions(questions, actions)
        out = tmp_path / "accepted.json"
        accepted = export_accepted(updated, out)
        assert len(accepted) == 1
        assert accepted[0].question_id == "q_a"
        loaded = load_questions(out)
        assert len(loaded) == 1
        assert loaded[0].question_id == "q_a"

    def test_export_accepted_writes_only_accepted(self, tmp_path):
        questions = [make_question("q_a", status="accepted"), make_question("q_b", status="rejected")]
        out = tmp_path / "accepted.json"
        export_accepted(questions, out)
        loaded = load_questions(out)
        assert all(q.status == "accepted" for q in loaded)


# ---------------------------------------------------------------------------
# run_review_cli (monkeypatched input)
# ---------------------------------------------------------------------------


class TestRunReviewCli:
    def _write_questions(self, tmp_path, questions):
        path = tmp_path / "questions.generated.json"
        save_questions(path, questions)
        return path

    def test_accept_one_then_quit_writes_files(self, tmp_path, monkeypatch):
        questions = [make_question("q_a"), make_question("q_b")]
        q_path = self._write_questions(tmp_path, questions)
        out_dir = tmp_path / "review"

        # q_a comes first alphabetically; accept it, then quit before q_b
        inputs = iter(["a", "q"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        records = run_review_cli(q_path, out_dir)

        assert len(records) == 1
        assert records[0].action == "accept"
        assert (out_dir / "questions.reviewed.json").exists()
        assert (out_dir / "questions.accepted.json").exists()
        assert (out_dir / "review_records.json").exists()

    def test_accepted_question_appears_in_accepted_file(self, tmp_path, monkeypatch):
        questions = [make_question("q_a")]
        q_path = self._write_questions(tmp_path, questions)
        out_dir = tmp_path / "review"

        monkeypatch.setattr("builtins.input", lambda _: "a")

        run_review_cli(q_path, out_dir)
        loaded = load_questions(out_dir / "questions.accepted.json")
        assert len(loaded) == 1
        assert loaded[0].question_id == "q_a"

    def test_eof_saves_progress(self, tmp_path, monkeypatch):
        questions = [make_question("q_a")]
        q_path = self._write_questions(tmp_path, questions)
        out_dir = tmp_path / "review"

        def raise_eof(_):
            raise EOFError()

        monkeypatch.setattr("builtins.input", raise_eof)
        records = run_review_cli(q_path, out_dir)
        assert records == []
        assert (out_dir / "questions.reviewed.json").exists()

    def test_edit_action_updates_question(self, tmp_path, monkeypatch):
        questions = [make_question("q_a")]
        q_path = self._write_questions(tmp_path, questions)
        out_dir = tmp_path / "review"

        # "e" to edit, then provide new question, new answer
        inputs = iter(["e", "Revised question", "Revised answer"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        records = run_review_cli(q_path, out_dir)
        assert len(records) == 1
        assert records[0].action == "edit"
        loaded = load_questions(out_dir / "questions.reviewed.json")
        edited = next(q for q in loaded if q.question_id == "q_a")
        assert edited.status == "edited"
        assert edited.question == "Revised question"
        assert edited.expected_answer == "Revised answer"

    def test_unknown_action_skips_without_crashing(self, tmp_path, monkeypatch):
        questions = [make_question("q_a")]
        q_path = self._write_questions(tmp_path, questions)
        out_dir = tmp_path / "review"

        # First input is bad, second is accept
        inputs = iter(["zzz", "a"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        records = run_review_cli(q_path, out_dir)
        # "zzz" is rejected without crashing; "a" accepts
        assert len(records) == 1
        assert records[0].action == "accept"

    def test_only_candidates_are_presented(self, tmp_path, monkeypatch):
        questions = [
            make_question("q_a", status="accepted"),   # already reviewed
            make_question("q_b", status="candidate"),  # should be reviewed
        ]
        q_path = self._write_questions(tmp_path, questions)
        out_dir = tmp_path / "review"

        # Only one candidate: one input needed
        monkeypatch.setattr("builtins.input", lambda _: "s")

        records = run_review_cli(q_path, out_dir)
        # Only q_b is a candidate
        assert len(records) == 1
        assert records[0].question_id == "q_b"


# ---------------------------------------------------------------------------
# No MVP1 imports check
# ---------------------------------------------------------------------------


class TestNoMVP1Imports:
    def test_recall_orchestrator_not_imported(self):
        import inspect

        import gonghaebun.review.review_cli as rc

        src = inspect.getsource(rc)
        assert "recall_orchestrator" not in src

    def test_mvp1_session_not_imported(self):
        import inspect

        import gonghaebun.review.review_cli as rc

        src = inspect.getsource(rc)
        assert "from gonghaebun.session" not in src
        assert "import session" not in src
