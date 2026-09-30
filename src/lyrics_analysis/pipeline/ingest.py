"""Track ingestion helpers for the lyrics analysis warehouse."""

from __future__ import annotations

import re
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


def extract_date_from_filename(filename: str) -> str | None:
    """Extract date in YYYY-MM-DD format from filename like 'regional-XX-weekly-YYYY-MM-DD.csv'"""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else None


def append_cache_chunk(rows_chunk: list[dict], out_path: Path, cache_cols: list[str]) -> None:
    """Append cache rows (as ordered by cache_cols) to a lyrics cache CSV.

    Writes the header only if out_path does not already exist, so repeated
    calls build up one CSV that an interrupted run can resume from.
    """
    if not rows_chunk:
        return
    chunk_df = pd.DataFrame(rows_chunk)[cache_cols]
    write_header = not out_path.exists()
    chunk_df.to_csv(out_path, mode='a', header=write_header, index=False)
