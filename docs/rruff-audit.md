# How specific is the 840 cm⁻¹ lead chromate marker? spice-screen 0.4.0 vs the RRUFF library

**Short answer: in 0.4.0 it was not specific enough.** spice-screen 0.4.0 flagged every real
crocoite (lead chromate) spectrum in the RRUFF library, 9 of 9. It also flagged **1,935 of the
5,713 spectra of minerals without chromium (33.9%)**. Most of those flags come from a fault
in how 0.4.0 estimates noise, and a fix is being tested (see "What changes next"). A smaller
set are real Raman bands of other minerals that sit at 840 cm⁻¹. One marker band cannot tell
those apart from lead chromate.

Until the fix ships, read a 0.4.0 `screen-positive` on a **smoothed or processed** spectrum
as weak evidence. It was always a reason to test in a laboratory, never proof.

## What was run

- **Data:** every processed spectrum in RRUFF's `excellent_unoriented.zip`: 5,787 spectra of
  1,948 minerals, 5,785 of which cover 840 cm⁻¹, read on 2026-10-14. RRUFF: Lafuente B, Downs
  RT, Yang H, Stone N, *The power of databases: the RRUFF project*, in *Highlights in
  Mineralogical Crystallography*, De Gruyter (2015) 1-30. The spectra are not redistributed
  here.
- **Code:** the released `spice_screen.py` v0.4.0 (sha256 `5be20a87472e…`), downloaded from
  this repository's v0.4.0 tag at run time. It ran the lead chromate marker with default
  settings (SNR ≥ 5, 840 ± 8 cm⁻¹, with the 825 and 856 cm⁻¹ bands as confirmation). The
  script is [tools/rruff-audit/audit.py](../tools/rruff-audit/audit.py).
