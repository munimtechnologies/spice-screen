#!/usr/bin/env python3
"""rruff-grain: how specific is spice-screen's grain mode on real mineral spectra?

Grain mode (spice-screen 0.6.0, docs/grain-mode.md) is for picked yellow-orange
particles. A lead chromate positive must then also pass three band-shape gates
(apex at 830-850 cm-1, the 840 band at least half the strongest band in
200-1100 cm-1, and under lasers of 700 nm or longer chromate's bending bands at
15% or more of the 840 band). The thresholds were published before this audit.

For every processed spectrum in the RRUFF Raman archive it records the 840 cm-1
check (the 0.5.0 verdict, default noise "lag") and the grain gates, using the
RRUFF laser wavelength from the file name. It reports, by mineral class and by
laser (near-infrared >= 700 nm, visible < 700 nm):
- how many crocoite (PbCrO4) spectra grain mode keeps;
- which minerals without chromium still pass (false positives);
- the same counts for nearby thresholds, so the choice can be judged;
- crocoite mixed into real filler spectra at falling peak-height fractions,
  pairing spectra taken with lasers of the same class.

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

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.dirname(os.path.dirname(HERE))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import spice_screen as ss  # noqa: E402

RRUFF_URL = "https://www.rruff.net/zipped_data_files/raman/excellent_unoriented.zip"
USER_AGENT = "spice-screen RRUFF grain audit (MV2 of Munim, Inc.; munimversion2@gmail.com)"

NIR_MIN_NM = 700.0
DOM_GRID = (0.3, 0.5, 0.7)
BEND_GRID = (0.1, 0.15, 0.3)
FRACTIONS = (0.0, 0.1, 0.3, 0.5, 0.7)
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
KINDS = ("crocoite", "other_cr", "lead_pigment", "filler", "other")
NON_CR = ("lead_pigment", "filler", "other")

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


def laser_class(laser):
    """'nir' (>= 700 nm), 'visible' or 'unknown'."""
    try:
        nm = float(laser)
    except (TypeError, ValueError):
        return "unknown"
    return "nir" if nm >= NIR_MIN_NM else "visible"


# ---- gates --------------------------------------------------------------------

def measure(x, y, laser_nm):
    """The 0.5.0 check at 840 cm-1 and the grain gates, as one flat dict."""
    band = ss.check_band(x, y, 840.0, 8.0, 5.0)
    g = ss.grain_check(x, y, laser_nm=laser_nm, band=band)
    return {"covered": band["covered"], "base": band["detected"], "snr840": band["snr"],
            "grain": g["verdict"], "apex": g["apex"], "apex_ok": g["apex_ok"], "dominance": g["dominance"],
            "bend_ratio": g["bend_ratio"], "bend_required": g["bend_required"],
            "failed": "+".join(g["failed"]), "skipped": "+".join(g["skipped"])}


def passes(row, dom_min, bend_min, apex=True):
    """Would a 0.5.0-positive spectrum pass grain mode with these thresholds?
    With the published ones (0.5, 0.15, apex) this must equal grain_check()."""
    if not row.get("base"):
        return False
    if apex and not row.get("apex_ok"):
        return False
    if (row.get("dominance") or 0.0) < dom_min:
        return False
    if row.get("bend_required") and row.get("bend_ratio") is not None and row["bend_ratio"] < bend_min:
        return False
    return True


def rule_grid():
    return [(d, b, a) for a in (True, False) for d in DOM_GRID for b in BEND_GRID]


def rule_name(rule):
    d, b, a = rule
    return "%sdom>=%g+bend>=%g" % ("apex+" if a else "", d, b)


PUBLISHED = (ss.GRAIN["dominance_min"], ss.GRAIN["bend_ratio_min"], True)


# ---- workers ----------------------------------------------------------------

def screen_text(member, text):
    meta = parse_meta(text)
    mineral, rid, laser = parse_name(member)
    mineral = meta.get("NAMES", mineral) or mineral
    rid = meta.get("RRUFFID", rid) or rid
    chem = meta.get("IDEAL CHEMISTRY", "")
    cr = has_element(chem, "Cr")
    row = {"file": os.path.basename(member), "mineral": mineral, "rruff_id": rid, "laser_nm": laser,
           "laser_class": laser_class(laser), "chemistry": chem, "group": group_of(chem),
           "kind": kind_of(mineral, cr), "error": ""}
    try:
        x, y = ss.parse_spectrum(text)
    except ValueError as exc:
        row["error"] = str(exc)
        return row, None
    row.update(measure(x, y, float(laser) if laser else None))
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
    fraction (as in the earlier rruff-rules and rruff-shape studies)."""
    fx, fy = filler
    cx, cy = croc
    fn = normalise(fy)
    cn = normalise(interp(fx, cx, cy))
    rng = random.Random(seed)
    return list(fx), [(1.0 - fraction) * a + fraction * b + rng.gauss(0.0, noise) for a, b in zip(fn, cn)]


