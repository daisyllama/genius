"""Lyrics cleaning and chunking helpers, extracted from
notebooks/04_classification.ipynb.
"""

from __future__ import annotations

import re

CHUNK_WORDS = 350  # words per chunk; both classifiers take 512 tokens
CHUNK_OVERLAP = 30  # words of overlap between consecutive chunks


def clean_lyrics(text: str, artist: str = "") -> str:
    """
    Remove structural noise but preserve punctuation and casing.
    Punctuation (! ? ...) and capitalisation carry emotional signal for both
    classifiers — don't strip them.

    artist: the artist string from the dataframe row. When provided, the first
    line is dropped only if its tokens are a subset of the known artist names —
    much more precise than a regex heuristic. Falls back to the regex heuristic
    when artist is unavailable.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    def is_artist_credit(line: str) -> bool:
        """
        True if every name token in `line` exists in the artist pool.
        Both strings are split on commas, ampersands, and feat/ft.

            artist = "Jason, Bonnie"          line = "Jason"          → True
            artist = "ARIA VEGA, Ryan Castro" line = "Ryan Castro"    → True
            artist = "Jason, Bonnie"          line = "Baby come back" → False
        """
        splitter = r"[,&]|\bfeat\.?\b|\bft\.?\b"
        artist_tokens = {
            t.strip().lower()
            for t in re.split(splitter, artist, flags=re.IGNORECASE)
            if t.strip()
        }
        line_tokens = {
            t.strip().lower()
            for t in re.split(splitter, line, flags=re.IGNORECASE)
            if t.strip()
        }
        return bool(line_tokens) and line_tokens.issubset(artist_tokens)

    # Remove section headers: [Verse 1], [Chorus], [Bridge] etc.
    text = re.sub(r"\[[^\]]*\]", "", text)

    # Remove repetition annotations: (x3), (×2), (2x)
    text = re.sub(r"\([\d×xX]+\)", "", text)

    # Remove leading artist/feature credits that sometimes appear at the top of
    # translated lyrics (e.g. "ARIA VEGA, Ryan Castro\n").
    lines = text.strip().splitlines()
    if lines:
        first = lines[0].strip()
        if artist and is_artist_credit(first):
            lines = lines[1:]
        elif not artist and re.match(r"^[A-Za-z\s,&]+$", first) and len(first) < 80:
            lines = lines[1:]
    text = "\n".join(lines)

    # Collapse excessive blank lines but keep single line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def dedupe_lines(text: str) -> str:
    """
    Remove duplicate lines (repeated choruses inflate scores).
    Keeps first occurrence; preserves order.
    """
    seen = set()
    result = []
    for line in text.splitlines():
        key = line.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(line.strip())
    return " ".join(result)


def prepare_lyrics(text: str, artist: str = "") -> str:
    return dedupe_lines(clean_lyrics(text, artist=artist))


def chunk_text(
    text: str,
    chunk_words: int = CHUNK_WORDS,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into word-count chunks with a small overlap.

    A trailing chunk that would be entirely covered by the previous chunk's
    tail (i.e. the remaining words all fall within the overlap window) is
    skipped, so the same words never get counted in two chunks the classifier
    both scores and averages over. Note: this changes chunk boundaries (and
    therefore scores) relative to any existing checkpoint CSVs — see
    load_checkpoint's docstring in scoring.py before re-running.
    """
    if chunk_words <= overlap:
        raise ValueError(f"chunk_words ({chunk_words}) must be greater than overlap ({overlap})")

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_words
        if end >= len(words):
            chunks.append(" ".join(words[start:]))
            break
        chunks.append(" ".join(words[start:end]))
        start = end - overlap  # small overlap so context isn't lost at boundaries
    return chunks
