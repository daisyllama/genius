"""Tests for lyrics_analysis.pipeline.publish."""

from __future__ import annotations

import pandas as pd

from lyrics_analysis.pipeline.publish import (
    dominant_emotion_by_region,
    top_tracks_per_emotion,
)


class TestDominantEmotionByRegion:
    def test_correct_argmax_per_region(self, emotion_frame: pd.DataFrame):
        result = dominant_emotion_by_region(emotion_frame)
        by_region = result.set_index("region")["dominant_emotion"].to_dict()

        # USA: mean joy=0.5, sadness=0.4, anger=0.075 -> joy
        assert by_region["USA"] == "emotion_joy"
        # Japan: mean joy=0.35, sadness=0.25, anger=0.5 -> anger
        assert by_region["Japan"] == "emotion_anger"

    def test_dominant_emotion_keeps_prefix(self, emotion_frame: pd.DataFrame):
        # Unlike scoring.derive_contract_columns, this helper does not strip
        # the "emotion_" prefix from the winning label.
        result = dominant_emotion_by_region(emotion_frame)
        assert all(v.startswith("emotion_") for v in result["dominant_emotion"])


class TestTopTracksPerEmotion:
    def test_limits_to_top_n(self, emotion_frame: pd.DataFrame):
        result = top_tracks_per_emotion(emotion_frame, top_n=1)
        counts = result.groupby("emotion").size()
        assert (counts <= 1).all()

    def test_descending_order_within_emotion(self, emotion_frame: pd.DataFrame):
        result = top_tracks_per_emotion(emotion_frame, top_n=10)
        for _, group in result.groupby("emotion"):
            scores = group["score"].tolist()
            assert scores == sorted(scores, reverse=True)

    def test_top_track_for_joy(self, emotion_frame: pd.DataFrame):
        result = top_tracks_per_emotion(emotion_frame, top_n=1)
        joy_row = result[result["emotion"] == "emotion_joy"].iloc[0]
        assert joy_row["spotify_uri"] == "uri1"  # emotion_joy=0.8, the max
