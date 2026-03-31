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
   → data/processed/00_titles.csv        # merged, deduplicated
   → data/processed/01_lyrics.csv        # + lyrics, length columns
   → data/processed/02_lyrics_lang.csv   # + original_lang column
   → data/processed/03_lyrics_trans.csv  # + lyrics_in_en, review metadata
   → data/processed/emotion_scores.csv   # + wide emotion columns
```

Columns at each stage (✓ = verified):
- **00_titles.csv** ✓            [artist, title, spotify_uri] — unique tracks
- **01_lyrics.csv** ✓            [artist, title, spotify_uri, lyrics, length] — lyrics fetched via Genius + character length of lyrics
- **02_lyrics_lang.csv** ✓       [artist, title, spotify_uri, lyrics, length, original_lang] — language detected (ISO 639-1: "en", "es", "ja", "pt", "tr", "ar", or "unknown")
- **03_lyrics_trans.csv** ✓      [artist, title, spotify_uri, original_lang, lyrics_in_en, length, translation_review_required] — English translation + review flags
- **emotion_scores.csv**            [artist, title, spotify_uri, original_lang, lyrics_in_en, dominant_emotion, emotion_<label...>] — wide emotion classification

## Phases

---

### Phase 1: Build 00_titles.csv and Fetch Lyrics

**Notebook:** notebooks/01_lyrics_ingestion.ipynb

**Goal:** Produce a deduplicated track list from Spotify regional charts, then fetch
lyrics for each unique track via Genius API.

**Data flow:**
- Input:  `data/raw/regional-{country}-weekly-{date}.csv` — one file per region/week
- Stage 1: `data/processed/00_titles.csv`       — [artist, title, spotify_uri] (unique)
- Cache:   `data/processed/01_lyrics_cache.csv` — [spotify_uri, lyrics] (checkpoint)
- Output:  `data/processed/01_lyrics.csv`       — [spotify_uri, artist, title, lyrics, length] (unique)

**Note on schema:** rank and region are intentionally excluded from 00_titles.csv and
01_lyrics.csv. These are deduplicated track reference files used purely for API lookups.
Regional data stays in the raw CSVs and will be joined back at the analysis stage.

Actions:
1. Define FILE_REGION_MAP — map each raw filename to its region label.
2. For each file, load CSV and rename columns to [artist, title, rank, spotify_uri].
3. Strip the `spotify:track:` prefix from the uri column.
4. Extract chart_date from filename using regex.
5. Concatenate all regions, drop duplicates on spotify_uri.
6. Write [artist, title, spotify_uri] to data/processed/00_titles.csv.
7. Check 01_lyrics_cache.csv — skip any spotify_uri already present.
8. For each pending track, call Genius API and append to 01_lyrics_cache.csv
   in batches of CHUNK_SIZE.
9. After fetch loop, merge unique_tracks + cache, compute `length=len(lyrics)` → write 01_lyrics.csv.

Resumability:
- 00_titles.csv is a full refresh — always overwritten, no external calls involved.
- 01_lyrics_cache.csv is the checkpoint — re-running resumes from last cached URI.
- Batch writes every CHUNK_SIZE tracks (default: 10).
- Missing lyrics written as empty string in cache; distinguishable from un-fetched
  (un-fetched rows simply don't exist in the cache yet).

Success criteria:
- 00_titles.csv exists with columns [artist, title, spotify_uri]
- No duplicate spotify_uri rows in 00_titles.csv
- Row count is plausible (≤ 200 × number of regions, likely less due to cross-region hits)
- 01_lyrics.csv exists with columns [spotify_uri, artist, title, lyrics, length]
- Row count matches 00_titles.csv row count exactly
- lyrics populated for ≥ 80% of rows (Genius coverage expectation)
- length equals character length of lyrics for every row
- No duplicate spotify_uri rows in 01_lyrics.csv

---

### Phase 2: Language Detection

**Notebook:** notebooks/02_language_detection.ipynb

**Goal:** Detect the original language of each lyric and append to file.

Actions:
1. Load 01_lyrics.csv.
2. Apply language detection to `lyrics` column.
3. Append `original_lang` column (ISO 639-1 codes, e.g. "en", "es", "ja").
4. Write to data/processed/02_lyrics_lang.csv.

Resumability:
- Skip rows where `original_lang` already populated.

Success criteria:
- 02_lyrics_lang.csv exists
- original_lang populated for all rows with non-null lyrics
- Distribution of languages is plausible per region

---

### Phase 3: Translation to English

**Notebook:** notebooks/03_lyrics_translate.ipynb

**Goal:** Translate non-English lyrics to English using GoogleTranslator, with a length gate and review flagging for long or suspicious outputs.

Actions:
1. Load 02_lyrics_lang.csv.
2. For rows where original_lang != "en" and `length < 5000`, apply GoogleTranslator to `lyrics`.
3. For rows where original_lang == "en", copy `lyrics` → `lyrics_in_en`.
4. For rows where original_lang != "en" and `length >= 5000`, skip translation and mark for manual review.
5. Set `translation_review_required` for non-English rows when either condition is true:
   - `length >= 5000`
   - `lyrics_in_en` appears suspicious (e.g., unchanged from source, non-English script still present, encoding artifacts, or very low English character signal)
6. Append `lyrics_in_en` plus review metadata columns (`length`, `translation_review_required`).
7. Write to data/processed/03_lyrics_trans.csv.

Resumability:
- Skip rows where `lyrics_in_en` already populated.
- Batch writes every N rows.

Dependencies:
- deep_translator: add `!pip install deep_translator` guard at top of notebook.

Success criteria:
- 03_lyrics_trans.csv exists
- lyrics_in_en populated for rows where translation is attempted (or copied for English rows)
- non-English rows with `length >= 5000` are preserved and flagged for review in 03_lyrics_trans.csv
- non-English rows with suspicious translated output are also flagged via `translation_review_required`
- Spot-check: non-English rows have visibly translated content

---

### Phase 4: Translation QA

**Notebook:** notebooks/04_lyrics_translation_qa.ipynb

**Goal:** Validate translation quality and review rows flagged as long or suspicious from the same `03_lyrics_trans.csv`.

Actions:
1. Load 03_lyrics_trans.csv.
2. Review rows flagged via `translation_review_required` (length >= 5000 or suspicious translated output).
3. Detect language for evaluable `lyrics_in_en` rows using FastText (`lid.176.ftz`).
4. Mark each evaluable row as pass/fail using: predicted lang == "en" and confidence >= 0.70.
5. Write failed rows to data/processed/lyrics_trans_qa_failures.csv.
6. Write summary metrics to data/processed/lyrics_trans_qa_summary.csv.

Success criteria:
- lyrics_trans_qa_summary.csv exists
- Pass rate on evaluable rows >= 97%
- Rows flagged for review (`translation_review_required`) are visible in Phase 4 output checks
- Failed rows are exported for manual review

---

### Phase 5: Emotion Analysis

**Notebook:** notebooks/06_analysis_zeroshot.ipynb

**Goal:** Define an emotion set, score each lyric against that set, and produce a wide analysis-ready output.

Actions:
1. Load 03_lyrics_trans.csv.
2. Define the emotion labels to analyse (single source of truth list), e.g. [love, anger, heartbreak, ...].
3. Apply zero-shot emotion classifier to `lyrics_in_en` using the labels from Step 2.
4. Build wide output columns:
   - Base columns: [artist, title, spotify_uri, original_lang, lyrics_in_en]
   - `dominant_emotion`: label with highest score for each row
   - One score column per defined emotion using `emotion_<label>` naming
5. Write to data/processed/emotion_scores.csv.
6. Produce summary aggregations:
   - Dominant emotion by region
   - Emotion distribution over time (if multi-week data)
   - Top tracks per emotion per region

Resumability:
- Skip rows where dominant_emotion already populated.
- Batch writes every N rows.

Success criteria:
- emotion_scores.csv exists in wide format with columns:
   [artist, title, spotify_uri, original_lang, lyrics_in_en, dominant_emotion, emotion_<label...>]
- Every label defined in Step 2 exists as a dedicated `emotion_<label>` column
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