#!/usr/bin/env python3
"""spice-screen: screen a Raman spectrum of a spice for known adulterants.

Checks a measured Raman (or SERS) spectrum for the published marker bands of
lead chromate, metanil yellow, Sudan I and rhodamine B, after removing the
fluorescence background around each band. It is a screen, not a test: a
positive must be confirmed by a laboratory method (ICP-MS or XRF for lead and
chromium, HPLC for dyes), and "not-detected" only means "below what this
screen can see".

Input is a two-column text file: Raman shift (cm-1), intensity. Commas,
semicolons (with decimal commas), tabs or spaces; header and # lines are
skipped. Works with any instrument that can export its spectrum.

Standard library only. Python 3.8+.

Usage:
    python spice_screen.py spectrum.csv                  # normal Raman, text report
    python spice_screen.py spectrum.csv --mode sers --json
    python spice_screen.py spectrum.csv --exit-code      # exit 1 on a positive
    python spice_screen.py --list                        # marker library with sources
    python spice_screen.py --demo                        # synthetic example

Made by MV2 of Munim, Inc. with AI agents working in his name. MIT licence.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

__version__ = "0.2.0"

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
        "bands": [840.0],
        "primary": 840.0,
        "min_bands": 1,
        "tolerance": 8.0,
        "reported_limit": "about 0.5-0.6% w/w lead chromate in turmeric powder (FT-Raman)",
        "sources": [
            "Erasmus SW, van Hasselt L, Ebbinge LM, van Ruth SM. Real or fake yellow in the "
            "vibrant colour craze: rapid detection of lead chromate in turmeric. Food Control "
            "(2021) 107714. doi:10.1016/j.foodcont.2020.107714",
        ],
        "note": (
            "Turmeric and curcumin show no intense band at 840 cm-1. In ground powder, "
            "field levels can sit below this limit; the pigment is applied to whole dried "
            "roots during polishing (Forsyth et al., Environ Res 2019, "
            "doi:10.1016/j.envres.2019.108722), so measure root surfaces where possible."
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
]

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


def screen_spectrum(x, y, mode="raman", snr_min=5.0, library=None):
    """Screen one spectrum. Returns a JSON-ready report."""
    if len(x) != len(y) or len(x) < 15:
        raise ValueError("need at least 15 points with matching x and y")
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
    return {
        "tool": "spice-screen",
        "version": __version__,
        "mode": mode,
        "snr_threshold": snr_min,
        "range_cm1": [min(x), max(x)],
        "points": len(x),
        "results": results,
        "summary": summary,
        "disclaimer": DISCLAIMER,
    }


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


def format_report(report):
    lines = [
        "spice-screen %s  mode=%s  range %.0f-%.0f cm-1  %d points  SNR >= %g"
        % (report["version"], report["mode"], report["range_cm1"][0], report["range_cm1"][1],
           report["points"], report["snr_threshold"])
    ]
    for r in report["results"]:
        bands = "  ".join(
            "%.0f:%s" % (b["center"], ("SNR %.1f" % b["snr"]) if b["covered"] else "n/a")
            for b in r["bands"]
        )
        lines.append("  %-24s %-16s %s" % (r["id"], r["verdict"].upper(), bands))
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Screen a Raman spectrum of a spice for known adulterants.")
    ap.add_argument("spectrum", nargs="?", help="two-column file: Raman shift (cm-1), intensity")
    ap.add_argument("--mode", choices=("raman", "sers"), default="raman",
                    help="normal Raman (default) or SERS markers")
    ap.add_argument("--snr", type=float, default=5.0, help="peak signal-to-noise needed (default 5)")
    ap.add_argument("--library", help="JSON file with your own marker list (same fields as --list)")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
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

    if args.demo:
        x, y = synthetic_spectrum(TURMERIC_LIKE + ((840.0, 40.0),))
    elif args.spectrum:
        try:
            x, y = read_spectrum(args.spectrum)
        except (OSError, ValueError) as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
    else:
        ap.print_usage(sys.stderr)
        return 2

    report = screen_spectrum(x, y, mode=args.mode, snr_min=args.snr, library=library)
    print(json.dumps(report, indent=2) if args.json else format_report(report))
    if args.exit_code and any(r["verdict"] == "screen-positive" for r in report["results"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
