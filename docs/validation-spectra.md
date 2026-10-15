# Validation spectra for lead-chromate screening: an open-source survey

Status: **reference note, 2026-10-15.** This file does not change any rule. It maps where
Raman spectra of the real pigment live, at which laser lines, and whether their licence lets
them be redistributed, so that [grain mode](grain-mode.md) can one day be tested on chrome
yellow itself and not only on the mineral crocoite.

## Why this note exists

Grain mode's gates (apex at 830-850 cm⁻¹, dominance ≥ 0.5, a near-infrared bend gate) were
calibrated on the nine RRUFF crocoite spectra, because crocoite (natural PbCrO₄) is the only
lead chromate in the open RRUFF Raman archive. But the thing found in adulterated spices is
not crocoite. It is the **pigment**: chrome yellow (synthetic PbCrO₄, Colour Index PY34),
often a **solid solution with lead sulfate** (PbCr₁₋ₓSₓO₄), and chrome orange (basic lead
chromate). grain-mode.md names this as an open limit: a strong sulfate band near 980 cm⁻¹
could in principle fail the dominance gate, and "real pigment spectra are needed to check
this." This note is the first step: finding those spectra and their terms.

## What the pigment literature reports for chrome yellow

The chromate ion's symmetric Cr–O stretch (ν₁) is the strong, diagnostic band. Across the
published pigment libraries it sits in a narrow window and, importantly for grain mode, it
holds its position from green excitation all the way into the near-infrared:

| Source | Excitation | ν₁ stretch (cm⁻¹) | Bend region (cm⁻¹) | Licence / reuse |
|---|---|---|---|---|
| Burgio & Clark 2001, *Spectrochim. Acta A* 57:1491 ([PubMed 11446703](https://pubmed.ncbi.nlm.nih.gov/11446703/)) | 1064 nm (FT-Raman) | ~840 | ~357 | Elsevier, © publisher — cite values only |
| Correia / Renaissance-yellow study, *Spectrochim. Acta A* 2010 ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1386142510006359)) | visible | 827, (plus) | 374, 358, 324 | Elsevier, © publisher — cite values only |
| CHSOS "Pigments Checker" ([chrome yellow page](https://chsopensource.org/chrome-yellow-c-lc11053f/)) | 532, 632, 785, 830, 1064 nm | ~840 | ~357 | "free database", © CHSOS, **no stated reuse licence** — cite only, do not redistribute |
| *Minerals* 2024, 14(6):557, 852 nm library ([MDPI](https://www.mdpi.com/2075-163X/14/6/557)) | 852 nm | ~841 | ~360 | MDPI open access, CC BY 4.0 — reusable with attribution |
| RRUFF crocoite (already used; band-shape study) | 514/532 and 780/785 nm | 834-839 | 320-410 | RRUFF, open for research |

Frost (2004), the source grain-mode.md cites for the bending bands (400, 377, 357, 338,
327 cm⁻¹), agrees with the 357-360 cm⁻¹ value these libraries report.

### Why this matters for the pre-registered gates

- **Apex gate (strongest point of 790-890 cm⁻¹ at 830-850 cm⁻¹).** Every source above puts
  chrome yellow's ν₁ at 827-841 cm⁻¹, i.e. inside or at the edge of the 830-850 window. This
  is independent, non-mineral confirmation that the window is set where the pigment's own
  band actually falls — not fitted to crocoite alone.
- **Bend gate (near-infrared only, ≥ 700 nm).** The 852 nm *Minerals* library and the
  785/830 nm CHSOS spectra are the closest published excitations to the Blaise kit's **808
  nm** laser. They all still show a chromate bend near 357-360 cm⁻¹ at those wavelengths, so
  the bend gate is asking for a band that the pigment genuinely retains in the near-infrared.
  What is **not yet** published anywhere we found is the *bend-to-stretch ratio* for the
  pigment (as opposed to the mineral crocoite) at 808 nm. Grain mode's 0.15 threshold rests
  on three NIR crocoite spectra; a pigment measurement would test it properly.

## Licence census (so nothing is republished that may not be)

- **Redistributable with attribution:** the *Minerals* 2024 852 nm library (CC BY 4.0). Its
  supplementary spectra, if posted as data, could be mirrored in `tools/` with credit. To be
  confirmed from the article's own supplement, which is paywalled to our fetcher (HTTP 403).
- **Free to download, but not to redistribute:** CHSOS Pigments Checker. The site calls it a
  "free Raman database" and offers direct downloads, but carries only "© 2026 Cultural
  Heritage Science Open Source" with no Creative Commons or reuse grant (its terms-of-use URL
  returns 404). So these spectra may be *consulted and cited*, and in principle analysed
  locally, but **not** copied into this repository.
- **Cite values only:** Burgio & Clark 2001 and the 2010 Renaissance-yellow paper are
  copyrighted journal articles. Their reported band positions are facts and may be cited; the
  spectra themselves may not be redistributed.
- **Already open:** RRUFF, used for every audit so far.

## What would make a real pigment validation

1. Obtain chrome yellow and chrome-orange Raman spectra at a near-infrared laser (ideally
   ~808 nm), **licence-cleared for redistribution** — the CC BY *Minerals* supplement is the
   first candidate, subject to confirming it contains the raw spectra.
2. Run grain mode over them and record: does each pass the apex and dominance gates; what is
   the measured bend-to-stretch ratio versus the 0.15 threshold; and does a lead-sulfate
   solid solution (the ~980 cm⁻¹ band) ever beat the 840 band and fail dominance.
3. Report the result in [grain-mode.md](grain-mode.md) under its limits, without changing the
   pre-registered rule.

## Honest limits of this note

- The band positions above were read from the publications and their abstracts/figure
  descriptions, not re-measured by us; the precise tables should be read from each paper.
- No pigment spectrum has yet been run through grain mode. This note only establishes that
  the *positions* the gates target are the positions the pigment literature reports, and
  which sources could, licence-permitting, supply a real test.
- The sulfate solid-solution dominance question remains open until a real chrome-yellow
  spectrum is run.

Made by MV2 of Munim, Inc. with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
