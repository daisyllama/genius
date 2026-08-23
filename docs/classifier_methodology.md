# Classifier Methodology — design decisions and learning points

Why the emotion-classification stage is built the way it is. Written 2026-08-06,
during the work that split the pipeline into two comparable classifier forks.

Audience: whoever next changes `04_classification.ipynb` or reads a regional
emotion claim and wants to know how much weight it holds.

---

## The question that started this

> Am I doing a fair comparison between zero-shot NLI and GoEmotions? One has 10
> emotions, one has 28.

No — but the label count was the *least* of it, and that turned out to be the
useful finding. Four things differed between the two classifiers, and only two
of them had to.

| difference | had to differ? | resolution |
|---|---|---|
| label count (10 vs 28) | yes — different taxonomies | keep; compare on the 4 shared names + a flagged near-equivalent map |
| model (zero-shot NLI vs supervised) | yes — that's the experiment | keep; it is the thing being compared |
| scoring mechanics (softmax vs sigmoid) | **no** | unified: both emit independent per-label probabilities |
| unclassified threshold (`> 0` vs `>= 0.30`) | **no** | unified: `unclassified` = no scoreable lyrics, in both |

The two avoidable differences were doing most of the damage.

---

## Learning point 1 — a config difference will happily impersonate a finding

The headline number before this work: zero-shot classified 997 songs, GoEmotions
896. It read as "the supervised model is worse at handling song lyrics."

It wasn't. It was two different `unclassified` rules:

```
threshold   zero-shot unclassified   goemotions unclassified
  > 0                108                      107
  >= 0.30            109                      201
  >= 0.50            112                      549
```

At a common bar the two drop *the same ~107 songs*, and those songs are the ones
with no lyrics at all. The entire 93-song gap was a constant chosen in two files
by two different lines of reasoning, neither wrong on its own.

**The lesson:** when two pipelines are compared, every constant that differs
between them is a candidate explanation for any difference you observe. Before
attributing a gap to the models, equalise the plumbing and see what survives.
Here, nothing did.

**How it's prevented now:** `MIN_CONFIDENCE` and `CHUNK_WORDS` are defined once
in `04_classification.ipynb` and consumed by both classifiers. They cannot drift
because there is only one of each.

---

## Learning point 2 — don't let a filter destroy the evidence it was based on

The old rule *dropped* songs that scored below threshold. That conflated two
genuinely different things:

- "this song has no lyrics to score" — a data problem
- "the model wasn't confident" — a model property, and interesting

Dropping on the second discards exactly the measurement you'd want when
comparing models, and it silently changes the denominator of every downstream
statistic.

**Current design:** `unclassified` is reserved for the data problem. Confidence
is kept as data — `dominant_score` plus a `low_confidence` flag — and nothing is
dropped on it. Any confidence filter is applied downstream, where it is visible
and applied identically to both forks.

This is what makes the interesting number visible: GoEmotions flags far more
songs low-confidence at the same 0.30 bar. That's a real, reportable property
(calibration) that the old design converted into a missing row.

**Generalise it:** prefer flag-and-carry over drop, whenever the reason for
dropping is itself a measurement.

---

## Learning point 3 — a complete checkpoint silently overrides your code

`04.1_classification_zeroshot.ipynb` read `multi_label=False`. Its output CSV had
rows summing to ~4.98. A softmax over labels must sum to 1.0, so the data had
been produced with `multi_label=True` — the notebook and its own output had been
disagreeing for weeks.

The mechanism: classification only ran on rows with NaN scores. With a complete
checkpoint on disk, changing a scoring setting and re-running printed
`No unclassified rows. Using existing scores.` and rewrote the stale numbers.
`local/progress.md` records that the checkpoint was deleted on 2026-07-12 for
exactly this reason; the deletion evidently didn't survive.

**Prevented now:** `load_checkpoint` prints a loud warning when the checkpoint is
complete, listing the settings that require deleting it. Its docstring says which
changes are safe (`MIN_CONFIDENCE`, applied at derivation) and which are not
(taxonomy, model, chunking, `ZEROSHOT_MULTI_LABEL`).

