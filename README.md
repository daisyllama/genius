# Lyrics Analysis

A notebook-first pipeline that pulls the top charting songs across 8 regions (Spotify Charts), fetches their lyrics, detects source language, translates everything to English, and scores each song's emotional content — with the goal of comparing emotional character across regions/cultures.

## What This Does

Starting from weekly regional Spotify chart exports, the pipeline:

1. **Ingests** the top-ranked tracks per region and fetches lyrics from Genius
2. **Detects** the original language of each song's lyrics
3. **Translates** non-English lyrics to English
4. **QA-checks** translation quality before trusting it downstream
5. **Classifies** each song's emotion — two alternative approaches (04.1 zero-shot NLI, 04.2 GoEmotions)
6. **Aggregates** results per region/song for comparison and charting

Regions covered: Argentina, Colombia, Global, Japan, Singapore, Spain, Taiwan, USA.

## Pipeline & Rationale

```
data/raw/regional/*.csv
  -> 00_titles.csv           (01_lyrics_ingestion.ipynb)
  -> 01_lyrics.csv           (01_lyrics_ingestion.ipynb)
  -> 02_lyrics_lang.csv      (02_language_detection.ipynb)
  -> 03_lyrics_trans.csv     (03_lyrics_translate.ipynb)
  -> qa_failures/qa_summary  (03_lyrics_translation_qa.ipynb)
  -> 04.1_emotion_scores_zeroshot.csv   (04.1_classification_zeroshot.ipynb)  -- zero-shot NLI, 10 custom labels
  -> 04.2_emotion_scores_goemotions.csv (04.2_classification_goemotions.ipynb) -- GoEmotions, 28 labels, run on Databricks
  -> 05_titles_emotion_scores.csv (05_song_analysis.ipynb)
  -> charts                 (06_exploration_charts.ipynb)
  -> 07_classifier_comparison_regional.csv (07_compare_classifiers.ipynb)
```

04.1 and 04.2 are alternative classifiers over the same `03_lyrics_trans.csv` input — not sequential steps. `05_song_analysis.ipynb` defaults to reading `04.1_emotion_scores_zeroshot.csv`. `07_compare_classifiers.ipynb` compares the two directly.

### 1. Ingestion — `lyricsgenius`

Raw chart CSVs give title/artist/rank per region but no lyrics. `lyricsgenius` wraps the Genius API and is the most maintained Python client for it. Lyrics fetching is deduplicated by `spotify_uri` before hitting the API (many tracks appear on multiple regional charts), and results are cached to a checkpoint CSV so an interrupted run can resume without re-fetching tracks already pulled — Genius lookups are slow and rate-limited, so this mattered in practice.

Of the initial ~694 unique tracks, 42 had no retrievable lyrics (no match / instrumental) — these carry through the pipeline as empty and get excluded from emotion scoring downstream.

