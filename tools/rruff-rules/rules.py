#!/usr/bin/env python3
"""rruff-rules: which noise rule keeps spice-screen's lead chromate marker
sensitive on real crocoite while cutting false flags on other minerals?

The 0.4.0 audit (docs/rruff-audit.md in spice-screen) found that 0.4.0 flags
34% of the RRUFF spectra of minerals without chromium at 840 cm-1, mostly on
"bands" smaller than 1% of the spectrum's strongest. RRUFF's processed
spectra are smoothed, and 0.4.0 measured noise from point-to-point
differences, which smoothing shrinks.

This job screens the same library with the candidate spice-screen under each
noise mode (diff = 0.4.0, scatter, lag), at several SNR thresholds and
optional relative-height gates. It then mixes real crocoite spectra into real
filler spectra (chalk, talc, clays, iron oxides, ...) at falling peak-height
fractions, with white noise added, to see what each rule still detects.

RRUFF spectra are not redistributed; only per-file numbers are written.
RRUFF: Lafuente B, Downs RT, Yang H, Stone N. The power of databases: the RRUFF
project. In: Highlights in Mineralogical Crystallography, De Gruyter (2015) 1-30.
Made by MV2 of Munim, Inc. with AI agents working in his name. Apache-2.0.
"""
from __future__ import annotations

import argparse
import csv
import glob
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spice_screen as ss  # noqa: E402

RRUFF_URL = "https://www.rruff.net/zipped_data_files/raman/excellent_unoriented.zip"
USER_AGENT = "spice-screen RRUFF rules (MV2 of Munim, Inc.; munimversion2@gmail.com)"

CENTER, TOL = 840.0, 8.0
SNR_GRID = (5.0, 8.0, 10.0, 20.0)
REL_GRID = (0.0, 0.01, 0.03, 0.05, 0.10)
FRACTIONS = (0.0, 0.003, 0.01, 0.03, 0.1, 0.3)
MIX_NOISE = 0.003  # white noise, as a fraction of the filler's strongest band
VERIFY_EVERY = 25  # re-screen 1 in N spectra with screen_entry() as a cross-check

# Fillers and soil minerals that end up in ground spices (no lead, no chromium).
FILLERS = {
    "calcite": "chalk, calcium carbonate", "aragonite": "calcium carbonate",
    "dolomite": "carbonate filler", "gypsum": "calcium sulfate", "talc": "talc",
    "kaolinite": "clay", "montmorillonite": "clay", "muscovite": "mica, soil",
    "quartz": "sand", "albite": "feldspar", "microcline": "feldspar", "orthoclase": "feldspar",
    "baryte": "barium sulfate", "barite": "barium sulfate", "rutile": "titanium dioxide",
    "anatase": "titanium dioxide (E171)", "halite": "salt", "fluorapatite": "phosphate",
    "hematite": "iron oxide, brick dust", "goethite": "ochre", "magnetite": "iron oxide",
}
# Lead pigments documented or plausible in spices: a flag on these is not a
# false alarm about lead, but it is not lead chromate either.
LEAD_PIGMENTS = {
    "minium": "red lead Pb3O4", "litharge": "PbO", "massicot": "PbO",
    "cerussite": "lead carbonate (white lead)", "hydrocerussite": "basic lead carbonate (white lead)",
    "anglesite": "lead sulfate",
}

_SPECTRA = {}


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


def kind_of(row):
    """crocoite, other_cr (other chromium minerals) or non_cr."""
    if row["mineral"].lower().startswith("crocoite"):
        return "crocoite"
    return "other_cr" if row["cr_bearing"] else "non_cr"


def rel_height(x, y, center=CENTER, tol=TOL):
    """Height of the strongest point near `center` above the spectrum's median,
    as a fraction of the spectrum's strongest point above the median (as in
    the 0.4.0 audit)."""
    med = ss._median(y)
    top = max(y) - med
    near = [b for a, b in zip(x, y) if abs(a - center) <= tol]
    if not near or top <= 0:
        return None
    return round((max(near) - med) / top, 4)


def band_row(x, y):
    """The 840 cm-1 band under every noise mode, plus its relative height."""
    out = {"covered": False, "edge": False, "pos840": None, "rel840": None}
    for mode in ss.NOISE_MODES:
        b = ss.check_band(x, y, CENTER, TOL, 5.0, noise=mode)
        out["covered"] = b["covered"]
        out["edge"] = b.get("edge", False)
        out["pos840"] = b["position"]
        out["snr_" + mode] = b["snr"]
    if out["covered"]:
        out["rel840"] = rel_height(x, y)
    return out


