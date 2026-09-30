"""Tests for lyrics_analysis.pipeline.compare."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lyrics_analysis.pipeline.compare import is_label_softmax, regional_z


class TestIsLabelSoftmax:
    def test_softmax_rows_return_true(self):
        df = pd.DataFrame({"emotion_a": [0.7, 0.3], "emotion_b": [0.3, 0.7]})
        assert is_label_softmax(df, ["emotion_a", "emotion_b"]) is True

    def test_independent_sigmoids_return_false(self):
        df = pd.DataFrame({"emotion_a": [0.9, 0.1], "emotion_b": [0.8, 0.2]})
        assert is_label_softmax(df, ["emotion_a", "emotion_b"]) is False

    def test_all_zero_rows_ignored(self):
        df = pd.DataFrame({"emotion_a": [0.5, 0.0], "emotion_b": [0.5, 0.0]})
        assert is_label_softmax(df, ["emotion_a", "emotion_b"]) is True


class TestRegionalZ:
    @pytest.fixture
    def titles(self):
        return pd.DataFrame(
            {
                "spotify_uri": ["u1", "u2", "u3", "u4"],
                "region": ["USA", "USA", "Japan", "Global"],
            }
        )

    def test_global_excluded_from_baseline_but_present_in_output(self, titles):
        scores = pd.DataFrame(
            {
                "spotify_uri": ["u1", "u2", "u3", "u4"],
                "emotion_joy": [0.8, 0.6, 0.2, 100.0],  # Global is a huge outlier
            }
        )
        result = regional_z(scores, ["emotion_joy"], ["joy"], titles, ref_region="Global")
        assert "Global" in result.index
        # USA/Japan z-scores should be computed from just USA+Japan, unaffected
        # by Global's outlier value.
        assert abs(result.loc["USA", "joy"]) < 10
        assert abs(result.loc["Japan", "joy"]) < 10

    def test_output_columns_renamed_to_labels(self, titles):
        scores = pd.DataFrame(
            {"spotify_uri": ["u1", "u2", "u3", "u4"], "emotion_joy": [0.1, 0.2, 0.3, 0.4]}
        )
        result = regional_z(scores, ["emotion_joy"], ["joy"], titles)
        assert list(result.columns) == ["joy"]

    def test_constant_label_gives_nan_not_inf(self, titles):
        # A label with identical values everywhere has zero baseline std, so
        # the z-score is 0/0. That's NaN (a "no signal" marker), not +-inf --
        # confirmed here so a future change to this division doesn't
        # silently start producing inf instead.
        scores = pd.DataFrame(
            {"spotify_uri": ["u1", "u2", "u3", "u4"], "emotion_joy": [0.5, 0.5, 0.5, 0.5]}
        )
        result = regional_z(scores, ["emotion_joy"], ["joy"], titles, ref_region="Global")
        assert not np.isinf(result["joy"]).any()
        assert result["joy"].isna().all()
