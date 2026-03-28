# Plan

Date: 2026-03-28
Mode: Notebook-first, RPI workflow (Review → Plan → Implement per phase)

## Goal

Analyse the emotional content of top songs across different regions.

Deliver a dataset and analysis showing how emotions (joy, sadness, anger, etc.)
vary by region and over time, derived from the lyrics of Spotify's regional
Top 200 charts.

## Architecture: Linear Pipeline

Each stage reads from the previous stage's output file.
No stage overwrites upstream files.
```
[Spotify API]
    → data/raw/regional-*.csv          # one file per region/week
    → data/processed/titles.csv        # merged, deduplicated
    → data/processed/lyrics.csv        # + lyrics column
    → data/processed/lyrics_lang.csv   # + original_lang column
    → data/processed/lyrics_trans.csv  # + lyrics_in_en column
    → data/processed/emotions.csv      # + emotion scores
```

Columns at each stage:
- titles.csv:       [artist, title, spotify_uri, region, chart_date]
- lyrics.csv:       [artist, title, spotify_uri, region, chart_date, lyrics]
- lyrics_lang.csv:  [..., original_lang]
- lyrics_trans.csv: [..., lyrics_in_en]
- emotions.csv:     [..., emotion_label, emotion_scores]

## Phases

---

### Phase 0: Stabilise Existing Notebooks (Unblocking Work)

**Goal:** Get the existing notebook environment to a clean, runnable state
before building new pipeline stages.

**This is cleanup, not feature work. Time-box to ~1 session.**

Actions:
1. Fix undefined variable diagnostics:
   - notebooks/00_genius_sample_checks.ipynb — guard `song_uri` before use
   - notebooks/05_lyrics_en_cleaning.ipynb — initialise or replace `df_test`
2. Resolve missing import:
   - notebooks/04_lyrics_translate.ipynb — add `pip install deep_translator`
     guard cell at top
3. Final legacy path sweep across notebooks 00–06:
   - Confirm all active path cells use the notebook-06 local root pattern
   - Databricks alternatives kept as comments only

Success criteria:
- Zero unresolved symbol/import diagnostics in notebooks 00–06
- All path cells consistent

Resume checkpoint: `progress.md` → Phase 0 complete

---

### Phase 1: Spotify Regional Data Download

**Notebook:** notebooks/01_lyrics_ingestion.ipynb (or new 01_spotify_download.ipynb)

**Goal:** Download Top 200 chart CSVs for target regions and merge into titles.csv.

Actions:
1. Identify target regions (e.g. SG, JP, ES, AR — confirm list).
2. Download or confirm existing regional CSVs in data/raw/.
3. Merge into titles.csv with columns:
   `[artist, title, spotify_uri, region, chart_date]`
4. Deduplicate on `spotify_uri + region + chart_date`.
5. Write to data/processed/titles.csv.

Resumability:
- Check if titles.csv exists and is non-empty before re-downloading.
- Append new regions/dates without full rewrite.

Success criteria:
- titles.csv exists with expected columns
- Row count > 0 per region
- No duplicate (spotify_uri, region, chart_date) rows

---

### Phase 2: Lyrics Ingestion via Genius API

**Notebook:** notebooks/02_lyrics_fill.ipynb

**Goal:** For each row in titles.csv, fetch lyrics from Genius and save to lyrics.csv.

Actions:
1. Load titles.csv.
2. For each track, call Genius API to fetch lyrics.
3. Append `lyrics` column.
4. Write to data/processed/lyrics.csv.

Resumability:
- Load lyrics.csv if it exists; skip rows where lyrics is already populated.
- Batch writes every N rows (not all-or-nothing).
- Log failed lookups separately (not as empty strings).

Success criteria:
- lyrics.csv exists with all titles.csv rows
- lyrics column populated for ≥ 80% of rows (Genius coverage expectation)
- Failed lookups logged clearly

---

### Phase 3: Language Detection

**Notebook:** notebooks/03_language_detection.ipynb

**Goal:** Detect the original language of each lyric and append to file.

Actions:
1. Load lyrics.csv.
2. Apply language detection to `lyrics` column.
3. Append `original_lang` column (ISO 639-1 codes, e.g. "en", "es", "ja").
4. Write to data/processed/lyrics_lang.csv.

Resumability:
- Skip rows where `original_lang` already populated.

Success criteria:
- lyrics_lang.csv exists
- original_lang populated for all rows with non-null lyrics
- Distribution of languages is plausible per region

---

### Phase 4: Translation to English

**Notebook:** notebooks/04_lyrics_translate.ipynb

**Goal:** Translate non-English lyrics to English using GoogleTranslator.

Actions:
1. Load lyrics_lang.csv.
2. For rows where original_lang != "en", apply GoogleTranslator to `lyrics`.
3. For rows where original_lang == "en", copy `lyrics` → `lyrics_in_en`.
4. Append `lyrics_in_en` column.
5. Write to data/processed/lyrics_trans.csv.

Resumability:
- Skip rows where `lyrics_in_en` already populated.
- Batch writes every N rows.

Dependencies:
- deep_translator: add `!pip install deep_translator` guard at top of notebook.

Success criteria:
- lyrics_trans.csv exists
- lyrics_in_en populated for all rows with non-null lyrics
- Spot-check: non-English rows have visibly translated content

---

### Phase 5: Emotion Analysis

**Notebook:** notebooks/06_analysis_zeroshot.ipynb

**Goal:** Score each lyric for emotional content and produce analysis-ready output.

Actions:
1. Load lyrics_trans.csv.
2. Apply zero-shot emotion classifier to `lyrics_in_en`.
3. Append `emotion_label` (top emotion) and `emotion_scores` (dict or JSON).
4. Write to data/processed/emotions.csv.
5. Produce summary aggregations:
   - Dominant emotion by region
   - Emotion distribution over time (if multi-week data)
   - Top tracks per emotion per region

Resumability:
- Skip rows where emotion_label already populated.
- Batch writes every N rows.

Success criteria:
- emotions.csv exists with emotion columns
- Aggregations produce plausible regional differences
- At least one chart/table per region showing emotion distribution

---

### Phase 6: Documentation and Handoff

Actions:
1. Update README with pipeline execution order and file descriptions.
2. Record environment/dependency notes (Python version, key packages).
3. Update plan.md and progress.md to reflect completed state.

Files:
- README.md
- progress.md
- plan.md

---

## Testing Approach

Each phase follows the same pattern:

| Check | Method |
|---|---|
| File exists | Assert path exists after write |
| Non-empty | Assert row count > 0 |
| Schema correct | Assert expected columns present |
| No full regression | Spot-check 5–10 rows manually |
| Resumability | Re-run phase — confirm no duplicate rows written |

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Genius API rate limits / missing lyrics | Batch with delay; log misses; proceed with partial data |
| GoogleTranslator rate limits | Sleep between calls; resume from checkpoint |
| Language detection errors on short lyrics | Accept ~5% error rate; flag rows with < 20 chars |
| Emotion model slow on large dataset | Batch inference; checkpoint every N rows |
| Regional data gaps (not all regions on Genius) | Proceed with available data; note coverage in README |

---

## Resume Protocol (New Session)

1. Read progress.md — identify last completed phase.
2. Read this plan — identify next phase.
3. Open the relevant notebook.
4. Run the resumability check cell first (load existing output, count rows).
5. Continue from first incomplete row.
6. Update progress.md before ending session.