def _init(spectra):
    global _SPECTRA
    _SPECTRA = spectra


def _mix_work(item):
    fkey, ckey, fraction, laser_nm = item
    seed = zlib.crc32(("%s|%s|%g" % (fkey, ckey, fraction)).encode())
    row = {"filler": fkey, "crocoite": ckey, "fraction": fraction, "laser_nm": laser_nm,
           "laser_class": laser_class(laser_nm), "error": ""}
    try:
        x, y = mix(_SPECTRA[fkey], _SPECTRA[ckey], fraction, seed=seed)
        row.update(measure(x, y, laser_nm))
    except Exception as exc:  # keep going
        row["error"] = "%s: %s" % (type(exc).__name__, exc)
    return row


def pick_fillers(kept, rows_by_file):
    """One filler spectrum per mineral and laser class (the first by file name)."""
    chosen = {}
    for name in sorted(kept):
        r = rows_by_file[name]
        if r["kind"] != "filler":
            continue
        chosen.setdefault((r["mineral"].lower(), r["laser_class"]), name)
    return [chosen[k] for k in sorted(chosen)]


def mix_items(spectra, rows_by_file):
    """(filler, crocoite, fraction, crocoite laser) for pairs of the same laser class."""
    crocs = sorted(f for f in spectra if rows_by_file[f]["kind"] == "crocoite")
    fillers = pick_fillers(spectra, rows_by_file)
    items = []
    for c in crocs:
        cr = rows_by_file[c]
        if cr["laser_class"] == "unknown":
            continue
        for f in fillers:
            if rows_by_file[f]["laser_class"] != cr["laser_class"]:
                continue
            for fr in FRACTIONS:
                items.append((f, c, fr, float(cr["laser_nm"])))
    return items, crocs, fillers


