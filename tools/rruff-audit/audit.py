#!/usr/bin/env python3
"""rruff-audit: how specific is spice-screen's lead chromate marker on real spectra?

Runs the normal-Raman markers of the released spice-screen (v0.4.0) over every
processed spectrum in a RRUFF Raman archive (Lafuente B, Downs RT, Yang H,
Stone N. The power of databases: the RRUFF project. In: Highlights in
Mineralogical Crystallography, De Gruyter (2015) 1-30) and reports:

- sensitivity on real crocoite (PbCrO4) spectra;
- which chromium-bearing minerals also flag (expected: chromate stretch);
- which minerals WITHOUT chromium flag at 840 cm-1 (false positives), and
  whether the 825/856 cm-1 triplet bands tell them apart;
- the verdicts for minerals that are known or plausible spice adulterants or
  fillers (red lead, chalk, talc, brick-dust iron oxides, clays, ...).

RRUFF spectra are not redistributed; only per-file verdicts are written.
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
import re
import sys
import time
import urllib.request
import zipfile

SPICE_SCREEN_URLS = [
    "https://raw.githubusercontent.com/munimtechnologies/spice-screen/v0.4.0/spice_screen.py",
    "https://raw.githubusercontent.com/munimv2/spice-screen/v0.4.0/spice_screen.py",
]
RRUFF_URL = "https://www.rruff.net/zipped_data_files/raman/excellent_unoriented.zip"
USER_AGENT = "spice-screen RRUFF audit (MV2 of Munim, Inc.; munimversion2@gmail.com)"

# Minerals that are documented or plausible spice adulterants, fillers or
# contaminants. Matched case-insensitively against the RRUFF mineral name.
FOOD_RELEVANT = {
    "minium": "red lead Pb3O4, reported in chili and paprika",
    "litharge": "lead oxide PbO",
    "massicot": "lead oxide PbO (yellow)",
    "cerussite": "lead carbonate (white lead)",
    "hydrocerussite": "basic lead carbonate (white lead)",
    "anglesite": "lead sulfate",
    "orpiment": "arsenic sulfide (yellow pigment)",
    "realgar": "arsenic sulfide (orange-red)",
    "cinnabar": "mercury sulfide (vermilion)",
    "hematite": "iron oxide, brick powder in chili",
    "goethite": "iron oxyhydroxide, ochre",
    "magnetite": "iron oxide",
    "calcite": "chalk, calcium carbonate filler",
    "aragonite": "calcium carbonate",
    "dolomite": "carbonate filler",
    "gypsum": "calcium sulfate filler",
    "talc": "talc filler",
    "kaolinite": "clay, soil",
    "montmorillonite": "clay, soil",
    "muscovite": "mica, soil",
    "quartz": "sand, soil",
    "albite": "feldspar, soil",
    "microcline": "feldspar, soil",
    "orthoclase": "feldspar, soil",
    "barite": "barium sulfate filler",
    "rutile": "titanium dioxide",
    "anatase": "titanium dioxide (E171)",
    "halite": "salt",
    "fluorapatite": "phosphate",
    "forsterite": "olivine; bands near 825 and 856 cm-1",
}

_SPICE = None


def load_spice_screen(out_dir):
    """Download the released spice_screen.py and import it by path."""
    global _SPICE
    if _SPICE is not None:
        return _SPICE
    path = os.path.join(out_dir, "spice_screen_v0.4.0.py")
    if not os.path.exists(path):
        last = None
        for url in SPICE_SCREEN_URLS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = resp.read()
                with open(path, "wb") as fh:
                    fh.write(body)
                break
            except OSError as exc:
                last = exc
        else:
            raise RuntimeError("could not download spice_screen.py: %s" % last)
    spec = importlib.util.spec_from_file_location("spice_screen_release", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with open(path, "rb") as fh:
        mod.SHA256 = hashlib.sha256(fh.read()).hexdigest()
    _SPICE = mod
    return mod


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


def rel_height(spice, x, y, center=840.0, tol=8.0):
    """Height of the strongest point near `center` above the spectrum's median,
    as a fraction of the spectrum's strongest point above the median."""
    med = spice._median(y)
    top = max(y) - med
    near = [b for a, b in zip(x, y) if abs(a - center) <= tol]
    if not near or top <= 0:
        return None
    return round((max(near) - med) / top, 4)


