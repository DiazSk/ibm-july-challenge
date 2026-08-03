# Validation sprint — results

Run 2026-08-01. Single account (@hot_cakesbakes), n=40 held-out posts,
granite3.1-dense:8b local. Reproduce with:

```bash
python eval/audit_profile.py && python eval/holdout.py && python eval/generate.py && python eval/score.py
```

Raw artifacts in `eval/artifacts/`.

---

## 1. The Drift Test is refuted

Scored on the same 40 held-out items, using the train-only profile:

| arm | legacy Drift Test |
|---|---|
| **the account's own real captions** | **10.2 / 100** |
| StyleSync | 23.8 / 100 |
| brand-blind baseline | 5.5 / 100 |

The account's actually-published captions score **below** the machine output on
a test of whether something sounds like the account. By the function's own
thresholds ([voice_fidelity.py:54](../src/generation/voice_fidelity.py)) the real
captions are labelled *"significant drift"* from the brand's own voice.

This is not a tuning problem. The scorer rewards reuse of a vocabulary list that
the generation prompt injects, so it measures instruction-following. A real
caption was never given the list and cannot comply with it. Any metric that
ranks the brand below the machine at being the brand is measuring the wrong
quantity, and no threshold change fixes it.

Supporting evidence from `eval/audit_profile.py`:

- **9 of 9 signature phrases are verbatim substrings of a single training
  caption.** A 15-point "signature phrase match" means the model reproduced one
  specific past post word-for-word.
- **1 of 22 recurring words is invented** (`carefully crafted`, absent from the
  12 posts Granite was shown); **3 more do not generalise** past the sample.
- `filled generously` — one of three matches the pitch deck credits — appears in
  **1 of 96** captions in its own pillar.
- The voice profile was extracted from **50 of 208** clustered posts, because
  `MAX_POSTS_PER_CALL = 12` caps what the extractor reads per pillar.

## 2. Profile grounding does real work

Authorship discrimination, fitted on train-real vs. baseline captions, then
applied to the held-out set. Paired per-item difference, bootstrap CI over n=40.

| control | mean chars (real/SS/BL) | paired gap | 95% CI | real-vs-SS AUC |
|---|---|---|---|---|
| raw | 169 / 363 / 204 | **+0.224** | [+0.190, +0.261] | 0.909 |
| hashtags stripped | — | +0.255 | [+0.215, +0.296] | 0.886 |
| stripped, first 25 words | 117 / 143 / 135 | +0.196 | [+0.160, +0.234] | 0.914 |
| stripped, first 15 words | 79 / 84 / 86 | +0.228 | [+0.180, +0.278] | 0.874 |

Every interval excludes zero. The effect survives removing hashtags and
normalising length to near-parity, so it is not a surface artifact — grounding
moves generated text measurably toward the account's real voice.

## 3. It does not reach the product claim

`real vs baseline` AUC is 0.999; `real vs stylesync` is 0.909. Chance is 0.500.

Grounding closes about **18% of the distance to indistinguishability**
(0.499 → 0.409 above chance). A plain logistic regression on sentence embeddings
still separates StyleSync output from the account's real captions roughly 9
times in 10. "Sounds like you" is not yet true; "sounds measurably less generic"
is.

## 4. A concrete, fixable defect

| | chars | words | emoji | hashtags | sentences |
|---|---|---|---|---|---|
| real | 168.7 | 28.9 | 3.6 | **0.0** | 3.7 |
| stylesync | **363.0** | 57.3 | 4.4 | **2.5** | 5.7 |
| baseline | 203.8 | 31.4 | 3.0 | 2.4 | 3.8 |

StyleSync writes **2.2x longer** than the account and adds ~2.5 hashtags to an
account that uses **zero** — in 37 of 40 items. On both counts the brand-blind
baseline is closer to the real distribution than the brand-grounded output is.

The profile carries a `structural_signature` field and it is not constraining
generation. This is the cheapest available improvement and it is untested: the
numbers in §2 and §3 were measured with the defect present.

## 5. Verdict against the pre-registered criteria

Criteria were written before results were seen (see the sprint plan).

- *"Gap ≥ 0.15 with CI clear of zero"* — **met** (+0.224, CI [+0.190, +0.261]).
- *"Human discrimination below ~65%"* — **not run**, but a linear model
  discriminates at 87–91%, so a human panel clearing that bar is unlikely.

This lands in the middle band: **a real effect, not yet a product claim.**

Caveat that bounds all of the above: **n=1 account.** Every number here
describes one bakery. Nothing establishes that the pipeline generalises.

## 6. Iteration: fixing the structural defect

The §4 defect turned out to be prompt-mandated, not emergent. The caption prompt
hardcoded `Stay under 150 words` and `Use a maximum of 5 hashtags`, plus two
padding instructions, and those lines sat below the brand profile in the same
prompt and silently overrode it. Against this account they were wrong by ~5x on
length and categorically wrong on hashtags.

[src/data/style_stats.py](../src/data/style_stats.py) now measures per-pillar
medians from train posts only (22–40 words, **0 hashtags** in every pillar) and
`CaptionGenerator.generate()` takes an optional `style_constraints`. Only the
StyleSync arm was regenerated; briefs and baselines were reused verbatim.

Surface shape is now essentially matched:

| | chars | words | emoji | hashtags |
|---|---|---|---|---|
| real | 168.7 | 28.9 | 3.6 | 0.0 |
| stylesync **before** | 363.0 | 57.3 | 4.4 | 2.5 |
| stylesync **after** | **174.3** | **29.6** | 2.7 | **0.4** |

Headline: `real vs stylesync` AUC **0.909 → 0.848**. Distance above chance falls
from 0.409 to 0.348 — grounding now closes **30%** of the way to
indistinguishability, up from 18%.

**But the robustness controls show what actually improved:**

| control | before | after | change |
|---|---|---|---|
| raw | 0.909 | 0.848 | −0.061 |
| hashtags stripped | 0.886 | 0.861 | −0.025 |
| stripped, first 25 words | 0.914 | 0.868 | −0.046 |
| stripped, first 15 words | 0.874 | 0.882 | +0.008 |

The gain shrinks monotonically as surface information is removed and disappears
under the strictest control. So the improvement is **surface conformance** —
the output now has the account's shape — and the underlying lexical/semantic
voice match is unchanged.

That is worth having. Length discipline and not spraying hashtags an account
never uses are a real part of sounding like someone, and it is what a reader
registers first while scrolling. It is not deeper voice capture, and it should
not be described as such.

Note also that the legacy Drift Test moved 23.8 → 22.2, i.e. slightly *down*,
for output that is now demonstrably closer to the real thing on every other
measure. A metric that cannot see this improvement is further evidence it is not
measuring brand fidelity.

## 7. What would change the verdict

1. ~~Constrain generation to the account's own length and hashtag
   distribution~~ — **done, see §6.** Raw AUC 0.909 → 0.848, but the gain is
   surface conformance only.
2. **Re-run the whole harness on 5–10 other accounts.** Until then every number
   here is an anecdote with confidence intervals. This is now the highest-value
   next step, because it is the one that could invalidate everything above.
3. The remaining 0.848 is lexical and semantic, not structural. Closing it means
   changing what the profile captures — sentence rhythm, how posts open, what
   the account never says — not tightening the prompt further.
4. Run the human forced-choice panel only after (2). A panel on n=1 measures one
   bakery.