def run_pool(func, items, workers, initializer=None, initargs=(), progress=""):
    """imap_unordered over a fork pool, or a plain loop with one worker."""
    out = []
    start = time.time()
    if workers <= 1:
        if initializer:
            initializer(*initargs)
        it = map(func, items)
        pool = None
    else:
        pool = mp.Pool(workers, initializer=initializer, initargs=initargs)
        it = pool.imap_unordered(func, items, chunksize=8)
    try:
        for res in it:
            out.append(res)
            if progress and len(out) % 500 == 0:
                print("%d %s, %.1f min" % (len(out), progress, (time.time() - start) / 60), flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    return out


# ---- data -------------------------------------------------------------------

def fetch(url, path, timeout=600):
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
    return [fetch(RRUFF_URL, os.path.join(data_dir, "excellent_unoriented.zip"))]


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


# ---- summary ----------------------------------------------------------------

def class_table(rows):
    """Counts by kind and laser class: covered, 0.5.0 positive, grain positive,
    and grain-inconclusive by the gates that failed."""
    out = {}
    for r in rows:
        if r.get("error") or not r.get("covered"):
            continue
        d = out.setdefault("%s/%s" % (r["kind"], r["laser_class"]),
                           {"covered": 0, "base": 0, "grain": 0, "failed": {}})
        d["covered"] += 1
        d["base"] += int(bool(r["base"]))
        d["grain"] += int(r["grain"] == "screen-positive")
        if r["grain"] == "inconclusive":
            d["failed"][r["failed"]] = d["failed"].get(r["failed"], 0) + 1
    return dict(sorted(out.items()))


def grid_table(rows, mrows):
    """Library and mixture counts for every rule in the grid."""
    ok = [r for r in rows if not r.get("error") and r.get("covered")]
    out = []
    for rule in rule_grid():
        line = {"rule": rule_name(rule), "published": rule == PUBLISHED}
        for lc in ("nir", "visible"):
            sel = [r for r in ok if r["laser_class"] == lc]
            line["crocoite_%s" % lc] = sum(passes(r, *rule) for r in sel if r["kind"] == "crocoite")
            line["non_cr_%s" % lc] = sum(passes(r, *rule) for r in sel if r["kind"] in NON_CR)
        line["non_cr_unknown_laser"] = sum(passes(r, *rule) for r in ok
                                           if r["laser_class"] == "unknown" and r["kind"] in NON_CR)
        for f in FRACTIONS:
            sel = [m for m in mrows if not m.get("error") and m["fraction"] == f]
            line["mix_f=%g" % f] = round(sum(passes(m, *rule) for m in sel) / len(sel), 4) if sel else None
        out.append(line)
    return out


def mixture_table(mrows):
    """Share flagged by 0.5.0 (base) and by grain mode, per laser class and fraction."""
    out = {}
    for lc in ("nir", "visible"):
        for f in FRACTIONS:
            sel = [m for m in mrows if not m.get("error") and m["laser_class"] == lc and m["fraction"] == f]
            if not sel:
                continue
            out["%s f=%g" % (lc, f)] = {
                "n": len(sel),
                "base": round(sum(bool(m["base"]) for m in sel) / len(sel), 4),
                "grain": round(sum(m["grain"] == "screen-positive" for m in sel) / len(sel), 4),
            }
    return out


def summarize(rows, mrows, crocs, fillers, sha, complete):
    ok = [r for r in rows if not r.get("error")]
    covered = [r for r in ok if r.get("covered")]
    mismatch = [r["file"] for r in covered
                if passes(r, *PUBLISHED) != (r["grain"] == "screen-positive")]
    non_cr_pos = [r for r in covered if r["kind"] in NON_CR and r["grain"] == "screen-positive"]
    other_cr_pos = [r for r in covered if r["kind"] == "other_cr" and r["grain"] == "screen-positive"]
    fields = ("mineral", "rruff_id", "laser_nm", "chemistry", "group", "apex", "dominance", "bend_ratio",
              "skipped")
    return {
        "tool": "spice-screen", "version": ss.__version__, "sha256": sha, "grain_params": ss.GRAIN,
        "complete": complete, "spectra_read": len(rows), "errors": len(rows) - len(ok),
        "covered_840": len(covered),
        "base_positive": sum(bool(r["base"]) for r in covered),
        "grain_positive": sum(r["grain"] == "screen-positive" for r in covered),
        "rule_mismatches": mismatch[:20], "rule_mismatch_count": len(mismatch),
        "crocoite": [{k: r.get(k) for k in ("rruff_id", "laser_nm", "base", "grain", "apex", "dominance",
                                            "bend_ratio", "failed", "skipped")}
                     for r in covered if r["kind"] == "crocoite"],
        "by_class": class_table(rows),
        "non_cr_grain_positive": [{k: r.get(k) for k in fields} for r in non_cr_pos],
        "other_cr_grain_positive": [{k: r.get(k) for k in fields} for r in other_cr_pos],
        "grid": grid_table(rows, mrows),
        "mixtures": {"n": len(mrows), "crocoite_spectra": len(crocs), "filler_spectra": len(fillers),
                     "errors": sum(1 for m in mrows if m.get("error")), "table": mixture_table(mrows)},
    }


def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return "%.3g" % v
    return str(v)


def write_markdown(s, path):
    lines = ["# spice-screen grain mode vs the RRUFF Raman library", "",
             "spice-screen %s (sha256 %s), complete: %s. Spectra read: %d (errors %d); covering 840 cm-1: %d; "
             "0.5.0 positive (840 cm-1 band, noise lag): %d; grain-mode positive: %d. Self-check: %d spectra where "
             "the audit's rule and grain_check() disagree." % (
                 s["version"], (s["sha256"] or "")[:12], s["complete"], s["spectra_read"], s["errors"],
                 s["covered_840"], s["base_positive"], s["grain_positive"], s["rule_mismatch_count"]),
             "", "Thresholds (fixed before this audit): %s" % json.dumps(s["grain_params"]),
             "", "## Crocoite (PbCrO4)", "",
             "| RRUFF ID | laser | 0.5.0 | grain | apex | dominance | bend ratio | failed | skipped |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in s["crocoite"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["rruff_id"], r["laser_nm"], "positive" if r["base"] else "-", r["grain"], _fmt(r["apex"]),
            _fmt(r["dominance"]), _fmt(r["bend_ratio"]), r["failed"] or "-", r["skipped"] or "-"))
    lines += ["", "## By class and laser", "",
              "| class / laser | covered | 0.5.0 positive | grain positive | grain inconclusive by failed gates |",
              "|---|---|---|---|---|"]
    for k, d in s["by_class"].items():
        failed = ", ".join("%s %d" % kv for kv in sorted(d["failed"].items(), key=lambda kv: -kv[1]))
        lines.append("| %s | %d | %d | %d | %s |" % (k, d["covered"], d["base"], d["grain"], failed or "-"))
    lines += ["", "## Minerals without chromium that pass grain mode", "",
              "| mineral | chemistry | laser | apex | dominance | bend ratio | skipped |", "|---|---|---|---|---|---|---|"]
    for r in s["non_cr_grain_positive"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["mineral"], r["chemistry"], r["laser_nm"] or "?", _fmt(r["apex"]), _fmt(r["dominance"]),
            _fmt(r["bend_ratio"]), r["skipped"] or "-"))
    lines += ["", "## Other chromium-bearing minerals that pass", "",
              ", ".join(sorted({"%s (%s)" % (r["mineral"], r["laser_nm"] or "?")
                                for r in s["other_cr_grain_positive"]})) or "none"]
    fr = ["mix_f=%g" % f for f in FRACTIONS]
    lines += ["", "## Nearby thresholds", "",
              "| rule | published | crocoite NIR | crocoite visible | no-Cr NIR | no-Cr visible | no-Cr laser unknown | "
              + " | ".join(fr) + " |", "|" + "---|" * (7 + len(fr))]
    for g in s["grid"]:
        lines.append("| %s | %s | %d | %d | %d | %d | %d | %s |" % (
            g["rule"], "yes" if g["published"] else "", g["crocoite_nir"], g["crocoite_visible"], g["non_cr_nir"],
            g["non_cr_visible"], g["non_cr_unknown_laser"], " | ".join(_fmt(g[k]) for k in fr)))
    m = s["mixtures"]
    lines += ["", "## Crocoite in filler (same laser class)", "",
              "%d mixtures from %d crocoite and %d filler spectra (errors %d). f is a peak-height fraction, not a "
              "mass fraction; f=0 is the filler alone (false flags)." % (
                  m["n"], m["crocoite_spectra"], m["filler_spectra"], m["errors"]), "",
              "| laser, fraction | n | 0.5.0 flags | grain flags |", "|---|---|---|---|"]
    for k, d in m["table"].items():
        lines.append("| %s | %d | %s | %s |" % (k, d["n"], _fmt(d["base"]), _fmt(d["grain"])))
    lines += ["", "RRUFF data: Lafuente et al. (2015), The power of databases: the RRUFF project. "
              "Spectra are not redistributed here."]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


