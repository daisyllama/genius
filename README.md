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
  -> 04.1_emotion_scores_zeroshot.csv    (04_classification.ipynb § A) -- zero-shot NLI, 10 custom labels
  -> 04.2_emotion_scores_goemotions.csv  (04_classification.ipynb § B) -- GoEmotions, 28 labels, run on Databricks
  -> 05.1_titles_emotion_scores_zeroshot.csv    (05.1_song_analysis_zeroshot.ipynb)
  -> 05.2_titles_emotion_scores_goemotions.csv  (05.2_song_analysis_goemotions.ipynb)
  -> charts                 (06.1_exploration_charts_zeroshot.ipynb, 06.2_exploration_charts_goemotions.ipynb)
  -> 07_classifier_comparison_regional.csv (07_compare_classifiers.ipynb)
```

04.1 and 04.2 are alternative classifiers over the same `03_lyrics_trans.csv` input, produced by one notebook (`04_classification.ipynb`, § A / § B) under a shared scoring contract — not sequential steps, and not two separate notebooks any more. Each fork stays separate all the way through `05.1`/`06.1` (zero-shot) and `05.2`/`06.2` (GoEmotions) so 10-label and 28-label scores never get pooled into one schema. `07_compare_classifiers.ipynb` is the only place the two forks meet. Design rationale for all of the above is in `docs/classifier_methodology.md`.

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

#### 5a. `04_classification.ipynb` § A — zero-shot NLI (`facebook/bart-large-mnli`)

**Zero-shot classification** via an NLI model lets us define our own emotion labels (`love`, `longing`, `joy`, `heartbreak`, `grief`, `despair`, `hope`, `lonely`, `sensual`, `anger`) without training data — the model just needs to judge whether lyrics entail "The dominant emotion in this song is `{label}`." This matters here because the interesting emotional vocabulary for songs (`longing`, `heartbreak`, `despair`) doesn't overlap much with any existing labeled emotion dataset.

`facebook/bart-large-mnli` was chosen as the strongest general-purpose zero-shot NLI model readily available via `transformers`; `cross-encoder/nli-deberta-v3-large` was noted as a higher-accuracy alternative at ~2x the inference cost, left as a future swap if quality demands it.

Two scoring decisions worth flagging, both revisited during the 2026-08-06 classifier-fairness pass (`docs/classifier_methodology.md`):
- **`ZEROSHOT_MULTI_LABEL = True`, not `False`.** Independent per-label scoring inflates — "longing" and "sensual" score high almost regardless of content, because the model over-estimates certain labels globally when they aren't forced to compete. A 2026-07-12 fix switched to `multi_label=False` (softmax competition) to fix that. But comparing this classifier against GoEmotions requires both to emit the *same kind* of score (independent per-label probabilities), and GoEmotions can't be made competitive without retraining — so as of 2026-08-06 `multi_label` is back to `True`. The inflation problem is real and still there; it's now handled at analysis time instead, by z-scoring each label against its own regional baseline (§6 below) rather than by suppressing it at scoring time.
- **Custom hypothesis template.** `"The dominant emotion in this song is {}."` instead of the default template — this phrasing pushes the model toward picking one best-fitting emotion per chunk rather than treating each label as an independent yes/no question.

Lyrics are chunked (~350 words) to stay under the model's token limit, classified in batches of 16, and chunk-level scores are averaged to a per-song score. The pipeline checkpoints every 10 songs so a multi-hour CPU/GPU run survives interruption.

#### 5b. `04_classification.ipynb` § B — GoEmotions (`SamLowe/roberta-base-go_emotions-onnx`)

The alternative: a **supervised, fine-tuned** classifier trained on GoEmotions (28 labels: `admiration`, `amusement`, `anger`, ..., `neutral`), exported to ONNX and served via `optimum`'s ONNX Runtime backend. One forward pass per chunk returns all 28 label scores directly — no NLI hypothesis pairs — so it's substantially faster than zero-shot inference. The tradeoff is losing the custom song-emotion vocabulary: GoEmotions' labels were trained on Reddit-comment tone, so categories like `admiration`, `curiosity`, `approval` show up that don't map cleanly onto lyrical themes, and labels like `longing`/`heartbreak`/`despair` that zero-shot lets you define directly aren't available at all.

Both classifiers now share one **scoring contract**: independent per-label probabilities in [0, 1] (GoEmotions via its native sigmoid head, zero-shot via `multi_label=True` above), `unclassified` means "no scoreable lyrics" in both (not a confidence cutoff), and confidence (`dominant_score` / `low_confidence` at a shared `MIN_CONFIDENCE = 0.30`) is recorded as data rather than used to drop rows. This wasn't always true — see `docs/classifier_methodology.md` for what the unforced differences were hiding before it was unified.

Cleaning/chunking logic, `MIN_CONFIDENCE`, and checkpointing are shared with § A in the same notebook, since that plumbing is model-agnostic; only the model call and label set differ. § B is intended to be run on Databricks rather than locally.

### 6. Analysis & Charting

`05.1_song_analysis_zeroshot.ipynb` / `05.2_song_analysis_goemotions.ipynb` join each classifier's emotion scores back onto chart metadata (rank, region) and produce the final per-song, per-region dataset for that fork. `06.1_exploration_charts_zeroshot.ipynb` / `06.2_exploration_charts_goemotions.ipynb` visualize regional emotional character, including a z-score heatmap showing each region's deviation from the global mean — this exists specifically because raw emotion scores are hard to compare across regions when the absolute scoring scale is compressed (see §7 below); showing deviation from mean surfaces what's actually distinctive per region. The two forks stay separate through 05/06 on purpose, so 10-label and 28-label scores never get pooled into one schema with mostly-missing cells.

### 7. Comparing the two classifiers — `07_compare_classifiers.ipynb`

Since 04.1 and 04.2 classify the same 1,105 songs under different taxonomies, this notebook checks how much they actually agree, restricted to the 4 labels both taxonomies share (`love`, `joy`, `grief`, `anger`) — comparing anything outside that overlap isn't meaningful since one side simply has no equivalent label.

Findings from the 2026-08-06 re-run (first run under the unified contract):
- **Coverage is no longer a differentiator, as intended**: both classifiers now score 90.3% of songs (998/1,105) and agree on exactly which 107 are `unclassified` — that used to look like a ~93-song gap, and it was entirely a threshold mismatch, not a model difference (see `docs/classifier_methodology.md`).
- **Confidence is** a real differentiator: GoEmotions flags 94 songs (8.5%) `low_confidence` at the shared 0.30 bar, vs. 5 for zero-shot (0.5%). Median `dominant_score` is 0.971 (zero-shot) vs. 0.536 (GoEmotions) — a calibration gap (conservative sigmoid trained on short Reddit comments vs. entailment probabilities that run hot), not an accuracy difference.
- **Score correlation** on the shared labels is positive but moderate (pearson r = 0.30–0.48 across love/joy/grief/anger) — the two models don't disagree on direction, but their scoring mechanics aren't directly comparable in magnitude, so rank/z-score comparisons are the trustworthy ones.
- **Dominant-emotion agreement** is low (29.8%, of 305 songs where GoEmotions' non-neutral pick lands in the shared set) — mostly because zero-shot's richer romantic/melancholic vocabulary (`sensual`, `longing`, `heartbreak`, `lonely`) captures nuance GoEmotions collapses into `love` or `sadness`. This reads as a taxonomy-granularity mismatch rather than the models disagreeing about song content.
- **The headline test — do the two classifiers draw the same regional map? — came back negative.** Z-scoring each shared label across regions within each fork and correlating the two profiles gives **r = 0.153** overall (love r=0.672, anger r=0.371, joy r=-0.027, grief r=-0.402). The methodology doc's own bar was r > 0.7 for "same story, different vocabulary" and r < 0.3 for "taxonomy choice materially changes the regional conclusion" — this result is squarely in the second bucket. **Practical upshot: regional claims in this README and the site report should be read as zero-shot-specific, not classifier-agnostic** — GoEmotions does not corroborate them, particularly for `joy` and `grief`.
- Neither classifier is "more correct" — zero-shot trades speed for a song-specific label set with better calibration; GoEmotions trades label nuance for faster, benchmarked, general-purpose inference. But which one you pick now visibly changes the regional conclusion, which it wasn't supposed to.

## Repo Layout

```
data/
  raw/regional/       weekly Spotify chart exports (input, one CSV per region)
  processed/          current pipeline outputs (00_titles.csv ... 07_classifier_comparison_regional.csv)
  archive/            superseded processing runs / old checkpoints, kept for reference
