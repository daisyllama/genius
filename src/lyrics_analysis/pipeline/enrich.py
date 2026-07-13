"""Incremental enrichment helpers for lyrics, language, translation, and emotion scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class EnrichmentVersion:
    language_detector_version: str
    translator_version: str
    emotion_model_version: str


def needs_translation(original_lang: str | None, lyrics: str | None) -> bool:
    if not lyrics:
        return False
    return original_lang not in {None, "", "en"}


def should_retry_translation(source_text: str | None, translated_text: str | None) -> bool:
    if not source_text:
        return False
    if not translated_text:
        return True
    return translated_text.strip() == source_text.strip()


def normalize_emotion_scores(scores: dict[str, float]) -> dict[str, float]:
    total = float(sum(scores.values())) if scores else 0.0
    if total <= 0:
        return {key: 0.0 for key in scores}
    return {key: value / total for key, value in scores.items()}


def to_emotion_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)
