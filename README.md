# spice-screen

Screen a **Raman spectrum of a spice** for known toxic adulterants: lead chromate, metanil
yellow, Sudan I, rhodamine B and auramine O. It removes the fluorescence background, then
looks for each adulterant's published marker bands. Every marker comes with its source and
its reported detection limit. It can also check an instrument's Raman shift axis against
polystyrene and screen a whole folder of spectra into one CSV table.

> **0.5.0 (2026-10-14): fewer false flags.** On the whole RRUFF mineral library, 0.4.0 found
> every real lead chromate (crocoite) spectrum but also flagged 34% of the spectra of minerals
> without chromium, mostly because smoothing fooled its noise estimate. 0.5.0 uses a noise
> estimate that smoothing cannot shrink. It still finds 9 of 9 crocoite spectra and flags
> 11.6% of the minerals without chromium. Most of the remaining flags are real bands of other
> minerals at 840 cm⁻¹, including white lead. See [docs/rruff-noise-rules.md](docs/rruff-noise-rules.md).
>
> **Grain mode (0.6.0.dev0), audited 2026-10-15,** for picked yellow-orange particles. It asks
> for lead chromate's whole band pattern, not just a band near 840 cm⁻¹. Its rule was published
> before the library audit that tests it. On the whole RRUFF library it keeps 9 of 9 crocoite
> spectra and cuts false flags on minerals without chromium from 11.6% to 2.6%, with none on
> common spice fillers or other lead pigments. It missed one of its four pre-registered
> expectations: 149 of those spectra still pass, against fewer than 100 predicted. See
> [Grain mode](#grain-mode-audited) below.

## Why

Lead chromate is a yellow pigment that is added to turmeric and other spices to brighten
their colour. It poisons the people who eat them.

- **Bangladesh.** Pigment was dusted onto whole dried turmeric roots during polishing in 7 of
  the 9 main growing districts. Turmeric powder reached 1,152 µg/g lead
  ([Forsyth et al., *Environ Res* 2019](https://doi.org/10.1016/j.envres.2019.108722)).
  Rapid screening at the wholesale market and enforcement by the Bangladesh Food Safety
  Authority followed. Market samples with detectable lead then fell **from 47% in 2019 to
  0% in 2021** (n = 631) ([Forsyth et al., *Environ Res* 2023](https://doi.org/10.1016/j.envres.2023.116328)).
- **Eastern India, 2021-2023.** About 30% of 503 samples exceeded India's 10 µg/g lead limit,
  with a maximum of 6,416 µg/g
  ([Forsyth et al., *npj Sci Food* 2026](https://doi.org/10.1038/s41538-026-00867-8)).
- **United States, 2023.** Cinnamon in recalled applesauce pouches held 2,270-5,110 ppm lead,
  with chromium consistent with lead chromate. By January 2024 the CDC had more than 300
  reports of elevated blood lead across 38 states, most of them young children ([FDA](https://www.fda.gov/food/outbreaks-foodborne-illness/investigation-elevated-lead-chromium-levels-cinnamon-applesauce-pouches-november-2023),
  [CDC](https://www.cdc.gov/lead-prevention/php/news-features/lead-and-chromium-poisoning-outbreak.html)).

Screening is what worked in Bangladesh, but new handheld XRF analyzers cost about
$20,000-65,000. Pocket Raman devices cost far less. The pigment has a strong Raman band at
840 cm⁻¹, which turmeric itself lacks, although some minerals and white lead also show bands
there (see the audits). This tool turns a spectrum from any Raman device into a cited,
cautious screening call.

Illegal dyes are the other half of spice fraud: metanil yellow and auramine O in turmeric,
and Sudan I and rhodamine B in chili and paprika. They are usually screened by SERS after a
quick extraction.

How low a screen must reach to matter is measured from public lead-testing data in the
companion repository [spice-lead-recalls](https://github.com/munimtechnologies/spice-lead-recalls).

## Use

Python 3.8+, standard library only.

```
python spice_screen.py spectrum.csv                 # normal Raman, text report
python spice_screen.py spectrum.csv --mode sers     # SERS markers (dyes after extraction)
python spice_screen.py spectrum.csv --json          # machine-readable report
python spice_screen.py spectrum.csv --exit-code     # exit 1 if anything is screen-positive
python spice_screen.py "market-survey/*.csv" --csv  # one row per spectrum, for batches
python spice_screen.py --calibrate polystyrene.csv  # check the instrument's shift axis
python spice_screen.py spectrum.csv --calibrate polystyrene.csv   # screen on a corrected axis
python spice_screen.py spectrum.csv --noise diff    # raw, unsmoothed spectra (more sensitive)
python spice_screen.py grain.csv --grain --laser 808  # a picked particle (experimental)
python spice_screen.py --list                       # the marker library and its sources
python spice_screen.py --demo                       # a synthetic example
python -m unittest -v                               # tests, offline
```

The input is two columns: Raman shift (cm⁻¹) and intensity. Commas, semicolons with decimal
commas, tabs and spaces all work, and headers and `#` lines are skipped. Most instrument
software can export this format.

Each adulterant gets one of these verdicts:

| Verdict | Meaning |
|---|---|
| `screen-positive` | The primary band and enough supporting bands stand above the noise (default SNR ≥ 5). Send the sample to a laboratory. |
| `inconclusive` | Some marker bands are present but not enough of them (or, in grain mode, the band shape does not match). Re-measure, or test in a laboratory. |
| `not-detected` | No marker band was found. This means "below what the screen can see", not "safe". |
| `not-covered` | The spectrum does not cover the primary band. |

Each report also has a `result`, the most serious verdict among its markers. Each marker
lists every band it checked, with its signal-to-noise ratio and position, and
`bands_detected`, the number of its bands found (shown as `2/3 bands` in the text report).

### Batches

Give several files, or a wildcard in quotes (it is expanded by the tool, so it works on
Windows too). `--csv` prints one row per file: the file, its overall result, then one column
per marker. A file that cannot be read gets an `error:` row, the rest are still screened, and
the exit code is 2. With `--json`, a batch prints a list of reports, each with its `file`.

### Checking the shift axis

Marker bands are searched within ±8 cm⁻¹ of their published positions, and low-cost
spectrometers can be off by more than that. In a study of 26 Raman systems, only 16 of the 26
measurements of polystyrene's 1001.4 cm⁻¹ band met the European Pharmacopoeia's ±1.5 cm⁻¹
tolerance ([Anal Sci 2019](https://doi.org/10.2116/analsci.18P501)).

Measure a piece of polystyrene on the same instrument, the same day, and pass it with
`--calibrate`. The tool finds the polystyrene bands at 620.9, 1001.4, 1602.3 and 3054.3 cm⁻¹
(ASTM E1840, as quoted in [Appl Spectrosc 2025](https://doi.org/10.1177/00037028251330654))
that the spectrum covers. It refines each band's position with a parabola through its top
three points and reports the error at each band against the ±1.5 cm⁻¹ tolerance. It then
fits a straight-line correction (an offset alone if only one band is found) and screens the
sample spectra on the corrected axis. Each report records the correction it used.

### Grain mode (audited)

Most leaded spice holds too little pigment for powder Raman to see. Picking out the bright
yellow-orange particles and measuring them one by one, the route FDA scientists used for
cinnamon ([Kubachka et al. 2026](https://doi.org/10.1177/27551857261425269)), puts mostly
pure pigment under the laser. With `--grain`, a lead chromate positive must then also show
the pigment's band pattern:

- **apex**: the strongest point of 790-890 cm⁻¹ lies at 830-850 cm⁻¹;
- **dominance**: the 840 band is at least half the strongest band in 200-1100 cm⁻¹ (curcumin's
  bands lie above 1100 cm⁻¹, so turmeric dust does not count against it);
- **bend**: with `--laser` 700 nm or longer, chromate's bending bands at 320-410 cm⁻¹ reach 15%
  of the 840 band. In the RRUFF crocoite spectra they are 58-82% of it under 780/785 nm
  lasers but only 4-13% under 514/532 nm, so the gate is not applied to green lasers.

If a gate fails, the verdict is `inconclusive` and the report says which gate failed. The
JSON report carries the measured values under `grain`. The rule, its thresholds and the
expected audit results were published before the audit was run:
[docs/grain-mode.md](docs/grain-mode.md). That page now has the results. Three of the four
expectations were met; 149 spectra of minerals without chromium still pass (2.6% of 5,713),
against fewer than 100 predicted, and they are rare arsenates, vanadates and silicates that
are not expected in food. Under near-infrared lasers, such as the 808 nm of the Blaise kit,
the rate is 1.9%. The mode has not been tested on real picked spice grains yet, so treat it
as experimental.

## Marker library

| Adulterant | Mode | Bands (cm⁻¹) | Reported limit | Source |
|---|---|---|---|---|
| Lead chromate | Raman | **840**, 825, 856 (1 needed) | ~0.5-0.6% w/w in turmeric powder | Erasmus et al., *Food Control* 2021, [doi:10.1016/j.foodcont.2020.107714](https://doi.org/10.1016/j.foodcont.2020.107714) (840 band, limit); Frost, *J Raman Spectrosc* 2004, [doi:10.1002/jrs.1121](https://doi.org/10.1002/jrs.1121) (triplet) |
| Metanil yellow | Raman | **1406**, 997, 1147 (2 needed) | ~1% w/w in turmeric | Dhakal et al., *Foods* 2016, [doi:10.3390/foods5020036](https://doi.org/10.3390/foods5020036) |
| Metanil yellow | SERS (Au) | **1383**, 504, 1176, 1588 (3 needed) | 0.1 mg/g in turmeric | [Metrohm AN-RS-019](https://www.metrohm.com/en/applications/application-notes/raman-anram/an-rs-019.html) |
| Sudan I | SERS | **721**, 1226 (2 needed) | ~1 ppm after TLC | Talanta 2015 (PubMed 26078169); PubMed 29056826 |
| Rhodamine B | SERS (Ag) | **1645**, 1360, 1509, 620 (3 needed) | ~1 µg/g in chili powder | Nguyen et al., *RSC Adv* 2025, [doi:10.1039/d5ra06188a](https://doi.org/10.1039/d5ra06188a) (bands); *Int J Biol Macromol* 2024, [doi:10.1016/j.ijbiomac.2024.135609](https://doi.org/10.1016/j.ijbiomac.2024.135609) (chili limit) |
| Auramine O | SERS (Ag) | **778**, 551, 649, 1189 (3 needed) | dye bath down to 0.003 mg/mL; ~1 µg/g in curry powder (Au, after extraction) | *Foods* 2023, 12:4124, [doi:10.3390/foods12224124](https://doi.org/10.3390/foods12224124) (bands); [Metrohm AN-RS-020](https://www.metrohm.com/en/applications/application-notes/raman-anram/an-rs-020.html) (curry powder) |

### Lead chromate's triplet

Crocoite (PbCrO4) shows three chromate stretching bands, at 856, 841 and 825 cm⁻¹, and the
middle one is the symmetric stretch (Frost 2004). The screen triggers on 840 alone, as
before, because the three bands lie within about 31 cm⁻¹ and often merge into one feature
on a handheld instrument. Requiring two of them would turn real positives into
`inconclusive`. The 825 and 856 cm⁻¹ bands are checked and reported for confirmation: when an
instrument resolves them, a `3/3 bands` positive is stronger evidence that the 840 cm⁻¹
feature really is chromate. See [docs/lead-chromate-raman.md](docs/lead-chromate-raman.md).
In all nine RRUFF crocoite spectra the triplet was one broad envelope, with no separate
bands, so in practice expect `1/3 bands` ([docs/rruff-audit.md](docs/rruff-audit.md)).

Auramine O's 1598 cm⁻¹ band is left out on purpose, because curcumin's strong bands near
1600 cm⁻¹ overlap it in turmeric.

Use `--library my_markers.json` to add markers of your own. It takes the same fields as
`--list --json`, and every entry needs at least one source.

## How it works

For each marker band, the tool takes a ±60 cm⁻¹ window. It fits the fluorescence background
by modified polynomial fitting (Lieber & Mahadevan-Jansen, *Appl Spectrosc* 57:1363, 2003).
It then measures the highest point within ±8 cm⁻¹ of the band against the local offset and
divides by the noise. A maximum that sits on the edge of that range is treated as the flank
of a neighbouring band, not a peak.

The noise estimate is chosen with `--noise`:

| `--noise` | Noise is | Use for |
|---|---|---|
| `lag` (default from 0.5.0) | the larger of the point-to-point spread and the spread of differences between points 4 cm⁻¹ apart, away from the band | any spectrum, including ones the instrument software has smoothed |
| `diff` (default up to 0.4.0) | the robust spread of point-to-point differences | raw, unsmoothed spectra; a little more sensitive there, but smoothing makes it see ripples as bands |
| `scatter` | the larger of that and the spread of the window's corrected points | experiments only; it can hide a resolved triplet |

In a window this narrow, a strong band pulls the polynomial fit into a slight bow: a little
above the true background under the band, a little below it at the window edges. The local
offset (the median of the corrected points away from the band) absorbs most of that, and
the tests check that a band keeps most of its height.

Grain mode measures the apex and the bending bands above straight lines through the lowest
points on either side, as in the band-shape study, and the dominance on a rolling-ball
baseline (a morphological opening ±60 cm⁻¹ wide) across 200-1100 cm⁻¹.

## Checked against real spectra

Four studies ran the lead chromate marker over all 5,787 processed spectra in the RRUFF
mineral library (Lafuente et al. 2015):

- [docs/rruff-audit.md](docs/rruff-audit.md), on 0.4.0: 9 of 9 crocoite spectra flagged, but
  also 1,935 of 5,713 spectra of minerals without chromium. White lead (cerussite) has a weak
  band at 837-839 cm⁻¹ in all 17 of its spectra.
- [docs/rruff-noise-rules.md](docs/rruff-noise-rules.md), which chose 0.5.0's noise estimate.
  With `lag`, crocoite stays at 9 of 9 and minerals without chromium fall to about 663 of
  5,713 (11.6%). On synthetic crocoite + filler mixtures, false flags on the filler alone fall
  from 6.3% to 0.5%, and detection at 3% crocoite peak height falls from 80% to 67%. Gates on
  band shape were also tested; they helped less and are not used in the normal mode.
- [audits/rruff-0.5.0.md](audits/rruff-0.5.0.md), a full re-audit of 0.5.0 with the original
  audit script (2026-10-15): crocoite 9 of 9; minerals without chromium 663 of 5,713 (11.6%),
  matching the estimate above; white lead (cerussite) still flags in 17 of 17 spectra;
  forsterite is inconclusive in 25 of 25, never positive.
- [audits/rruff-grain-0.6.0.md](audits/rruff-grain-0.6.0.md), the pre-registered audit of grain
  mode (2026-10-15): crocoite 9 of 9; minerals without chromium 149 of 5,713 (2.6%); none of 227
  common filler spectra and none of 38 other lead pigment spectra; 10 of 16 flagged spectra of
  other chromate minerals, including phoenicochroite (basic lead chromate). Results and what
  they mean: [docs/grain-mode.md](docs/grain-mode.md#audit).

The audits list RRUFF IDs and derived numbers only; the spectra are not redistributed here.

## Limits

- This is a **screen**, not a certified test. It has not been validated on real spice samples
  yet; the tests use synthetic spectra, and the only real-spectrum checks so far are the
  mineral-library studies above. Treat a positive as a reason to test in a laboratory (ICP-MS
  or XRF for lead and chromium, HPLC for dyes), never as proof. Treat a negative as "not
  seen", never as "safe".
- An 840 cm⁻¹ positive means "a chromate-like band". Other chromates, white lead and some
  minerals (arsenates, vanadates, some phosphates and silicates) also have bands there.
- Normal Raman sees lead chromate only at percent levels in ground powder (about 0.5%,
  roughly 3,200 µg/g lead). That is above many contaminated field samples. Measuring the
  surface of whole polished roots, where the pigment sits, or picked particles in grain
  mode, should help. Validating that is the next step.
- Grain mode is meant for particles that are mostly pigment. On ground powder it rejects true
  lead chromate whenever another mineral band is stronger, by design. Its thresholds come
  from mineral spectra; chrome yellow pigments mixed with lead sulfate, and real picked
  grains, have not been measured yet.
- Band positions vary by a few cm⁻¹ between instruments, and SERS bands also vary with the
  substrate, solvent and pH. Use `--calibrate` for the instrument, and check a known
  reference sample on your substrate first.
- The polystyrene correction is only as good as the polystyrene spectrum: measure it on the
  same instrument and settings, and on the same day, as the samples.
- This is not food-safety, medical or legal advice. Follow your local regulator's methods
  for any enforcement decision.

## Changes

- **Audits (2026-10-16)** Results of the grain-mode audit and the full re-audit of 0.5.0, in
  `audits/` and [docs/grain-mode.md](docs/grain-mode.md#audit). Grain mode's rule is unchanged.
- **0.6.0.dev0 (unreleased)** Grain mode (`--grain`, `--laser`) for picked particles: apex,
  dominance and laser-dependent bending-band gates on top of the 840 cm⁻¹ check, with the
  rule pre-registered in [docs/grain-mode.md](docs/grain-mode.md) and its audit tool in
  `tools/rruff-grain/`. Normal mode is unchanged. `tools/rruff-audit/audit_local.py`, listed
  in `tools/README.md` since 0.5.0, is now in the repository.
- **0.5.0** Default noise estimate is now `lag`, which smoothing cannot shrink. On the RRUFF
  library, it keeps 9 of 9 crocoite spectra and cuts flags on minerals without chromium from
  33.9% to 11.6% ([docs/rruff-noise-rules.md](docs/rruff-noise-rules.md)). The new `--noise`
  option chooses `lag`, `diff` (the old behaviour, for raw spectra) or `scatter`, and each
  report records the estimate it used in `noise`. The study's per-spectrum data are in
  `docs/data/`.
- **Docs (2026-10-14)** RRUFF library audit of 0.4.0 ([docs/rruff-audit.md](docs/rruff-audit.md)),
  with its script in `tools/rruff-audit/` and per-spectrum results in `docs/data/`.
- **0.4.0** Lead chromate now also checks the 825 and 856 cm⁻¹ bands of the chromate triplet
  (Frost 2004) for confirmation. 840 alone still flags, so sensitivity is unchanged. Each
  marker reports `bands_detected`, and the text report shows it as `n/m bands`.
- **0.3.0** Auramine O (SERS) marker for turmeric and curry powder. `--calibrate`: checks the
  Raman shift axis against polystyrene and screens on the corrected axis. Batch screening:
  several files or a wildcard, with `--csv` for one row per spectrum. Each report now has an
  overall `result`.
- **0.2.0** First public release. Rhodamine B (SERS) marker for chili products. Baseline
  test now checks what the screen relies on (a band keeps most of its height) instead of a
  bound the method cannot meet in narrow windows; the 0.1.0 draft never shipped because of it.

## About

Made by MV2 of Munim, Inc. The code was produced with AI agents working in his name and is
published in the open. Corrections, new markers (with sources) and real spectra shared under
an open licence are welcome as issues or pull requests.

Apache-2.0 license. Contact: mv2@munimtech.com