**Generalise it:** resume-on-NaN caching is invisible by design, which is fine
until an input that isn't the data changes. Any cache keyed on *completeness*
rather than on *configuration* will eventually serve stale results. A config
hash in the checkpoint filename would fix this properly — currently a known gap.

---

## Learning point 4 — comparability and interpretability pulled in opposite directions

The contested setting is `ZEROSHOT_MULTI_LABEL`, and both positions are recorded
in the notebook because neither is obviously right.

**Against independent scoring (the 2026-07-12 position):** it inflates. `longing`
and `sensual` average 0.74–0.77 corpus-wide and win 575 of 1,105 songs between
them. "Dominant emotion" then partly reports which label bart-mnli over-estimates
globally, not what's distinctive about a song.

**For independent scoring (current):** softmax scores are an artifact of the
label list — add an 11th emotion and all ten existing scores move. That makes
them hard to defend and impossible to compare against a fixed-taxonomy model.
It's also the only setting that produces the same *kind* of quantity as
GoEmotions' sigmoid head.

**Resolution:** independent scoring, with the inflation handled in analysis
rather than in scoring. Inflation is a global per-label offset, and z-scoring
each label against its own regional baseline removes exactly that — which is
what the differential heatmap added on 2026-07-12 was already reaching for.
Handling it downstream keeps the raw scores interpretable *and* comparable.

**The meta-lesson:** when a correction can be applied either at measurement time
or at analysis time, prefer analysis time. Baked-in corrections are invisible,
unreversible, and travel badly into comparisons the original author didn't
anticipate.

The decision is a single constant with both arguments written beside it, and
`07` detects the flip and degrades to rank-only comparisons rather than silently
comparing incomparable magnitudes.

---

## Learning point 5 — a shared contract is not the same as a shared scale

Unifying the scoring mechanics does *not* make the numbers interchangeable.
RoBERTa's sigmoids are calibrated far lower than bart-mnli's entailment
probabilities — median top score ~0.50 vs ~0.97 — so a raw 0.4 still means
different things in each fork.

Three tiers of comparability, in decreasing strength:

1. **Within a fork, raw scores** — fully valid.
2. **Across forks, ranks and z-scores** — valid. Standardising within a fork
   cancels the calibration offset.
3. **Across forks, raw magnitudes** — never valid, contract or no contract.

Every chart in `06.1` / `06.2` is labelled with which tier it belongs to. The
z-scored regional-character view (§ 4 heatmap and § 4b dot strip in both) is the
designated cross-fork view, and `07 § 5` is built on the same idea: *do the two
classifiers draw the same regional map?* — a question invariant to scale, which
is the only kind of cross-classifier question worth asking here.

Tier 2 only holds if the two forks are standardised *identically*, which turned
out to need two explicit decisions (both made 2026-08-06):

- **Fixed shared domain.** § 4 originally scaled its colour to each fork's own
  max, so +1.5 SD rendered as a different colour in each notebook — the charts
  looked comparable and weren't. Both forks now pin `Z_LIM = 2.9` and raise if
  the data exceeds it.
- **`Global` is held out of the baseline.** It is a worldwide chart, not a
  market, so including it meant it was partly its own reference. The baseline is
  the seven market regions; Global is scored against them. This makes Global's
  position interpretable ("the worldwide chart vs the markets") at the cost of
  the rows no longer summing to zero across all eight regions.

`07 § 5`'s `regional_z()` now takes the same `ref_region` parameter and applies
the identical held-out baseline, so the headline number in learning point 8 is
computed the same way as `06.1`/`06.2` § 4. One thing worth knowing if you ever
touch this again: **the per-label correlations didn't move at all** —
`pearsonr` is invariant to each fork's own affine rescaling, and swapping which
7-vs-8 regions set the mean/std is exactly that, an affine rescale, applied
identically to both z-columns being correlated. Only the *flat* correlation
(computed across labels, where each label now carries a slightly different
rescale) shifted, and only by 0.001 — see learning point 8.

---

## Learning point 6 — some asymmetries can't be config'd away

GoEmotions has a `neutral` label; the zero-shot taxonomy has no equivalent, and
inventing one would be fabrication. `neutral` wins outright on ~28% of songs, so
leaving it in makes the two dominant-emotion distributions look far more
different than the content warrants.