- **Per-spectrum results** (verdict, SNR, peak position and the 840 cm⁻¹ point's height as a
  fraction of the spectrum's strongest point; no spectra) are in
  [docs/data/rruff-audit-v0.4.0.csv](data/rruff-audit-v0.4.0.csv).

## Results

### Crocoite (PbCrO4): 9 of 9 flagged

| RRUFF ID | laser (nm) | peak position (cm⁻¹) | SNR (0.4.0) | triplet bands |
|---|---|---|---|---|
| R040053 | 514 | 839.2 | 104 | 1/3 |
| R040053 | 532 | 836.0 | 90 | 1/3 |
| R040053 | 785 | 838.9 | 220 | 1/3 |
| R050044 | 514 | 839.2 | 73 | 1/3 |
| R050044 | 514 | 833.7 | 25 | 1/3 |
| R050044 | 532 | 834.7 | 85 | 1/3 |
| R050044 | 785 | 838.9 | 167 | 1/3 |
| R160016 | 532 | 838.8 | 149 | 1/3 |
| R160016 | 780 | 839.2 | 185 | 1/3 |

- In every spectrum the 840 cm⁻¹ point is the strongest point of the whole spectrum.
- **The 825/840/856 cm⁻¹ triplet was never resolved.** In these processed spectra the
  chromate stretch is one broad envelope. For example, R050044 at 532 nm has its maximum at
  834.75 cm⁻¹ and a full width at half maximum of about 28-29 cm⁻¹. This supports the design
  choice that 840 alone must flag. It also means that "3/3 bands" will rarely help in practice.
- The maxima sit at 833.7-839.2 cm⁻¹, all inside the 840 ± 8 window, but up to 6.3 cm⁻¹ below
  840. The same sample measures about 4 cm⁻¹ lower at 532 nm than at 514 or 785 nm, which
  suggests instrument calibration. That is what `--calibrate` is for.

### Other chromium minerals: 28 of 63 flagged

The flagged ones are chromates: edoylerite, georgerobinsonite, hemihedrite, iranite,
phoenicochroite and petterdite. Their chromate stretch is the same vibration, so these flags
are expected. A few spectra of chromium(III) minerals without chromate were also flagged
(uvarovite, chromite, stichtite), with small relative heights of 0.02-0.20.

### Minerals without chromium: 1,935 of 5,713 flagged (33.9%)

Two very different things are mixed in this number.

1. **Small features flagged because the noise was underestimated.** Only 346 of the 1,935
   flagged spectra have an 840 cm⁻¹ point at 10% or more of the spectrum's strongest point,
   and 266 at 25% or more. The other 1,589 are below 10%. Some are real weak bands
   (cerussite, below), but many rest on a "band" of 0.01-0.2% of the strongest point. Calcite, for example, was flagged in 10 of 26 spectra, with relative heights of
   0.0001-0.0016. Calcite has no Raman band there. RRUFF's processed spectra are smoothed, and
   0.4.0 estimated noise from the spread of point-to-point differences. Smoothing makes
   neighbouring points almost equal, so that estimate collapses, and small ripples pass
   SNR ≥ 5. This is a fault in 0.4.0, not a property of lead chromate. Raw spectra from a
   handheld device that does no smoothing are less affected, but some instruments smooth by
   default.
2. **Real bands at 840 cm⁻¹ (a smaller set, up to 100% relative height).** These include:
   - many **arsenates**, whose AsO4 stretching bands lie around 800-880 cm⁻¹ (adamite,
     conichalcite, roselite, talmessite and many more);
   - **vanadates** (descloizite, cechite, namibite);
   - **uranyl minerals**;
   - **olivine- and humite-group silicates** (fayalite, tephroite, chondrodite, humite).

   A single band cannot separate these from lead chromate. They are unlikely in a spice,
   but a screen should say so plainly, not hide it.

### Lead pigments and spice fillers

| mineral | why it matters | spectra | flagged by 0.4.0 |
|---|---|---|---|
| Cerussite | lead carbonate (white lead) | 17 | 17 |
| Hydrocerussite | basic lead carbonate | 6 | 4 |
| Minium | red lead, reported in chili and paprika | 4 | 2 |
| Litharge | lead oxide | 2 | 1 |
| Anglesite | lead sulfate | 9 | 1 |
| Calcite | chalk filler | 26 | 10 |
| Muscovite | mica, soil | 23 | 11 |
| Gypsum | calcium sulfate filler | 5 | 3 |
| Talc | talc filler | 9 | 2 |
| Hematite | iron oxide, brick dust in chili | 8 | 2 |
| Quartz | sand | 21 | 0 |
| Forsterite | olivine | 25 | 0 (25 inconclusive) |

**Cerussite is a real finding.** It has a weak band at 837-839 cm⁻¹ (1-7% of its strongest
band) that overlaps the lead chromate window. White lead is itself a lead adulterant, so a
flag still means "send it to a laboratory". But a cerussite flag is not lead chromate, and the
report should not name it as such. The filler flags (calcite, muscovite, gypsum, talc) are
almost all of the tiny-bump kind above.

## Limits of this audit

- These are pure minerals measured on research instruments and then processed, not spices.
  The audit measures specificity against the library, not performance on turmeric.
- The relative height uses the spectrum's median as its floor. It is a coarse measure,
  reported to sort the flags, and not part of 0.4.0's decision.
- RRUFF holds few spectra of some minerals and none of organic spice matrices.
- The audit was run with AI agents working for MV2 of Munim, Inc. The code and every
  per-spectrum number are published so that anyone can check it.

## What changes next

1. **Noise estimate (in testing).** The candidate 0.5.0 lets a band stand out only against
   the larger of two estimates: the point-to-point spread, and either the spread of the
   baseline-corrected points away from the band (`scatter`) or the spread of differences
   between points 4 cm⁻¹ apart (`lag`). Smoothing shrinks neither of the second pair. A
   queued job screens the whole RRUFF library again under each option, at SNR 5-20, with
   and without a relative-height gate. It also mixes the real crocoite spectra into real
   filler spectra (chalk, talc, clays, iron oxides) at falling fractions, to check that
   sensitivity survives. The default changes only if crocoite is still found and the false
   flags fall. The numbers will be published here.
2. **Confirmation by bending bands.** Crocoite is commonly confirmed by its CrO4 bending
   bands near 334, 355, 373 and 397 cm⁻¹ together with the stretch near 835-841 cm⁻¹ (Burgio
   and Clark 2001; Frost 2004). Arsenates and vanadates have different patterns there. This
   is the planned way to tell the true overlaps apart.
3. **Wording.** Reports will say that a positive at 840 cm⁻¹ means "a chromate-like band",
   and that white lead (cerussite) can also trigger it.

Made by MV2 of Munim, Inc. The work was produced with AI agents working in his name.
Text and per-spectrum data: CC BY 4.0. Code: Apache-2.0.
