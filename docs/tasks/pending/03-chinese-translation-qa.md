# Task: Manual QA Review of Chinese Song Translations

**Status:** Pending  
**Priority:** 3  
**Date Created:** 2026-08-19

## Context

File: `data/processed/lyrics_trans_qa_failures.csv`

Two short Chinese songs failed translation QA checks. They are missing the `translation_review_required` flag.

## Objective

Manually review the two Chinese songs and determine:
1. Was the translation skipped due to length or suspicion?
2. Is the translation adequate for emotion analysis?
3. Should the flag be added retroactively?

## Acceptance Criteria

- Both songs reviewed and documented
- Clear decision made for each (accept / flag for manual translation / skip)
- lyrics_trans_qa_failures.csv updated if needed
- Notes added to progress.md

## Related Files

- notebooks/04_lyrics_translation_qa.ipynb (logic for flagging)
- data/processed/03_lyrics_trans.csv (full translation output)
