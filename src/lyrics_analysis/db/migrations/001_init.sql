-- Initial PostgreSQL schema for the lyrics analysis pipeline.

CREATE TABLE IF NOT EXISTS dim_region (
    region_id SERIAL PRIMARY KEY,
    region_code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_artist (
    artist_id BIGSERIAL PRIMARY KEY,
    artist_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_track (
    track_id BIGSERIAL PRIMARY KEY,
    spotify_uri TEXT NOT NULL UNIQUE,
    artist_id BIGINT REFERENCES dim_artist(artist_id),
    track_title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_chart_entry (
    chart_entry_id BIGSERIAL PRIMARY KEY,
    region_id INTEGER NOT NULL REFERENCES dim_region(region_id),
    track_id BIGINT NOT NULL REFERENCES dim_track(track_id),
    chart_week DATE NOT NULL,
    rank INTEGER NOT NULL,
    chart_source TEXT NOT NULL,
    streams INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (region_id, track_id, chart_week)
);

CREATE TABLE IF NOT EXISTS fact_lyrics (
    track_id BIGINT PRIMARY KEY REFERENCES dim_track(track_id),
    lyrics TEXT,
    lyrics_length INTEGER,
    lyrics_source TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_language (
    track_id BIGINT PRIMARY KEY REFERENCES dim_track(track_id),
    original_lang TEXT,
    language_confidence NUMERIC(5, 4),
    detector_version TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_translation (
    track_id BIGINT PRIMARY KEY REFERENCES dim_track(track_id),
    source_lang TEXT,
    lyrics_in_en TEXT,
    translation_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    translator_version TEXT,
    translated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_emotion_score (
    track_id BIGINT PRIMARY KEY REFERENCES dim_track(track_id),
    dominant_emotion TEXT,
    emotion_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version TEXT,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS etl_file_manifest (
    manifest_id BIGSERIAL PRIMARY KEY,
    source_url TEXT NOT NULL UNIQUE,
    region_code TEXT NOT NULL,
    chart_week DATE,
    checksum TEXT,
    local_path TEXT,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    downloaded_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'discovered',
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS etl_run (
    run_id BIGSERIAL PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    triggered_by TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS etl_task_run (
    task_run_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES etl_run(run_id),
    task_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    rows_read INTEGER NOT NULL DEFAULT 0,
    rows_written INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS etl_dead_letter (
    dead_letter_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES etl_run(run_id),
    stage_name TEXT NOT NULL,
    payload JSONB NOT NULL,
    error_message TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_fact_chart_entry_region_week
    ON fact_chart_entry (region_id, chart_week);

CREATE INDEX IF NOT EXISTS idx_fact_chart_entry_track_week
    ON fact_chart_entry (track_id, chart_week);

CREATE INDEX IF NOT EXISTS idx_etl_file_manifest_status
    ON etl_file_manifest (status, region_code, chart_week);

CREATE INDEX IF NOT EXISTS idx_etl_dead_letter_stage_retry
    ON etl_dead_letter (stage_name, retry_count);