ROW_FIELDS = ["file", "mineral", "rruff_id", "laser_nm", "laser_class", "chemistry", "group", "kind", "covered",
              "base", "snr840", "grain", "apex", "apex_ok", "dominance", "bend_ratio", "bend_required", "failed",
              "skipped", "error"]
MIX_FIELDS = ["filler", "crocoite", "fraction", "laser_nm", "laser_class", "covered", "base", "snr840", "grain",
              "apex", "apex_ok", "dominance", "bend_ratio", "bend_required", "failed", "skipped", "error"]


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--limit", type=int, default=0, help="stop after this many spectra (0 = all)")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    if args.workers > 1:
        mp.set_start_method("fork", force=True)
    start = time.time()
    with open(ss.__file__, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    print("spice-screen %s sha256 %s" % (ss.__version__, sha), flush=True)
    archives = find_archives(args.data_dir)
    print("archives: %s" % archives, flush=True)

    rows, spectra = [], {}
    for row, keep in run_pool(_work, iter_members(archives, args.limit), args.workers, progress="spectra"):
        rows.append(row)
        if keep is not None:
            spectra[row["file"]] = keep
    rows.sort(key=lambda r: (r.get("mineral", ""), r.get("file", "")))
    write_csv(os.path.join(args.out_dir, "grain.csv"), rows, ROW_FIELDS)

    by_file = {r["file"]: r for r in rows if not r.get("error")}
    items, crocs, fillers = mix_items(spectra, by_file)
    print("mixtures: %d (%d crocoite, %d filler spectra)" % (len(items), len(crocs), len(fillers)), flush=True)
    mrows = run_pool(_mix_work, items, args.workers, initializer=_init, initargs=(spectra,), progress="mixtures")
    mrows.sort(key=lambda m: (m["filler"], m["crocoite"], m["fraction"]))
    write_csv(os.path.join(args.out_dir, "mixtures.csv"), mrows, MIX_FIELDS)

    s = summarize(rows, mrows, crocs, fillers, sha, complete=not args.limit)
    s["minutes"] = round((time.time() - start) / 60, 1)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=1)
    write_markdown(s, os.path.join(args.out_dir, "summary.md"))
    print(json.dumps({k: s[k] for k in ("spectra_read", "covered_840", "base_positive", "grain_positive",
                                        "rule_mismatch_count", "minutes")}))
    print("crocoite:", json.dumps(s["crocoite"]))
    print("non-Cr grain positives:", len(s["non_cr_grain_positive"]),
          ", ".join(sorted({r["mineral"] for r in s["non_cr_grain_positive"]}))[:2000])
    for g in s["grid"]:
        if g["published"]:
            print("published rule:", json.dumps(g))
    print("mixtures:", json.dumps(s["mixtures"]["table"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
