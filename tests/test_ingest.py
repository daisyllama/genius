"""Tests for lyrics_analysis.pipeline.ingest."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lyrics_analysis.pipeline.ingest import (
    append_cache_chunk,
    build_chart_fact,
    build_track_dimension,
    extract_date_from_filename,
    load_chart_csv,
)


class TestBuildTrackDimension:
    def test_dedupes_by_spotify_uri_across_regions(self):
        frame_a = pd.DataFrame(
            {"artist": ["A"], "title": ["Song"], "spotify_uri": ["uri1"]}
        )
        frame_b = pd.DataFrame(
            {"artist": ["A"], "title": ["Song"], "spotify_uri": ["uri1"]}
        )
        result = build_track_dimension([frame_a, frame_b])
        assert len(result) == 1

    def test_output_columns(self):
        frame = pd.DataFrame(
            {"artist": ["A"], "title": ["Song"], "spotify_uri": ["uri1"]}
        )
        result = build_track_dimension([frame])
        assert list(result.columns) == ["artist", "track_title", "spotify_uri"]
        assert result.iloc[0]["track_title"] == "Song"


class TestBuildChartFact:
    def test_includes_streams_when_present(self):
        frame = pd.DataFrame(
            {
                "region_code": ["ar"],
                "chart_week": [date(2026, 3, 5)],
                "spotify_uri": ["uri1"],
                "rank": [1],
                "streams": [1000],
            }
        )
        result = build_chart_fact([frame])
        assert "streams" in result.columns
        assert result.iloc[0]["streams"] == 1000

    def test_omits_streams_when_absent(self):
        frame = pd.DataFrame(
            {
                "region_code": ["ar"],
                "chart_week": [date(2026, 3, 5)],
                "spotify_uri": ["uri1"],
                "rank": [1],
            }
        )
        result = build_chart_fact([frame])
        assert "streams" not in result.columns


class TestLoadChartCsv:
    """Regression tests for the real Spotify CSV column-name bug (see docs)."""

    def test_columns_mapped_by_name_not_position(self, spotify_csv: Path):
        frame = load_chart_csv(spotify_csv, "ar", date(2026, 3, 5))

        first = frame.iloc[0]
        assert first["artist"] == "Ryan Castro, Kapo, Gangsta"
        assert first["title"] == "LA VILLA"
        assert first["rank"] == 1
        assert first["spotify_uri"] == "2ZyrAym0sRLwt4PhGotHuI"

    def test_spotify_uri_prefix_stripped(self, spotify_csv: Path):
        frame = load_chart_csv(spotify_csv, "ar", date(2026, 3, 5))
        assert not frame["spotify_uri"].str.startswith("spotify:track:").any()

    def test_streams_column_retained_and_numeric(self, spotify_csv: Path):
        frame = load_chart_csv(spotify_csv, "ar", date(2026, 3, 5))
        assert "streams" in frame.columns
        assert frame.iloc[0]["streams"] == 1989059

    def test_region_and_week_attached(self, spotify_csv: Path):
        frame = load_chart_csv(spotify_csv, "ar", date(2026, 3, 5))
        assert (frame["region_code"] == "ar").all()
        assert (frame["chart_week"] == date(2026, 3, 5)).all()

    def test_missing_required_column_raises(self, tmp_path: Path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("rank,artist_names,track_name\n1,Someone,Song\n")
        with pytest.raises(ValueError):
            load_chart_csv(bad_csv, "ar", date(2026, 3, 5))


class TestExtractDateFromFilename:
    def test_extracts_date(self):
        assert extract_date_from_filename("regional-ar-weekly-2026-03-05.csv") == "2026-03-05"

    def test_no_date_returns_none(self):
        assert extract_date_from_filename("no_date_here.csv") is None


class TestAppendCacheChunk:
    def test_writes_header_once_across_two_appends(self, tmp_path: Path):
        out_path = tmp_path / "cache.csv"
        cols = ["artist", "title", "spotify_uri", "lyrics"]

        append_cache_chunk(
            [{"artist": "A", "title": "T1", "spotify_uri": "u1", "lyrics": "la la"}],
            out_path,
            cols,
        )
        append_cache_chunk(
            [{"artist": "B", "title": "T2", "spotify_uri": "u2", "lyrics": "da da"}],
            out_path,
            cols,
        )

        lines = out_path.read_text().splitlines()
        assert lines[0] == "artist,title,spotify_uri,lyrics"
        assert len(lines) == 3  # 1 header + 2 data rows, header not repeated

    def test_empty_rows_is_noop(self, tmp_path: Path):
        out_path = tmp_path / "cache.csv"
        append_cache_chunk([], out_path, ["artist"])
        assert not out_path.exists()
