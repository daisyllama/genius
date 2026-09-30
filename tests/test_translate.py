"""Tests for lyrics_analysis.pipeline.translate. No network access —
translate_once/get_translator are monkeypatched throughout.
"""

from __future__ import annotations

import time

import pandas as pd
import pytest

from lyrics_analysis.pipeline import translate as translate_mod
from lyrics_analysis.pipeline.translate import (
    LANGUAGE_CODE_MAP,
    has_cjk,
    normalize_source_language,
    translate_line_by_line,
    translate_once,
    translate_to_english,
)


class TestNormalizeSourceLanguage:
    @pytest.mark.parametrize("raw,expected", list(LANGUAGE_CODE_MAP.items()))
    def test_known_mappings(self, raw, expected):
        assert normalize_source_language(raw) == expected

    def test_nan_returns_auto(self):
        assert normalize_source_language(float("nan")) == "auto"

    def test_none_returns_auto(self):
        assert normalize_source_language(None) == "auto"

    def test_blank_returns_auto(self):
        assert normalize_source_language("   ") == "auto"

    def test_unmapped_language_lowercased(self):
        assert normalize_source_language("ES") == "es"

    def test_unmapped_language_passthrough(self):
        assert normalize_source_language("fr") == "fr"


class TestHasCjk:
    def test_hanzi_returns_true(self):
        assert has_cjk("你好世界") is True

    def test_latin_returns_false(self):
        assert has_cjk("hello world") is False

    def test_nan_returns_false(self):
        assert has_cjk(float("nan")) is False


class FakeTranslator:
    def __init__(self, translate_fn):
        self._translate_fn = translate_fn

    def translate(self, text):
        return self._translate_fn(text)


class TestTranslateOnce:
    def test_returns_translated_text(self, monkeypatch):
        monkeypatch.setattr(
            translate_mod, "get_translator", lambda src: FakeTranslator(lambda t: f"[en] {t}")
        )
        assert translate_once("hola", "es") == "[en] hola"

    def test_exception_returns_na(self, monkeypatch):
        def raise_error(text):
            raise RuntimeError("boom")

        monkeypatch.setattr(translate_mod, "get_translator", lambda src: FakeTranslator(raise_error))
        assert pd.isna(translate_once("hola", "es"))

    def test_timeout_returns_na(self, monkeypatch):
        def slow(text):
            time.sleep(0.2)
            return text

        monkeypatch.setattr(translate_mod, "get_translator", lambda src: FakeTranslator(slow))
        assert pd.isna(translate_once("hola", "es", timeout_sec=0.01))


class TestTranslateLineByLine:
    def test_preserves_blank_lines(self, monkeypatch):
        monkeypatch.setattr(
            translate_mod, "translate_once", lambda text, src, **kw: f"[en]{text}"
        )
        result = translate_line_by_line("hola\n\nmundo", "es")
        assert result == "[en]hola\n\n[en]mundo"

    def test_falls_back_to_auto_then_original(self, monkeypatch):
        def fake_translate_once(text, src, **kw):
            if src == "auto":
                return pd.NA
            return pd.NA

        monkeypatch.setattr(translate_mod, "translate_once", fake_translate_once)
        result = translate_line_by_line("hola mundo", "es")
        assert result == "hola mundo"  # falls back to the original line


class TestTranslateToEnglish:
    def test_nan_returns_na(self):
        assert pd.isna(translate_to_english(float("nan")))

    def test_blank_returns_na(self):
        assert pd.isna(translate_to_english("   "))

    def test_success_on_first_try(self, monkeypatch):
        monkeypatch.setattr(
            translate_mod, "translate_once", lambda text, src, **kw: "hello world"
        )
        result = translate_to_english("hola mundo", "es")
        assert result == "hello world"

    def test_retries_auto_when_first_try_fails(self, monkeypatch):
        calls = []

        def fake_translate_once(text, src, **kw):
            calls.append(src)
            if src == "es":
                return pd.NA
            return "hello world"

        monkeypatch.setattr(translate_mod, "translate_once", fake_translate_once)
        result = translate_to_english("hola mundo", "es")
        assert result == "hello world"
        assert calls[0] == "es"
        assert "auto" in calls

    def test_retries_when_output_unchanged(self, monkeypatch):
        calls = []

        def fake_translate_once(text, src, **kw):
            calls.append(src)
            if len(calls) == 1:
                return text  # unchanged -> should trigger retry
            return "translated!"

        monkeypatch.setattr(translate_mod, "translate_once", fake_translate_once)
        result = translate_to_english("some text", "auto")
        assert result == "translated!"
        assert len(calls) >= 2

    def test_retries_when_still_cjk(self, monkeypatch):
        calls = []

        def fake_translate_once(text, src, **kw):
            calls.append(src)
            if len(calls) == 1:
                return "你好"  # still CJK -> should trigger retry
            return "hello"

        monkeypatch.setattr(translate_mod, "translate_once", fake_translate_once)
        result = translate_to_english("some text", "zh-cn")
        assert result == "hello"
