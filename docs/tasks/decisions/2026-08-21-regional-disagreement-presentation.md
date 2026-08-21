# Decision: How to present the r=0.152 classifier-disagreement finding

**Task:** `docs/tasks/01-regional-disagreement-presentation.md`
**Date:** 2026-08-21

## Decision

README and `docs/classifier_methodology.md` already met acceptance criteria 1-3
(zero-shot-specific disclosure, r=0.152 documented with implications) and were
already committed — no changes needed there. The remaining gap was criterion 4,
a stakeholder-ready presentation. Built `site/scrollytelling2.html`, a
scrollytelling data story centered on the classifier disagreement itself as the
narrative thesis, rather than treating it as a caveat appended to a regional
finding.

Structure: hook (two classifiers, two regional maps) -> method (funnel,
1,600 -> 1,105 songs) -> raw scores look uniform across regions -> baselining
against the 7-market mean reveals real spread -> the resulting zero-shot
regional fingerprint (Japan/Singapore hopeful, USA despair-leaning,
Spain/Colombia/Argentina angry) -> the audit: GoEmotions cross-check, r=0.152
overall, per-label breakdown -> verdict (what survives the audit, what doesn't).

## Why this framing

An earlier draft opened with a romantic "does a broken heart sound the same
everywhere?" hook. Rejected by the user as the wrong tone for this finding —
the page's job is to communicate a measurement/robustness result to
stakeholders, not to sell a cultural narrative. The hero was rewritten to lead
with the actual epistemic finding (two classifiers, two maps) instead.

Considered leading immediately with r=0.152 as the very first thing on the
page (skip the regional-map buildup entirely). Rejected: the buildup — raw
scores look identical, baselining reveals a signal, that signal has a specific
shape — is what makes the r=0.152 gut-punch land. Spoiling it in the hero
would flatten the arc into a single stat with no story. Kept the hook framed
around the *fact* of disagreement (not spoiling the number) and paid off the
number itself in the "Two Ears, One Chart" step and the closing verdict.

## Alternatives considered

- **Lead with regional culture claims, footnote the classifier caveat.**
  Rejected — this is the framing the task exists to correct; burying r=0.152
  at the end undersells exactly the finding stakeholders need to see first.
- **Drop the regional-fingerprint section entirely, present only the
  disagreement.** Rejected — without showing what the confident-looking
  zero-shot-only finding would have been, the disagreement has no contrast to
  land against.

## Implications

- Regional claims elsewhere (README, future decks) should keep citing this
  page's verdict language ("zero-shot's read, not classifier-agnostic") rather
  than restating the regional fingerprint as fact.
- If a GoEmotions-corroborated regional claim is ever produced, this page's
  verdict section is the place to update, not the fingerprint step.
