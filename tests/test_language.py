"""Tests for lyrics_analysis.pipeline.language, including a regression test
for the Japanese-labelled-as-Chinese bug (bug 2).
"""

from __future__ import annotations

import math

from lyrics_analysis.pipeline.language import detect_by_script, make_snippet


class TestDetectByScript:
    def test_kanji_heavy_japanese_is_japanese(self):
        # Mostly kanji with a sprinkling of kana -- this is the exact shape
        # that used to get mislabelled 'zh' because kanji outcounted kana.
        text = "東京特許許可局長今日急遽休暇許可拒否の夜"
        assert detect_by_script(text) == "ja"

    def test_kana_only_is_japanese(self):
        assert detect_by_script("わたしはねこがすきです" * 2) == "ja"

    def test_pure_chinese_with_no_kana_is_chinese(self):
        assert detect_by_script("我爱北京天安门我爱北京天安门今天天气") == "zh"

    def test_hangul_is_korean(self):
        assert detect_by_script("안녕하세요저는사람입니다안녕") == "ko"

    def test_cyrillic_is_russian(self):
        assert detect_by_script("привет как у тебя дела сегодня") == "ru"

    def test_arabic(self):
        assert detect_by_script("مرحبا كيف حالك اليوم يا صديقي") == "ar"

    def test_thai(self):
        assert detect_by_script("สวัสดีครับวันนี้อากาศดีมาก") == "th"

    def test_below_threshold_returns_none(self):
        assert detect_by_script("你好") is None  # only 2 hanzi

    def test_plain_english_returns_none(self):
        assert detect_by_script("hello there my friend how are you") is None

    def test_none_input(self):
        assert detect_by_script(None) is None

    def test_empty_string(self):
        assert detect_by_script("") is None

    def test_nan_input(self):
        assert detect_by_script(float("nan")) is None


class TestMakeSnippet:
    def test_truncates_to_n_chars(self):
        assert make_snippet("a" * 300, n_chars=200) == "a" * 200

    def test_replaces_newlines_with_spaces(self):
        assert make_snippet("hello\nworld") == "hello world"

    def test_non_str_returns_empty(self):
        assert make_snippet(None) == ""
        assert make_snippet(math.nan) == ""

    def test_blank_returns_empty(self):
        assert make_snippet("   ") == ""
