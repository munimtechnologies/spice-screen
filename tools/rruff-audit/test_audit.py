import os
import random
import tempfile
import unittest

import audit


def rruff_text(name, chem, peaks, start=100.0, stop=1300.0, step=1.0):
    lines = ["##NAMES=%s" % name, "##RRUFFID=R000001", "##IDEAL CHEMISTRY=%s" % chem]
    rng = random.Random(11)
    v = start
    while v <= stop:
        y = 10.0 + sum(h / (1.0 + ((v - c) / 5.0) ** 2) for c, h in peaks)
        y += rng.gauss(0.0, 0.5)
        lines.append("%.2f, %.4f" % (v, y))
        v += step
    lines.append("##END=")
    return "\n".join(lines)


class TestParsing(unittest.TestCase):
    def test_name(self):
        m, rid, laser = audit.parse_name(
            "excellent_unoriented/Crocoite__R050080__Raman__532__0__unoriented__Raman_Data_Processed__21434.txt")
        self.assertEqual((m, rid, laser), ("Crocoite", "R050080", "532"))

    def test_meta(self):
        meta = audit.parse_meta("##NAMES=Crocoite\n##IDEAL CHEMISTRY=Pb(CrO_4_)\n1, 2\n")
        self.assertEqual(meta["NAMES"], "Crocoite")
        self.assertEqual(meta["IDEAL CHEMISTRY"], "Pb(CrO_4_)")

    def test_elements(self):
        self.assertTrue(audit.has_element("Pb(CrO_4_)", "Cr"))
        self.assertFalse(audit.has_element("CaCO_3_", "Cr"))
        self.assertTrue(audit.has_element("Ca_5_(PO_4_)_3_F", "P"))
        self.assertFalse(audit.has_element("Cs_2_O", "C"))
        self.assertEqual(audit.group_of("Pb_5_(VO_4_)_3_Cl"), "vanadium-bearing")
        self.assertEqual(audit.group_of("Mg_2_SiO_4_"), "silicate")


class TestScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp()
        try:
            audit.load_spice_screen(cls.out)
        except RuntimeError as exc:
            raise unittest.SkipTest(str(exc))

    def test_crocoite_like_is_positive(self):
        text = rruff_text("Crocoite", "Pb(CrO_4_)", [(841.0, 400.0), (825.0, 120.0), (856.0, 150.0), (360.0, 200.0)])
        row = audit.screen_text("Crocoite__R000001__Raman__532__x.txt", text, self.out)
        self.assertEqual(row["error"], "")
        self.assertTrue(row["cr_bearing"])
        self.assertEqual(row["lc_verdict"], "screen-positive")
        self.assertGreater(row["rel840"], 0.5)

    def test_calcite_like_is_not_positive(self):
        text = rruff_text("Calcite", "CaCO_3_", [(1086.0, 500.0), (712.0, 60.0), (282.0, 120.0)])
        row = audit.screen_text("Calcite__R000002__Raman__532__x.txt", text, self.out)
        self.assertFalse(row["cr_bearing"])
        self.assertNotEqual(row["lc_verdict"], "screen-positive")

    def test_summary_counts(self):
        rows = [
            audit.screen_text("Crocoite__R1__Raman__532__a.txt",
                              rruff_text("Crocoite", "Pb(CrO_4_)", [(841.0, 400.0)]), self.out),
            audit.screen_text("Calcite__R2__Raman__532__b.txt",
                              rruff_text("Calcite", "CaCO_3_", [(1086.0, 500.0)]), self.out),
        ]
        s = audit.summarize(rows, "0.4.0", "0" * 64, ["x.zip"], True)
        self.assertEqual(s["crocoite"]["n"], 1)
        self.assertEqual(s["crocoite"]["positive"], 1)
        self.assertEqual(s["non_cr"]["n"], 1)
        self.assertEqual(s["non_cr"]["positive"], 0)
        self.assertEqual(s["food_relevant"]["Calcite"]["n"], 1)
        audit.write_markdown(s, os.path.join(self.out, "summary.md"))


if __name__ == "__main__":
    unittest.main()
