# Progress Snapshot

Date: 2026-03-28
Mode: Notebook-first workflow

## Completed So Far

- Performed a full project review and cleanup assessment.
- Aligned notebook path handling to match the style used in notebook 06.
- Preserved Databricks-compatible path comments while standardizing local paths.
- Applied path updates in:
  - notebooks/00_genius_sample_checks.ipynb
  - notebooks/01_lyrics_ingestion.ipynb
  - notebooks/02_lyrics_fill.ipynb
  - notebooks/03_language_detection.ipynb
  - notebooks/04_lyrics_translate.ipynb
- Confirmed edits by reading back updated notebook cells.

## Repository Change State (Current)

Modified:
- notebooks/00_genius_sample_checks.ipynb
- notebooks/01_lyrics_ingestion.ipynb
- notebooks/02_lyrics_fill.ipynb
- notebooks/03_language_detection.ipynb
- notebooks/04_lyrics_translate.ipynb

Deleted:
- src/lyrics_analysis/__init__.py
- src/lyrics_analysis/__main__.py
- src/lyrics_analysis/cleaning.py
- src/lyrics_analysis/cli.py
- src/lyrics_analysis/pipeline.py
- notebooks/99_analysis_BERTopics.ipynb
- several generated output CSV files under outputs/
- selected raw files moved out of data/raw root (now represented in archive/new files)

Untracked:
- data/raw/archive/
- data/raw/regional-ar-weekly-2026-03-05.csv
- data/raw/regional-es-weekly-2026-03-05.csv
- data/raw/regional-jp-weekly-2026-03-05.csv
- data/raw/regional-sg-weekly-2026-03-05.csv
- notebooks/archive/

## Diagnostics / Tests

Automated test suite:
- Not run in this phase.

Current diagnostics status: FAILING (not fully clean)
- notebooks/00_genius_sample_checks.ipynb
  - song_uri is referenced before definition in update cells.
- notebooks/04_lyrics_translate.ipynb
  - deep_translator import unresolved in current environment.
- notebooks/05_lyrics_en_cleaning.ipynb
  - df_test referenced before definition.

## Current Status

- Path consistency work is mostly complete for active notebook pipeline files.
- Databricks path support was intentionally preserved as comments.
- Remaining blockers are notebook diagnostics issues and final validation.

## Open Issues In Progress

- Undefined variables in specific notebook cells.
- Missing translation package import resolution.
- Need one final sweep for any residual legacy path patterns.
- No end-to-end smoke execution completed after latest edits.

## Exact Next Step To Resume

1. Fix diagnostics in notebooks/00_genius_sample_checks.ipynb (define/guard song_uri in update cells).
2. Fix diagnostics in notebooks/05_lyrics_en_cleaning.ipynb (replace or initialize df_test).
3. Resolve dependency in notebooks/04_lyrics_translate.ipynb (install/guard deep_translator).
4. Re-scan notebooks 00-06 for any remaining legacy path patterns.
5. Run a short smoke pass of setup cells in notebooks 01-06.