**Genius API lyrics are not always accurate.** `search_song()` sometimes matches the wrong track, returns a page with ads/annotations baked into the text, or pulls a different version/remix than the one on the chart. Rather than trust every result blindly, songs were flagged for manual review when they showed signs of a bad match — length > 5,000 characters (often duplicated/glued lyrics from a wrong-page match) or unexpected non-language characters and symbols (scraping artifacts, ad text, or wrong-script content that shouldn't be there for that track). Flagged rows were manually corrected by hand — patching the record and re-sourcing the actual lyrics via a Google search — rather than re-running the fetch, since the wrong Genius match wouldn't fix itself on retry. See `cleanup_notes.txt` for the tracks flagged this way.

### 2. Language Detection — script check + FastText

A single language-ID approach wasn't reliable on its own, so this is a **two-pass** strategy:

- **Pass 1 (rule-based script detection):** scans lyrics for Unicode script ranges (Hiragana/Katakana, CJK ideographs, Hangul, Arabic, Thai, Cyrillic) and assigns a language directly if one of these scripts dominates. This exists because many chart songs mix scripts — e.g. Japanese lyrics with English hooks — and FastText alone would misclassify these as English due to the Latin-script segments.
- **Pass 2 (FastText `lid.176`):** for anything that passes through Pass 1 unchanged (Latin-script or ambiguous), FastText's language-identification model classifies the first 200 characters. FastText was chosen over `langdetect` (tried earlier, see `data/archive/`) for speed and better short-text accuracy.

A NumPy 2.x compatibility shim is monkey-patched onto FastText's `predict()` in the notebook, since the installed `fasttext` build calls `np.array(..., copy=False)`, which NumPy 2.x rejects.

### 3. Translation — `deep-translator` (Google Translate backend)

`deep-translator`'s `GoogleTranslator` was chosen over a local MT model (e.g. NLLB, MarianMT) for pragmatic reasons: chart lyrics span many languages (Spanish, Chinese, Japanese, Korean, Portuguese, etc.) and a single hosted API avoids managing per-language local models and their quality inconsistencies. It runs with a timeout guard per call (30s) and language-code normalization (e.g. mapping `zh-cn`/`zh_cn` variants to what the API expects) since chart-detected language codes aren't always in the exact form the translator needs.

Songs longer than 5,000 characters are flagged `translation_review_required` rather than blindly trusted, since very long lyrics are more likely to hit truncation or partial-translation failures silently.

### 4. Translation QA — FastText again, as a validator

Rather than trusting translation output, a dedicated QA pass re-runs FastText on `lyrics_in_en` to confirm it actually reads as English (confidence ≥ 0.70). Target pass rate was 97%; the last full run measured **90.48%** — root-caused to a batch of Chinese songs that partially failed translation (mixed-language output). Most of these were already caught by the length-based `translation_review_required` flag; a couple of short Chinese songs slipped through silently.

Those remaining slipped-through, still-non-English rows were left as-is rather than manually re-translated. `facebook/bart-large-mnli` (used in 04.1) is itself multilingual under the hood — its underlying BART/mBART-style training means zero-shot NLI still produces reasonable entailment scores on non-English text, even against English-language candidate labels. So a handful of songs reaching emotion classification without full translation doesn't silently corrupt those scores the way it would for a model that only understands English — the QA step still matters for catching *broken* translations, but perfect translation coverage isn't a hard precondition for 04.1 specifically.

### 5. Emotion Classification — two approaches, run side by side

No labeled emotion dataset exists for this song set. Two different classification strategies are implemented as parallel notebooks over the same input (`03_lyrics_trans.csv`), rather than one replacing the other — they trade off label flexibility against inference speed/calibration, and it's an open question which is more useful for this dataset.

#### 5a. `04.1_classification_zeroshot.ipynb` — zero-shot NLI (`facebook/bart-large-mnli`)

**Zero-shot classification** via an NLI model lets us define our own emotion labels (`love`, `longing`, `joy`, `heartbreak`, `grief`, `despair`, `hope`, `lonely`, `sensual`, `anger`) without training data — the model just needs to judge whether lyrics entail "The dominant emotion in this song is `{label}`." This matters here because the interesting emotional vocabulary for songs (`longing`, `heartbreak`, `despair`) doesn't overlap much with any existing labeled emotion dataset.

`facebook/bart-large-mnli` was chosen as the strongest general-purpose zero-shot NLI model readily available via `transformers`; `cross-encoder/nli-deberta-v3-large` was noted as a higher-accuracy alternative at ~2x the inference cost, left as a future swap if quality demands it.

Two scoring decisions worth flagging:
- **`multi_label=False`, not `True`.** The first pass used `multi_label=True` (each emotion scored independently), which caused score inflation — nearly every song scored 0.7+ on "longing" and "sensual" regardless of content, because the model over-estimates certain labels globally when they aren't forced to compete. Switching to `multi_label=False` makes emotions compete via softmax in one pass, so a song's dominant emotion reflects what's actually distinctive about it rather than a global bias.
- **Custom hypothesis template.** `"The dominant emotion in this song is {}."` instead of the default template — this phrasing pushes the model toward picking one best-fitting emotion per chunk rather than treating each label as an independent yes/no question.

Lyrics are chunked (~350 words) to stay under the model's token limit, classified in batches of 16, and chunk-level scores are averaged to a per-song score. The pipeline checkpoints every 10 songs so a multi-hour CPU/GPU run survives interruption.

#### 5b. `04.2_classification_goemotions.ipynb` — GoEmotions (`SamLowe/roberta-base-go_emotions-onnx`)

The alternative: a **supervised, fine-tuned** classifier trained on GoEmotions (28 labels: `admiration`, `amusement`, `anger`, ..., `neutral`), exported to ONNX and served via `optimum`'s ONNX Runtime backend. One forward pass per chunk returns all 28 label scores directly — no NLI hypothesis pairs — so it's substantially faster than zero-shot inference. The tradeoff is losing the custom song-emotion vocabulary: GoEmotions' labels were trained on Reddit-comment tone, so categories like `admiration`, `curiosity`, `approval` show up that don't map cleanly onto lyrical themes, and labels like `longing`/`heartbreak`/`despair` that zero-shot lets you define directly aren't available at all.

Scoring is structurally different from 04.1: GoEmotions is multi-label by training (independent sigmoid per label, not a competing softmax), so a song's scores don't sum to ~1 the way 04.1's do — multiple emotions can legitimately score high simultaneously. Dominant emotion is still derived via argmax across the emotion columns, but gated on an `UNCLASSIFIED_THRESHOLD` (0.30) rather than `> 0`, since independent sigmoids rarely land on an exact zero.

Cleaning/chunking logic is shared with 04.1 (same `clean_lyrics`/`chunk_text`, since that preprocessing is model-agnostic). This notebook is intended to be run on Databricks rather than locally.

### 6. Analysis & Charting

`05_song_analysis.ipynb` joins emotion scores back onto chart metadata (rank, region) and produces the final per-song, per-region dataset. `06_exploration_charts.ipynb` visualizes regional emotional character, including a differential chart showing each region's deviation from the global mean — this was added specifically because raw emotion scores are hard to compare across regions when the absolute scoring scale is compressed; showing deviation from mean surfaces what's actually distinctive per region.

### 7. Comparing the two classifiers — `07_compare_classifiers.ipynb`

Since 04.1 and 04.2 classify the same 1,105 songs under different taxonomies, this notebook checks how much they actually agree, restricted to the 4 labels both taxonomies share (`love`, `joy`, `grief`, `anger`) — comparing anything outside that overlap isn't meaningful since one side simply has no equivalent label.

Findings from the last run:
- **Coverage**: zero-shot classifies 90.2% of songs (108 unclassified), GoEmotions 81.8% (201 unclassified) — expected, since GoEmotions' independent sigmoid scores rarely all clear a fixed 0.30 bar the way a forced-competition softmax does.
- **Score correlation** on the shared labels is positive but moderate (r = 0.28–0.48) — the two models don't disagree on direction, but their scoring mechanics (competing softmax vs. independent sigmoid) aren't directly comparable in magnitude.
- **Dominant-emotion agreement** is low (23.4%) even when GoEmotions' pick is in the shared set — mostly because 04.1's richer romantic/melancholic vocabulary (`sensual`, `longing`, `heartbreak`, `lonely`) captures nuance GoEmotions collapses into `love` or `sadness`. This reads as a taxonomy-granularity mismatch rather than the models disagreeing about song content.
- Neither classifier is "more correct" — 04.1 trades speed for a song-specific label set, 04.2 trades label nuance for faster, general-purpose inference.

## Repo Layout

```
data/
  raw/regional/       weekly Spotify chart exports (input, one CSV per region)
  processed/          current pipeline outputs (00_titles.csv ... 05_titles_emotion_scores.csv)
  archive/            superseded processing runs / old checkpoints, kept for reference
notebooks/            the pipeline, run in numeric order (01 -> 06)
src/lyrics_analysis/  early attempt at a package/DB-backed version (see Notes)
```

See `DATA_STRUCTURE.md` for the full breakdown of `data/`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Genius API access requires a `.env` file at the project root with:
```
GENIUS_ACCESS_TOKEN=...
```

## Key Dependencies & Why

| Tool | Used for | Why this over alternatives |
|---|---|---|
| `lyricsgenius` | Lyrics fetch | Best-maintained Genius API wrapper |
| `fasttext` (`lid.176`) | Language ID | Faster + more accurate than `langdetect` on short lyric snippets; used for both initial detection and translation QA |
| `deep-translator` | Translation | Single hosted API covers all chart languages without managing per-language local MT models |
| `transformers` (`facebook/bart-large-mnli`) | Emotion classification (04.1) | No labeled emotion data exists, so zero-shot NLI is the only classification approach that doesn't require training; BART-MNLI is the strongest general zero-shot model available off the shelf |
| `optimum[onnxruntime]` (`SamLowe/roberta-base-go_emotions-onnx`) | Emotion classification (04.2) | Supervised, single-pass classifier — faster than zero-shot NLI; traded off against being locked into GoEmotions' fixed 28-label taxonomy |
| `duckdb` | Joining pipeline outputs | SQL joins over CSVs in `05_song_analysis.ipynb` without standing up a database |
| `pandas` | Everything tabular | Notebook-first workflow, no need for a heavier data framework at this scale (~1-2k songs) |

`bertopic`, `sentence-transformers`, `umap-learn`, `hdbscan`, `scikit-learn` are installed for exploratory topic-modeling work that hasn't been folded into the numbered pipeline yet.

## Known Limitations

- ~31% of unique chart songs (495 of ~1,600 title entries) have no Genius lyrics match and are excluded from emotion scoring.
- Genius lyrics are not always accurate — some tracks matched the wrong song/version or returned lyrics with scraping artifacts (ads, wrong-script text). Flagged via length > 5,000 chars or unexpected symbols/non-language characters, then manually patched using a Google search for the correct lyrics rather than trusting the API result as-is. See `cleanup_notes.txt`.
- Translation QA pass rate is 90.48% against a 97% target — ~56 Chinese songs have partial/mixed-language translations; most are flagged via `translation_review_required`, and a couple of short songs slipped through silently (see `data/processed/lyrics_trans_qa_failures.csv`). Left unpatched: zero-shot NLI (04.1) still scores non-English text reasonably, so this doesn't block emotion classification the way it would for an English-only model.
- `fasttext-wheel` must be installed separately from `requirements.txt` for the QA notebook to run.

## Notes

- This repository is notebook-only by design — the pipeline runs interactively and each stage's output is inspected before moving on. A `src/lyrics_analysis/` package/DB-backed variant was explored but is not part of the active workflow.
- Source chart data is Spotify Charts weekly regional exports, stored in `data/raw/regional/`.
- `plan.md` and `progress.md` are local working notes (task planning / session progress) and are gitignored — they're not part of the versioned project state.