def positive(row, mode, snr_min, rel_min=0.0):
    """Would the rule (noise mode, SNR threshold, relative-height gate) flag it?"""
    if not row.get("covered") or row.get("edge"):
        return False
    if (row.get("snr_" + mode) or 0.0) < snr_min:
        return False
    return (row.get("rel840") or 0.0) >= rel_min


def screen_text(member, text):
    meta = parse_meta(text)
    mineral, rid, laser = parse_name(member)
    mineral = meta.get("NAMES", mineral) or mineral
    rid = meta.get("RRUFFID", rid) or rid
    chem = meta.get("IDEAL CHEMISTRY", "")
    row = {"file": os.path.basename(member), "mineral": mineral, "rruff_id": rid, "laser_nm": laser,
           "chemistry": chem, "group": group_of(chem), "cr_bearing": has_element(chem, "Cr"),
           "pb_bearing": has_element(chem, "Pb"), "error": ""}
    try:
        x, y = ss.parse_spectrum(text)
    except ValueError as exc:
        row["error"] = str(exc)
        return row, None
    row["points"] = len(x)
    row.update(band_row(x, y))
    if row["covered"] and zlib.crc32(row["file"].encode()) % VERIFY_EVERY == 0:
        lc = next(e for e in ss.LIBRARY if e["id"] == "lead_chromate")
        bad = [m for m in ss.NOISE_MODES
               if (ss.screen_entry(x, y, lc, 5.0, noise=m)["verdict"] == "screen-positive")
               != positive(row, m, 5.0)]
        row["verify"] = "mismatch:" + "+".join(bad) if bad else "ok"
    key = mineral.lower()
    keep = (x, y) if row["covered"] and (key.startswith("crocoite") or key in FILLERS) else None
    return row, keep


def _work(item):
    member, text = item
    try:
        return screen_text(member, text)
    except Exception as exc:  # one bad file must not stop the run
        return {"file": os.path.basename(member), "error": "%s: %s" % (type(exc).__name__, exc)}, None


