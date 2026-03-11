from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from umap import UMAP

from .cleaning import clean_lyrics


def _chunk_text(text: str, max_words: int = 180) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def _emotion_scores_for_text(text: str, emotion_clf, max_words: int = 180) -> Dict[str, float]:
    chunks = _chunk_text(text, max_words=max_words)
    all_scores = []

    for chunk in chunks:
        if not chunk.strip():
            continue
        raw_scores = emotion_clf(chunk, truncation=True)

        if isinstance(raw_scores, list) and raw_scores and isinstance(raw_scores[0], dict):
            normalized_scores = raw_scores
        elif isinstance(raw_scores, list) and raw_scores and isinstance(raw_scores[0], list):
            normalized_scores = raw_scores[0]
        else:
            continue

        all_scores.append(normalized_scores)

    if not all_scores:
        return {}

    labels = sorted({item["label"] for chunk_scores in all_scores for item in chunk_scores})
    averaged = {}
    for label in labels:
        label_values = [next((x["score"] for x in chunk_scores if x["label"] == label), 0.0) for chunk_scores in all_scores]
        averaged[label] = float(np.mean(label_values))

    return averaged


def lyric_topic_emotion_pipeline(df: pd.DataFrame):
    """
    Input DataFrame columns required: [song, region, lyrics]

    Steps:
    - generate embeddings using sentence-transformers (all-MiniLM-L6-v2)
    - apply BERTopic
    - return topic assignments per song
    - extract top keywords per topic
    - output topic distribution grouped by region
    - compare emotional tone by region and topic
    """
    required = {"song", "region", "lyrics"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    work = df.copy()
    work["clean_lyrics"] = work["lyrics"].fillna("").map(clean_lyrics)
    n_samples = len(work)
    if n_samples == 0:
        raise ValueError("Input dataframe is empty.")

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = embedder.encode(work["clean_lyrics"].tolist(), show_progress_bar=True, convert_to_numpy=True)

    n_neighbors = max(2, min(15, n_samples - 1)) if n_samples > 2 else 2
    min_cluster_size = max(2, min(10, n_samples))
    min_samples = max(1, min(5, n_samples))

    umap_model = UMAP(
        n_neighbors=n_neighbors,
        n_components=2,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )

    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        prediction_data=True,
    )

    topic_model = BERTopic(verbose=True, umap_model=umap_model, hdbscan_model=hdbscan_model)
    topics, probs = topic_model.fit_transform(work["clean_lyrics"].tolist(), embeddings)

    assignments = work[["song", "region"]].copy()
    assignments["topic"] = topics
    assignments["topic_probability"] = [
        float(np.max(prob)) if isinstance(prob, np.ndarray) and prob.size > 0 else np.nan
        for prob in probs
    ]

    topic_keywords_rows = []
    for topic_id in sorted(topic for topic in set(topics) if topic != -1):
        words_scores = topic_model.get_topic(topic_id) or []
        topic_keywords_rows.append(
            {
                "topic": topic_id,
                "keywords": ", ".join([word for word, _ in words_scores[:10]]),
            }
        )
    topic_keywords = pd.DataFrame(topic_keywords_rows)

    topic_distribution_by_region = pd.crosstab(assignments["region"], assignments["topic"], normalize="index").reset_index()

    emotion_clf = pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base",
        return_all_scores=True,
    )

    emotion_scores = work["clean_lyrics"].map(lambda text: _emotion_scores_for_text(text, emotion_clf))
    emotion_df = pd.json_normalize(emotion_scores).fillna(0.0)
    emotion_df.columns = [f"emotion_{col}" for col in emotion_df.columns]

    assignments = pd.concat([assignments, emotion_df], axis=1)
    emotion_cols = [col for col in assignments.columns if col.startswith("emotion_")]

    if emotion_cols:
        assignments["dominant_emotion"] = assignments[emotion_cols].idxmax(axis=1).str.replace("emotion_", "", regex=False)
    else:
        assignments["dominant_emotion"] = np.nan

    emotion_by_region = assignments.groupby("region")[emotion_cols].mean().reset_index() if emotion_cols else pd.DataFrame()
    emotion_by_topic = assignments.groupby("topic")[emotion_cols].mean().reset_index() if emotion_cols else pd.DataFrame()

    return {
        "topic_model": topic_model,
        "assignments_per_song": assignments,
        "topic_keywords": topic_keywords,
        "topic_distribution_by_region": topic_distribution_by_region,
        "emotion_by_region": emotion_by_region,
        "emotion_by_topic": emotion_by_topic,
    }