def screen_text(member, text, out_dir):
    spice = load_spice_screen(out_dir)
    meta = parse_meta(text)
    mineral, rid, laser = parse_name(member)
    mineral = meta.get("NAMES", mineral) or mineral
    rid = meta.get("RRUFFID", rid) or rid
    chem = meta.get("IDEAL CHEMISTRY", "")
    row = {"file": os.path.basename(member), "mineral": mineral, "rruff_id": rid, "laser_nm": laser,
           "chemistry": chem, "group": group_of(chem), "cr_bearing": has_element(chem, "Cr"),
           "error": ""}
    try:
        x, y = spice.parse_spectrum(text)
    except ValueError as exc:
        row["error"] = str(exc)
        return row
    row["range"] = "%.0f-%.0f" % (x[0], x[-1])
    row["points"] = len(x)
    lib = {e["id"]: e for e in spice.LIBRARY}
    lc = spice.screen_entry(x, y, lib["lead_chromate"], 5.0)
    prim = next(b for b in lc["bands"] if b["center"] == 840.0)
    row.update({
        "lc_verdict": lc["verdict"],
        "lc_bands_detected": lc["bands_detected"],
        "snr840": prim["snr"],
        "pos840": prim["position"],
        "rel840": rel_height(spice, x, y) if prim["covered"] else None,
    })
    if "metanil_yellow_raman" in lib:
        my = spice.screen_entry(x, y, lib["metanil_yellow_raman"], 5.0)
        row["my_verdict"] = my["verdict"]
    return row


def _work(item):
    member, text, out_dir = item
    try:
        return screen_text(member, text, out_dir)
    except Exception as exc:  # one bad file must not stop the audit
        return {"file": os.path.basename(member), "error": "%s: %s" % (type(exc).__name__, exc)}


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


def summarize(rows, spice_version, sha, archives, complete):
    ok = [r for r in rows if not r.get("error")]
    covered = [r for r in ok if r.get("lc_verdict") not in (None, "not-covered")]
    pos = [r for r in covered if r["lc_verdict"] == "screen-positive"]
    croc = [r for r in covered if r["mineral"].lower().startswith("crocoite")]
    cr = [r for r in covered if r["cr_bearing"] and r not in croc]
    non_cr = [r for r in covered if not r["cr_bearing"]]
    non_cr_pos = [r for r in non_cr if r["lc_verdict"] == "screen-positive"]

    def by_mineral(items):
        out = {}
        for r in items:
            d = out.setdefault(r["mineral"], {"chemistry": r["chemistry"], "group": r["group"], "n": 0,
                                              "max_rel840": 0.0, "triplet_3of3": 0})
            d["n"] += 1
            d["max_rel840"] = max(d["max_rel840"], r.get("rel840") or 0.0)
            d["triplet_3of3"] += int(r.get("lc_bands_detected") == 3)
        return dict(sorted(out.items(), key=lambda kv: (-kv[1]["max_rel840"], kv[0])))

    def frac(a, b):
        return round(a / b, 4) if b else None

    groups = {}
    for r in non_cr_pos:
        groups[r["group"]] = groups.get(r["group"], 0) + 1

    def strong(items, t):
        return [r for r in items if (r.get("rel840") or 0.0) >= t]

    food = {}
    for r in covered:
        key = r["mineral"].lower()
        if key in FOOD_RELEVANT:
            d = food.setdefault(r["mineral"], {"why": FOOD_RELEVANT[key], "n": 0, "positive": 0,
                                               "inconclusive": 0})
            d["n"] += 1
            d["positive"] += int(r["lc_verdict"] == "screen-positive")
            d["inconclusive"] += int(r["lc_verdict"] == "inconclusive")
    return {
        "tool": "spice-screen", "version": spice_version, "sha256": sha,
        "archives": [os.path.basename(a) for a in archives], "complete": complete,
        "spectra_read": len(rows), "errors": len(rows) - len(ok), "covered_840": len(covered),
        "minerals_covered": len({r["mineral"] for r in covered}),
        "screen_positive": len(pos),
        "crocoite": {"n": len(croc), "positive": sum(r["lc_verdict"] == "screen-positive" for r in croc),
                     "triplet_3of3": sum(r["lc_bands_detected"] == 3 for r in croc),
                     "rows": [{k: r.get(k) for k in ("rruff_id", "laser_nm", "lc_verdict", "lc_bands_detected",
                                                    "snr840", "pos840", "rel840")} for r in croc]},
        "other_cr_bearing": {"n": len(cr), "positive": sum(r["lc_verdict"] == "screen-positive" for r in cr),
                             "minerals_positive": by_mineral([r for r in cr if r["lc_verdict"] == "screen-positive"])},
        "non_cr": {
            "n": len(non_cr), "positive": len(non_cr_pos),
            "false_positive_rate": frac(len(non_cr_pos), len(non_cr)),
            "positive_rel840_ge_0.10": len(strong(non_cr_pos, 0.10)),
            "positive_rel840_ge_0.25": len(strong(non_cr_pos, 0.25)),
            "positive_triplet_3of3": sum(r["lc_bands_detected"] == 3 for r in non_cr_pos),
            "positive_by_group": dict(sorted(groups.items(), key=lambda kv: -kv[1])),
            "minerals_positive": by_mineral(non_cr_pos),
        },
        "food_relevant": dict(sorted(food.items())),
        "metanil_yellow_positive_on_minerals": sum(r.get("my_verdict") == "screen-positive" for r in covered),
    }


