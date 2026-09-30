"""Language-detection helpers, extracted from notebooks/02_language_detection.ipynb.

Two-pass strategy: a fast Unicode-script check catches songs where a
non-Latin script dominates (this module), falling back to FastText for
anything left ambiguous (still done in the notebook, since it needs the
`fasttext` model loaded).
"""

from __future__ import annotations

import re

SCRIPT_THRESHOLD = 8  # min characters of a script to trigger assignment


def detect_by_script(lyrics: str, threshold: int = SCRIPT_THRESHOLD) -> str | None:
    """
    Return ISO 639-1 code if a non-Latin script is dominant, else None.

    Japanese is checked first and separately: kana (Hiragana/Katakana) never
    appears in Chinese text, so any kana at all is decisive, and Japanese
    lyrics are frequently mostly-kanji with only a sprinkling of kana — a
    plain "highest count wins" comparison would then call them Chinese
    (kanji and CJK ideographs share the same Unicode block). Once kana rules
    Japanese in or out, the remaining scripts (zh, ko, ar, th, ru) are
    compared by raw character count as before.
    """
    if not isinstance(lyrics, str) or not lyrics.strip():
        return None
    s = lyrics

    # Unicode block regexes
    cnt_kana = len(re.findall(r'[぀-ヿㇰ-ㇿ]', s))  # Hiragana/Katakana
    cnt_zh = len(re.findall(r'[一-鿿]', s))                # CJK ideographs
    cnt_ko = len(re.findall(r'[가-힯ᄀ-ᇿ]', s))  # Hangul
    cnt_ar = len(re.findall(r'[؀-ۿݐ-ݿࢠ-ࣿ]', s))
    cnt_th = len(re.findall(r'[฀-๿]', s))
    cnt_ru = len(re.findall(r'[Ѐ-ӿ]', s))                # Cyrillic

    if cnt_kana >= 1 and (cnt_kana + cnt_zh) >= threshold:
        return 'ja'

    script_counts = {
        'zh': cnt_zh,
        'ko': cnt_ko,
        'ar': cnt_ar,
        'th': cnt_th,
        'ru': cnt_ru,
    }

    lang, max_cnt = max(script_counts.items(), key=lambda kv: kv[1])
    if max_cnt >= threshold:
        return lang
    return None


def make_snippet(lyrics: str, n_chars: int = 200) -> str:
    if not isinstance(lyrics, str) or not lyrics.strip():
        return ''
    return lyrics[:n_chars].replace('\n', ' ').strip()
