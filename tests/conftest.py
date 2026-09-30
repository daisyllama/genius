"""Shared pytest fixtures for the lyrics_analysis test suite."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

# Real header + row shape from data/raw/regional/regional-ar-weekly-2026-03-05.csv,
# including the UTF-8 BOM that Spotify's export actually ships with.
_SPOTIFY_CSV_BODY = (
    "rank,uri,artist_names,track_name,source,peak_rank,previous_rank,weeks_on_chart,streams\n"
    '1,"spotify:track:2ZyrAym0sRLwt4PhGotHuI","Ryan Castro, Kapo, Gangsta","LA VILLA",'
    '"AWOO Corp./Sony Music Latin",1,1,9,"1989059"\n'
    '2,"spotify:track:2lTm559tuIvatlT1u0JYG2","Bad Bunny","BAILE INoLVIDABLE",'
    '"Rimas Entertainment LLC.",1,2,61,"1649272"\n'
    '3,"spotify:track:4xdBrk0nFZaP54vvZj0yx7","KAROL G","OKI DOKI",'
    '"Bichota Records/Interscope",2,3,15,"1204832"\n'
)


@pytest.fixture
def spotify_csv(tmp_path: Path) -> Path:
    """A realistic regional chart CSV, BOM included, written to a temp file."""
    path = tmp_path / "regional-ar-weekly-2026-03-05.csv"
    path.write_bytes(("﻿" + _SPOTIFY_CSV_BODY).encode("utf-8"))
    return path


@pytest.fixture
def emotion_frame() -> pd.DataFrame:
    """A small emotion-scores frame spanning a few regions."""
    return pd.DataFrame(
        [
            {"region": "USA", "artist": "Artist A", "title": "Song A", "spotify_uri": "uri1",
             "emotion_joy": 0.8, "emotion_sadness": 0.1, "emotion_anger": 0.05},
            {"region": "USA", "artist": "Artist B", "title": "Song B", "spotify_uri": "uri2",
             "emotion_joy": 0.2, "emotion_sadness": 0.7, "emotion_anger": 0.1},
            {"region": "Japan", "artist": "Artist C", "title": "Song C", "spotify_uri": "uri3",
             "emotion_joy": 0.1, "emotion_sadness": 0.2, "emotion_anger": 0.9},
            {"region": "Japan", "artist": "Artist D", "title": "Song D", "spotify_uri": "uri4",
             "emotion_joy": 0.6, "emotion_sadness": 0.3, "emotion_anger": 0.1},
            {"region": "Global", "artist": "Artist E", "title": "Song E", "spotify_uri": "uri5",
             "emotion_joy": 0.5, "emotion_sadness": 0.5, "emotion_anger": 0.2},
        ]
    )
