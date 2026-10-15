#!/usr/bin/env python3
"""spice-screen: screen a Raman spectrum of a spice for known adulterants.

Checks a measured Raman (or SERS) spectrum for the published marker bands of
lead chromate, metanil yellow, Sudan I, rhodamine B and auramine O, after
removing the fluorescence background around each band. It is a screen, not a
test: a positive must be confirmed by a laboratory method (ICP-MS or XRF for
lead and chromium, HPLC for dyes), and "not-detected" only means "below what
this screen can see".

Input is a two-column text file: Raman shift (cm-1), intensity. Commas,
semicolons (with decimal commas), tabs or spaces; header and # lines are
skipped. Works with any instrument that can export its spectrum.

Standard library only. Python 3.8+.

Usage:
    python spice_screen.py spectrum.csv                  # normal Raman, text report
    python spice_screen.py spectrum.csv --mode sers --json
    python spice_screen.py spectrum.csv --exit-code      # exit 1 on a positive
    python spice_screen.py "batch/*.csv" --csv           # one CSV row per spectrum
    python spice_screen.py --calibrate polystyrene.csv   # check the shift axis
    python spice_screen.py spectrum.csv --calibrate polystyrene.csv
    python spice_screen.py spectrum.csv --noise diff     # raw, unsmoothed spectra (see local_noise)
    python spice_screen.py grain.csv --grain --laser 808 # a picked yellow particle (see grain_check)
    python spice_screen.py --list                        # marker library with sources
    python spice_screen.py --demo                        # synthetic example

Made by MV2 of Munim, Inc. with AI agents working in his name. Apache-2.0 licence.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import sys
from collections import deque

__version__ = "0.6.0.dev0"

# Half-width (cm-1) of the local window used for baseline and noise around a band.
WINDOW = 60.0

# How check_band() estimates the noise a band must stand above; see local_noise().
# "lag" is the default from 0.5.0: on the RRUFF mineral library it kept every
# crocoite spectrum and flagged about a third as many minerals without chromium
# as "diff" did (docs/rruff-noise-rules.md).
NOISE = "lag"
NOISE_MODES = ("diff", "scatter", "lag")
# Lag (cm-1) for the "lag" noise estimate: longer than the smoothing that
# instrument software applies, shorter than a Raman band.
LAG_CM1 = 4.0

# Grain mode (see grain_check). Thresholds were fixed and published before the
# RRUFF audit that tests them (docs/grain-mode.md); change them only with a new audit.
GRAIN = {
    "stretch_left": (780.0, 815.0),    # side windows for the local line under the 840 band
    "stretch_right": (865.0, 900.0),
    "apex_search": (790.0, 890.0),     # the strongest point here must lie in apex_range
    "apex_range": (830.0, 850.0),
    "fingerprint": (200.0, 1100.0),    # the 840 band must dominate this region
    "dominance_min": 0.5,
    "half_width": 60.0,                # rolling-ball half-width for the fingerprint
    "bend_left": (260.0, 315.0),       # side windows for the local line under the bends
    "bend_right": (415.0, 470.0),
    "bend_range": (320.0, 410.0),
    "bend_ratio_min": 0.15,
    "bend_laser_min_nm": 700.0,        # the bend gate applies from this laser wavelength up
}

DISCLAIMER = (
    "Screening result only. A positive must be confirmed by a laboratory method "
    "(ICP-MS or XRF for lead and chromium, HPLC for dyes) before anyone acts on it. "
    "'not-detected' means below what this screen can see at the reported limits; "
    "it does not mean the sample is safe."
)

# Marker bands taken from the cited sources. Band positions shift a few cm-1
# between instruments and, for SERS, between substrates; `tolerance` allows for it.
LIBRARY = [
    {
        "id": "lead_chromate",
        "name": "Lead chromate (PbCrO4)",
        "mode": "raman",
        "matrices": ["turmeric", "cinnamon", "other yellow or orange spices"],
        "bands": [840.0, 825.0, 856.0],
        "primary": 840.0,
        "min_bands": 1,
        "tolerance": 8.0,
        "reported_limit": "about 0.5-0.6% w/w lead chromate in turmeric powder (FT-Raman)",
        "sources": [
            "Erasmus SW, van Hasselt L, Ebbinge LM, van Ruth SM. Real or fake yellow in the "
            "vibrant colour craze: rapid detection of lead chromate in turmeric. Food Control "
            "(2021) 107714. doi:10.1016/j.foodcont.2020.107714",
            "Frost RL. Raman microscopy of selected chromate minerals. J Raman Spectrosc "
            "35(2):153-158 (2004). doi:10.1002/jrs.1121 (crocoite, PbCrO4: CrO4 stretching "
            "bands at 856, 841 and 825 cm-1; 841 is the symmetric stretch)",
        ],
        "note": (
            "Turmeric and curcumin show no intense band at 840 cm-1. 825 and 856 cm-1 are the "
            "weaker bands of the chromate triplet; they are reported for confirmation only, "
            "and 840 alone still flags, because on handheld instruments the three bands can "
            "merge into one. In ground powder, field levels can sit below this limit; the "
            "pigment is applied to whole dried roots during polishing (Forsyth et al., "
            "Environ Res 2019, doi:10.1016/j.envres.2019.108722), so measure root surfaces "
            "where possible."
        ),
    },
    {
        "id": "metanil_yellow_raman",
        "name": "Metanil yellow (normal Raman)",
        "mode": "raman",
        "matrices": ["turmeric"],
        "bands": [1406.0, 997.0, 1147.0],
        "primary": 1406.0,
        "min_bands": 2,
        "tolerance": 8.0,
        "reported_limit": "about 1% w/w in turmeric powder (FT-Raman)",
        "sources": [
            "Dhakal S, Chao K, Schmidt W, Qin J, Kim M, Chan D. Evaluation of turmeric powder "
            "adulterated with metanil yellow using FT-Raman and FT-IR spectroscopy. Foods "
            "5(2):36 (2016). doi:10.3390/foods5020036",
        ],
        "note": "The three bands were chosen by the authors because they do not overlap turmeric bands.",
    },
    {
        "id": "metanil_yellow_sers",
        "name": "Metanil yellow (SERS, gold nanoparticles)",
        "mode": "sers",
        "matrices": ["turmeric (dilute-HCl extract)"],
        "bands": [1383.0, 504.0, 1176.0, 1588.0],
        "primary": 1383.0,
        "min_bands": 3,
        "tolerance": 8.0,
        "reported_limit": "0.1 mg/g (100 ug/g) in turmeric",
        "sources": [
            "Metrohm application note AN-RS-019, SERS detection of metanil yellow in turmeric. "
            "https://www.metrohm.com/en/applications/application-notes/raman-anram/an-rs-019.html",
        ],
        "note": "Extract 100 mg in 1 mL 0.5 M HCl; mix extract with Au colloid and NaCl, as in the note.",
    },
    {
        "id": "sudan_i_sers",
        "name": "Sudan I (SERS)",
        "mode": "sers",
        "matrices": ["paprika", "chili powder", "chili sauce or oil"],
        "bands": [721.0, 1226.0],
        "primary": 721.0,
        "min_bands": 2,
        "tolerance": 8.0,
        "reported_limit": "about 1 ppm after thin-layer separation",
        "sources": [
            "Determination of Sudan I in paprika powder by molecularly imprinted "
            "polymers-thin layer chromatography-surface enhanced Raman spectroscopic "
            "biosensor. Talanta (2015). PubMed 26078169 (721 cm-1 band)",
            "Ultra-sensitive lab-on-a-chip detection of Sudan I in food using "
            "plasmonics-enhanced diatomaceous thin film. PubMed 29056826 (1226 cm-1 band)",
        ],
        "note": "The two bands come from different SERS substrates; one band alone is reported as inconclusive.",
    },
    {
        "id": "rhodamine_b_sers",
        "name": "Rhodamine B (SERS, silver)",
        "mode": "sers",
        "matrices": ["chili powder", "chili sauce", "paprika"],
        "bands": [1645.0, 1360.0, 1509.0, 620.0],
        "primary": 1645.0,
        "min_bands": 3,
        "tolerance": 8.0,
        "reported_limit": "about 1 ug/g (10^-6 g/g) in chili powder (Ag SERS substrate)",
        "sources": [
            "Nguyen TNT et al. SERS substrates based on a ZnO porous membrane decorated with "
            "silver nanoparticles for detecting low concentrations of Rhodamine B. RSC Advances "
            "15(48):40846-40854 (2025). doi:10.1039/d5ra06188a (bands 620, 1360, 1509, 1645 cm-1; "
            "1645 strongest)",
            "Magnetic-responsive sensors based on polydopamine macromolecules for highly "
            "sensitive detection of trace food colorant residues. Int J Biol Macromol (2024). "
            "doi:10.1016/j.ijbiomac.2024.135609 (rhodamine B in chili powder, 10^-6 g/g)",
        ],
        "note": (
            "Rhodamine B is a non-food xanthene dye used to redden chili products. The four "
            "bands are the strongest of the eight SERS bands reported by Nguyen et al."
        ),
    },
    {
        "id": "auramine_o_sers",
        "name": "Auramine O (SERS, silver)",
        "mode": "sers",
        "matrices": ["turmeric", "curry powder", "saffron"],
        "bands": [778.0, 551.0, 649.0, 1189.0],
        "primary": 778.0,
        "min_bands": 3,
        "tolerance": 8.0,
        "reported_limit": (
            "dyeing solution down to 0.003 mg/mL (Ag SERS; a limit for the dye bath, not the "
            "herb); about 1 ug/g in curry powder after extraction (Au SERS, Metrohm)"
        ),
        "sources": [
            "Rapid Indentification of Auramine O Dyeing Adulteration in Dendrobium officinale, "
            "Saffron and Curcuma by SERS Raman Spectroscopy Combined with SSA-BP Neural Networks "
            "Model. Foods 12(22):4124 (2023). doi:10.3390/foods12224124 (bands 551, 649, 778, "
            "1189, 1598 cm-1; 778 chosen as the characteristic band)",
            "Metrohm application note AN-RS-020, trace detection of auramine O in curry powder. "
            "https://www.metrohm.com/en/applications/application-notes/raman-anram/an-rs-020.html "
            "(extraction; 1 ug/g)",
        ],
        "note": (
            "Auramine O is a yellow industrial dye. The 1598 cm-1 band is left out because "
            "curcumin's strong bands near 1600 cm-1 overlap it. Its SERS bands shift with "
            "solvent and pH (Metrohm), so check a reference on your substrate first."
        ),
    },
]

# Polystyrene bands (cm-1) for checking the Raman shift axis. Measure a
# polystyrene reference on the same instrument, the same day.
POLYSTYRENE = {
    "reference": "polystyrene",
    "bands": [620.9, 1001.4, 1602.3, 3054.3],
    "tolerance_cm1": 1.5,
    "sources": [
        "ASTM E1840, Standard Guide for Raman Shift Standards for Spectrometer Calibration; "
        "the four bands as quoted in Appl Spectrosc (2025), doi:10.1177/00037028251330654",
        "Tolerance +/-1.5 cm-1: European Pharmacopoeia, as applied to 26 Raman systems in "
        "Anal Sci (2019), doi:10.2116/analsci.18P501",
    ],
}

# Synthetic stand-ins for a turmeric matrix, used by --demo and the tests.
# Not reference data.
TURMERIC_LIKE = ((1601.0, 120.0), (1626.0, 70.0), (1250.0, 40.0))

# Synthetic stand-in for a picked lead chromate grain under a near-infrared
# laser: the chromate triplet and the bending bands at 400, 377, 357, 338 and
# 327 cm-1 (positions from Frost 2004). Used by --demo --grain and the tests.
# Not reference data.
CHROMATE_GRAIN_LIKE = ((840.0, 200.0), (825.0, 70.0), (856.0, 60.0), (400.0, 60.0), (377.0, 90.0),
                       (357.0, 120.0), (338.0, 80.0), (327.0, 50.0))


def _solve(a, b):
    """Solve a small dense linear system by Gaussian elimination."""
    n = len(b)
    m = [list(row) + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-300:
            raise ValueError("singular matrix in polynomial fit")
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            if f:
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    out = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = m[r][n] - sum(m[r][c] * out[c] for c in range(r + 1, n))
        out[r] = s / m[r][r]
    return out


def polyfit(x, y, deg):
    """Least-squares polynomial fit of degree `deg`. Returns a callable p(x)."""
    if len(x) <= deg:
        raise ValueError("need more points than the polynomial degree")
    lo, hi = min(x), max(x)
    mid = (hi + lo) / 2.0
    half = (hi - lo) / 2.0 or 1.0
    k = deg + 1
    a = [[0.0] * k for _ in range(k)]
    b = [0.0] * k
    for xi, yi in zip(x, y):
        u = (xi - mid) / half
        powers = [u ** j for j in range(2 * k - 1)]
        for i in range(k):
            b[i] += yi * powers[i]
            for j in range(k):
                a[i][j] += powers[i + j]
    coef = _solve(a, b)

    def p(v):
        t = (v - mid) / half
        return sum(c * t ** j for j, c in enumerate(coef))

    return p


def modpoly_baseline(x, y, deg=2, max_iter=500, tol=1e-7):
    """Fluorescence baseline by modified polynomial fitting (Lieber and
    Mahadevan-Jansen, Appl. Spectrosc. 57:1363, 2003): fit, clip the data to
    the fit, repeat until the fit stops moving.

    In a narrow window with a strong band in the middle, the fit bows: it
    sits a little above the true background under the band and a little
    below it at the window edges. check_band() measures peaks against the
    median of the corrected points away from the band, which absorbs most of
    that offset."""
    work = list(y)
    base = work
    for _ in range(max_iter):
        p = polyfit(x, work, deg)
        base = [p(v) for v in x]
        new = [min(w, bv) for w, bv in zip(work, base)]
        change = math.sqrt(sum((n - w) ** 2 for n, w in zip(new, work)))
        norm = math.sqrt(sum(w * w for w in work)) or 1.0
        work = new
        if change / norm < tol:
            break
    return base


def _median(values):
    s = sorted(values)
    n = len(s)
    if not n:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def noise_sigma(values, lag=1):
    """Robust noise estimate from differences between points `lag` apart
    (MAD), so slow background and isolated peaks barely affect it."""
    lag = max(1, int(lag))
    d = [b - a for a, b in zip(values, values[lag:])]
    if len(d) < 2:
        return 0.0
    med = _median(d)
    mad = _median([abs(v - med) for v in d])
    return 1.4826 * mad / math.sqrt(2.0)


def robust_scatter(values):
    """Robust spread of `values` (MAD scaled to a standard deviation)."""
    if len(values) < 2:
        return 0.0
    med = _median(values)
    return 1.4826 * _median([abs(v - med) for v in values])


def local_noise(xs, corr, outside, mode=None):
    """Noise a band must stand above, from a baseline-corrected window.

    "diff" (the default up to 0.4.0): spread of point-to-point differences.
    Software smoothing shrinks it, so on smoothed spectra small ripples pass
    as peaks. Use it for raw, unsmoothed spectra.
    "scatter": the larger of that and the spread of the corrected points away
    from the band, so a band must also stand out from the window's own texture.
    "lag" (the default from 0.5.0): the larger of that and the spread of
    differences between points LAG_CM1 apart, away from the band, which
    smoothing shorter than LAG_CM1 does not shrink."""
    mode = NOISE if mode is None else mode
    if mode not in NOISE_MODES:
        raise ValueError("noise mode must be one of: %s" % ", ".join(NOISE_MODES))
    sigma = noise_sigma(corr)
    if mode == "scatter":
        sigma = max(sigma, robust_scatter(outside))
    elif mode == "lag":
        step = (xs[-1] - xs[0]) / (len(xs) - 1) if len(xs) > 1 else 0.0
        lag = int(round(LAG_CM1 / step)) if step > 0 else 1
        sigma = max(sigma, noise_sigma(outside, lag))
    return sigma


def check_band(x, y, center, tol, snr_min, window=WINDOW, noise=None):
    """Look for a peak at `center` +/- `tol` above the local baseline."""
    res = {"center": center, "covered": False, "detected": False, "snr": 0.0, "position": None}
    idx = [i for i, v in enumerate(x) if abs(v - center) <= window]
    if len(idx) < 15:
        return res
    if x[idx[0]] > center - window / 2.0 or x[idx[-1]] < center + window / 2.0:
        return res
    xs = [x[i] for i in idx]
    ys = [y[i] for i in idx]
    base = modpoly_baseline(xs, ys)
    corr = [a - b for a, b in zip(ys, base)]
    outside = [c for v, c in zip(xs, corr) if abs(v - center) > 2 * tol]
    inside = [(c, v) for v, c in zip(xs, corr) if abs(v - center) <= tol]
    if len(outside) < 8 or not inside:
        return res
    res["covered"] = True
    offset = _median(outside)
    floor = 1e-9 * max(abs(v) for v in ys) or 1e-12
    sigma = max(local_noise(xs, corr, outside, noise), floor)
    k = max(range(len(inside)), key=lambda i: inside[i][0])
    height = inside[k][0] - offset
    snr = height / sigma
    # A maximum on the edge of the search range is a neighbour's flank, not a peak.
    at_edge = len(inside) >= 3 and k in (0, len(inside) - 1)
    res["snr"] = round(snr, 2)
    res["position"] = inside[k][1]
    res["edge"] = at_edge
    res["detected"] = (not at_edge) and snr >= snr_min
    return res


def _sliding(x, y, half, sign):
    """Running maximum (sign 1) or minimum (sign -1) of y over the points
    within +/- `half` cm-1 of each point. x must be sorted."""
    out = []
    dq = deque()
    hi = 0
    n = len(x)
    for i in range(n):
        while hi < n and x[hi] <= x[i] + half:
            while dq and sign * y[dq[-1]] <= sign * y[hi]:
                dq.pop()
            dq.append(hi)
            hi += 1
        while x[dq[0]] < x[i] - half:
            dq.popleft()
        out.append(y[dq[0]])
    return out


def tophat(x, y, half):
    """Height of each point above a rolling-ball baseline (a morphological
    opening with a flat element +/- `half` cm-1 wide). Bands narrower than
    about 2 x half keep most of their height; slower background goes to zero."""
    opened = _sliding(x, _sliding(x, y, half, -1), half, 1)
    return [a - b for a, b in zip(y, opened)]


def _line_under(x, y, left, right):
    """(x0, y0, slope) of the line through the lowest point of each side
    window, or None if either window is empty."""
    lw = [(a, b) for a, b in zip(x, y) if left[0] <= a <= left[1]]
    rw = [(a, b) for a, b in zip(x, y) if right[0] <= a <= right[1]]
    if not lw or not rw:
        return None
    x0, y0 = min(lw, key=lambda p: p[1])
    x1, y1 = min(rw, key=lambda p: p[1])
    if x1 <= x0:
        return None
    return x0, y0, (y1 - y0) / (x1 - x0)


def _above_line(x, y, lo, hi, line):
    """[(height above the line, shift)] for lo <= x <= hi."""
    x0, y0, k = line
    return [(b - (y0 + k * (a - x0)), a) for a, b in zip(x, y) if lo <= a <= hi]


def grain_check(x, y, snr_min=5.0, noise=None, laser_nm=None, band=None, params=None):
    """Grain mode: does the 840 cm-1 band look like lead chromate pigment's
    whole pattern? Meant for picked yellow-orange particles, which should be
    mostly pigment, so a band near 840 cm-1 is not enough. Gates:

    - apex: above a line through the lowest points of 780-815 and 865-900
      cm-1, the strongest point of 790-890 cm-1 lies at 830-850 cm-1, so the
      band is not the flank of a stronger neighbour (vanadates near 827 cm-1);
    - dominance: on a rolling-ball baseline, the 840 band is at least half
      the strongest band in 200-1100 cm-1, the mineral fingerprint. Curcumin's
      strong bands lie above 1100 cm-1, so a turmeric coating does not count;
    - bend: chromate's bending bands (320-410 cm-1, above a line through the
      lowest points of 260-315 and 415-470 cm-1) reach 15% of the 840 band.
      Required only for lasers of 700 nm or longer. Under green lasers the
      840 band is resonance-enhanced and the bends are weak: in the RRUFF
      crocoite spectra this ratio is 0.04-0.13 at 514/532 nm and 0.58-0.82 at
      780/785 nm (docs/data/band-shape). A spectrum without both side windows
      skips the gate, and the result says so.

    `band` is check_band()'s result at 840 cm-1, if already computed.
    Returns a dict; its verdict is screen-positive only if every gate passes."""
    g = GRAIN if params is None else params
    if band is None:
        band = check_band(x, y, 840.0, 8.0, snr_min, noise=noise)
    res = {"verdict": "not-covered", "laser_nm": laser_nm, "apex": None, "apex_ok": None,
           "dominance": None, "dominance_ok": None, "bend_ratio": None, "bend_ok": None,
           "bend_required": bool(laser_nm and laser_nm >= g["bend_laser_min_nm"]),
           "failed": [], "skipped": []}
    if not band["covered"]:
        return res
    if not band["detected"]:
        res["verdict"] = "not-detected"
        return res
    line = _line_under(x, y, g["stretch_left"], g["stretch_right"])
    if line is None:
        return res
    stretch = _above_line(x, y, g["apex_search"][0], g["apex_search"][1], line)
    apex_h, apex_x = max(stretch)
    near = [h for h, v in stretch if abs(v - 840.0) <= 8.0]
    h840 = max(near) if near else 0.0
    res["apex"] = round(apex_x, 2)
    res["apex_ok"] = g["apex_range"][0] <= apex_x <= g["apex_range"][1]

    half = g["half_width"]
    lo, hi = g["fingerprint"]
    idx = [i for i, v in enumerate(x) if lo - half <= v <= hi + half]
    xs = [x[i] for i in idx]
    th = tophat(xs, [y[i] for i in idx], half)
    finger = [t for v, t in zip(xs, th) if lo <= v <= hi]
    at840 = [t for v, t in zip(xs, th) if abs(v - 840.0) <= 8.0]
    top = max(finger) if finger else 0.0
    res["dominance"] = round(max(at840) / top, 4) if at840 and top > 0 else 0.0
    res["dominance_ok"] = res["dominance"] >= g["dominance_min"]

    bline = _line_under(x, y, g["bend_left"], g["bend_right"])
    if bline is not None and h840 > 0:
        bend = _above_line(x, y, g["bend_range"][0], g["bend_range"][1], bline)
        if bend:
            res["bend_ratio"] = round(max(bend)[0] / h840, 4)
            res["bend_ok"] = res["bend_ratio"] >= g["bend_ratio_min"]

    if not res["apex_ok"]:
        res["failed"].append("apex")
    if not res["dominance_ok"]:
        res["failed"].append("dominance")
    if res["bend_required"]:
        if res["bend_ok"] is None:
            res["skipped"].append("bend (spectrum does not cover %g-%g cm-1)"
                                  % (g["bend_left"][0], g["bend_right"][1]))
        elif not res["bend_ok"]:
            res["failed"].append("bend")
    res["verdict"] = "inconclusive" if res["failed"] else "screen-positive"
    return res


def _vertex(x0, x1, x2, y0, y1, y2):
    """x of the top of the parabola through three points (x1 if it opens upward)."""
    d = (x0 - x1) * (x0 - x2) * (x1 - x2)
    a = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / d
    b = (x2 * x2 * (y0 - y1) + x1 * x1 * (y2 - y0) + x0 * x0 * (y1 - y2)) / d
    if a >= 0:
        return x1
    return min(max(-b / (2.0 * a), x0), x2)


def locate_peak(x, y, center, search, snr_min=10.0, window=WINDOW):
    """Position (cm-1) of the strongest peak within `search` of `center`,
    refined by a parabola through its top three points. None if the range is
    not covered or no clear peak stands there."""
    idx = [i for i, v in enumerate(x) if abs(v - center) <= window]
    if len(idx) < 15 or x[idx[0]] > center - search or x[idx[-1]] < center + search:
        return None
    xs = [x[i] for i in idx]
    ys = [y[i] for i in idx]
    base = modpoly_baseline(xs, ys)
    corr = [a - b for a, b in zip(ys, base)]
    near = [i for i, v in enumerate(xs) if abs(v - center) <= search]
    outside = [c for v, c in zip(xs, corr) if abs(v - center) > search]
    if len(near) < 3 or len(outside) < 8:
        return None
    k = max(near, key=lambda i: corr[i])
    if k in (near[0], near[-1]):
        return None
    floor = 1e-9 * max(abs(v) for v in ys) or 1e-12
    sigma = max(noise_sigma(corr), floor)
    if (corr[k] - _median(outside)) / sigma < snr_min:
        return None
    return _vertex(xs[k - 1], xs[k], xs[k + 1], corr[k - 1], corr[k], corr[k + 1])


def calibrate(x, y, reference=POLYSTYRENE, search=12.0, snr_min=10.0):
    """Compare a reference spectrum (polystyrene by default) with its known
    bands and return a linear correction: true shift = offset + slope * measured.
    With one band found, the correction is an offset only."""
    found = []
    for ref in reference["bands"]:
        pos = locate_peak(x, y, ref, search, snr_min)
        if pos is not None:
            found.append((pos, ref))
    if not found:
        raise ValueError("no %s band found within %g cm-1 of its reference position"
                         % (reference["reference"], search))
    if len(found) >= 2:
        mm = sum(p for p, _ in found) / len(found)
        mr = sum(r for _, r in found) / len(found)
        slope = (sum((p - mm) * (r - mr) for p, r in found)
                 / sum((p - mm) ** 2 for p, _ in found))
        offset = mr - slope * mm
    else:
        slope = 1.0
        offset = found[0][1] - found[0][0]
    if abs(slope - 1.0) > 0.02:
        raise ValueError("calibration slope %.4f is implausible; check the reference spectrum" % slope)
    worst = max(abs(p - r) for p, r in found)
    tol = float(reference["tolerance_cm1"])
    return {
        "reference": reference["reference"],
        "bands": [
            {"reference": r, "measured": round(p, 2), "error": round(p - r, 2),
             "corrected_error": round(offset + slope * p - r, 2)}
            for p, r in found
        ],
        "max_abs_error": round(worst, 2),
        "tolerance_cm1": tol,
        "within_tolerance": worst <= tol,
        "offset": offset,
        "slope": slope,
        "sources": list(reference["sources"]),
    }


def apply_calibration(x, calibration):
    """Correct a Raman shift axis with a calibrate() result."""
    return [calibration["offset"] + calibration["slope"] * v for v in x]


def screen_entry(x, y, entry, snr_min, noise=None):
    tol = float(entry.get("tolerance", 8.0))
    bands = [check_band(x, y, float(c), tol, snr_min, noise=noise) for c in entry["bands"]]
    primary = next(b for b in bands if b["center"] == float(entry["primary"]))
    detected = [b for b in bands if b["detected"]]
    if not primary["covered"]:
        verdict = "not-covered"
    elif primary["detected"] and len(detected) >= int(entry["min_bands"]):
        verdict = "screen-positive"
    elif detected:
        verdict = "inconclusive"
    else:
        verdict = "not-detected"
    return {
        "id": entry["id"],
        "name": entry["name"],
        "verdict": verdict,
        "bands": bands,
        "bands_detected": len(detected),
        "reported_limit": entry.get("reported_limit", ""),
        "sources": list(entry["sources"]),
        "note": entry.get("note", ""),
    }


def validate_library(library):
    """Raise ValueError if a library entry is malformed."""
    if not isinstance(library, list) or not library:
        raise ValueError("library must be a non-empty list")
    seen = set()
    for e in library:
        for key in ("id", "name", "mode", "bands", "primary", "min_bands", "sources"):
            if key not in e:
                raise ValueError("entry %r lacks %r" % (e.get("id"), key))
        if e["id"] in seen:
            raise ValueError("duplicate id %r" % e["id"])
        seen.add(e["id"])
        if e["mode"] not in ("raman", "sers"):
            raise ValueError("%s: mode must be raman or sers" % e["id"])
        bands = [float(b) for b in e["bands"]]
        if not bands or any(not 50.0 <= b <= 3500.0 for b in bands):
            raise ValueError("%s: bands must lie in 50-3500 cm-1" % e["id"])
        if float(e["primary"]) not in bands:
            raise ValueError("%s: primary band must be one of the bands" % e["id"])
        if not 1 <= int(e["min_bands"]) <= len(bands):
            raise ValueError("%s: min_bands out of range" % e["id"])
        if not e["sources"]:
            raise ValueError("%s: at least one source is required" % e["id"])
    return True


def overall_result(results):
    """The most serious verdict among the markers screened."""
    verdicts = [r["verdict"] for r in results]
    for level in ("screen-positive", "inconclusive", "not-detected"):
        if level in verdicts:
            return level
    return "not-covered"


def screen_spectrum(x, y, mode="raman", snr_min=5.0, library=None, calibration=None, noise=None,
                    grain=False, laser_nm=None):
    """Screen one spectrum. Returns a JSON-ready report. `calibration` is an
    optional calibrate() result; the shift axis is corrected with it first.
    `noise` picks the noise estimate (see local_noise); None means NOISE.
    With `grain`, a lead chromate positive must also pass grain_check(), at
    excitation wavelength `laser_nm` (nm, or None if unknown); if it does not,
    the verdict becomes inconclusive."""
    if len(x) != len(y) or len(x) < 15:
        raise ValueError("need at least 15 points with matching x and y")
    if calibration is not None:
        x = apply_calibration(x, calibration)
    lib = LIBRARY if library is None else library
    noise = NOISE if noise is None else noise
    results = [screen_entry(x, y, e, snr_min, noise) for e in lib if e["mode"] == mode]
    if grain:
        for r in results:
            if r["id"] != "lead_chromate":
                continue
            primary = next((b for b in r["bands"] if b["center"] == 840.0), None)
            g = grain_check(x, y, snr_min, noise, laser_nm, band=primary)
            r["grain"] = g
            if r["verdict"] == "screen-positive" and g["verdict"] != "screen-positive":
                r["verdict"] = "inconclusive"
    positives = [r["name"] for r in results if r["verdict"] == "screen-positive"]
    partial = [r["name"] for r in results if r["verdict"] == "inconclusive"]
    if positives:
        summary = "screen-positive: %s. Confirm by laboratory test." % "; ".join(positives)
    elif partial:
        summary = "inconclusive: partial match for %s. Re-measure or test in a laboratory." % "; ".join(partial)
    else:
        summary = "no listed adulterant detected at this screen's limits."
    report = {
        "tool": "spice-screen",
        "version": __version__,
        "mode": mode,
        "snr_threshold": snr_min,
        "noise": noise,
        "range_cm1": [min(x), max(x)],
        "points": len(x),
        "result": overall_result(results),
        "results": results,
        "summary": summary,
        "disclaimer": DISCLAIMER,
    }
    if grain:
        report["grain"] = True
        report["laser_nm"] = laser_nm
    if calibration is not None:
        report["calibration"] = calibration
    return report


def _fields(line):
    if ";" in line:
        return [p.strip().replace(",", ".") for p in line.split(";")]
    if "," in line:
        return [p.strip() for p in line.split(",")]
    return line.split()


def parse_spectrum(text):
    """Parse two-column text into sorted (shift, intensity) lists."""
    pts = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        nums = []
        for f in _fields(line):
            try:
                nums.append(float(f))
            except ValueError:
                break
        if len(nums) >= 2 and math.isfinite(nums[0]) and math.isfinite(nums[1]):
            pts.append((nums[0], nums[1]))
    if len(pts) < 15:
        raise ValueError("need at least 15 numeric (Raman shift, intensity) rows")
    pts.sort()
    return [p[0] for p in pts], [p[1] for p in pts]


def read_spectrum(path):
    with open(path, encoding="utf-8-sig") as fh:
        return parse_spectrum(fh.read())


def expand_paths(args):
    """Expand wildcard arguments ourselves, since Windows shells do not."""
    out = []
    for a in args:
        if any(ch in a for ch in "*?["):
            hits = sorted(glob.glob(a))
            out.extend(hits if hits else [a])
        else:
            out.append(a)
    return out


def synthetic_spectrum(peaks=(), start=200.0, stop=1800.0, step=2.0, noise=1.0, seed=7, hwhm=5.0):
    """Curved fluorescence-like background + Lorentzian peaks + noise.
    For demos and tests only; not reference data."""
    n = int(round((stop - start) / step)) + 1
    x = [start + i * step for i in range(n)]
    state = seed & 0xFFFFFFFF
    y = []
    for v in x:
        t = v - start
        val = 3000.0 + 1.2 * t - 0.0004 * t * t
        for center, height in peaks:
            val += height / (1.0 + ((v - center) / hwhm) ** 2)
        g = 0.0
        for _ in range(12):
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            g += state / 4294967296.0
        y.append(val + noise * (g - 6.0))
    return x, y


def format_calibration(cal):
    lines = ["Raman shift check against %s (tolerance +/-%g cm-1)" % (cal["reference"], cal["tolerance_cm1"])]
    for b in cal["bands"]:
        lines.append("  %7.1f cm-1: measured %.1f, error %+.1f, after correction %+.1f"
                     % (b["reference"], b["measured"], b["error"], b["corrected_error"]))
    if cal["within_tolerance"]:
        lines.append("result: within tolerance")
    else:
        lines.append("result: OUTSIDE tolerance; screen with --calibrate to correct the shift axis")
    lines.append("correction: shift = %.3f + %.6f x measured" % (cal["offset"], cal["slope"]))
    return "\n".join(lines)


def _bend_text(g):
    if g["bend_ratio"] is None:
        return "not covered" + (", gate skipped" if g["bend_required"] else "")
    state = "ok" if g["bend_ok"] else "low"
    if not g["bend_required"]:
        state += ", not required below %g nm" % GRAIN["bend_laser_min_nm"]
    return "%.2f (%s)" % (g["bend_ratio"], state)


def format_grain(g):
    """One line describing a grain_check() result."""
    if g["verdict"] in ("not-covered", "not-detected"):
        return "    grain mode: no 840 cm-1 band to check"
    return ("    grain mode: apex %.0f cm-1 (%s), dominance %.2f (%s), bend %s -> %s"
            % (g["apex"], "ok" if g["apex_ok"] else "off", g["dominance"],
               "ok" if g["dominance_ok"] else "low", _bend_text(g), g["verdict"].upper()))


def format_report(report):
    head = ("spice-screen %s  mode=%s  range %.0f-%.0f cm-1  %d points  SNR >= %g  noise=%s"
            % (report["version"], report["mode"], report["range_cm1"][0], report["range_cm1"][1],
               report["points"], report["snr_threshold"], report.get("noise", NOISE)))
    if report.get("grain"):
        laser = report.get("laser_nm")
        head += "  grain mode, laser %s" % (("%g nm" % laser) if laser else "unknown")
    lines = [head]
    cal = report.get("calibration")
    if cal:
        lines.append("  shift axis corrected against %s: largest error was %.1f cm-1 over %d bands (%s +/-%g)"
                     % (cal["reference"], cal["max_abs_error"], len(cal["bands"]),
                        "within" if cal["within_tolerance"] else "outside", cal["tolerance_cm1"]))
    for r in report["results"]:
        bands = "  ".join(
            "%.0f:%s" % (b["center"], ("SNR %.1f" % b["snr"]) if b["covered"] else "n/a")
            for b in r["bands"]
        )
        lines.append("  %-24s %-16s %d/%d bands  %s"
                     % (r["id"], r["verdict"].upper(), r["bands_detected"], len(r["bands"]), bands))
        if "grain" in r:
            lines.append(format_grain(r["grain"]))
    lines.append(report["summary"])
    lines.append(report["disclaimer"])
    return "\n".join(lines)


def format_library(library):
    out = []
    for e in library:
        out.append("%s [%s] bands %s cm-1 (need %d; primary %.0f)"
                   % (e["name"], e["mode"], ", ".join("%.0f" % b for b in e["bands"]),
                      e["min_bands"], e["primary"]))
        out.append("  reported limit: %s" % e.get("reported_limit", "n/a"))
        for s in e["sources"]:
            out.append("  source: %s" % s)
    return "\n".join(out)


def write_csv(done, ids, stream):
    """One row per spectrum: file, overall result, then each marker's verdict."""
    w = csv.writer(stream, lineterminator="\n")
    w.writerow(["file", "result"] + ids)
    for path, report, error in done:
        if report is None:
            w.writerow([path, "error: %s" % error] + [""] * len(ids))
            continue
        v = {r["id"]: r["verdict"] for r in report["results"]}
        w.writerow([path, report["result"]] + [v.get(i, "") for i in ids])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Screen a Raman spectrum of a spice for known adulterants.")
    ap.add_argument("spectrum", nargs="*",
                    help="two-column files: Raman shift (cm-1), intensity; wildcards work")
    ap.add_argument("--mode", choices=("raman", "sers"), default="raman",
                    help="normal Raman (default) or SERS markers")
    ap.add_argument("--snr", type=float, default=5.0, help="peak signal-to-noise needed (default 5)")
    ap.add_argument("--noise", choices=NOISE_MODES, default=None,
                    help="noise estimate a band must stand above (default %s)" % NOISE)
    ap.add_argument("--grain", action="store_true",
                    help="grain mode, for a picked yellow-orange particle: a lead chromate positive must "
                         "also have the pigment's band shape (docs/grain-mode.md)")
    ap.add_argument("--laser", type=float, default=None, metavar="NM",
                    help="excitation wavelength in nm; with --grain, %g nm or more also requires "
                         "chromate's bending bands" % GRAIN["bend_laser_min_nm"])
    ap.add_argument("--library", help="JSON file with your own marker list (same fields as --list)")
    ap.add_argument("--calibrate", metavar="POLYSTYRENE",
                    help="polystyrene spectrum from the same instrument: check the shift axis "
                         "and correct the spectra with it")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--csv", action="store_true", help="print one CSV row per spectrum (for batches)")
    ap.add_argument("--exit-code", action="store_true", help="exit 1 if anything is screen-positive")
    ap.add_argument("--list", action="store_true", help="print the marker library and its sources")
    ap.add_argument("--demo", action="store_true", help="screen a synthetic turmeric spectrum with an 840 cm-1 band")
    args = ap.parse_args(argv)

    if args.grain and args.mode != "raman":
        print("error: --grain works with normal Raman spectra only", file=sys.stderr)
        return 2

    library = LIBRARY
    if args.library:
        try:
            with open(args.library, encoding="utf-8") as fh:
                library = json.load(fh)
            validate_library(library)
        except (OSError, ValueError) as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2

    if args.list:
        print(json.dumps(library, indent=2) if args.json else format_library(library))
        return 0

    cal = None
    if args.calibrate:
        try:
            cal = calibrate(*read_spectrum(args.calibrate))
        except (OSError, ValueError) as exc:
            print("error: calibration: %s" % exc, file=sys.stderr)
            return 2
        if not args.spectrum and not args.demo:
            print(json.dumps(cal, indent=2) if args.json else format_calibration(cal))
            return 0

    if args.demo:
        peaks = CHROMATE_GRAIN_LIKE if args.grain else TURMERIC_LIKE + ((840.0, 40.0),)
        x, y = synthetic_spectrum(peaks)
        report = screen_spectrum(x, y, mode=args.mode, snr_min=args.snr, library=library, calibration=cal,
                                 noise=args.noise, grain=args.grain, laser_nm=args.laser)
        print(json.dumps(report, indent=2) if args.json else format_report(report))
        if args.exit_code and report["result"] == "screen-positive":
            return 1
        return 0

    if not args.spectrum:
        ap.print_usage(sys.stderr)
        return 2

    paths = expand_paths(args.spectrum)
    done = []
    for path in paths:
        try:
            x, y = read_spectrum(path)
        except (OSError, ValueError) as exc:
            print("error: %s: %s" % (path, exc), file=sys.stderr)
            done.append((path, None, str(exc)))
            continue
        report = screen_spectrum(x, y, mode=args.mode, snr_min=args.snr, library=library, calibration=cal,
                                 noise=args.noise, grain=args.grain, laser_nm=args.laser)
        done.append((path, report, ""))

    if args.csv:
        write_csv(done, [e["id"] for e in library if e["mode"] == args.mode], sys.stdout)
    elif len(paths) == 1:
        if done[0][1] is not None:
            print(json.dumps(done[0][1], indent=2) if args.json else format_report(done[0][1]))
    elif args.json:
        out = [dict(report, file=path) if report is not None else {"file": path, "error": error}
               for path, report, error in done]
        print(json.dumps(out, indent=2))
    else:
        for path, report, error in done:
            print("== %s ==" % path)
            print(format_report(report) if report is not None else "error: %s" % error)

    if any(report is None for _, report, _ in done):
        return 2
    if args.exit_code and any(r is not None and r["result"] == "screen-positive" for _, r, _ in done):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
