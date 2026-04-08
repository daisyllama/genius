"""Track ingestion helpers for the lyrics analysis warehouse."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TRACK_COLUMNS = ["artist", "title", "rank", "spotify_uri"]


def load_chart_csv(csv_path: Path, region_code: str, chart_week) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    frame = frame.copy()
    if frame.shape[1] >= 4:
        frame = frame.iloc[:, :4]
        frame.columns = TRACK_COLUMNS
    frame["region_code"] = region_code
    frame["chart_week"] = chart_week
    frame["spotify_uri"] = frame["spotify_uri"].astype(str).str.replace("spotify:track:", "", regex=False)
    return frame


def build_track_dimension(chart_frames: list[pd.DataFrame]) -> pd.DataFrame:
    combined = pd.concat(chart_frames, ignore_index=True)
    tracks = combined[["artist", "title", "spotify_uri"]].drop_duplicates(subset=["spotify_uri"]).copy()
    tracks["track_title"] = tracks["title"]
    return tracks[["artist", "track_title", "spotify_uri"]]


def build_chart_fact(chart_frames: list[pd.DataFrame]) -> pd.DataFrame:
    combined = pd.concat(chart_frames, ignore_index=True)
    columns = ["region_code", "chart_week", "spotify_uri", "rank"]
    if "streams" in combined.columns:
        columns.append("streams")
    return combined[columns].copy()
