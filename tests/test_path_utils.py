"""
Unit tests for apps.api.services.path_utils.
"""
from __future__ import annotations

import pytest

from apps.api.services.path_utils import sanitize_filename_stem, validate_slug


class TestValidateSlug:
    def test_valid_slug(self):
        assert validate_slug("compactness", field_name="concept_id") == "compactness"

    def test_valid_slug_with_hyphen(self):
        assert validate_slug("my-concept", field_name="concept_id") == "my-concept"

    def test_valid_slug_with_underscore(self):
        assert validate_slug("my_concept", field_name="concept_id") == "my_concept"

    def test_spaces_converted_to_underscores(self):
        assert validate_slug("my concept", field_name="concept_id") == "my_concept"

    def test_leading_trailing_whitespace_stripped(self):
        assert validate_slug("  compactness  ", field_name="concept_id") == "compactness"

    def test_dotdot_raises(self):
        with pytest.raises(ValueError, match="concept_id"):
            validate_slug("../evil", field_name="concept_id")

    def test_slash_raises(self):
        with pytest.raises(ValueError, match="concept_id"):
            validate_slug("compactness/evil", field_name="concept_id")

    def test_backslash_raises(self):
        with pytest.raises(ValueError, match="concept_id"):
            validate_slug("path\\traversal", field_name="concept_id")

    def test_dot_raises(self):
        with pytest.raises(ValueError, match="concept_id"):
            validate_slug(".", field_name="concept_id")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="concept_id"):
            validate_slug("", field_name="concept_id")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="concept_id"):
            validate_slug("   ", field_name="concept_id")

    def test_exceeds_max_len_raises(self):
        long_val = "a" * 81
        with pytest.raises(ValueError, match="maximum length"):
            validate_slug(long_val, field_name="concept_id")

    def test_exactly_max_len_ok(self):
        val = "a" * 80
        assert validate_slug(val, field_name="concept_id") == val

    def test_special_chars_raise(self):
        with pytest.raises(ValueError):
            validate_slug("concept@id", field_name="concept_id")

    def test_field_name_in_message(self):
        with pytest.raises(ValueError, match="document_id"):
            validate_slug("../evil", field_name="document_id")


class TestSanitizeFilenameStem:
    def test_clean_name(self):
        assert sanitize_filename_stem("sample_source") == "sample_source"

    def test_spaces_replaced(self):
        result = sanitize_filename_stem("my file")
        assert " " not in result

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            sanitize_filename_stem("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            sanitize_filename_stem("   ")

    def test_dotdot_raises(self):
        with pytest.raises(ValueError, match="traversal"):
            sanitize_filename_stem("../evil")

    def test_slash_raises(self):
        with pytest.raises(ValueError, match="traversal"):
            sanitize_filename_stem("dir/file")

    def test_backslash_raises(self):
        with pytest.raises(ValueError, match="traversal"):
            sanitize_filename_stem("dir\\file")

    def test_unsafe_chars_replaced(self):
        result = sanitize_filename_stem("my@file!name")
        assert "@" not in result
        assert "!" not in result

    def test_truncated_to_max_len(self):
        result = sanitize_filename_stem("a" * 100)
        assert len(result) <= 80
