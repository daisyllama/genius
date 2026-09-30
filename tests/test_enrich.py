"""Tests for lyrics_analysis.pipeline.enrich."""

from __future__ import annotations

import pytest

from lyrics_analysis.pipeline.enrich import (
    needs_translation,
    normalize_emotion_scores,
    should_retry_translation,
)


class TestNeedsTranslation:
    def test_no_lyrics_returns_false(self):
        assert needs_translation("es", None) is False
        assert needs_translation("es", "") is False

    def test_english_returns_false(self):
        assert needs_translation("en", "hello") is False

    def test_missing_lang_returns_false(self):
        assert needs_translation(None, "hello") is False
        assert needs_translation("", "hello") is False

    def test_non_english_returns_true(self):
        assert needs_translation("es", "hola") is True

    def test_unknown_lang_returns_true(self):
        assert needs_translation("unknown", "some lyrics") is True

    @pytest.mark.xfail(strict=True, reason="original_lang comparison is case-sensitive; 'EN' is treated as non-English")
    def test_uppercase_english_returns_false(self):
        assert needs_translation("EN", "hello") is False


class TestShouldRetryTranslation:
    def test_empty_source_returns_false(self):
        assert should_retry_translation(None, "anything") is False
        assert should_retry_translation("", "anything") is False

    def test_none_translation_returns_true(self):
        assert should_retry_translation("hola", None) is True

    def test_empty_translation_returns_true(self):
        assert should_retry_translation("hola", "") is True

    def test_identical_after_strip_returns_true(self):
        assert should_retry_translation("hola mundo", "  hola mundo  ") is True

    def test_different_translation_returns_false(self):
        assert should_retry_translation("hola mundo", "hello world") is False


class TestNormalizeEmotionScores:
    def test_scores_sum_to_one(self):
        result = normalize_emotion_scores({"joy": 2.0, "sadness": 2.0})
        assert sum(result.values()) == pytest.approx(1.0)
        assert result["joy"] == pytest.approx(0.5)
        assert result["sadness"] == pytest.approx(0.5)

    def test_empty_dict(self):
        assert normalize_emotion_scores({}) == {}

    def test_all_zeros(self):
        result = normalize_emotion_scores({"joy": 0.0, "sadness": 0.0})
        assert result == {"joy": 0.0, "sadness": 0.0}

    def test_negative_total_returns_zeros(self):
        result = normalize_emotion_scores({"joy": -1.0, "sadness": -1.0})
        assert result == {"joy": 0.0, "sadness": 0.0}

    def test_preserves_keys(self):
        result = normalize_emotion_scores({"a": 1.0, "b": 3.0})
        assert set(result.keys()) == {"a", "b"}
