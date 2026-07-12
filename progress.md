# Progress Snapshot

Date: 2026-07-12
Mode: Notebook-first workflow

## Compact Project Review

### Overall Health

- Full pipeline is complete end-to-end. All output CSVs present through Phase 5.
- Translation QA outputs now generated (previously missing).
- Notebook bugs fixed this session (see below).

### Pipeline Row Counts (validated 2026-07-12)

| File | Rows | Notes |
|------|------|-------|
| `00_titles.csv` | 1,600 | 8 regions × 200 tracks |
| `01_lyrics.csv` | 1,105 | 495 tracks had no Genius match (expected) |
| `02_lyrics_lang.csv` | 1,105 | |
| `03_lyrics_trans.csv` | 1,105 | 107 null `lyrics_in_en` (no-lyrics tracks); 181 flagged for review |
| `04_emotion_scores.csv` | 1,105 | 108 unclassified (null/empty lyrics tracks) |
| `05_titles_emotion_scores.csv` | 1,470 | Chart data joined with emotions; unclassified excluded |
| `null_dom_emo.csv` | 452 | Chart entries with no scoreable emotion |

### Translation QA Results (Phase 3.1)

- Evaluable rows: 998
- Passed: 903
- **Pass rate: 90.48%** (target: 97%) — FAIL
- Root cause: 56 Chinese (`zh`) songs remain partially untranslated. 54/56 were correctly flagged via `translation_review_required = True` (too long or mixed-language). 2 short Chinese songs failed silently.
- 17 English-original failures are false positives: low FastText confidence on songs with repetitive/non-word content (e.g., "Ha-ha-ha") or Genius navigation artifacts in lyrics.
- QA outputs: `lyrics_trans_qa_failures.csv`, `lyrics_trans_qa_summary.csv`

### Regions

Argentina, Colombia, Global, Japan, Singapore, Spain, Taiwan, USA

### Confirmed Working Assets

- Notebooks:
  - `notebooks/01_lyrics_ingestion.ipynb` ✓ (bugs fixed this session)
  - `notebooks/02_language_detection.ipynb` ✓
  - `notebooks/03_lyrics_translate.ipynb` ✓
  - `notebooks/03_lyrics_translation_qa.ipynb` ✓ (run this session)
  - `notebooks/04_classification_zeroshot.ipynb` ✓
  - `notebooks/05_song_analysis.ipynb` ✓
  - `notebooks/06_exploration_charts.ipynb` ✓ (bug fixed this session)
- Processed outputs present through Phase 5 including new QA files.

### Bugs Fixed (2026-07-12)

- `01_lyrics_ingestion.ipynb`:
  - `FILE_REGION_MAP` had only 4 of 8 regions (was missing CO, Global, TW, USA).
  - `RAW_DIR` pointed to `data/raw/` but CSV files are in `data/raw/archive/`.
  - `CACHE_PATH` was `01_01_01_01_lyrics_cache.csv` (typo) → fixed to `01_lyrics_cache.csv`.
  - `LYRICS_OUT` was `lyrics.csv` → fixed to `01_lyrics.csv`.
  - `chart_date` column removed from `00_titles.csv` output (matches actual file schema).
- `06_exploration_charts.ipynb`:
  - `df.columns[7:]` → `df.columns[6:]` in 3 cells (was skipping `emotion_love` column).

### Known Limitations

- 495 tracks (31% of unique chart songs) have no Genius lyrics — cannot be emotion-scored.
- 56 Chinese songs failed translation QA. Manual re-translation required for full coverage.
- `fasttext-wheel` must be installed separately (`pip install fasttext-wheel`) for QA notebook.

### Emotion Scoring Fix (2026-07-12)

**Problem**: `04_classification_zeroshot.ipynb` used `multi_label=True` which scores each emotion independently via NLI entailment. This causes score inflation — all emotions score high simultaneously (mean 0.74–0.77 for longing/sensual). The dominant emotion is then just whichever label the model consistently over-estimates globally, not what's distinctive about each song.

**Fix applied**:
- Changed to `multi_label=False`: emotions now compete via softmax in one forward pass
- Added `hypothesis_template = "The dominant emotion in this song is {}."` for more precise NLI matching
- Removed NOISE_FLOOR from dominant_emotion derivation (not needed when scores sum to ~1)
- Deleted old checkpoint so next run re-classifies from scratch with new settings

**Action required**: Re-run `notebooks/04_classification_zeroshot.ipynb` in full, then re-run `notebooks/05_song_analysis.ipynb`.

**Differential analysis chart** added to `notebooks/06_exploration_charts.ipynb` (last cell) — shows each region's deviation from global mean, making regional character visible regardless of absolute score levels.

## Priority Next Steps

1. **Re-run `04_classification_zeroshot.ipynb`** with new scoring settings (expect ~1–2 hrs on CPU).
2. Re-run `05_song_analysis.ipynb` to regenerate `05_titles_emotion_scores.csv`.
3. Re-run `06_exploration_charts.ipynb` to refresh charts.
4. Manual review of `lyrics_trans_qa_failures.csv` for the 2 short Chinese songs with `translation_review_required = False`.
5. Optionally archive or remove stale `src/lyrics_analysis/` remnants.

## Resume Point

- Classification notebook updated. Checkpoint deleted. **Must re-run 04 notebook to get accurate scores.**
- All other notebooks are correct and ready to run.

