# Grain mode: lead chromate's whole band pattern, for picked particles

Status: **pre-registered, 2026-10-15.** The rule and its thresholds below were published
before the RRUFF audit that tests them (`tools/rruff-grain/grain_audit.py`). Results will be
added under "Audit" without changing the rule. A different rule would need a new audit.

## Why a second mode

In ground spice powder, lead chromate is a minor component. The normal screen therefore
flags any band near 840 cm⁻¹, and on the RRUFF mineral library 0.5.0 still flags 11.6% of
the spectra of minerals without chromium ([rruff-noise-rules.md](rruff-noise-rules.md)).
Public lead data also show that most leaded spices hold far less pigment than powder Raman
can see (about 0.5% w/w; [spice-lead-recalls](https://github.com/munimtechnologies/spice-lead-recalls)).

Picking the bright yellow-orange particles out of a sample changes both problems. FDA
scientists identified lead chromate in cinnamon by examining such particles (Kubachka et
al. 2026, [doi:10.1177/27551857261425269](https://doi.org/10.1177/27551857261425269)). A
picked grain is mostly pigment, so its spectrum should show lead chromate's whole pattern,
not just a band somewhere near 840 cm⁻¹. Grain mode asks for that pattern.

```
python spice_screen.py grain.csv --grain --laser 808
```

A lead chromate positive in grain mode must pass every gate below. If a gate fails, the
verdict becomes `inconclusive` and the report names the gate.

## The rule

| Gate | Test | Why |
|---|---|---|
| stretch | the 0.5.0 check: a band at 840 ± 8 cm⁻¹, SNR ≥ 5 (noise `lag`) | unchanged |
| apex | above a line through the lowest points of 780-815 and 865-900 cm⁻¹, the strongest point of 790-890 cm⁻¹ lies at **830-850 cm⁻¹** | the band must be the top of the chromate stretch, not the flank of a stronger neighbour such as a vanadate band near 827 cm⁻¹. The nine RRUFF crocoite spectra peak at 834-839 cm⁻¹ |
| dominance | on a rolling-ball baseline (±60 cm⁻¹), the 840 band is at least **0.5** of the strongest band in **200-1100 cm⁻¹** | in pure pigment the chromate stretch is the strongest band of the mineral fingerprint. Curcumin's strong bands lie above 1100 cm⁻¹, so turmeric dust on a grain does not count against it |
| bend | above a line through the lowest points of 260-315 and 415-470 cm⁻¹, the strongest point of 320-410 cm⁻¹ is at least **0.15** of the 840 band, required for lasers of **700 nm or longer** | chromate's bending bands (400, 377, 357, 338 and 327 cm⁻¹; Frost 2004). The laser condition is explained below |

The thresholds live in `GRAIN` in `spice_screen.py` and are checked by the tests.

### Why the bend gate depends on the laser

In the band-shape study ([data/band-shape](data/band-shape/summary.md)), the ratio of the
bending bands to the 840 band in the RRUFF crocoite spectra was:

| Laser | Spectra | Bend ratio |
|---|---|---|
| 514 or 532 nm | 6 | 0.040, 0.048, 0.055, 0.059, 0.091, 0.126 |
| 780 or 785 nm | 3 | 0.579, 0.710, 0.821 |

This fits pre-resonance: green light lies near lead chromate's absorption edge, which
would strengthen the symmetric stretch at 840 cm⁻¹ much more than the bending bands. Only 3
of the 9 spectra used a near-infrared laser (one each from samples R040053, R050044 and
R160016), so the pattern is clear but rests on few spectra. Under near-infrared light the bends are more than half the
stretch. A bend gate would therefore reject every
green-laser crocoite spectrum, while under near-infrared light it can separate chromate from
minerals that have a band near 840 cm⁻¹ but nothing at 320-410 cm⁻¹. The Blaise
spectrometer uses an 808 nm laser.

The 0.15 threshold sits well below the near-infrared crocoite values (0.58-0.82). It is
also above every green-laser value, which is why the gate is not applied there.

If a spectrum does not reach 260 cm⁻¹, the bend gate is skipped and the report says so in
`skipped`. The verdict then rests on the other gates.

## What the audit will report

`tools/rruff-grain/grain_audit.py` runs grain mode over every processed spectrum in the RRUFF
Raman archive, using each file's laser wavelength. It reports:

- how many of the 9 crocoite spectra grain mode keeps;
- how many spectra of minerals without chromium still pass, by class and laser, with the
  full list;
- the same counts for nearby thresholds (dominance 0.3/0.5/0.7, bend 0.1/0.15/0.3, with and
  without the apex gate), so the choice can be judged;
- crocoite mixed into real filler spectra at peak-height fractions 0-0.7, pairing spectra
  taken with lasers of the same class.

### Expectations, written before the audit

1. All 9 crocoite spectra pass (3 near-infrared with the bend gate, 6 visible without it).
2. Of the 663 spectra of minerals without chromium that 0.5.0 flags, fewer than 100 pass.
   Most 0.5.0 flags are small 840 cm⁻¹ bands on minerals with a stronger band elsewhere in
   200-1100 cm⁻¹, which the dominance gate removes.
3. The survivors are mostly arsenates and vanadates whose own strongest band sits at
   830-850 cm⁻¹. Under near-infrared lasers, the bend gate removes some of them but not all,
   because AsO4 and VO4 also have bending bands at 300-450 cm⁻¹.
4. For filler alone (fraction 0), grain-mode flags are at or near zero. At fractions of 0.5
   and above, grain mode flags most mixtures.

If expectation 1 fails, grain mode is not released as it stands. Any other failure is
reported as it comes out.

## Limits

- Grain mode is for particles that are mostly pigment. On ground powder it rejects true
  lead chromate whenever another mineral band is stronger, by design.
- Chrome yellow pigments are often solid solutions with lead sulfate (a band near 980 cm⁻¹),
  and chrome orange is basic lead chromate. Neither is in the RRUFF crocoite set. A strong
  sulfate band could fail the dominance gate. Real pigment spectra are needed to check this.
- The rolling-ball baseline under-reads a band on a steep fluorescence slope. The dominance
  gate is therefore most reliable on spectra with a modest background.
- RRUFF spectra are of minerals, not of spice particles. A real validation needs spectra of
  picked grains, paired with laboratory lead and chromium results.
- A grain-mode positive is still a screening result. Confirm by a laboratory method (XRF,
  ICP-MS or SEM-EDS for lead and chromium).

## Audit

Pending (queued 2026-10-15). Results will be added here.

Made by MV2 of Munim, Inc. with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
