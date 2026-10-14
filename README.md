# spice-screen

Screen a **Raman spectrum of a spice** for known toxic adulterants: lead chromate, metanil
yellow, Sudan I and rhodamine B. It removes the fluorescence background, then looks for each
adulterant's published marker bands. Every marker comes with its source and its reported
detection limit.

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
$20,000-65,000. Pocket Raman devices cost far less, and the pigment has a strong, isolated
Raman band at 840 cm⁻¹. This tool turns a spectrum from any Raman device into a cited,
cautious screening call.

Illegal dyes are the other half of spice fraud: metanil yellow in turmeric, and Sudan I and
rhodamine B in chili and paprika. They are usually screened by SERS after a quick extraction.

## Use

Python 3.8+, standard library only.

```
python spice_screen.py spectrum.csv                 # normal Raman, text report
python spice_screen.py spectrum.csv --mode sers     # SERS markers (dyes after extraction)
python spice_screen.py spectrum.csv --json          # machine-readable report
python spice_screen.py spectrum.csv --exit-code     # exit 1 if anything is screen-positive
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
| `inconclusive` | Some marker bands are present but not enough of them. Re-measure, or test in a laboratory. |
| `not-detected` | No marker band was found. This means "below what the screen can see", not "safe". |
| `not-covered` | The spectrum does not cover the primary band. |

## Marker library

| Adulterant | Mode | Bands (cm⁻¹) | Reported limit | Source |
|---|---|---|---|---|
| Lead chromate | Raman | **840** | ~0.5-0.6% w/w in turmeric powder | Erasmus et al., *Food Control* 2021, [doi:10.1016/j.foodcont.2020.107714](https://doi.org/10.1016/j.foodcont.2020.107714) |
| Metanil yellow | Raman | **1406**, 997, 1147 (2 needed) | ~1% w/w in turmeric | Dhakal et al., *Foods* 2016, [doi:10.3390/foods5020036](https://doi.org/10.3390/foods5020036) |
| Metanil yellow | SERS (Au) | **1383**, 504, 1176, 1588 (3 needed) | 0.1 mg/g in turmeric | [Metrohm AN-RS-019](https://www.metrohm.com/en/applications/application-notes/raman-anram/an-rs-019.html) |
| Sudan I | SERS | **721**, 1226 (2 needed) | ~1 ppm after TLC | Talanta 2015 (PubMed 26078169); PubMed 29056826 |
| Rhodamine B | SERS (Ag) | **1645**, 1360, 1509, 620 (3 needed) | ~1 µg/g in chili powder | Nguyen et al., *RSC Adv* 2025, [doi:10.1039/d5ra06188a](https://doi.org/10.1039/d5ra06188a) (bands); *Int J Biol Macromol* 2024, [doi:10.1016/j.ijbiomac.2024.135609](https://doi.org/10.1016/j.ijbiomac.2024.135609) (chili limit) |

Use `--library my_markers.json` to add markers of your own. It takes the same fields as
`--list --json`, and every entry needs at least one source.

## How it works

For each marker band, the tool takes a ±60 cm⁻¹ window. It fits the fluorescence background
by modified polynomial fitting (Lieber & Mahadevan-Jansen, *Appl Spectrosc* 57:1363, 2003).
It then estimates noise from the robust spread of point-to-point differences and measures
the highest point within ±8 cm⁻¹ of the band against the local offset. A maximum that sits
on the edge of that range is treated as the flank of a neighbouring band, not a peak.

In a window this narrow, a strong band pulls the polynomial fit into a slight bow: a little
above the true background under the band, a little below it at the window edges. The local
offset (the median of the corrected points away from the band) absorbs most of that, and
the tests check that a band keeps most of its height.

## Limits

- This is a **screen**, not a certified test. It has not been validated on real samples
  yet; the tests use synthetic spectra. Treat a positive as a reason to test in a
  laboratory (ICP-MS or XRF for lead and chromium, HPLC for dyes), never as proof. Treat
  a negative as "not seen", never as "safe".
- Normal Raman sees lead chromate only at percent levels in ground powder (about 0.5%,
  roughly 3,200 µg/g lead). That is above many contaminated field samples. Measuring the
  surface of whole polished roots, where the pigment sits, or measuring before grinding,
  should help. Validating that is the next step.
- Band positions vary by a few cm⁻¹ between instruments, and SERS bands also vary with the
  substrate. Check a known reference sample on your device first.
- This is not food-safety, medical or legal advice. Follow your local regulator's methods
  for any enforcement decision.

## Changes

- **0.2.0** First public release. Rhodamine B (SERS) marker for chili products. Baseline
  test now checks what the screen relies on (a band keeps most of its height) instead of a
  bound the method cannot meet in narrow windows; the 0.1.0 draft never shipped because of it.

## About

Made by MV2 of Munim, Inc. The code was produced with AI agents working in his name and is
published in the open. Corrections, new markers (with sources) and real spectra shared under
an open licence are welcome as issues or pull requests.

MIT license. Contact: munimversion2@gmail.com