notebooks/            the pipeline, run in numeric order (01 -> 07); notebooks/archive/ holds
                      the pre-2026-08-06 04.1/04.2/05/06 notebooks superseded by the split above
src/lyrics_analysis/  early attempt at a package/DB-backed version (see Notes)
docs/classifier_methodology.md  design rationale for the two-classifier setup and its scoring contract
site/                local-only (gitignored) data-story report built from these outputs — see its own
                      dated source note before trusting numbers in it
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
| `transformers` (`facebook/bart-large-mnli`) | Emotion classification (04.1, § A) | No labeled emotion data exists, so zero-shot NLI is the only classification approach that doesn't require training; BART-MNLI is the strongest general zero-shot model available off the shelf |
| `optimum[onnxruntime]` (`SamLowe/roberta-base-go_emotions-onnx`) | Emotion classification (04.2, § B) | Supervised, single-pass classifier — faster than zero-shot NLI; traded off against being locked into GoEmotions' fixed 28-label taxonomy |
| `duckdb` | Joining pipeline outputs | SQL joins over CSVs in `05.1`/`05.2_song_analysis_*.ipynb` without standing up a database |
| `pandas` | Everything tabular | Notebook-first workflow, no need for a heavier data framework at this scale (~1-2k songs) |

`bertopic`, `sentence-transformers`, `umap-learn`, `hdbscan`, `scikit-learn` are installed for exploratory topic-modeling work that hasn't been folded into the numbered pipeline yet.

