"""Contract checks against the real files in data/processed/.

These are skipped by default (see the `data` marker / addopts in
pyproject.toml) since data/processed/ is a local artifact, not something CI
or a fresh clone will have. Run explicitly with `pytest -m data`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

pytestmark = pytest.mark.data


def _skip_if_missing(*filenames: str) -> None:
    for name in filenames:
        if not (PROCESSED / name).exists():
            pytest.skip(f"{name} not present in data/processed/")


def _emotion_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("emotion_")]


def test_lyrics_spotify_uri_is_unique():
    _skip_if_missing("01_lyrics.csv")
    df = pd.read_csv(PROCESSED / "01_lyrics.csv")
    assert df["spotify_uri"].is_unique


@pytest.mark.parametrize(
    "filename",
    ["04.1_emotion_scores_zeroshot.csv", "04.2_emotion_scores_goemotions.csv"],
)
def test_emotion_scores_in_unit_range(filename):
    _skip_if_missing(filename)
    df = pd.read_csv(PROCESSED / filename)
    cols = _emotion_cols(df)
    assert cols, f"no emotion_* columns found in {filename}"
    for col in cols:
        values = df[col].dropna()
        assert (values >= 0).all() and (values <= 1).all(), f"{col} out of [0,1] range"


def test_zeroshot_and_goemotions_cover_the_same_tracks():
    _skip_if_missing("04.1_emotion_scores_zeroshot.csv", "04.2_emotion_scores_goemotions.csv")
    zeroshot = pd.read_csv(PROCESSED / "04.1_emotion_scores_zeroshot.csv")
    goemotions = pd.read_csv(PROCESSED / "04.2_emotion_scores_goemotions.csv")
    assert set(zeroshot["spotify_uri"]) == set(goemotions["spotify_uri"])


@pytest.mark.parametrize(
    "filename",
    ["04.1_emotion_scores_zeroshot.csv", "04.2_emotion_scores_goemotions.csv"],
)
def test_unclassified_rows_are_exactly_all_zero_rows(filename):
    _skip_if_missing(filename)
    df = pd.read_csv(PROCESSED / filename)
    cols = _emotion_cols(df)
    unclassified = set(df.loc[df["dominant_emotion"] == "unclassified", "spotify_uri"])
    all_zero = set(df.loc[df[cols].max(axis=1) <= 0, "spotify_uri"])
    assert unclassified == all_zero
