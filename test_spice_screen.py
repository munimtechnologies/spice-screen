"""Offline tests for spice-screen. Run: python -m unittest -v"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spice_screen as ss  # noqa: E402

TURMERIC = ss.TURMERIC_LIKE


def verdicts(report):
    return {r["id"]: r["verdict"] for r in report["results"]}


def write_temp(text):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestFit(unittest.TestCase):
    def setUp(self):
        self.x = [800.0 + 2 * i for i in range(61)]
        self.bg = [1000.0 + 0.5 * (v - 800) + 0.001 * (v - 800) ** 2 for v in self.x]

    def test_polyfit_recovers_quadratic(self):
        x = [float(i) for i in range(100, 200)]
        y = [5.0 + 0.3 * v - 0.002 * v * v for v in x]
        p = ss.polyfit(x, y, 2)
        for v in (100.0, 150.0, 199.0):
            self.assertAlmostEqual(p(v), 5.0 + 0.3 * v - 0.002 * v * v, places=6)

    def test_polyfit_needs_enough_points(self):
        with self.assertRaises(ValueError):
            ss.polyfit([1.0, 2.0], [1.0, 2.0], 2)

    def test_modpoly_baseline_is_exact_without_peaks(self):
        base = ss.modpoly_baseline(self.x, self.bg)
        worst = max(abs(a - b) for a, b in zip(base, self.bg))
        self.assertLess(worst, 1e-6)

    def test_modpoly_baseline_keeps_most_of_a_central_peak(self):
        # In a 120 cm-1 window with a strong band in the middle, ModPoly bows a few
        # units away from the true background (measured: at most about 6.5 for a
        # 50-unit band). The band must keep most of its height above the fit.
        y = [b + 50.0 / (1 + ((v - 860) / 5) ** 2) for v, b in zip(self.x, self.bg)]
        base = ss.modpoly_baseline(self.x, y)
        worst = max(abs(a - b) for a, b in zip(base, self.bg))
        self.assertLess(worst, 10.0)
        i = self.x.index(860.0)
        self.assertGreater(y[i] - base[i], 40.0)
        self.assertLess(y[i] - base[i], 60.0)

    def test_noise_sigma_ignores_slow_trend(self):
        x, y = ss.synthetic_spectrum(noise=1.0)
        sigma = ss.noise_sigma(y)
        self.assertGreater(sigma, 0.6)
        self.assertLess(sigma, 1.5)


class TestScreen(unittest.TestCase):
    def test_clean_turmeric_is_not_detected(self):
        x, y = ss.synthetic_spectrum(TURMERIC)
        v = verdicts(ss.screen_spectrum(x, y))
        self.assertEqual(v["lead_chromate"], "not-detected")
        self.assertEqual(v["metanil_yellow_raman"], "not-detected")

    def test_lead_chromate_band_is_screen_positive(self):
        x, y = ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))
        report = ss.screen_spectrum(x, y)
        self.assertEqual(verdicts(report)["lead_chromate"], "screen-positive")
        self.assertIn("Lead chromate", report["summary"])
        band = report["results"][0]["bands"][0]
        self.assertTrue(abs(band["position"] - 840.0) <= 4.0)

    def test_weak_band_below_threshold_is_not_detected(self):
        x, y = ss.synthetic_spectrum(TURMERIC + ((840.0, 0.5),))
        self.assertEqual(verdicts(ss.screen_spectrum(x, y))["lead_chromate"], "not-detected")

    def test_band_outside_range_is_not_covered(self):
        x, y = ss.synthetic_spectrum(TURMERIC, start=1000.0)
        self.assertEqual(verdicts(ss.screen_spectrum(x, y))["lead_chromate"], "not-covered")

    def test_metanil_needs_two_bands(self):
        x, y = ss.synthetic_spectrum(TURMERIC + ((1406.0, 30.0),))
        self.assertEqual(verdicts(ss.screen_spectrum(x, y))["metanil_yellow_raman"], "inconclusive")
        x, y = ss.synthetic_spectrum(TURMERIC + ((1406.0, 30.0), (997.0, 30.0), (1147.0, 30.0)))
        report = ss.screen_spectrum(x, y)
        self.assertEqual(verdicts(report)["metanil_yellow_raman"], "screen-positive")
        self.assertEqual(verdicts(report)["lead_chromate"], "not-detected")

    def test_sers_mode_uses_sers_markers_only(self):
        x, y = ss.synthetic_spectrum(((721.0, 50.0), (1226.0, 50.0)), start=400.0)
        v = verdicts(ss.screen_spectrum(x, y, mode="sers"))
        self.assertEqual(v["sudan_i_sers"], "screen-positive")
        self.assertNotIn("lead_chromate", v)
        self.assertNotEqual(v["metanil_yellow_sers"], "screen-positive")
        self.assertEqual(v["rhodamine_b_sers"], "not-detected")

    def test_rhodamine_b_needs_three_bands(self):
        x, y = ss.synthetic_spectrum(((1645.0, 50.0),), start=400.0)
        v = verdicts(ss.screen_spectrum(x, y, mode="sers"))
        self.assertEqual(v["rhodamine_b_sers"], "inconclusive")
        peaks = ((1645.0, 50.0), (1360.0, 50.0), (1509.0, 50.0), (620.0, 50.0))
        x, y = ss.synthetic_spectrum(peaks, start=400.0)
        report = ss.screen_spectrum(x, y, mode="sers")
        v = verdicts(report)
        self.assertEqual(v["rhodamine_b_sers"], "screen-positive")
        self.assertNotEqual(v["sudan_i_sers"], "screen-positive")
        self.assertIn("Rhodamine B", report["summary"])

    def test_report_is_json_with_sources_and_disclaimer(self):
        x, y = ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))
        report = json.loads(json.dumps(ss.screen_spectrum(x, y)))
        self.assertIn("laboratory", report["disclaimer"])
        for r in report["results"]:
            self.assertTrue(r["sources"])

    def test_rejects_tiny_input(self):
        with self.assertRaises(ValueError):
            ss.screen_spectrum([1.0, 2.0], [1.0, 2.0])


class TestLibrary(unittest.TestCase):
    def test_builtin_library_is_valid(self):
        self.assertTrue(ss.validate_library(ss.LIBRARY))

    def test_every_marker_cites_a_source(self):
        for e in ss.LIBRARY:
            self.assertTrue(all(len(s) > 20 for s in e["sources"]), e["id"])
            self.assertTrue(e.get("reported_limit"), e["id"])

    def test_bad_entry_is_rejected(self):
        bad = [dict(ss.LIBRARY[0], primary=999.0)]
        with self.assertRaises(ValueError):
            ss.validate_library(bad)
        with self.assertRaises(ValueError):
            ss.validate_library([dict(ss.LIBRARY[0], sources=[])])


class TestParse(unittest.TestCase):
    def test_formats_headers_and_order(self):
        rows = [(200.0 + 10 * i, 100.0 + i) for i in range(20)]
        comma = "# exported\nshift,intensity\n" + "\n".join("%g,%g" % r for r in reversed(rows))
        x, y = ss.parse_spectrum(comma)
        self.assertEqual(x[0], 200.0)
        self.assertEqual(y[-1], 119.0)
        semi = "\n".join("%s;%s" % (str(a).replace(".", ","), str(b).replace(".", ",")) for a, b in rows)
        self.assertEqual(ss.parse_spectrum(semi)[0][1], 210.0)
        tabs = "\n".join("%g\t%g" % r for r in rows)
        self.assertEqual(len(ss.parse_spectrum(tabs)[0]), 20)

    def test_short_input_is_rejected(self):
        with self.assertRaises(ValueError):
            ss.parse_spectrum("1,2\n3,4\n")


class TestCli(unittest.TestCase):
    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ss.main(argv)
        return code, buf.getvalue()

    def test_list_and_demo(self):
        code, out = self.run_main(["--list"])
        self.assertEqual(code, 0)
        self.assertIn("840", out)
        self.assertIn("Rhodamine B", out)
        code, out = self.run_main(["--demo"])
        self.assertEqual(code, 0)
        self.assertIn("SCREEN-POSITIVE", out)

    def test_file_json_and_exit_code(self):
        x, y = ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))
        path = write_temp("shift,intensity\n" + "\n".join("%.1f,%.4f" % p for p in zip(x, y)))
        try:
            code, out = self.run_main([path, "--json", "--exit-code"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["tool"], "spice-screen")
            code, _ = self.run_main([path])
            self.assertEqual(code, 0)
        finally:
            os.remove(path)

    def test_custom_library(self):
        lib = [{"id": "x", "name": "Test marker", "mode": "raman", "bands": [840.0],
                "primary": 840.0, "min_bands": 1, "sources": ["test"]}]
        lib_path = write_temp(json.dumps(lib))
        x, y = ss.synthetic_spectrum(((840.0, 40.0),))
        spec_path = write_temp("\n".join("%.1f,%.4f" % p for p in zip(x, y)))
        try:
            code, out = self.run_main([spec_path, "--library", lib_path, "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["results"][0]["verdict"], "screen-positive")
        finally:
            os.remove(lib_path)
            os.remove(spec_path)

    def test_missing_file_is_an_error(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code, _ = self.run_main(["no-such-file.csv"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
