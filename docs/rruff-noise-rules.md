# Choosing spice-screen's noise estimate on the RRUFF library (0.5.0)

**Short version.** spice-screen 0.5.0 measures noise with the `lag` estimate instead of
`diff`. On all 5,785 RRUFF mineral spectra that cover 840 cm⁻¹, the lead chromate marker
still flags **every crocoite spectrum (9 of 9)**. Spectra of minerals without chromium that it
also flags fall from **1,937 (33.9%) to 663 (11.6%)**. In synthetic crocoite + filler mixtures,
false flags on the filler alone drop from **6.3% to 0.5%**, and detection at 3% crocoite peak
height drops from **80% to 67%**. The roughly 660 flags that remain are mostly real Raman bands
of other minerals near 840 cm⁻¹ (arsenates, vanadates, phosphates, some silicates, white lead).
Noise handling cannot remove those.

## Why this was needed

The [0.4.0 audit](rruff-audit.md) ran the lead chromate marker over the whole RRUFF library
(Lafuente et al. 2015). It caught 9 of 9 crocoite (PbCrO₄) spectra but also flagged 1,935 of
5,713 spectra of minerals without chromium. Most of those flags were small features. RRUFF's
processed spectra are smoothed, and 0.4.0 estimated noise from point-to-point differences.
Smoothing shrinks that estimate, so ripples passed as bands.

## What was tested

Two jobs ran on the full `excellent_unoriented` archive: 5,787 processed spectra, of which
5,785 cover 840 cm⁻¹, with no read errors.

