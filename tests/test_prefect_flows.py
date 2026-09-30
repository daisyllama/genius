"""Tests for lyrics_analysis.jobs.prefect_flows (task logic, not orchestration)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("prefect")

from lyrics_analysis.jobs.prefect_flows import build_summary_tables, ingest_charts
from lyrics_analysis.pipeline.discovery import DiscoveredChartFile


def test_ingest_charts_builds_dimension_and_fact(tmp_path: Path):
    csv_path = tmp_path / "regional-ar-weekly-2026-03-05.csv"
    csv_path.write_text(
        "rank,uri,artist_names,track_name,source,peak_rank,previous_rank,weeks_on_chart,streams\n"
        '1,"spotify:track:uri1","Artist A","Song A","Src",1,1,1,"100"\n'
    )
    chart_file = DiscoveredChartFile(
        region_code="ar",
        chart_week=date(2026, 3, 5),
        source_url="https://example.com/regional-ar-weekly-2026-03-05.csv",
        local_path=csv_path,
    )

    track_dim, chart_fact = ingest_charts.fn([chart_file])

    assert list(track_dim.columns) == ["artist", "track_title", "spotify_uri"]
    assert track_dim.iloc[0]["spotify_uri"] == "uri1"
    assert chart_fact.iloc[0]["region_code"] == "ar"


def test_build_summary_tables_delegates_to_publish():
    emotion_frame = pd.DataFrame(
        [
            {"region": "USA", "emotion_joy": 0.9, "emotion_sadness": 0.1},
            {"region": "USA", "emotion_joy": 0.8, "emotion_sadness": 0.2},
        ]
    )
    result = build_summary_tables.fn(emotion_frame)
    assert result.iloc[0]["dominant_emotion"] == "emotion_joy"
