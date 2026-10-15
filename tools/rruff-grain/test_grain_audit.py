"""Offline tests for the RRUFF grain-mode audit. Run: python -m unittest -v test_grain_audit"""
import json
import os
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.dirname(os.path.dirname(HERE))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import grain_audit as ga  # noqa: E402
import spice_screen as ss  # noqa: E402

NO_BENDS = tuple(p for p in ss.CHROMATE_GRAIN_LIKE if p[0] > 700.0)


def rruff_text(name, rid, chem, peaks, n=None):
    x, y = ss.synthetic_spectrum(peaks)
    if n is not None:
        x, y = x[:n], y[:n]
    head = "##NAMES=%s\n##RRUFFID=%s\n##IDEAL CHEMISTRY=%s\n" % (name, rid, chem)
    return head + "\n".join("%.2f, %.4f" % p for p in zip(x, y)) + "\n##END=\n"


def member(name, rid, laser, k):
    return "%s__%s__Raman__%s__0__unoriented__Raman_Data_Processed__%d.txt" % (name, rid, laser, k)


SPECTRA = [
    (member("Crocoite", "R000001", "785", 1), rruff_text("Crocoite", "R000001", "Pb(CrO_4_)", ss.CHROMATE_GRAIN_LIKE)),
    (member("Crocoite", "R000001", "532", 2), rruff_text("Crocoite", "R000001", "Pb(CrO_4_)", NO_BENDS)),
    # Visible lasers, so only the gate under test can fail (no bend gate below 700 nm).
    (member("Calcite", "R000002", "532", 3), rruff_text("Calcite", "R000002", "Ca(CO_3_)",
                                                        ((1086.0, 300.0), (840.0, 40.0)))),
    (member("Calcite", "R000002", "785", 4), rruff_text("Calcite", "R000002", "Ca(CO_3_)", ((1086.0, 300.0),))),
    (member("Vanadinite", "R000003", "532", 5), rruff_text("Vanadinite", "R000003", "Pb_5_(VO_4_)_3_Cl",
                                                           ((822.0, 100.0), (845.0, 80.0)))),
    (member("Junk", "R000004", "785", 6), rruff_text("Junk", "R000004", "Si", (), n=5)),
]


class TestHelpers(unittest.TestCase):
    def test_parse_name_and_laser_class(self):
        mineral, rid, laser = ga.parse_name(SPECTRA[0][0])
        self.assertEqual((mineral, rid, laser), ("Crocoite", "R000001", "785"))
        self.assertEqual(ga.laser_class("785"), "nir")
        self.assertEqual(ga.laser_class(532.0), "visible")
        self.assertEqual(ga.laser_class(""), "unknown")

    def test_kind_and_group(self):
        self.assertEqual(ga.kind_of("Crocoite", True), "crocoite")
        self.assertEqual(ga.kind_of("Calcite", False), "filler")
        self.assertEqual(ga.kind_of("Cerussite", False), "lead_pigment")
        self.assertEqual(ga.group_of("Pb_5_(VO_4_)_3_Cl"), "vanadium-bearing")
        self.assertFalse(ga.has_element("Ca(CO_3_)", "Cr"))

    def test_published_rule_matches_grain_check(self):
        for peaks, laser in ((ss.CHROMATE_GRAIN_LIKE, 785.0), (NO_BENDS, 785.0), (NO_BENDS, 532.0),
                             (((1086.0, 300.0), (840.0, 40.0)), 785.0), (((822.0, 100.0), (845.0, 80.0)), None)):
            x, y = ss.synthetic_spectrum(peaks)
            row = ga.measure(x, y, laser)
            self.assertEqual(ga.passes(row, *ga.PUBLISHED), row["grain"] == "screen-positive", (peaks, laser))
        self.assertIn(ga.PUBLISHED, ga.rule_grid())


class TestAuditRun(unittest.TestCase):
    def test_end_to_end_on_a_small_archive(self):
        with tempfile.TemporaryDirectory() as data, tempfile.TemporaryDirectory() as out:
            with zipfile.ZipFile(os.path.join(data, "excellent_unoriented.zip"), "w") as zf:
                for name, text in SPECTRA:
                    zf.writestr(name, text)
            self.assertEqual(ga.main(["--data-dir", data, "--out-dir", out, "--workers", "1"]), 0)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as fh:
                s = json.load(fh)
            for name in ("grain.csv", "mixtures.csv", "summary.md"):
                self.assertTrue(os.path.exists(os.path.join(out, name)), name)

        self.assertEqual(s["spectra_read"], 6)
        self.assertEqual(s["errors"], 1)
        self.assertEqual(s["rule_mismatch_count"], 0)
        croc = {r["laser_nm"]: r for r in s["crocoite"]}
        self.assertEqual(croc["785"]["grain"], "screen-positive")
        self.assertEqual(croc["532"]["grain"], "screen-positive")
        self.assertEqual(s["non_cr_grain_positive"], [])
        self.assertEqual(s["by_class"]["filler/visible"]["base"], 1)
        self.assertEqual(s["by_class"]["filler/visible"]["failed"], {"dominance": 1})
        self.assertEqual(s["by_class"]["filler/nir"]["base"], 0)
        self.assertEqual(s["by_class"]["other/visible"]["failed"], {"apex": 1})
        published = [g for g in s["grid"] if g["published"]]
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["crocoite_nir"], 1)
        self.assertEqual(published[0]["crocoite_visible"], 1)
        self.assertEqual(published[0]["non_cr_visible"], 0)
        m = s["mixtures"]
        self.assertEqual((m["crocoite_spectra"], m["filler_spectra"], m["n"], m["errors"]), (2, 2, 10, 0))
        self.assertIn("nir f=0.7", m["table"])
        self.assertIn("visible f=0", m["table"])


if __name__ == "__main__":
    unittest.main()
