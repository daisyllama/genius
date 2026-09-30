"""Translation helpers, extracted from notebooks/03_lyrics_translate.ipynb.

`GoogleTranslator` (deep_translator) is imported lazily inside
`get_translator` so this module stays importable without deep_translator
installed and without touching the network at import time.
"""

from __future__ import annotations

import concurrent.futures as cf
import re

import pandas as pd

LANGUAGE_CODE_MAP = {
    "zh-cn": "zh-CN",
    "zh_cn": "zh-CN",
    "zh-tw": "zh-TW",
    "zh_tw": "zh-TW",
    "jp": "ja",
    "kr": "ko",
    "latin": "auto",
    "other": "auto",
    "unknown": "auto",
}

CJK_PATTERN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
TRANSLATE_TIMEOUT_SEC = 30
translator_cache: dict = {}


def normalize_source_language(language_value):
    if pd.isna(language_value):
        return "auto"
    language = str(language_value).strip().lower()
    if not language:
        return "auto"
    return LANGUAGE_CODE_MAP.get(language, language)


def has_cjk(text):
    if pd.isna(text):
        return False
    return bool(CJK_PATTERN.search(str(text)))


def get_translator(source_language):
    if source_language not in translator_cache:
        from deep_translator import GoogleTranslator

        translator_cache[source_language] = GoogleTranslator(source=source_language, target="en")
    return translator_cache[source_language]


def translate_once(text, source_language, timeout_sec=TRANSLATE_TIMEOUT_SEC):
    try:
        translator = get_translator(source_language)
        with cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(translator.translate, text)
            return fut.result(timeout=timeout_sec)
    except cf.TimeoutError:
        return pd.NA
    except Exception:
        return pd.NA


def translate_line_by_line(text, source_language):
    lines = str(text).splitlines()
    out_lines = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            out_lines.append("")
            continue

        translated = translate_once(line_stripped, source_language)
        if pd.isna(translated):
            translated = translate_once(line_stripped, "auto")
        if pd.isna(translated):
            translated = line_stripped

        out_lines.append(str(translated))

    return "\n".join(out_lines)


def translate_to_english(text, source_language="auto"):
    if pd.isna(text):
        return pd.NA

    original = str(text).strip()
    if not original:
        return pd.NA

    normalized_source = normalize_source_language(source_language)

    first_try = translate_once(original, normalized_source)
    if pd.isna(first_try) and normalized_source != "auto":
        first_try = translate_once(original, "auto")

    if pd.isna(first_try):
        first_try = translate_line_by_line(original, normalized_source)

    unchanged = (not pd.isna(first_try)) and (str(first_try).strip() == original)
    still_cjk = (not pd.isna(first_try)) and has_cjk(first_try)

    if unchanged or still_cjk:
        retry_auto = translate_once(original, "auto")
        if not pd.isna(retry_auto) and str(retry_auto).strip() != original and not has_cjk(retry_auto):
            return retry_auto

        retry_lines = translate_line_by_line(original, "auto")
        if retry_lines and retry_lines.strip():
            return retry_lines

    return first_try
