"""Tests for lyrics_analysis.pipeline.text, including a regression test for
the chunk_text tail-double-counting bug (bug 3).
"""

from __future__ import annotations

import pytest

from lyrics_analysis.pipeline.text import chunk_text, clean_lyrics, dedupe_lines, prepare_lyrics


class TestCleanLyrics:
    def test_removes_section_headers(self):
        result = clean_lyrics("[Verse 1]\nHello world\n[Chorus]\nLa la la", artist="Someone")
        assert "[Verse 1]" not in result
        assert "[Chorus]" not in result
        assert "Hello world" in result

    def test_removes_repetition_annotations(self):
        result = clean_lyrics("La la la (x3)\nOoh (×2)\nYeah (2x)", artist="Someone")
        assert "(x3)" not in result
        assert "(×2)" not in result
        assert "(2x)" not in result

    def test_keeps_punctuation_and_casing(self):
        result = clean_lyrics("I LOVE YOU!! Really?\nDo you love me?", artist="Someone")
        assert "I LOVE YOU!!" in result
        assert "Really?" in result

    def test_drops_artist_credit_first_line(self):
        text = "Ryan Castro\nLA VILLA lyrics here\nMore lyrics"
        result = clean_lyrics(text, artist="ARIA VEGA, Ryan Castro")
        assert result.splitlines()[0] == "LA VILLA lyrics here"

    def test_keeps_first_line_when_not_artist_credit(self):
        text = "Baby come back\nI need you here"
        result = clean_lyrics(text, artist="Jason, Bonnie")
        assert "Baby come back" in result

    def test_collapses_excessive_blank_lines(self):
        result = clean_lyrics("Line one\n\n\n\nLine two", artist="X")
        assert "\n\n\n" not in result

    def test_non_str_returns_empty(self):
        assert clean_lyrics(None) == ""

    def test_blank_returns_empty(self):
        assert clean_lyrics("   ") == ""

    @pytest.mark.xfail(strict=True, reason="without an artist, the regex fallback drops any short all-letter first line, even real lyrics")
    def test_no_artist_keeps_short_lyric_first_line(self):
        text = "Baby come back\nI need you here"
        result = clean_lyrics(text)  # no artist provided
        assert "Baby come back" in result

    @pytest.mark.xfail(strict=True, reason="a NaN artist (float) crashes re.split with a TypeError instead of falling back to the regex heuristic")
    def test_nan_artist_does_not_raise(self):
        text = "Someone\nReal lyric line"
        clean_lyrics(text, artist=float("nan"))


class TestDedupeLines:
    def test_removes_duplicate_lines_case_insensitive(self):
        result = dedupe_lines("Hello\nHELLO\nWorld")
        assert result == "Hello World"

    def test_keeps_first_occurrence(self):
        result = dedupe_lines("First\nSecond\nFirst")
        assert result == "First Second"

    def test_removes_blank_lines(self):
        result = dedupe_lines("Line one\n\nLine two")
        assert result == "Line one Line two"


class TestPrepareLyrics:
    def test_composes_clean_and_dedupe(self):
        text = "[Chorus]\nLa la la\nLa la la\n[Chorus]\nLa la la"
        result = prepare_lyrics(text, artist="Someone")
        assert result.count("La la la") == 1


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = " ".join(f"w{i}" for i in range(340))
        chunks = chunk_text(text, chunk_words=350)
        assert len(chunks) == 1
        assert len(chunks[0].split()) == 340

    def test_exactly_chunk_words_is_single_chunk(self):
        text = " ".join(f"w{i}" for i in range(350))
        chunks = chunk_text(text, chunk_words=350)
        assert len(chunks) == 1

    def test_no_double_counted_tail_words(self):
        # Regression test for bug 3: a 351-word text used to produce a second
        # chunk of only 20 words (words 320-340 twice-counted, 340-350 once).
        words = [f"w{i}" for i in range(351)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_words=350, overlap=30)
        assert len(chunks) == 2
        second_chunk_words = chunks[1].split()
        assert second_chunk_words[0] == "w320"
        assert second_chunk_words[-1] == "w350"

    def test_all_words_covered_with_consistent_overlap(self):
        words = [f"w{i}" for i in range(1000)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_words=350, overlap=30)

        # every word appears in at least one chunk
        seen = set()
        for chunk in chunks:
            seen.update(chunk.split())
        assert seen == set(words)

        # consecutive chunks overlap by exactly `overlap` words, and no chunk
        # is fully contained within the previous one
        for prev, curr in zip(chunks, chunks[1:]):
            prev_words = prev.split()
            curr_words = curr.split()
            assert prev_words[-30:] == curr_words[:30]
            assert not set(curr_words).issubset(set(prev_words))

    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("") == []

    def test_chunk_words_must_exceed_overlap(self):
        with pytest.raises(ValueError):
            chunk_text("word " * 100, chunk_words=30, overlap=30)
