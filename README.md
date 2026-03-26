# Lyrics Analysis

Topic modeling and emotional-tone comparison for song lyrics using BERTopic.

## What this project does

- Cleans lyrics text while preserving stopwords/pronouns.
- Generates sentence embeddings with `all-MiniLM-L6-v2`.
- Runs BERTopic to assign each song to a topic.
- Extracts top keywords per topic.
- Aggregates topic distribution by region.
- Scores emotional tone and aggregates by region and topic.

## Current architecture

```mermaid
flowchart TD
	A[Input CSV<br/>columns: song, region, lyrics] --> B[clean_lyrics]
	B --> B1[Remove bracket tags: [Verse], [Chorus], ...]
	B1 --> B2[Lowercase]
	B2 --> B3[Remove punctuation]
	B3 --> B4[Collapse whitespace]
	B4 --> C[Clean lyrics list]

	C --> D[SentenceTransformer<br/>all-MiniLM-L6-v2]
	D --> E[Embeddings]

	E --> F[BERTopic<br/>UMAP + HDBSCAN]
	C --> F
	F --> G[Topic per song]
	F --> H[Top keywords per topic]

	G --> I[Topic distribution by region]

	C --> J[Emotion model<br/>j-hartmann/emotion-english-distilroberta-base]
	J --> K[Chunk-level emotion scores]
	K --> L[Average per song]
	L --> M[Emotion by region]
	L --> N[Emotion by topic]

	G --> O[assignments_per_song.csv]
	H --> P[topic_keywords.csv]
	I --> Q[topic_distribution_by_region.csv]
	M --> R[emotion_by_region.csv]
	N --> S[emotion_by_topic.csv]
```

## Input format

Provide a CSV with these columns:

- `song`
- `region`
- `lyrics`

Example file: `data/processed/archive/sample_lyrics.csv`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Run

```bash
python -m lyrics_analysis --input data/processed/archive/sample_lyrics.csv --output-dir outputs
```

## Outputs

Generated files:

- `outputs/<input_name>_<timestamp>/topic_assignments_per_song.csv`
- `outputs/<input_name>_<timestamp>/topic_keywords.csv`
- `outputs/<input_name>_<timestamp>/topic_distribution_by_region.csv`
- `outputs/<input_name>_<timestamp>/emotion_by_region.csv`
- `outputs/<input_name>_<timestamp>/emotion_by_topic.csv`

Example run folder: `outputs/sample_lyrics_20260311_114120/`

## Notes

- BERTopic settings are adapted so small datasets can still run.
- Emotion scoring is chunked and averaged per song.
- Spotify/Genius ingestion is intentionally not wired yet (paused by request).