## Known Limitations

- ~31% of unique chart songs (495 of ~1,600 title entries) have no Genius lyrics match and are excluded from emotion scoring.
- Genius lyrics are not always accurate — some tracks matched the wrong song/version or returned lyrics with scraping artifacts (ads, wrong-script text). Flagged via length > 5,000 chars or unexpected symbols/non-language characters, then manually patched using a Google search for the correct lyrics rather than trusting the API result as-is. See `cleanup_notes.txt`.
- Translation QA pass rate is 90.48% against a 97% target — ~56 Chinese songs have partial/mixed-language translations; most are flagged via `translation_review_required`, and a couple of short songs slipped through silently (see `data/processed/lyrics_trans_qa_failures.csv`). Left unpatched: zero-shot NLI (04.1) still scores non-English text reasonably, so this doesn't block emotion classification the way it would for an English-only model.
- `fasttext-wheel` must be installed separately from `requirements.txt` for the QA notebook to run.
- **Regional emotion claims are zero-shot-specific, not classifier-agnostic.** §7's regional z-score map comparison between the two classifiers came back r = 0.153 (love and anger agree reasonably, joy and grief don't at all) — well below the bar for "same regional story, different vocabulary." A regional claim backed only by the zero-shot fork should not be assumed to hold under GoEmotions too.

## Notes

- This repository is notebook-only by design — the pipeline runs interactively and each stage's output is inspected before moving on. A `src/lyrics_analysis/` package/DB-backed variant was explored but is not part of the active workflow.
- Source chart data is Spotify Charts weekly regional exports, stored in `data/raw/regional/`.
- `plan.md` and `progress.md` are local working notes (task planning / session progress) and are gitignored — they're not part of the versioned project state.
