"""Checkpointing and classifier-scoring helpers, extracted from
notebooks/04_classification.ipynb.

`load_zeroshot_classifier` / `load_goemotions_classifier` (which import
transformers/optimum and download model weights) are intentionally left in
the notebook — the classifier is passed into the classify_* functions here
as a plain callable, so this module stays importable without those heavy,
network-touching dependencies.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lyrics_analysis.pipeline.text import chunk_text

MIN_CONFIDENCE = 0.30  # confidence bar for the low_confidence FLAG (drops nothing)

# The zero-shot NLI classifier's candidate labels.
ZEROSHOT_EMOTIONS = [
    "love", "longing", "joy", "heartbreak", "grief",
    "despair", "hope", "lonely",
    "sensual", "anger",
]

# The sentence each candidate label is slotted into before the NLI model judges
# entailment against the lyrics. Phrasing it as "the dominant emotion" keeps the
# model judging song-level affect rather than whether the word merely appears.
HYPOTHESIS_TEMPLATE = "The dominant emotion in this song is {}."

# GoEmotions' fixed taxonomy (27 emotions + neutral).
GOEMOTIONS_EMOTIONS = [
    "admiration", "amusement", "anger", "annoyance", "approval",
    "caring", "confusion", "curiosity", "desire", "disappointment",
    "disapproval", "disgust", "embarrassment", "excitement", "fear",
    "gratitude", "grief", "joy", "love", "nervousness",
    "optimism", "pride", "realization", "relief", "remorse",
    "sadness", "surprise", "neutral",
]


def load_checkpoint(checkpoint_path: Path, emotion_cols: list[str]) -> pd.DataFrame | None:
    """
    Load an existing checkpoint CSV if it exists, else None.

    NOTE: a COMPLETE checkpoint makes classification a no-op — only rows with
    NaN scores get classified, so changing a SCORING setting and re-running
    silently reuses the old scores. This is exactly how this notebook came to
    disagree with its own data once already (04.1's checkpoint kept
    multi_label=True-shaped scores after the code was edited to
    multi_label=False — see docs/classifier_methodology.md). Delete the
    checkpoint when you change the taxonomy, the model, the chunking (the
    chunk_text overlap fix changes chunk boundaries), or ZEROSHOT_MULTI_LABEL.
    Changing MIN_CONFIDENCE is safe — it's applied below, which always re-runs.
    """
    if not checkpoint_path.exists():
        return None
    df = pd.read_csv(checkpoint_path)
    done = df[emotion_cols].notna().all(axis=1).sum()
    print(f"Checkpoint found: {done} / {len(df)} songs already classified.")
    if done == len(df):
        print("  ⚠ Checkpoint is COMPLETE — no song will be re-scored this run.")
        print("    Delete it first if you changed how scores are PRODUCED.")
    return df


def save_checkpoint(df: pd.DataFrame, checkpoint_path: Path) -> None:
    """Write current state (including any NaN emotion cols) to disk."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(checkpoint_path, index=False)


def derive_contract_columns(
    df: pd.DataFrame,
    emotion_cols: list[str],
    min_confidence: float = MIN_CONFIDENCE,
) -> pd.DataFrame:
    """
    Scores are independent per-label probabilities, so the dominant emotion is
    just the argmax; there is no competition to resolve. 'unclassified' is
    reserved for songs with NO scoreable lyrics (every score 0). Low confidence
    is recorded and flagged, never dropped — dropping on a per-classifier
    threshold is what previously left the two classifiers holding different
    song sets and made a config difference look like a model difference.
    """
    df = df.copy()
    df[emotion_cols] = df[emotion_cols].astype(float)

    max_score = df[emotion_cols].max(axis=1)
    has_signal = max_score > 0

    df["dominant_emotion"] = (
        df[emotion_cols].idxmax(axis=1).str.replace("emotion_", "", regex=False)
          .where(has_signal, other="unclassified")
    )
    df["dominant_score"] = max_score.where(has_signal)
    df["low_confidence"] = has_signal & (max_score < min_confidence)

    print(f"unclassified (no scoreable lyrics): {(~has_signal).sum()} / {len(df)}")
    print(f"low_confidence (scored, but < {min_confidence}): "
          f"{df['low_confidence'].sum()} / {len(df)}")
    return df


def classify_song_zeroshot(
    lyrics: str,
    classifier,
    emotions: list[str] = ZEROSHOT_EMOTIONS,
    multi_label: bool = True,
    hypothesis_template: str = HYPOTHESIS_TEMPLATE,
    batch_size: int = 16,
) -> dict:
    """
    Classify a single song's lyrics.
    Chunk scores are averaged to produce a song-level score per emotion.
    Returns dict {emotion: score}.
    """
    if not isinstance(lyrics, str) or not lyrics.strip():
        return {e: 0.0 for e in emotions}

    chunks = chunk_text(lyrics)
    raw_results = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        raw_results.extend(
            classifier(
                batch,
                candidate_labels=emotions,
                multi_label=multi_label,
                hypothesis_template=hypothesis_template,
            )
        )

    # The pipeline returns labels sorted by score, so zip back into a dict
    # rather than assuming `emotions` order.
    all_scores = [dict(zip(r["labels"], r["scores"])) for r in raw_results]

    return {
        e: round(sum(s[e] for s in all_scores) / len(all_scores), 4)
        for e in emotions
    }


def classify_song_goemotions(
    lyrics: str,
    classifier,
    emotions: list[str] = GOEMOTIONS_EMOTIONS,
) -> dict:
    """
    Classify a single song's lyrics.

    Each chunk gets independent sigmoid scores for all 28 labels — a song can
    score high on several emotions at once, and scores do not sum to 1 (same
    behaviour as zero-shot under multi_label=True; the two differ in model and
    label set, not in scoring mechanics). Chunk scores are averaged to a
    song-level score.

    Chunks are classified one at a time, NOT batched. The ONNX export this was
    built for has a fixed-batch assumption in its position-embedding
    broadcast — passing a list of >1 texts triggers "INVALID_ARGUMENT ...
    Expand node ... invalid expand shape" from onnxruntime. Single-example
    calls avoid the broadcast entirely.

    Whether a single-string call returns a flat list of 28 dicts or a nested
    [[...]] list varies by transformers/optimum version, so unwrap defensively.

    Returns dict {emotion: score}.
    """
    if not isinstance(lyrics, str) or not lyrics.strip():
        return {e: 0.0 for e in emotions}

    all_scores = []
    for chunk in chunk_text(lyrics):
        result = classifier(chunk, truncation=True)
        if isinstance(result, list) and result and isinstance(result[0], list):
            result = result[0]  # unwrap [[{...}, ...]] -> [{...}, ...]
        all_scores.append({d["label"]: d["score"] for d in result})

    return {
        e: round(sum(s.get(e, 0.0) for s in all_scores) / len(all_scores), 4)
        for e in emotions
    }
