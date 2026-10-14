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
    python spice_screen.py --list                        # marker library with sources
    python spice_screen.py --demo                        # synthetic example

Made by MV2 of Munim, Inc. with AI agents working in his name. MIT licence.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import sys

__version__ = "0.4.0"

# Half-width (cm-1) of the local window used for baseline and noise around a band.
WINDOW = 60.0

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


def noise_sigma(values):
    """Robust noise estimate from point-to-point differences (MAD), so slow
    background and isolated peaks barely affect it."""
    d = [b - a for a, b in zip(values, values[1:])]
    if len(d) < 2:
        return 0.0
    med = _median(d)
    mad = _median([abs(v - med) for v in d])
    return 1.4826 * mad / math.sqrt(2.0)


def check_band(x, y, center, tol, snr_min, window=WINDOW):
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
    sigma = max(noise_sigma(corr), floor)
    k = max(range(len(inside)), key=lambda i: inside[i][0])
    height = inside[k][0] - offset
    snr = height / sigma
    # A maximum on the edge of the search range is a neighbour's flank, not a peak.
    at_edge = len(inside) >= 3 and k in (0, len(inside) - 1)
    res["snr"] = round(snr, 2)
    res["position"] = inside[k][1]
    res["detected"] = (not at_edge) and snr >= snr_min
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


def screen_entry(x, y, entry, snr_min):
    tol = float(entry.get("tolerance", 8.0))
    bands = [check_band(x, y, float(c), tol, snr_min) for c in entry["bands"]]
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


def screen_spectrum(x, y, mode="raman", snr_min=5.0, library=None, calibration=None):
    """Screen one spectrum. Returns a JSON-ready report. `calibration` is an
    optional calibrate() result; the shift axis is corrected with it first."""
    if len(x) != len(y) or len(x) < 15:
        raise ValueError("need at least 15 points with matching x and y")
    if calibration is not None:
        x = apply_calibration(x, calibration)
    lib = LIBRARY if library is None else library
    results = [screen_entry(x, y, e, snr_min) for e in lib if e["mode"] == mode]
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
        "range_cm1": [min(x), max(x)],
        "points": len(x),
        "result": overall_result(results),
        "results": results,
        "summary": summary,
        "disclaimer": DISCLAIMER,
    }
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


def format_report(report):
    lines = [
        "spice-screen %s  mode=%s  range %.0f-%.0f cm-1  %d points  SNR >= %g"
        % (report["version"], report["mode"], report["range_cm1"][0], report["range_cm1"][1],
           report["points"], report["snr_threshold"])
    ]
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
        x, y = synthetic_spectrum(TURMERIC_LIKE + ((840.0, 40.0),))
        report = screen_spectrum(x, y, mode=args.mode, snr_min=args.snr, library=library, calibration=cal)
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
        report = screen_spectrum(x, y, mode=args.mode, snr_min=args.snr, library=library, calibration=cal)
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