**Handling:** keep `dominant_emotion` exactly as the model reported it, and add
`dominant_emotion_emotive` (best non-neutral) alongside. Charts use the emotive
column so the profile isn't swamped; the neutral share is reported separately as
its own statistic, because "this classifier reads 28% of song lyrics as
affectively flat" is a real finding about taxonomy fit — GoEmotions was trained
on Reddit comments, not lyrics.

**Generalise it:** when two schemes don't align, add a column, don't overwrite
one. Keep the model's actual output and the harmonised view side by side, and
report the asymmetry as a result rather than smoothing it away.

The same reasoning governs `NEAR_EQUIVALENT` in `07` (`heartbreak`↔`sadness`,
`sensual`↔`desire`, …): it's a human judgment call, so it's reported in a
separate block from the four genuinely shared label names and labelled as a
hypothesis about the taxonomies rather than a measurement.

---

## Pipeline shape

```
03_lyrics_trans.csv
        │
        ▼
04_classification.ipynb        shared: cleaning, chunking, checkpointing,
   ├── § 4A zero-shot          contract derivation, MIN_CONFIDENCE, CHUNK_WORDS
   │      └─► 04.1_emotion_scores_zeroshot.csv
   └── § 4B GoEmotions
          └─► 04.2_emotion_scores_goemotions.csv
        │
        ├─► 05.1 ─► 06.1        zero-shot fork
        ├─► 05.2 ─► 06.2        GoEmotions fork
        └─► 07_compare_classifiers.ipynb    the only place the forks meet
```

`RUN = ["zeroshot", "goemotions"]` in `04` guards the expensive sections, since
the two differ a lot in cost and "run all cells" shouldn't be the only option.

Forks stay separate through 05 and 06 deliberately: pooling 10-label and
28-label scores into one table would produce a schema where most cells are
structurally missing, and would invite exactly the cross-scale magnitude
comparisons that tier 3 above forbids.

---

## Known gaps

- **Checkpoints are keyed on completeness, not configuration.** Learning point 3
  is mitigated by a warning, not solved. A config hash in the checkpoint filename
  would solve it.
- **`NEAR_EQUIVALENT` is unvalidated.** The mapping is plausible and clearly
  labelled as a judgment call, but nothing tests it against human annotation.
- **No human-labelled ground truth.** Everything here compares the two
  classifiers *to each other*. Neither is validated against what listeners
  actually hear, so "which is more correct" remains unanswerable — only "do they
  agree, and where don't they" is in scope.
- **Chunk averaging is unweighted.** A 3-chunk song weights its final chorus
  chunk as heavily as its first verse, and short trailing chunks count fully.
  Applies identically to both forks, so it doesn't bias the comparison.

---

## Post-re-run addendum (2026-08-06)

The design above was tested against real model output for the first time on
2026-08-06 (`04` → `05.1`/`05.2` → `06.1`/`06.2` → `07`; see `local/progress.md`
for exact numbers). Two results worth recording here, since they bear directly
on how much weight the design choices above should get:

- **Learning points 1–3 held up as predicted.** Coverage converged to
  identical (90.3%/90.3%) once the contract was actually applied — the
  ~93-song "gap" really was just the threshold mismatch this doc diagnosed,
  not a residual model difference.
- **Learning point 5's "same map, different vocabulary" hope did *not* hold.**
  The §5 regional z-score test — designed to be the one comparison immune to
  the calibration gap — came back r = 0.152 overall (0.153 before `Global` was
  held out of the baseline, see learning point 5; the per-label numbers below
  are unaffected by that change), with `joy` (r=-0.03) and `grief` (r=-0.40)
  essentially uncorrelated between the two classifiers. Only `love` (r=0.67)
  shows real agreement. This doesn't invalidate the tiering argument in
  learning point 5 (ranks/z-scores are still more comparable than
  raw magnitudes) — it means the *taxonomy* itself, not just its calibration,
  is doing real work in shaping which regional signal comes through. A
  regional claim from one classifier is not evidence for the same claim under
  the other, and downstream write-ups should say which classifier they used.
