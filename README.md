# Lyrics Analysis

Notebook-first pipeline for collecting lyrics from Spotify chart tracks, detecting language, translating to English, and scoring emotions.

## Workflow

Run notebooks in this order:

1. `notebooks/01_lyrics_ingestion.ipynb`
2. `notebooks/02_language_detection.ipynb`
3. `notebooks/03_lyrics_translate.ipynb`
4. `notebooks/03_lyrics_translation_qa.ipynb`
5. `notebooks/04_classification_zeroshot.ipynb`
6. `notebooks/05_song_analysis.ipynb`

## Data Pipeline

```text
data/raw/regional-*.csv
  -> data/processed/00_titles.csv
  -> data/processed/01_lyrics.csv
  -> data/processed/02_lyrics_lang.csv
  -> data/processed/03_lyrics_trans.csv
  -> data/processed/04_emotion_scores.csv
  -> data/processed/05_titles_emotion_scores.csv
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Key Dependencies

- Data: `pandas`, `numpy`
- Topic/embeddings: `bertopic`, `sentence-transformers`, `torch`, `umap-learn`, `hdbscan`
- Translation: `deep-translator`
- Modeling: `transformers`, `scikit-learn`

## Notes

- This repository is currently notebook-only.
- Python package/CLI execution is intentionally not part of the active workflow.
- Top chart source data is from Spotify charts exports in `data/raw/`.