def write_markdown(s, path):
    lines = ["# spice-screen lead chromate marker vs the RRUFF Raman library", "",
             "spice-screen %s (sha256 %s), archives: %s, complete: %s." % (
                 s["version"], s["sha256"][:12], ", ".join(s["archives"]), s["complete"]),
             "Spectra read: %d (errors %d); covering 840 cm-1: %d from %d minerals; screen-positive: %d." % (
                 s["spectra_read"], s["errors"], s["covered_840"], s["minerals_covered"], s["screen_positive"]),
             "", "## Crocoite (PbCrO4), the true positive",
             "%d spectra, %d screen-positive, %d with all three triplet bands." % (
                 s["crocoite"]["n"], s["crocoite"]["positive"], s["crocoite"]["triplet_3of3"]), ""]
    lines += ["| RRUFF ID | laser | verdict | bands | SNR 840 | position | rel. height |", "|---|---|---|---|---|---|---|"]
    for r in s["crocoite"]["rows"]:
        lines.append("| %s | %s | %s | %s/3 | %s | %s | %s |" % (
            r["rruff_id"], r["laser_nm"], r["lc_verdict"], r["lc_bands_detected"], r["snr840"],
            r["pos840"], r["rel840"]))
    nc = s["non_cr"]
    lines += ["", "## Minerals without chromium (false positives)",
              "%d spectra, %d screen-positive (rate %s); %d with the 840 cm-1 point >= 10%% of the "
              "spectrum's strongest, %d >= 25%%; %d with all three triplet bands." % (
                  nc["n"], nc["positive"], nc["false_positive_rate"], nc["positive_rel840_ge_0.10"],
                  nc["positive_rel840_ge_0.25"], nc["positive_triplet_3of3"]),
              "", "By group: " + ", ".join("%s %d" % kv for kv in nc["positive_by_group"].items()), "",
              "| mineral | chemistry | spectra | max rel. height | 3/3 bands |", "|---|---|---|---|---|"]
    for name, d in list(nc["minerals_positive"].items())[:60]:
        lines.append("| %s | %s | %d | %.2f | %d |" % (name, d["chemistry"], d["n"], d["max_rel840"], d["triplet_3of3"]))
    oc = s["other_cr_bearing"]
    lines += ["", "## Other chromium-bearing minerals",
              "%d spectra, %d screen-positive." % (oc["n"], oc["positive"]), "",
              "## Spice adulterants and fillers in the library", "",
              "| mineral | why it matters | spectra | positive | inconclusive |", "|---|---|---|---|---|"]
    for name, d in s["food_relevant"].items():
        lines.append("| %s | %s | %d | %d | %d |" % (name, d["why"], d["n"], d["positive"], d["inconclusive"]))
    lines += ["", "Metanil yellow (normal Raman) screen-positive on minerals: %d." % s["metanil_yellow_positive_on_minerals"],
              "", "RRUFF data: Lafuente et al. (2015), The power of databases: the RRUFF project. "
              "Spectra are not redistributed here."]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


FIELDS = ["file", "mineral", "rruff_id", "laser_nm", "chemistry", "group", "cr_bearing", "range", "points",
          "lc_verdict", "lc_bands_detected", "snr840", "pos840", "rel840", "my_verdict", "error"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--limit", type=int, default=0, help="stop after this many spectra (0 = all)")
    ap.add_argument("--budget-min", type=float, default=200.0, help="stop submitting work after this many minutes")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    spice = load_spice_screen(args.out_dir)
    print("spice-screen %s sha256 %s" % (spice.__version__, spice.SHA256), flush=True)
    archives = find_archives(args.data_dir)
    print("archives: %s" % archives, flush=True)

    start = time.time()
    rows, complete = [], True
    items = ((m, t, args.out_dir) for m, t in iter_members(archives, args.limit))
    with mp.Pool(args.workers) as pool:
        for row in pool.imap_unordered(_work, items, chunksize=4):
            rows.append(row)
            if len(rows) % 250 == 0:
                print("%d spectra, %.1f min" % (len(rows), (time.time() - start) / 60), flush=True)
            if (time.time() - start) / 60 > args.budget_min:
                complete = False
                pool.terminate()
                break

    rows.sort(key=lambda r: (r.get("mineral", ""), r.get("file", "")))
    with open(os.path.join(args.out_dir, "results.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    s = summarize(rows, spice.__version__, spice.SHA256, archives, complete)
    s["minutes"] = round((time.time() - start) / 60, 1)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=1)
    write_markdown(s, os.path.join(args.out_dir, "summary.md"))
    print(json.dumps({k: s[k] for k in ("spectra_read", "covered_840", "screen_positive", "complete")}))
    print("crocoite:", json.dumps({k: v for k, v in s["crocoite"].items() if k != "rows"}))
    nc = {k: v for k, v in s["non_cr"].items() if k != "minerals_positive"}
    print("non-Cr:", json.dumps(nc))
    print("non-Cr positive minerals:", ", ".join(list(s["non_cr"]["minerals_positive"])[:40]))
    print("food-relevant:", json.dumps(s["food_relevant"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
