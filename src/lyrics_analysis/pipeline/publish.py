"""Publish curated analysis tables for notebooks and dashboards."""

from __future__ import annotations

import pandas as pd


def dominant_emotion_by_region(emotion_frame: pd.DataFrame) -> pd.DataFrame:
    emotion_columns = [column for column in emotion_frame.columns if column.startswith("emotion_")]
    grouped = emotion_frame.groupby("region")[emotion_columns].mean()
    grouped["dominant_emotion"] = grouped.idxmax(axis=1)
    return grouped.reset_index()


def top_tracks_per_emotion(emotion_frame: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    emotion_columns = [column for column in emotion_frame.columns if column.startswith("emotion_")]
    melted = emotion_frame.melt(
        id_vars=["region", "artist", "title", "spotify_uri"],
        value_vars=emotion_columns,
        var_name="emotion",
        value_name="score",
    )
    return (
        melted.sort_values(["emotion", "score"], ascending=[True, False])
        .groupby("emotion", as_index=False)
        .head(top_n)
        .reset_index(drop=True)
    )
