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
│   ├── 04_emotion_scores.csv       # Emotion classification results
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

04_classification_zeroshot.ipynb
  → 04_emotion_scores.csv, regional_summary.csv

05_song_analysis.ipynb
  → 05_titles_emotion_scores.csv, null_dom_emo.csv

06_exploration_charts.ipynb
  → Interactive visualization (no CSV output)
```

## Changes (2026-08-05)

- Moved raw data from `data/raw/archive/` → `data/raw/regional/`
- Updated `01_lyrics_ingestion.ipynb` (`RAW_DIR`) to reference the new raw path
- Consolidated historical/interim data into a top-level `data/archive/`:
  - `data/processed/archive/*` (old checkpoint CSVs)
  - `data/processed/co_global_tw_usa/` and `data/processed/sg_es_ar_jp/` (earlier region-grouped processing runs)
- All other notebooks (02–06) already referenced `data/processed/` directly and needed no path changes.

All notebooks resolve paths consistently via:
```python
PROJECT_ROOT = Path.cwd().parent  # from notebooks/
# Input:  PROJECT_ROOT / 'data' / 'raw' / 'regional'
# Output: PROJECT_ROOT / 'data' / 'processed'
```