1. **Noise rules** (`tools/rruff-rules/rules.py`). Three noise estimates were tested, each at
   SNR thresholds 5, 8, 10 and 20 and with optional gates on relative band height (0, 1, 3, 5
   and 10% of the spectrum's strongest point):
   - `diff`: point-to-point differences, as in 0.4.0.
   - `scatter`: also the spread of the window's corrected points.
   - `lag`: also differences between points 4 cm⁻¹ apart.

   Each rule was then run on mixtures. Each of the 9 crocoite spectra was mixed into 49
   spectra of 17 filler and soil minerals (calcite, talc, gypsum, quartz, feldspars, micas,
   iron oxides, TiO₂ and others) at crocoite peak-height fractions f = 0, 0.003, 0.01, 0.03,
   0.1 and 0.3. White noise of 0.3% of the strongest band was added, giving 441 mixtures per
   fraction.
2. **Band shape** (`tools/rruff-shape/shape.py`). This job asked whether the shape of the
   840 cm⁻¹ feature separates crocoite from the minerals that trip 0.4.0. It looked at a true
   apex versus a neighbour's flank, dominance within ±60 cm⁻¹, width (FWHM) and the
   330-400 cm⁻¹ bending bands, and scored 128 gate combinations.

The 4 cm⁻¹ lag was fixed in the code before either job ran: it is longer than typical software
smoothing and shorter than a Raman band. It was not tuned on these results.

## A correction to the job's own numbers

The rules job cross-checked its quick rule maths against the real `screen_entry()` on 1 in 25
spectra. **20 of 212 disagreed.** All 20 had their 840 cm⁻¹ region below the spectrum's median
intensity. For those spectra the quick maths computed a negative "relative height" and
dropped them even when no height gate was set, while the screen itself flags them. So the
job's "no gate" counts were too low. The gated counts are unaffected, because a negative
height fails any gate.

The counts below add these spectra back from the published per-spectrum results
(`docs/data/noise-rules/results.csv`). They are the rows with a negative `rel840` and an SNR at
or above the threshold. With that correction, the 0.4.0 rule gives 1,512 + 425 = 1,937
non-chromium flags, against 1,935 in the 0.4.0 audit. The 2-spectrum gap most likely comes
from SNR values rounded to two decimals right at the threshold. The mixture counts get the same correction: 5
mixtures at f = 0.03 were added back for `diff` and `lag` at SNR 5. A re-audit of the
released 0.5.0 file with the original audit script, which calls the screen itself, is
queued, and this page will be updated with its exact counts.

## Results

Library (5,785 spectra covering 840 cm⁻¹; 9 crocoite, 63 other chromium-bearing, 5,713
without chromium):

| Rule | Crocoite | Other Cr | No-Cr flagged | Rate | Filler spectra flagged |
|---|---|---|---|---|---|
| `diff`, SNR 5 (0.4.0) | 9/9 | 27/63+ | 1,937 | 33.9% | 49+ |
| **`lag`, SNR 5 (0.5.0 default)** | **9/9** | **16/63** | **663** | **11.6%** | **10** |
| `lag`, SNR 8 | 9/9 | 10/63 | 413 | 7.2% | 3 |
| `lag`, SNR 10 | 9/9 | 9/63 | 348 | 6.1% | 1 |
| `lag`, SNR 10, height ≥ 10% | 9/9 | 9/63 | 222 | 3.9% | 0 |
| `scatter`, SNR 5 | **8/9** | 8/63 | 322+ | 5.6%+ | 1+ |

"+" marks counts that the job's quick rule maths may have undercounted and that were not
corrected by hand.

Mixtures (share of the 441 mixtures flagged at each crocoite peak-height fraction; f = 0 is the
filler alone, so it is a false-flag rate):

| Rule | f = 0 | 0.003 | 0.01 | 0.03 | 0.1 | 0.3 |
|---|---|---|---|---|---|---|
| `diff`, SNR 5 (0.4.0) | 6.3% | 5.4% | 18.6% | 79.8% | 93.7% | 98.0% |
| **`lag`, SNR 5 (0.5.0)** | **0.5%** | 0.9% | 5.4% | **66.7%** | 93.0% | 98.0% |
| `lag`, SNR 8 | 0% | 0% | 0% | 26.5% | 84.8% | 95.9% |
| `lag`, SNR 10 | 0% | 0% | 0% | 4.5% | 76.6% | 90.9% |
| `lag`, SNR 10, height ≥ 10% | 0% | 0% | 0% | 0% | 68.5% | 90.9% |

The `scatter` estimate failed one of the 44 unit tests (it hides a resolved chromate triplet)
and lost one crocoite spectrum, so it was dropped. `lag` passed all 44.

**Why `lag` at SNR 5.** It is the only rule here that keeps every crocoite spectrum, keeps
detection at f = 0.1 within one point of 0.4.0, and cuts false flags on the filler-only
mixtures by more than ten times (6.3% to 0.5%). Rules with a higher threshold or a height gate cut library flags further, but they
lose the 3% mixtures almost completely. A screen exists to send doubtful samples to a
laboratory, so 0.5.0 keeps the more sensitive rule.

**Band shape gates (not adopted).** On top of 0.4.0, the best shape gate kept every crocoite
spectrum and stayed within 5 points of 0.4.0 on mixtures: a true apex, dominance ≥ 0.5 and
FWHM ≤ 45 cm⁻¹. It cut flags among the 1,880 covered non-chromium positives only to 1,170.
All 25 flagged lead-pigment spectra (white lead and other lead minerals used as pigments) stayed flagged, because they
really have a band there. Changing the noise estimate does more than any shape gate tested.
Whether shape gates add anything on top of `lag` is still untested.

## What still trips the screen, and what that means

With `lag`, most of the remaining flags are minerals with genuine bands near 840 cm⁻¹. These
include As-O and V-O stretches, some phosphates and silicates, and the weak 837-839 cm⁻¹ band
of white lead (cerussite). A single-band screen cannot tell these from chromate. That is why
a positive from spice-screen is "send to a laboratory" and never a finding. In real spices,
the mineral fillers that matter (chalk, talc, gypsum, clays, quartz, feldspars, iron oxides,
TiO₂) are flagged far less often under `lag`: 10 of their library spectra, against 49 or more
under `diff`.

## Limits

- RRUFF spectra are pure minerals, not spices. Turmeric's fluorescence and its own bands are
  not part of this test.
- The mixtures add spectra by peak height. f is a peak-height fraction, not a mass fraction,
  and it says nothing about the 0.5% w/w limit in turmeric (Erasmus et al. 2021).
- The noise added to the mixtures is white and unsmoothed, which suits `diff`. On raw,
  unsmoothed spectra, `--noise diff` is still available and is more sensitive at low levels.
- Only 9 crocoite spectra from 3 specimens exist in the library, so 9/9 is a small sample.

## Data and code

- `docs/data/noise-rules/`: per-spectrum SNRs under every noise mode (`results.csv`), every
  rule (`rules.csv`), the mixtures (`mixtures.csv`, `mixture_rules.csv`), the unit-test run
  under each mode (`mode_tests.json`) and the job's own summary (`summary.md`, with the
  undercount described above).
- `docs/data/band-shape/`: shape features of every 0.4.0 positive (`features.csv`), the gate
  results (`rules.csv`, `mixture_rules.csv`) and `summary.md`.
- `tools/rruff-rules/` and `tools/rruff-shape/`: the scripts. RRUFF spectra are not
  redistributed. The scripts download `excellent_unoriented.zip` from rruff.net.

RRUFF: Lafuente B, Downs RT, Yang H, Stone N. The power of databases: the RRUFF project. In:
Highlights in Mineralogical Crystallography, De Gruyter (2015) 1-30.

Made by MV2 of Munim, Inc. The study and code were produced with AI agents working in his
name. Text CC BY 4.0, code Apache-2.0.
