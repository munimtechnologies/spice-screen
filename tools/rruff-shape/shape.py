#!/usr/bin/env python3
"""rruff-shape: can band shape tell real lead chromate from the minerals that
trip spice-screen's 840 cm-1 marker?

The 0.4.0 audit (docs/rruff-audit.md in spice-screen) found that 0.4.0 flags
all 9 RRUFF crocoite spectra but also 1,935 of 5,713 spectra of minerals
without chromium. A noise-rule fix is tested separately (rruff-rules). This
job asks a different question that does not depend on noise at all: does the
840 cm-1 band LOOK like crocoite's?

For every processed spectrum it measures, against local baselines:
- apex: is the strongest point in 840 +/- 8 cm-1 a real local maximum, or the
  flank of a neighbouring band (vanadates ~827, olivine ~824/856)?
- dominance: the 840 band's height over the strongest band in 780-900 cm-1
  (crocoite's symmetric stretch dominates that region);
- fwhm: the 840 band's full width at half height (smoothing humps are broad);
- bend: the strongest band in 320-410 cm-1 (crocoite's CrO4 bending bands,
  327/338/357/377/400 cm-1; Frost 2004) over the 840 band.

It then scores every combination of gates on these features, on top of the
released 0.4.0 verdicts (published per-file CSV), over the library and over
real crocoite mixed into real filler spectra at falling peak-height fractions.

RRUFF spectra are not redistributed; only per-file numbers are written.
RRUFF: Lafuente B, Downs RT, Yang H, Stone N. The power of databases: the RRUFF
project. In: Highlights in Mineralogical Crystallography, De Gruyter (2015) 1-30.
Made by MV2 of Munim, Inc. with AI agents working in his name. Apache-2.0.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import importlib.util
import io
import json
import multiprocessing as mp
import os
import random
import re
import sys
import time
import urllib.request
import zipfile
import zlib

RRUFF_URL = "https://www.rruff.net/zipped_data_files/raman/excellent_unoriented.zip"
AUDIT_CSV_URL = ("https://raw.githubusercontent.com/munimtechnologies/spice-screen/main/"
                 "docs/data/rruff-audit-v0.4.0.csv")
SPICE_URL = "https://raw.githubusercontent.com/munimtechnologies/spice-screen/v0.4.0/spice_screen.py"
USER_AGENT = "spice-screen RRUFF shape (MV2 of Munim, Inc.; munimversion2@gmail.com)"

CENTER, TOL = 840.0, 8.0
STRETCH = (780.0, 900.0)
BASE_LEFT, BASE_RIGHT = (780.0, 815.0), (865.0, 900.0)
BEND = (320.0, 410.0)
BEND_LEFT, BEND_RIGHT = (260.0, 315.0), (415.0, 470.0)
APEX_HALF = 4.0  # the apex must be the highest point within +/- this many cm-1
PEAK_HALF = 5.0  # a bending peak must be the highest point within +/- this many cm-1

APEX_GRID = (False, True)
DOM_GRID = (0.0, 0.5, 0.7, 0.9)
WIDTH_GRID = (0.0, 20.0, 30.0, 45.0)  # 0 = no width gate
BEND_GRID = (0.0, 0.05, 0.1, 0.2)
FRACTIONS = (0.0, 0.003, 0.01, 0.03, 0.1, 0.3)
MIX_NOISE = 0.003  # white noise, as a fraction of the filler's strongest band

FILLERS = {
    "calcite": "chalk, calcium carbonate", "aragonite": "calcium carbonate",
    "dolomite": "carbonate filler", "gypsum": "calcium sulfate", "talc": "talc",
    "kaolinite": "clay", "montmorillonite": "clay", "muscovite": "mica, soil",
    "quartz": "sand", "albite": "feldspar", "microcline": "feldspar", "orthoclase": "feldspar",
    "baryte": "barium sulfate", "barite": "barium sulfate", "rutile": "titanium dioxide",
    "anatase": "titanium dioxide (E171)", "halite": "salt", "fluorapatite": "phosphate",
    "hematite": "iron oxide, brick dust", "goethite": "ochre", "magnetite": "iron oxide",
}
LEAD_PIGMENTS = {
    "minium": "red lead Pb3O4", "litharge": "PbO", "massicot": "PbO",
    "cerussite": "lead carbonate (white lead)", "hydrocerussite": "basic lead carbonate (white lead)",
    "anglesite": "lead sulfate",
}

FEATURES = ("apex_pos", "apex_ok", "h840", "dominance", "fwhm", "bend_ratio", "bend_peaks")

_SPICE = None
_SPECTRA = {}


# ---- reading ----------------------------------------------------------------

def parse_meta(text):
    """RRUFF header lines look like '##NAMES=Crocoite'."""
    meta = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("##") and "=" in s:
            key, val = s[2:].split("=", 1)
            meta[key.strip().upper()] = val.strip()
    return meta


def parse_name(member):
    """Mineral, RRUFF ID and laser (nm) from a name like
    'Crocoite__R050080__Raman__532__0__unoriented__Raman_Data_Processed__1234.txt'."""
    stem = os.path.basename(member)
    if stem.lower().endswith(".txt"):
        stem = stem[:-4]
    parts = stem.split("__")
    mineral = parts[0] if parts else stem
    rid = next((p for p in parts if re.fullmatch(r"R\d{6}(-\d+)?", p)), "")
    laser = ""
    for p in parts[1:]:
        if re.fullmatch(r"\d{3,4}", p) and 300 <= int(p) <= 1100:
            laser = p
            break
    return mineral, rid, laser


def parse_spectrum(text):
    """Two numeric columns (shift, intensity), comma or whitespace separated;
    header and comment lines are skipped. Returns (x, y) sorted by shift."""
    pts = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = re.split(r"[,\s;]+", s)
        if len(parts) < 2:
            continue
        try:
            pts.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    if len(pts) < 10:
        raise ValueError("fewer than 10 data points")
    pts.sort()
    return [p[0] for p in pts], [p[1] for p in pts]


def has_element(chem, symbol):
    """True if the formula names this element (Cr, not Cr inside another symbol)."""
    return re.search(r"%s(?![a-z])" % re.escape(symbol), chem or "") is not None


def group_of(chem):
    """Coarse anion group, for reading the false-positive list."""
    for sym, name in (("Cr", "chromium-bearing"), ("V", "vanadium-bearing"), ("As", "arsenic-bearing"),
                      ("Mo", "molybdenum-bearing"), ("W", "tungsten-bearing"), ("Se", "selenium-bearing"),
                      ("P", "phosphorus-bearing"), ("Si", "silicate"), ("S", "sulfur-bearing"),
                      ("C", "carbon-bearing")):
        if has_element(chem, sym):
            return name
    return "other"


def kind_of(mineral, cr_bearing):
    """crocoite, other_cr, lead_pigment, filler or other (the last three have no Cr)."""
    key = mineral.lower()
    if key.startswith("crocoite"):
        return "crocoite"
    if cr_bearing:
        return "other_cr"
    if key in LEAD_PIGMENTS:
        return "lead_pigment"
    if key in FILLERS:
        return "filler"
    return "other"


# ---- band shape -------------------------------------------------------------

def baseline_line(x, y, left, right):
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


def corrected(x, y, lo, hi, line):
    """(shifts, heights above the line) for lo <= x <= hi."""
    x0, y0, k = line
    xs = [a for a in x if lo <= a <= hi]
    cs = [b - (y0 + k * (a - x0)) for a, b in zip(x, y) if lo <= a <= hi]
    return xs, cs


def _half_side(xs, cs, i, half, step):
    """Distance from xs[i] to where cs falls to `half`, walking by `step`;
    None if it never does inside the region."""
    j = i
    while 0 <= j + step < len(xs) and cs[j + step] > half:
        j += step
    if not 0 <= j + step < len(xs):
        return None
    c0, c1 = cs[j], cs[j + step]
    t = (c0 - half) / (c0 - c1) if c0 != c1 else 0.0
    return abs(xs[j] + t * (xs[j + step] - xs[j]) - xs[i])


def band_shape(x, y):
    """Shape features of the 840 cm-1 band (see the module docstring)."""
    out = {"covered": False, "apex_pos": None, "apex_ok": False, "h840": None, "dominance": None,
           "fwhm": None, "bend_ratio": None, "bend_peaks": None}
    if x[0] > CENTER - TOL or x[-1] < CENTER + TOL:
        return out
    line = baseline_line(x, y, BASE_LEFT, BASE_RIGHT)
    if line is None:
        return out
    xs, cs = corrected(x, y, STRETCH[0], STRETCH[1], line)
    near = [i for i, a in enumerate(xs) if abs(a - CENTER) <= TOL]
    if not near:
        return out
    out["covered"] = True
    i = max(near, key=lambda j: cs[j])
    h = cs[i]
    out["apex_pos"] = round(xs[i], 2)
    out["h840"] = h
    if h <= 0:
        return out
    around = [c for a, c in zip(xs, cs) if abs(a - xs[i]) <= APEX_HALF]
    out["apex_ok"] = cs[i] >= max(around)
    out["dominance"] = round(h / max(cs), 4)
    left = _half_side(xs, cs, i, h / 2.0, -1)
    right = _half_side(xs, cs, i, h / 2.0, 1)
    if left is not None and right is not None:
        out["fwhm"] = round(left + right, 2)
    bline = baseline_line(x, y, BEND_LEFT, BEND_RIGHT)
    if bline is not None:
        bx, bc = corrected(x, y, BEND[0], BEND[1], bline)
        if bc:
            out["bend_ratio"] = round(max(bc) / h, 4)
            out["bend_peaks"] = sum(
                1 for a, c in zip(bx, bc)
                if c >= 0.05 * h and c >= max(d for e, d in zip(bx, bc) if abs(e - a) <= PEAK_HALF))
    return out


# ---- rules ------------------------------------------------------------------

def rule_grid():
    return [(a, d, w, b) for a in APEX_GRID for d in DOM_GRID for w in WIDTH_GRID for b in BEND_GRID]


def rule_name(rule):
    a, d, w, b = rule
    parts = []
    if a:
        parts.append("apex")
    if d:
        parts.append("dom>=%g" % d)
    if w:
        parts.append("fwhm<=%g" % w)
    if b:
        parts.append("bend>=%g" % b)
    return "+".join(parts) or "none"


def passes(row, rule):
    """Does a covered band with these shape features pass every gate of `rule`?
    A feature that could not be measured fails its gate."""
    a, d, w, b = rule
    if not row.get("covered") or (row.get("h840") or 0.0) <= 0.0:
        return False
    if a and not row.get("apex_ok"):
        return False
    if d and (row.get("dominance") or 0.0) < d:
        return False
    if w and (row.get("fwhm") is None or row["fwhm"] > w):
        return False
    if b and (row.get("bend_ratio") is None or row["bend_ratio"] < b):
        return False
    return True


def base_positive(row):
    """The 0.4.0 verdict, when known; True when the audit CSV was unavailable."""
    v = row.get("v040")
    return True if v is None else v == "screen-positive"


def evaluate(rows):
    """One line per rule: what 0.4.0 + the gates flag in the library."""
    ok = [r for r in rows if not r.get("error") and r.get("covered") and base_positive(r)]
    kinds = ("crocoite", "other_cr", "lead_pigment", "filler", "other")
    n = {k: sum(r["kind"] == k for r in ok) for k in kinds}
    n_non_cr = n["lead_pigment"] + n["filler"] + n["other"]
    out = []
    for rule in rule_grid():
        kept = {k: 0 for k in kinds}
        for r in ok:
            if passes(r, rule):
                kept[r["kind"]] += 1
        non_cr = kept["lead_pigment"] + kept["filler"] + kept["other"]
        line = {"rule": rule_name(rule), "crocoite": kept["crocoite"], "crocoite_n": n["crocoite"],
                "other_cr": kept["other_cr"], "non_cr": non_cr, "non_cr_n": n_non_cr,
                "lead_pigment": kept["lead_pigment"], "filler": kept["filler"]}
        out.append(line)
    return out


def evaluate_mixtures(mrows):
    """One line per rule: detection (0.4.0 positive + gates) at each fraction."""
    out = []
    for rule in rule_grid():
        line = {"rule": rule_name(rule)}
        for f in FRACTIONS:
            sel = [m for m in mrows if m["fraction"] == f and not m.get("error")]
            hit = sum(1 for m in sel if base_positive(m) and passes(m, rule))
            line["f=%g" % f] = round(hit / len(sel), 4) if sel else None
        out.append(line)
    return out


def shortlist(lib, mixes, n=12, slack=0.05):
    """Rules that keep every crocoite spectrum and lose at most `slack` of the
    no-gate detection at f = 0.03 and 0.1, ranked by non-Cr flags left."""
    mix = {m["rule"]: m for m in mixes}
    base = mix.get("none", {})
    good = []
    for r in lib:
        if not r["crocoite_n"] or r["crocoite"] < r["crocoite_n"]:
            continue
        m = mix.get(r["rule"], {})
        if any((m.get(k) or 0.0) < (base.get(k) or 0.0) - slack for k in ("f=0.03", "f=0.1")):
            continue
        good.append(dict(r, **{k: v for k, v in m.items() if k != "rule"}))
    good.sort(key=lambda r: (r["non_cr"], -(r.get("f=0.01") or 0.0), -(r.get("f=0.003") or 0.0)))
    return good[:n]


def quantiles(values):
    v = sorted(x for x in values if x is not None)
    if not v:
        return None
    pick = lambda q: v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]  # noqa: E731
    return {"n": len(v), "min": v[0], "p10": pick(0.1), "median": pick(0.5), "p90": pick(0.9), "max": v[-1]}


def feature_table(rows):
    """Quantiles of each numeric feature among 0.4.0 positives, by class."""
    ok = [r for r in rows if not r.get("error") and r.get("covered") and base_positive(r)]
    classes = {
        "crocoite": lambda r: r["kind"] == "crocoite",
        "lead pigments": lambda r: r["kind"] == "lead_pigment",
        "fillers": lambda r: r["kind"] == "filler",
        "vanadium-bearing (no Cr)": lambda r: r["kind"] == "other" and r["group"] == "vanadium-bearing",
        "arsenic-bearing (no Cr)": lambda r: r["kind"] == "other" and r["group"] == "arsenic-bearing",
        "silicates (no Cr)": lambda r: r["kind"] == "other" and r["group"] == "silicate",
        "all other no-Cr": lambda r: r["kind"] == "other",
    }
    out = {}
    for name, test in classes.items():
        sel = [r for r in ok if test(r)]
        out[name] = {"n": len(sel), "apex_ok": sum(bool(r["apex_ok"]) for r in sel)}
        for f in ("dominance", "fwhm", "bend_ratio", "bend_peaks"):
            out[name][f] = quantiles([r.get(f) for r in sel])
    return out


# ---- data -------------------------------------------------------------------

def fetch(url, path, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(path + ".part", "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(path + ".part", path)
    return path


def find_archives(data_dir):
    hits = sorted(glob.glob(os.path.join(data_dir, "**", "*.zip"), recursive=True))
    if hits:
        return hits
    os.makedirs(data_dir, exist_ok=True)
    return [fetch(RRUFF_URL, os.path.join(data_dir, "excellent_unoriented.zip"), timeout=600)]


def iter_members(archives, limit=0):
    """Yield (member name, text) for processed spectra (all spectra if no
    file says 'Processed'), including zips nested one level deep."""
    count = 0
    for arc in archives:
        with zipfile.ZipFile(arc) as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            inner = [n for n in names if n.lower().endswith(".zip")]
            sources = [(zf, [n for n in names if n.lower().endswith(".txt")])]
            for n in inner:
                sub = zipfile.ZipFile(io.BytesIO(zf.read(n)))
                sources.append((sub, [m for m in sub.namelist() if m.lower().endswith(".txt")]))
            for z, txts in sources:
                processed = [n for n in txts if "processed" in n.lower()]
                for n in (processed or txts):
                    yield n, z.read(n).decode("utf-8", "replace")
                    count += 1
                    if limit and count >= limit:
                        return


def load_audit(out_dir):
    """file -> 0.4.0 verdict from the published audit CSV, or {} if unavailable."""
    path = os.path.join(out_dir, "rruff-audit-v0.4.0.csv")
    try:
        if not os.path.exists(path):
            fetch(AUDIT_CSV_URL, path)
        with open(path, newline="", encoding="utf-8") as fh:
            return {r["file"]: r["lc_verdict"] for r in csv.DictReader(fh) if r.get("file")}
    except (OSError, KeyError, csv.Error) as exc:
        print("audit CSV unavailable: %s" % exc, flush=True)
        return {}


def load_spice(path):
    """Import the released spice_screen.py from `path` (downloading it first)."""
    global _SPICE
    if _SPICE is None:
        if not os.path.exists(path):
            fetch(SPICE_URL, path)
        spec = importlib.util.spec_from_file_location("spice_screen_release", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SPICE = mod
    return _SPICE


# ---- workers ----------------------------------------------------------------

def screen_text(member, text):
    meta = parse_meta(text)
    mineral, rid, laser = parse_name(member)
    mineral = meta.get("NAMES", mineral) or mineral
    rid = meta.get("RRUFFID", rid) or rid
    chem = meta.get("IDEAL CHEMISTRY", "")
    cr = has_element(chem, "Cr")
    row = {"file": os.path.basename(member), "mineral": mineral, "rruff_id": rid, "laser_nm": laser,
           "chemistry": chem, "group": group_of(chem), "kind": kind_of(mineral, cr), "error": ""}
    try:
        x, y = parse_spectrum(text)
    except ValueError as exc:
        row["error"] = str(exc)
        return row, None
    row.update(band_shape(x, y))
    keep = (x, y) if row["covered"] and row["kind"] in ("crocoite", "filler") else None
    return row, keep


def _work(item):
    member, text = item
    try:
        return screen_text(member, text)
    except Exception as exc:  # one bad file must not stop the run
        return {"file": os.path.basename(member), "error": "%s: %s" % (type(exc).__name__, exc)}, None


def normalise(y):
    lo, hi = min(y), max(y)
    span = (hi - lo) or 1.0
    return [(v - lo) / span for v in y]


def interp(xq, x, y):
    """Linear interpolation of (x, y) at the sorted points xq, clamped at the ends."""
    out = []
    j = 0
    for v in xq:
        if v <= x[0]:
            out.append(y[0])
            continue
        if v >= x[-1]:
            out.append(y[-1])
            continue
        while x[j + 1] < v:
            j += 1
        x0, x1 = x[j], x[j + 1]
        t = (v - x0) / (x1 - x0) if x1 > x0 else 0.0
        out.append(y[j] + t * (y[j + 1] - y[j]))
    return out


def mix(filler, croc, fraction, noise=MIX_NOISE, seed=0):
    """(1 - f) x filler + f x crocoite, each scaled to its own 0-1 range on the
    filler's axis, plus white noise. f is a peak-height fraction, not a mass
    fraction (as in rruff-rules)."""
    fx, fy = filler
    cx, cy = croc
    fn = normalise(fy)
    cn = normalise(interp(fx, cx, cy))
    rng = random.Random(seed)
    return list(fx), [(1.0 - fraction) * a + fraction * b + rng.gauss(0.0, noise) for a, b in zip(fn, cn)]


def _init(spectra, spice_path):
    global _SPECTRA
    _SPECTRA = spectra
    if spice_path:
        try:
            load_spice(spice_path)
        except Exception as exc:  # the gates are still measured without it
            print("spice_screen unavailable in worker: %s" % exc, flush=True)


def _mix_work(item):
    fkey, ckey, fraction = item
    seed = zlib.crc32(("%s|%s|%g" % (fkey, ckey, fraction)).encode())
    row = {"filler": fkey, "crocoite": ckey, "fraction": fraction, "v040": None}
    try:
        x, y = mix(_SPECTRA[fkey], _SPECTRA[ckey], fraction, seed=seed)
        row.update(band_shape(x, y))
        if _SPICE is not None:
            lc = next(e for e in _SPICE.LIBRARY if e["id"] == "lead_chromate")
            row["v040"] = _SPICE.screen_entry(x, y, lc, 5.0)["verdict"]
    except Exception as exc:  # keep going
        row["error"] = "%s: %s" % (type(exc).__name__, exc)
    return row


def pick_fillers(kept, rows_by_file, per_mineral=2):
    """Up to `per_mineral` filler spectra per mineral, one per laser where possible."""
    chosen = {}
    for name in sorted(kept):
        r = rows_by_file[name]
        if r["kind"] != "filler":
            continue
        lst = chosen.setdefault(r["mineral"].lower(), [])
        if len(lst) < per_mineral and all(rows_by_file[o]["laser_nm"] != r["laser_nm"] for o in lst):
            lst.append(name)
    return [n for lst in chosen.values() for n in lst]


# ---- output -----------------------------------------------------------------

def write_csv(path, rows, fields=None):
    fields = fields or sorted({k for r in rows for k in r})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return "%.3g" % v
    return str(v)


def write_markdown(s, path):
    fr = ["f=%g" % f for f in FRACTIONS]
    lines = ["# Band shape vs spice-screen's 840 cm-1 lead chromate flags (RRUFF)", "",
             "Base verdicts: %s. Spectra read: %d (errors %d); covering 840 cm-1: %d; 0.4.0-positive and "
             "covered: %d. Mixtures: %d (%d crocoite x %d filler spectra x %d fractions; 0.4.0 run on each: %s)." % (
                 s["base"], s["spectra_read"], s["errors"], s["covered"], s["base_positive"], s["mixtures"],
                 s["mix_crocoite"], s["mix_fillers"], len(FRACTIONS), s["mix_v040"]),
             "", "## Crocoite spectra", "",
             "| file | laser | 0.4.0 | apex | apex ok | dominance | FWHM | bend ratio | bend peaks |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in s["crocoite_rows"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["rruff_id"], r["laser_nm"], r.get("v040") or "-", _fmt(r["apex_pos"]), r["apex_ok"],
            _fmt(r["dominance"]), _fmt(r["fwhm"]), _fmt(r["bend_ratio"]), _fmt(r["bend_peaks"])))
    lines += ["", "## Features among 0.4.0 positives (min / p10 / median / p90 / max)", "",
              "| class | n | apex ok | dominance | FWHM (cm-1) | bend ratio |", "|---|---|---|---|---|---|"]
    for name, d in s["features"].items():
        cells = []
        for f in ("dominance", "fwhm", "bend_ratio"):
            q = d[f]
            cells.append(" / ".join(_fmt(q[k]) for k in ("min", "p10", "median", "p90", "max")) if q else "-")
        lines.append("| %s | %d | %d | %s |" % (name, d["n"], d["apex_ok"], " | ".join(cells)))
    head = "| rule | crocoite | other Cr | no-Cr | lead pigments | fillers | " + " | ".join(fr) + " |"
    lines += ["", "## Shortlist (keeps every crocoite spectrum; mixtures at f=0.03/0.1 within 5 points of "
              "no gate)", "", head, "|" + "---|" * (6 + len(fr))]

    def rule_line(r):
        return "| %s | %d/%d | %d | %d/%d | %d | %d | %s |" % (
            r["rule"], r["crocoite"], r["crocoite_n"], r["other_cr"], r["non_cr"], r["non_cr_n"],
            r["lead_pigment"], r["filler"], " | ".join(_fmt(r.get(k)) for k in fr))
    lines.append(rule_line(s["no_gate"]))
    for r in s["shortlist"]:
        lines.append(rule_line(r))
    lines += ["", "Detection columns are the share of crocoite-in-filler mixtures flagged by 0.4.0 AND the gates; "
              "f=0 is the filler alone (false flags). f is a peak-height fraction, not a mass fraction.", "",
              "RRUFF data: Lafuente et al. (2015), The power of databases: the RRUFF project. "
              "Spectra are not redistributed here."]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


LIB_FIELDS = ["file", "mineral", "rruff_id", "laser_nm", "chemistry", "group", "kind", "v040", "covered",
              "apex_pos", "apex_ok", "h840", "dominance", "fwhm", "bend_ratio", "bend_peaks", "error"]
MIX_FIELDS = ["filler", "crocoite", "fraction", "v040", "covered", "apex_pos", "apex_ok", "dominance", "fwhm",
              "bend_ratio", "bend_peaks", "error"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--limit", type=int, default=0, help="stop after this many spectra (0 = all)")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    start = time.time()

    audit = load_audit(args.out_dir)
    print("0.4.0 verdicts from audit CSV: %d" % len(audit), flush=True)
    archives = find_archives(args.data_dir)
    print("archives: %s" % archives, flush=True)

    rows, spectra = [], {}
    with mp.Pool(args.workers) as pool:
        for row, keep in pool.imap_unordered(_work, iter_members(archives, args.limit), chunksize=8):
            if audit:
                row["v040"] = audit.get(row["file"], "missing")
            rows.append(row)
            if keep is not None:
                spectra[row["file"]] = keep
            if len(rows) % 500 == 0:
                print("%d spectra, %.1f min" % (len(rows), (time.time() - start) / 60), flush=True)
    rows.sort(key=lambda r: (r.get("mineral", ""), r.get("file", "")))
    write_csv(os.path.join(args.out_dir, "features.csv"), rows, LIB_FIELDS)

    spice_path = os.path.join(args.out_dir, "spice_screen_v0.4.0.py")
    try:
        load_spice(spice_path)
        with open(spice_path, "rb") as fh:
            sha = hashlib.sha256(fh.read()).hexdigest()
    except Exception as exc:
        print("spice_screen 0.4.0 unavailable, mixtures use gates only: %s" % exc, flush=True)
        spice_path, sha = "", None

    by_file = {r["file"]: r for r in rows if not r.get("error")}
    crocs = sorted(f for f in spectra if by_file[f]["kind"] == "crocoite")
    fillers = pick_fillers(spectra, by_file)
    items = [(f, c, fr) for f in fillers for c in crocs for fr in FRACTIONS]
    print("mixtures: %d crocoite x %d fillers x %d fractions" % (len(crocs), len(fillers), len(FRACTIONS)),
          flush=True)
    mrows = []
    with mp.Pool(args.workers, initializer=_init, initargs=(spectra, spice_path)) as pool:
        for m in pool.imap_unordered(_mix_work, items, chunksize=4):
            mrows.append(m)
            if len(mrows) % 250 == 0:
                print("%d mixtures, %.1f min" % (len(mrows), (time.time() - start) / 60), flush=True)
    mrows.sort(key=lambda m: (m["filler"], m["crocoite"], m["fraction"]))
    write_csv(os.path.join(args.out_dir, "mixtures.csv"), mrows, MIX_FIELDS)

    lib = evaluate(rows)
    mixes = evaluate_mixtures(mrows)
    write_csv(os.path.join(args.out_dir, "rules.csv"), lib,
              ["rule", "crocoite", "crocoite_n", "other_cr", "non_cr", "non_cr_n", "lead_pigment", "filler"])
    write_csv(os.path.join(args.out_dir, "mixture_rules.csv"), mixes, ["rule"] + ["f=%g" % f for f in FRACTIONS])
    mix_by = {m["rule"]: m for m in mixes}
    no_gate = dict(next(r for r in lib if r["rule"] == "none"), **{k: v for k, v in mix_by["none"].items()
                                                                   if k != "rule"})
    ok = [r for r in rows if not r.get("error")]
    s = {
        "base": "spice-screen 0.4.0 verdicts (published audit CSV)" if audit else "none (audit CSV unavailable)",
        "spice_sha256": sha, "spectra_read": len(rows), "errors": len(rows) - len(ok),
        "covered": sum(bool(r.get("covered")) for r in ok),
        "base_positive": sum(bool(r.get("covered")) and base_positive(r) for r in ok),
        "mixtures": len(mrows), "mix_crocoite": len(crocs), "mix_fillers": len(fillers),
        "mix_v040": bool(spice_path),
        "crocoite_rows": [{k: r.get(k) for k in ["rruff_id", "laser_nm", "v040"] + list(FEATURES)}
                          for r in ok if r["kind"] == "crocoite"],
        "features": feature_table(rows),
        "no_gate": no_gate,
        "shortlist": shortlist(lib, mixes),
        "minutes": round((time.time() - start) / 60, 1),
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=1)
    write_markdown(s, os.path.join(args.out_dir, "summary.md"))
    print(json.dumps({k: s[k] for k in ("base", "spectra_read", "covered", "base_positive", "mixtures",
                                        "minutes")}))
    print("no gate:", json.dumps(no_gate))
    for r in s["shortlist"]:
        print("shortlist:", json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