def find_archives(data_dir):
    hits = sorted(glob.glob(os.path.join(data_dir, "**", "*.zip"), recursive=True))
    if hits:
        return hits
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "excellent_unoriented.zip")
    req = urllib.request.Request(RRUFF_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as resp, open(path + ".part", "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(path + ".part", path)
    return [path]


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


# ---- mixtures ---------------------------------------------------------------

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
    fraction."""
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
    fkey, ckey, fraction, seed = item
    try:
        x, y = mix(_SPECTRA[fkey], _SPECTRA[ckey], fraction, seed=seed)
        row = band_row(x, y)
    except Exception as exc:  # keep going
        row = {"error": "%s: %s" % (type(exc).__name__, exc)}
    row.update({"filler": fkey, "crocoite": ckey, "fraction": fraction})
    return row


def pick_fillers(kept, rows_by_file, per_mineral=3):
    """Up to `per_mineral` filler spectra per mineral, one per laser where possible."""
    chosen = {}
    for name in sorted(kept):
        r = rows_by_file[name]
        key = r["mineral"].lower()
        if key not in FILLERS:
            continue
        lst = chosen.setdefault(key, [])
        if len(lst) < per_mineral and all(rows_by_file[o]["laser_nm"] != r["laser_nm"] for o in lst):
            lst.append(name)
    return [n for lst in chosen.values() for n in lst]


# ---- summaries --------------------------------------------------------------

def rule_grid():
    return [(m, t, g) for m in ss.NOISE_MODES for t in SNR_GRID for g in REL_GRID]


def evaluate(rows):
    """One line per rule: what it flags in the library."""
    ok = [r for r in rows if not r.get("error") and r.get("covered")]
    groups = {"crocoite": [], "other_cr": [], "non_cr": []}
    for r in ok:
        groups[kind_of(r)].append(r)
    out = []
    for mode, snr_min, rel_min in rule_grid():
        def hit(rs):
            return [r for r in rs if positive(r, mode, snr_min, rel_min)]
        croc, other, non = hit(groups["crocoite"]), hit(groups["other_cr"]), hit(groups["non_cr"])
        by_group = {}
        for r in non:
            by_group[r["group"]] = by_group.get(r["group"], 0) + 1
        fillers = sorted({r["mineral"] for r in non if r["mineral"].lower() in FILLERS})
        out.append({
            "noise": mode, "snr_min": snr_min, "rel_min": rel_min,
            "crocoite_pos": len(croc), "crocoite_n": len(groups["crocoite"]),
            "other_cr_pos": len(other), "other_cr_n": len(groups["other_cr"]),
            "non_cr_pos": len(non), "non_cr_n": len(groups["non_cr"]),
            "non_cr_rate": round(len(non) / len(groups["non_cr"]), 4) if groups["non_cr"] else None,
            "non_cr_pb_pos": sum(1 for r in non if r["pb_bearing"]),
            "filler_pos": sum(1 for r in non if r["mineral"].lower() in FILLERS),
            "fillers_flagged": "; ".join(fillers),
            "top_groups": "; ".join("%s %d" % kv for kv in sorted(by_group.items(), key=lambda kv: -kv[1])[:5]),
        })
    return out


def evaluate_mixtures(mrows):
    """Detection rate of each rule at each crocoite fraction."""
    ok = [r for r in mrows if not r.get("error")]
    out = []
    for mode, snr_min, rel_min in rule_grid():
        line = {"noise": mode, "snr_min": snr_min, "rel_min": rel_min}
        for f in FRACTIONS:
            at = [r for r in ok if r["fraction"] == f]
            hits = sum(1 for r in at if positive(r, mode, snr_min, rel_min))
            line["f=%g" % f] = round(hits / len(at), 4) if at else None
        out.append(line)
    return out


def shortlist(lib, mixes, n=12):
    """Rules that keep every crocoite spectrum, ranked by false flags on
    minerals without chromium, then by detection at 1% peak height."""
    mx = {(m["noise"], m["snr_min"], m["rel_min"]): m for m in mixes}
    keep = [r for r in lib if r["crocoite_n"] and r["crocoite_pos"] == r["crocoite_n"]]
    keep.sort(key=lambda r: (r["non_cr_pos"], -(mx.get((r["noise"], r["snr_min"], r["rel_min"]), {}).get("f=0.01") or 0)))
    out = []
    for r in keep[:n]:
        m = mx.get((r["noise"], r["snr_min"], r["rel_min"]), {})
        out.append(dict(r, **{k: v for k, v in m.items() if k.startswith("f=")}))
    return out


def write_csv(path, rows, fields=None):
    fields = fields or sorted({k for r in rows for k in r})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_markdown(s, path):
    lines = ["# spice-screen lead chromate rules vs the RRUFF Raman library", "",
             "Candidate spice-screen %s; archives %s; complete: %s; %d spectra read, %d covering 840 cm-1, %d errors." % (
                 s["version"], ", ".join(s["archives"]), s["complete"], s["spectra_read"], s["covered"], s["errors"]),
             "Cross-check of rule maths against screen_entry(): %s." % s["verify"],
             "0.4.0 rule (diff, SNR 5, no gate) here: crocoite %s, non-Cr positives %s (0.4.0 audit: 9/9, 1935)." % (
                 s["v040"]["crocoite"], s["v040"]["non_cr_pos"]), "",
             "## Rules that keep all crocoite spectra (best first)", "",
             "| noise | SNR | rel. gate | crocoite | non-Cr flagged | rate | of them Pb | fillers | "
             + " | ".join("f=%g" % f for f in FRACTIONS) + " |",
             "|---|---|---|---|---|---|---|---|" + "---|" * len(FRACTIONS)]
    for r in s["shortlist"]:
        lines.append("| %s | %g | %g | %d/%d | %d | %s | %d | %d | %s |" % (
            r["noise"], r["snr_min"], r["rel_min"], r["crocoite_pos"], r["crocoite_n"], r["non_cr_pos"],
            r["non_cr_rate"], r["non_cr_pb_pos"], r["filler_pos"],
            " | ".join(str(r.get("f=%g" % f)) for f in FRACTIONS)))
    lines += ["", "f is the crocoite share of peak height in a crocoite + filler mixture with white noise "
              "(%g of the strongest band); f=0 is the filler alone. %d mixtures per fraction." % (
                  MIX_NOISE, s["mixtures_per_fraction"]), "",
              "## Every rule without a gate", "",
              "| noise | SNR | crocoite | other Cr | non-Cr flagged | rate | fillers flagged | top groups |",
              "|---|---|---|---|---|---|---|---|"]
    for r in s["rules"]:
        if r["rel_min"] == 0.0:
            lines.append("| %s | %g | %d/%d | %d/%d | %d | %s | %s | %s |" % (
                r["noise"], r["snr_min"], r["crocoite_pos"], r["crocoite_n"], r["other_cr_pos"], r["other_cr_n"],
                r["non_cr_pos"], r["non_cr_rate"], r["fillers_flagged"] or "none", r["top_groups"]))
    lines += ["", "## Crocoite spectra", "", "| file | laser | position | rel. height | SNR diff | SNR scatter | SNR lag |",
              "|---|---|---|---|---|---|---|"]
    for r in s["crocoite"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["rruff_id"], r["laser_nm"], r["pos840"], r["rel840"], r.get("snr_diff"), r.get("snr_scatter"),
            r.get("snr_lag")))
    lines += ["", "RRUFF data: Lafuente et al. (2015). Spectra are not redistributed here.",
              "Made by MV2 of Munim, Inc. with AI agents working in his name."]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--limit", type=int, default=0, help="stop after this many spectra (0 = all)")
    ap.add_argument("--budget-min", type=float, default=150.0, help="stop the library pass after this many minutes")
    ap.add_argument("--fillers-per-mineral", type=int, default=3)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    print("spice-screen %s, noise modes %s" % (ss.__version__, ", ".join(ss.NOISE_MODES)), flush=True)
    archives = find_archives(args.data_dir)
    print("archives: %s" % archives, flush=True)

    start = time.time()
    rows, kept, complete = [], {}, True
    with mp.Pool(args.workers) as pool:
        for row, keep in pool.imap_unordered(_work, iter_members(archives, args.limit), chunksize=4):
            rows.append(row)
            if keep is not None:
                kept[row["file"]] = keep
            if len(rows) % 250 == 0:
                print("%d spectra, %.1f min" % (len(rows), (time.time() - start) / 60), flush=True)
            if (time.time() - start) / 60 > args.budget_min:
                complete = False
                pool.terminate()
                break
    rows.sort(key=lambda r: (r.get("mineral", ""), r.get("file", "")))
    by_file = {r["file"]: r for r in rows}
    write_csv(os.path.join(args.out_dir, "results.csv"), rows,
              ["file", "mineral", "rruff_id", "laser_nm", "chemistry", "group", "cr_bearing", "pb_bearing",
               "points", "covered", "edge", "pos840", "rel840", "snr_diff", "snr_scatter", "snr_lag",
               "verify", "error"])
    lib = evaluate(rows)
    write_csv(os.path.join(args.out_dir, "rules.csv"), lib, list(lib[0].keys()))
    print("library pass done: %d spectra, %.1f min" % (len(rows), (time.time() - start) / 60), flush=True)

    crocs = sorted(n for n in kept if by_file[n]["mineral"].lower().startswith("crocoite"))
    fillers = pick_fillers(kept, by_file, args.fillers_per_mineral)
    items = [(fk, ck, f, i) for i, (fk, ck, f) in enumerate(
        (fk, ck, f) for fk in fillers for ck in crocs for f in FRACTIONS)]
    print("mixtures: %d crocoite x %d fillers x %d fractions = %d" % (
        len(crocs), len(fillers), len(FRACTIONS), len(items)), flush=True)
    spectra = {k: kept[k] for k in set(crocs) | set(fillers)}
    with mp.Pool(args.workers, initializer=_init, initargs=(spectra,)) as pool:
        mrows = list(pool.imap_unordered(_mix_work, items, chunksize=8))
    write_csv(os.path.join(args.out_dir, "mixtures.csv"), mrows,
              ["filler", "crocoite", "fraction", "covered", "edge", "pos840", "rel840",
               "snr_diff", "snr_scatter", "snr_lag", "error"])
    mixes = evaluate_mixtures(mrows)
    write_csv(os.path.join(args.out_dir, "mixture_rules.csv"), mixes, list(mixes[0].keys()))

    ok = [r for r in rows if not r.get("error")]
    checked = [r for r in ok if r.get("verify")]
    bad = [r["file"] + " " + r["verify"] for r in checked if r["verify"] != "ok"]
    v040 = next(r for r in lib if r["noise"] == "diff" and r["snr_min"] == 5.0 and r["rel_min"] == 0.0)
    s = {
        "tool": "spice-screen", "version": ss.__version__, "archives": [os.path.basename(a) for a in archives],
        "complete": complete, "spectra_read": len(rows), "errors": len(rows) - len(ok),
        "covered": sum(1 for r in ok if r.get("covered")),
        "verify": "%d of %d sampled spectra agree%s" % (len(checked) - len(bad), len(checked),
                                                       ("; mismatches: " + ", ".join(bad[:10])) if bad else ""),
        "v040": {"crocoite": "%d/%d" % (v040["crocoite_pos"], v040["crocoite_n"]), "non_cr_pos": v040["non_cr_pos"]},
        "mixtures_per_fraction": len(crocs) * len(fillers),
        "fillers_used": sorted({by_file[f]["mineral"] for f in fillers}),
        "shortlist": shortlist(lib, mixes),
        "rules": lib,
        "crocoite": [by_file[n] for n in crocs],
        "minutes": round((time.time() - start) / 60, 1),
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=1)
    write_markdown(s, os.path.join(args.out_dir, "summary.md"))
    print(json.dumps({k: s[k] for k in ("spectra_read", "covered", "errors", "complete", "verify", "v040",
                                        "mixtures_per_fraction", "minutes")}))
    for r in s["shortlist"]:
        print(json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
