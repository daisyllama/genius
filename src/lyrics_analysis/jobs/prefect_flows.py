"""Prefect flow for the lyrics analysis pipeline."""

from __future__ import annotations

try:
    from prefect import flow, task
except ImportError:  # pragma: no cover
    def flow(func=None, **_kwargs):
        return func

    def task(func=None, **_kwargs):
        return func

from lyrics_analysis.pipeline.discovery import discover_new_files
from lyrics_analysis.pipeline.ingest import build_chart_fact, build_track_dimension
from lyrics_analysis.pipeline.publish import dominant_emotion_by_region


@task
def discover_chart_files(source_urls, target_dir):
    return discover_new_files(source_urls, target_dir)


@task
def ingest_charts(chart_files):
    frames = []
    for chart_file in chart_files:
        from lyrics_analysis.pipeline.ingest import load_chart_csv

        frames.append(load_chart_csv(chart_file.local_path, chart_file.region_code, chart_file.chart_week))
    return build_track_dimension(frames), build_chart_fact(frames)


@task
def build_summary_tables(emotion_frame):
    return dominant_emotion_by_region(emotion_frame)


@flow(name="lyrics-analysis-pipeline")
def run_pipeline(source_urls, download_dir, emotion_frame=None):
    chart_files = discover_chart_files(source_urls, download_dir)
    track_dim, chart_fact = ingest_charts(chart_files)
    summary = build_summary_tables(emotion_frame) if emotion_frame is not None else None
    return {
        "chart_files": chart_files,
        "track_dim": track_dim,
        "chart_fact": chart_fact,
        "summary": summary,
    }
