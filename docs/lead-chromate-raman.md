# Lead chromate in turmeric — the Raman basis for spice-screen's marker

Lead chromate (PbCrO4, the mineral **crocoite**) is a bright yellow pigment that has
been added illegally to turmeric to make dull or low-curcumin powder look richer and
more valuable. Because chromate carries lead, even small amounts raise the blood-lead
burden of anyone eating the spice, and lead is a neurotoxin with no safe level in
children. Adulteration of turmeric with lead chromate has been documented in South
Asian supply chains and is the headline hazard that spice-screen's `lead_chromate`
marker is built to catch.

This note records the published Raman evidence behind that marker, so a user can judge
the screen for themselves. **spice-screen is a screen, not a certified test**: a
screen-positive result means "send this to a laboratory", not "this is lead chromate".

## The Raman signature

Lead chromate's Raman spectrum is dominated by the vibrations of its chromate
(CrO4(2-)) tetrahedron. In the Cr-O stretching region, crocoite shows a characteristic
**triplet** of bands:

| Band (cm-1) | Assignment |
|---|---|
| 856 | asymmetric Cr-O stretch |
| **841** | **nu1, totally symmetric Cr-O stretch (most intense)** |
| 825 | asymmetric Cr-O stretch |

These three positions, and the assignment of the central ~841 cm-1 band as the
totally symmetric nu1 stretch, are reported by:

- R. L. Frost, *Raman microscopy of selected chromate minerals*, **Journal of Raman
  Spectroscopy** 35(2): 153-158 (2004), DOI 10.1002/jrs.1121. "The Raman spectrum of
  crocoite shows three bands in the CrO stretching region at 856, 841 and 825 cm-1",
  with the 841 cm-1 band assigned to the nu1 symmetric stretching vibration. (Author's
  accepted version is openly available at QUT ePrints:
  https://eprints.qut.edu.au/811/ )

The same ~840 cm-1 nu1 band is reported for lead chromate ("chrome yellow") pigments in
the conservation-science literature, alongside the two flanking asymmetric stretches —
so the triplet, not a lone peak, is the diagnostic feature.

## How spice-screen uses it

The `lead_chromate` entry (normal Raman mode) screens on the **primary band at
840 cm-1**, the strong nu1 stretch. Normal (non-SERS) Raman only reaches lead chromate
at percent-level adulteration — roughly 0.5% w/w in turmeric powder, on the order of a
few thousand ppm of lead — so a *not-detected* result means "below this screen's reach",
never "safe". SERS or elemental methods (pXRF, ICP-MS) are needed for trace levels; see
A. M. Lopez et al., *Assessing Analytical Methods for the Rapid Detection of Lead
Adulteration in the Global Spice Market*, **Environmental Science & Technology** (2022),
PMCID PMC9730856, which compares pXRF, colorimetry and ICP-MS for exactly this problem.

### Why a single band is screened, and the caveat

The three crocoite bands span only about 31 cm-1 (856 to 825). On a low-resolution
handheld Raman — the setting spice-screen is meant for — they often merge into one
broad feature around 840 cm-1, so requiring two resolved bands would turn real
positives into *inconclusive* and defeat the screen. spice-screen therefore keeps the
nu1 band at 840 cm-1 as the trigger, and leaves confirmation of the full triplet to a
bench instrument or the laboratory follow-up.

### Planned refinement

A future version will carry the 825 and 856 cm-1 asymmetric stretches as **reported
confirmatory bands** on the `lead_chromate` entry while keeping `min_bands` at 1, so
that:

- the 840 cm-1 nu1 band alone still flags screen-positive (sensitivity unchanged), and
- when an instrument does resolve the triplet, the report shows all three bands, giving
  an analyst stronger evidence that the 840 cm-1 feature really is chromate and not an
  unrelated overlap.

This keeps the screen sensitive while making a confirmed triplet visible in the output.

---

Prepared by MV2 of Munim, Inc. This document and the spice-screen project are produced
with AI agents working in MV2's name; the Raman band positions and assignments are
taken from the cited peer-reviewed sources, not generated. MIT license. Contact:
munimversion2@gmail.com
