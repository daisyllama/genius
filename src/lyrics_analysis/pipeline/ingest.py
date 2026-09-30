"""Track ingestion helpers for the lyrics analysis warehouse."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Source column names as Spotify's regional chart export uses them.
REQUIRED_SOURCE_COLUMNS = ["rank", "uri", "artist_names", "track_name"]
SOURCE_COLUMN_RENAME = {
    "artist_names": "artist",
    "track_name": "title",
    "uri": "spotify_uri",
}


def load_chart_csv(csv_path: Path, region_code: str, chart_week) -> pd.DataFrame:
    # utf-8-sig strips the BOM Spotify's export ships with, so "rank" (not
    # "﻿rank") is the first column name.
    frame = pd.read_csv(csv_path, encoding="utf-8-sig")

    missing = [c for c in REQUIRED_SOURCE_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"Chart CSV missing required column(s): {missing}")

    frame = frame.rename(columns=SOURCE_COLUMN_RENAME)
    frame["rank"] = pd.to_numeric(frame["rank"], errors="coerce")
    if "streams" in frame.columns:
        frame["streams"] = pd.to_numeric(frame["streams"], errors="coerce")

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
