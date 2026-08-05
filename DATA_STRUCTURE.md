# Data Structure

Reorganized on 2026-08-05 for clarity and maintainability.

## Directory Layout

```
data/
├── raw/
│   └── regional/                    # Input data from Spotify Charts
│       ├── regional-ar-weekly-*.csv # Argentina
│       ├── regional-co-weekly-*.csv # Colombia
│       ├── regional-es-weekly-*.csv # Spain
│       ├── regional-global-weekly-*.csv
│       ├── regional-jp-weekly-*.csv # Japan
│       ├── regional-sg-weekly-*.csv # Singapore
│       ├── regional-tw-weekly-*.csv # Taiwan
│       └── regional-us-weekly-*.csv # USA
│
├── processed/                       # Current pipeline outputs
│   ├── 00_titles.csv               # Extracted from raw regional charts
│   ├── 01_lyrics_cache.csv         # Cache for Genius API fetch
│   ├── 01_lyrics.csv               # Unique tracks with lyrics
│   ├── 02_lyrics_lang.csv          # Language detection results
│   ├── 03_lyrics_trans.csv         # Translation results
│   ├── lyrics_trans_qa_failures.csv # Translation QA outputs
│   ├── lyrics_trans_qa_summary.csv
│   ├── 04.1_emotion_scores_zeroshot.csv    # Zero-shot NLI emotion classification (10 custom labels)
│   ├── 04.2_emotion_scores_goemotions.csv  # GoEmotions emotion classification (28 labels, run on Databricks)
│   ├── 07_classifier_comparison_regional.csv # 04.1 vs 04.2 regional comparison, shared labels only
│   ├── 05_titles_emotion_scores.csv # Final analysis-ready dataset
│   └── null_dom_emo.csv            # Records with missing emotions
│
└── archive/                         # Historical versions & interim data
    ├── co_global_tw_usa/           # Previous region-grouped processing run
    ├── sg_es_ar_jp/                # Previous region-grouped processing run
    └── *.csv                       # Old checkpoint files
```

## Pipeline Flow

```
data/raw/regional/ → notebooks → data/processed/

01_lyrics_ingestion.ipynb
  → 00_titles.csv, 01_lyrics_cache.csv, 01_lyrics.csv

02_language_detection.ipynb
  → 02_lyrics_lang.csv

03_lyrics_translate.ipynb
  → 03_lyrics_trans.csv

03_lyrics_translation_qa.ipynb
  → lyrics_trans_qa_failures.csv, lyrics_trans_qa_summary.csv

04.1_classification_zeroshot.ipynb    (zero-shot NLI, bart-large-mnli, 10 custom labels)
  → 04.1_emotion_scores_zeroshot.csv, 04.1_regional_summary_zeroshot.csv

04.2_classification_goemotions.ipynb  (GoEmotions, ONNX, 28 fixed labels — run on Databricks)
  → 04.2_emotion_scores_goemotions.csv, 04.2_regional_summary_goemotions.csv

05_song_analysis.ipynb
  → 05_titles_emotion_scores.csv, null_dom_emo.csv  (reads 04.1_emotion_scores_zeroshot.csv by default)

06_exploration_charts.ipynb
  → Interactive visualization (no CSV output)

07_compare_classifiers.ipynb
  → 07_classifier_comparison_regional.csv  (compares 04.1 vs 04.2 on their 4 shared labels)
```

04.1 and 04.2 are two alternative classification approaches over the same input
(`03_lyrics_trans.csv`) — see README.md for the rationale behind each. Downstream
notebooks default to the 04.1 (zero-shot) output; swap the path in 05 to use 04.2 instead.
07 compares the two directly on coverage, score correlation, and dominant-emotion
agreement, restricted to the 4 labels (`love`, `joy`, `grief`, `anger`) both taxonomies share.

## Changes (2026-08-05)

- Moved raw data from `data/raw/archive/` → `data/raw/regional/`
- Updated `01_lyrics_ingestion.ipynb` (`RAW_DIR`) to reference the new raw path
- Consolidated historical/interim data into a top-level `data/archive/`:
  - `data/processed/archive/*` (old checkpoint CSVs)
  - `data/processed/co_global_tw_usa/` and `data/processed/sg_es_ar_jp/` (earlier region-grouped processing runs)
- All other notebooks (02–06) already referenced `data/processed/` directly and needed no path changes.
- Renamed `04_classification_zeroshot.ipynb` → `04.1_classification_zeroshot.ipynb` and its outputs
  (`04_emotion_scores.csv` → `04.1_emotion_scores.csv`, etc.) to make room for an alternative
  classification approach.
- Added `04.2_classification_goemotions.ipynb` — GoEmotions (28-label, ONNX) classifier, run on
  Databricks; outputs pulled back via git merge.
- Renamed both classifiers' outputs to disambiguate by approach: `04.1_emotion_scores.csv` →
  `04.1_emotion_scores_zeroshot.csv`, `04.2_emotion_scores.csv` → `04.2_emotion_scores_goemotions.csv`
  (same pattern for their checkpoint/regional_summary files). Notebook path references updated to match.
- Added `07_compare_classifiers.ipynb` comparing 04.1 vs 04.2 on coverage, shared-label score
  correlation, and dominant-emotion agreement.

All notebooks resolve paths consistently via:
```python
PROJECT_ROOT = Path.cwd().parent  # from notebooks/
# Input:  PROJECT_ROOT / 'data' / 'raw' / 'regional'
# Output: PROJECT_ROOT / 'data' / 'processed'
```
