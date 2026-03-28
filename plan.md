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
    → data/processed/titles.csv        # merged, deduplicated
    → data/processed/lyrics.csv        # + lyrics column
    → data/processed/lyrics_lang.csv   # + original_lang column
    → data/processed/lyrics_trans.csv  # + lyrics_in_en column
    → data/processed/emotions.csv      # + emotion scores
```

Columns at each stage:
- titles.csv:       [artist, title, spotify_uri]
- lyrics.csv:       [artist, title, spotify_uri, lyrics]
- lyrics_lang.csv:  [..., original_lang]
- lyrics_trans.csv: [..., lyrics_in_en]
- emotions.csv:     [..., emotion_<emotion>, emotion_scores]

## Phases

---

### Phase 1: Build titles.csv and Fetch Lyrics

**Notebook:** notebooks/01_lyrics_ingestion.ipynb

**Goal:** Produce a deduplicated track list from Spotify regional charts, then fetch
lyrics for each unique track via Genius API.

**Data flow:**
- Input:  `data/raw/regional-{country}-weekly-{date}.csv` — one file per region/week
- Stage 1: `data/processed/titles.csv`       — [artist, title, spotify_uri] (unique)
- Cache:   `data/processed/lyrics_cache.csv` — [spotify_uri, lyrics] (checkpoint)
- Output:  `data/processed/lyrics.csv`       — [spotify_uri, artist, title, lyrics] (unique)

**Note on schema:** rank and region are intentionally excluded from titles.csv and
lyrics.csv. These are deduplicated track reference files used purely for API lookups.
Regional data stays in the raw CSVs and will be joined back at the analysis stage.

Actions:
1. Define FILE_REGION_MAP — map each raw filename to its region label.
2. For each file, load CSV and rename columns to [artist, title, rank, spotify_uri].
3. Strip the `spotify:track:` prefix from the uri column.
4. Extract chart_date from filename using regex.
5. Concatenate all regions, drop duplicates on spotify_uri.
6. Write [artist, title, spotify_uri] to data/processed/titles.csv.
7. Check lyrics_cache.csv — skip any spotify_uri already present.
8. For each pending track, call Genius API and append to lyrics_cache.csv
   in batches of CHUNK_SIZE.
9. After fetch loop, merge unique_tracks + cache → write lyrics.csv.

Resumability:
- titles.csv is a full refresh — always overwritten, no external calls involved.
- lyrics_cache.csv is the checkpoint — re-running resumes from last cached URI.
- Batch writes every CHUNK_SIZE tracks (default: 10).
- Missing lyrics written as empty string in cache; distinguishable from un-fetched
  (un-fetched rows simply don't exist in the cache yet).

Success criteria:
- titles.csv exists with columns [artist, title, spotify_uri]
- No duplicate spotify_uri rows in titles.csv
- Row count is plausible (≤ 200 × number of regions, likely less due to cross-region hits)
- lyrics.csv exists with columns [spotify_uri, artist, title, lyrics]
- Row count matches titles.csv row count exactly
- lyrics populated for ≥ 80% of rows (Genius coverage expectation)
- No duplicate spotify_uri rows in lyrics.csv

---

### Phase 2: Language Detection

**Notebook:** notebooks/02_language_detection.ipynb

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

### Phase 3: Translation to English

**Notebook:** notebooks/03_lyrics_translate.ipynb

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

### Phase 4: Emotion Analysis

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