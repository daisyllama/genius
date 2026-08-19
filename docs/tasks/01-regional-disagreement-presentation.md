# Task: Present Regional Disagreement Finding

**Status:** Pending  
**Priority:** 1  
**Date Created:** 2026-08-19

## Context

Classifier robustness evaluation (07_compare_classifiers.ipynb) revealed r=0.152 correlation between zero-shot and GoEmotions classifiers on regional z-score maps. This is well below the r>0.7 bar for "same story, different vocabulary."

Per-label breakdown: joy r=-0.027, anger r=0.371, grief r=-0.402 (near-total disagreement on joy and grief).

## Objective

Decide how to present this finding in README and site documentation.

**Current approach:** Label every regional claim as "zero-shot-specific" rather than classifier-agnostic. A GoEmotions cross-check would be needed for stronger/broader claims.

## Acceptance Criteria

- README updated with clear disclosure of classifier dependency
- Regional claims explicitly labeled as zero-shot-specific
- Methodology doc references the r=0.152 result and explains implications
- Site/presentation ready for stakeholder review

## Notes

- The finding is already documented in classifier_methodology.md
- Commits are uncommitted but fully reproducible (all notebooks re-executed)
