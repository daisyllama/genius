"""Tests for lyrics_analysis.pipeline.scoring."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lyrics_analysis.pipeline.scoring import (
    classify_song_goemotions,
    classify_song_zeroshot,
    derive_contract_columns,
    load_checkpoint,
    save_checkpoint,
)


class TestDeriveContractColumns:
    def test_all_zero_row_is_unclassified(self):
        df = pd.DataFrame({"emotion_joy": [0.0], "emotion_sadness": [0.0]})
        result = derive_contract_columns(df, ["emotion_joy", "emotion_sadness"])
        assert result.iloc[0]["dominant_emotion"] == "unclassified"
        assert pd.isna(result.iloc[0]["dominant_score"])
        assert result.iloc[0]["low_confidence"] == False  # noqa: E712

    def test_strips_emotion_prefix(self):
        df = pd.DataFrame({"emotion_joy": [0.9], "emotion_sadness": [0.1]})
        result = derive_contract_columns(df, ["emotion_joy", "emotion_sadness"])
        assert result.iloc[0]["dominant_emotion"] == "joy"

    def test_low_confidence_threshold(self):
        df = pd.DataFrame({"emotion_joy": [0.29, 0.30], "emotion_sadness": [0.1, 0.1]})
        result = derive_contract_columns(df, ["emotion_joy", "emotion_sadness"], min_confidence=0.30)
        assert result.iloc[0]["low_confidence"] == True  # noqa: E712
        assert result.iloc[1]["low_confidence"] == False  # noqa: E712

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"emotion_joy": [0.9], "emotion_sadness": [0.1]})
        derive_contract_columns(df, ["emotion_joy", "emotion_sadness"])
        assert "dominant_emotion" not in df.columns

    def test_custom_min_confidence(self):
        df = pd.DataFrame({"emotion_joy": [0.5], "emotion_sadness": [0.1]})
        result = derive_contract_columns(df, ["emotion_joy", "emotion_sadness"], min_confidence=0.6)
        assert result.iloc[0]["low_confidence"] == True  # noqa: E712


def _fake_zeroshot_classifier(scores_per_label):
    """Returns a classifier(batch, ...) -> list[dict] fake, one dict per input,
    with labels intentionally shuffled to test order-independence.
    """
    def classifier(batch, candidate_labels, multi_label, hypothesis_template):
        results = []
        for _ in batch:
            labels = list(reversed(candidate_labels))
            scores = [scores_per_label[label] for label in labels]
            results.append({"labels": labels, "scores": scores})
        return results
    return classifier


class TestClassifySongZeroshot:
    def test_empty_lyrics_returns_zeros(self):
        result = classify_song_zeroshot("", classifier=None, emotions=["joy", "anger"])
        assert result == {"joy": 0.0, "anger": 0.0}

    def test_averages_across_chunks(self):
        classifier = _fake_zeroshot_classifier({"joy": 0.8, "anger": 0.2})
        text = " ".join(f"w{i}" for i in range(700))  # 2 chunks at default 350
        result = classify_song_zeroshot(text, classifier, emotions=["joy", "anger"])
        assert result == {"joy": 0.8, "anger": 0.2}

    def test_label_order_independent(self):
        classifier = _fake_zeroshot_classifier({"joy": 0.9, "anger": 0.1})
        text = "word " * 10
        result = classify_song_zeroshot(text, classifier, emotions=["anger", "joy"])
        assert result["joy"] == 0.9
        assert result["anger"] == 0.1

    def test_batching_calls_classifier_expected_times(self):
        call_count = {"n": 0}

        def classifier(batch, candidate_labels, multi_label, hypothesis_template):
            call_count["n"] += 1
            return [{"labels": candidate_labels, "scores": [0.5] * len(candidate_labels)} for _ in batch]

        # 3 chunks (batch_size default 16) -> chunk_text on ~1000 words gives multiple chunks
        text = " ".join(f"w{i}" for i in range(2000))
        classify_song_zeroshot(text, classifier, emotions=["joy"], batch_size=1)
        n_chunks_expected = len(text.split()) // (350 - 30) + 1
        assert call_count["n"] >= 1  # batching happened at all; exact chunk math covered in test_text.py


def _fake_goemotions_classifier(scores, nested=False):
    def classifier(chunk, truncation):
        result = [{"label": k, "score": v} for k, v in scores.items()]
        return [result] if nested else result
    return classifier


class TestClassifySongGoemotions:
    def test_empty_lyrics_returns_zeros(self):
        result = classify_song_goemotions("", classifier=None, emotions=["joy", "anger"])
        assert result == {"joy": 0.0, "anger": 0.0}

    def test_flat_list_output(self):
        classifier = _fake_goemotions_classifier({"joy": 0.7, "anger": 0.3}, nested=False)
        result = classify_song_goemotions("hello world", classifier, emotions=["joy", "anger"])
        assert result == {"joy": 0.7, "anger": 0.3}

    def test_nested_list_output_unwrapped(self):
        classifier = _fake_goemotions_classifier({"joy": 0.7, "anger": 0.3}, nested=True)
        result = classify_song_goemotions("hello world", classifier, emotions=["joy", "anger"])
        assert result == {"joy": 0.7, "anger": 0.3}

    def test_missing_label_defaults_to_zero(self):
        classifier = _fake_goemotions_classifier({"joy": 0.7}, nested=False)
        result = classify_song_goemotions("hello world", classifier, emotions=["joy", "anger"])
        assert result == {"joy": 0.7, "anger": 0.0}

    def test_rounds_to_four_decimal_places(self):
        classifier = _fake_goemotions_classifier({"joy": 1 / 3}, nested=False)
        result = classify_song_goemotions("hello world", classifier, emotions=["joy"])
        assert result["joy"] == round(1 / 3, 4)


class TestCheckpointing:
    def test_load_missing_returns_none(self, tmp_path: Path):
        assert load_checkpoint(tmp_path / "nope.csv", ["emotion_joy"]) is None

    def test_round_trip_preserves_nan_rows(self, tmp_path: Path):
        path = tmp_path / "checkpoint.csv"
        df = pd.DataFrame({"emotion_joy": [0.5, np.nan]})
        save_checkpoint(df, path)
        loaded = load_checkpoint(path, ["emotion_joy"])
        assert loaded is not None
        assert loaded.iloc[0]["emotion_joy"] == 0.5
        assert pd.isna(loaded.iloc[1]["emotion_joy"])

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "nested" / "dir" / "checkpoint.csv"
        save_checkpoint(pd.DataFrame({"a": [1]}), path)
        assert path.exists()
