"""Offline tests for spice-screen. Run: python -m unittest -v"""
import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spice_screen as ss  # noqa: E402

TURMERIC = ss.TURMERIC_LIKE

# Synthetic polystyrene-like bands (positions from ss.POLYSTYRENE plus 1031.8).
PS_BANDS = ((620.9, 150.0), (1001.4, 400.0), (1031.8, 100.0), (1602.3, 200.0))


def verdicts(report):
    return {r["id"]: r["verdict"] for r in report["results"]}


def write_temp(text, folder=None, name=None):
    if folder and name:
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def spectrum_text(x, y):
    return "shift,intensity\n" + "\n".join("%.2f,%.4f" % p for p in zip(x, y))


def polystyrene_like(shift):
    """A polystyrene-like spectrum measured on an instrument whose axis is off by `shift`."""
    return ss.synthetic_spectrum(tuple((c + shift, h) for c, h in PS_BANDS), start=400.0, step=1.0)


def shifted(peaks, shift):
    return tuple((c + shift, h) for c, h in peaks)


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

    def test_vertex_of_parabola(self):
        self.assertAlmostEqual(ss._vertex(-1.0, 0.0, 1.0, 0.0, 1.0, 0.0), 0.0)
        # y = -(x - 10.3)^2 sampled at 9, 10, 11
        ys = [-(v - 10.3) ** 2 for v in (9.0, 10.0, 11.0)]
        self.assertAlmostEqual(ss._vertex(9.0, 10.0, 11.0, *ys), 10.3)


class TestScreen(unittest.TestCase):
    def test_clean_turmeric_is_not_detected(self):
        x, y = ss.synthetic_spectrum(TURMERIC)
        report = ss.screen_spectrum(x, y)
        v = verdicts(report)
        self.assertEqual(v["lead_chromate"], "not-detected")
        self.assertEqual(v["metanil_yellow_raman"], "not-detected")
        self.assertEqual(report["result"], "not-detected")

    def test_lead_chromate_band_is_screen_positive(self):
        x, y = ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))
        report = ss.screen_spectrum(x, y)
        self.assertEqual(verdicts(report)["lead_chromate"], "screen-positive")
        self.assertEqual(report["result"], "screen-positive")
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
        self.assertNotEqual(v["auramine_o_sers"], "screen-positive")

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

    def test_auramine_o_needs_three_bands(self):
        x, y = ss.synthetic_spectrum(((778.0, 50.0),), start=400.0)
        self.assertEqual(verdicts(ss.screen_spectrum(x, y, mode="sers"))["auramine_o_sers"], "inconclusive")
        peaks = ((778.0, 50.0), (551.0, 50.0), (649.0, 50.0), (1189.0, 50.0))
        x, y = ss.synthetic_spectrum(peaks, start=400.0)
        report = ss.screen_spectrum(x, y, mode="sers")
        v = verdicts(report)
        self.assertEqual(v["auramine_o_sers"], "screen-positive")
        for other in ("sudan_i_sers", "rhodamine_b_sers", "metanil_yellow_sers"):
            self.assertNotEqual(v[other], "screen-positive", other)
        self.assertIn("Auramine O", report["summary"])

    def test_report_is_json_with_sources_and_disclaimer(self):
        x, y = ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))
        report = json.loads(json.dumps(ss.screen_spectrum(x, y)))
        self.assertIn("laboratory", report["disclaimer"])
        self.assertNotIn("calibration", report)
        for r in report["results"]:
            self.assertTrue(r["sources"])

    def test_rejects_tiny_input(self):
        with self.assertRaises(ValueError):
            ss.screen_spectrum([1.0, 2.0], [1.0, 2.0])


class TestCalibration(unittest.TestCase):
    def test_well_calibrated_instrument_passes(self):
        cal = ss.calibrate(*polystyrene_like(0.0))
        self.assertTrue(cal["within_tolerance"])
        self.assertEqual([b["reference"] for b in cal["bands"]], [620.9, 1001.4, 1602.3])
        for b in cal["bands"]:
            self.assertLess(abs(b["error"]), 0.5)

    def test_shifted_axis_is_measured_and_corrected(self):
        cal = ss.calibrate(*polystyrene_like(3.3))
        self.assertFalse(cal["within_tolerance"])
        self.assertGreater(cal["max_abs_error"], 2.8)
        for b in cal["bands"]:
            self.assertLess(abs(b["error"] - 3.3), 0.5)
            self.assertLess(abs(b["corrected_error"]), 0.5)
        self.assertLess(abs(cal["slope"] - 1.0), 0.005)
        fixed = ss.apply_calibration([1004.7], cal)[0]
        self.assertLess(abs(fixed - 1001.4), 0.5)

    def test_calibration_recovers_a_band_the_raw_axis_misses(self):
        # An axis 10 cm-1 off puts lead chromate at 850, outside the 840 +/- 8 search.
        x, y = ss.synthetic_spectrum(shifted(TURMERIC + ((840.0, 40.0),), 10.0))
        self.assertNotEqual(verdicts(ss.screen_spectrum(x, y))["lead_chromate"], "screen-positive")
        cal = ss.calibrate(*polystyrene_like(10.0))
        report = ss.screen_spectrum(x, y, calibration=cal)
        self.assertEqual(verdicts(report)["lead_chromate"], "screen-positive")
        self.assertEqual(verdicts(report)["metanil_yellow_raman"], "not-detected")
        self.assertGreater(report["calibration"]["max_abs_error"], 9.0)

    def test_spectrum_without_reference_bands_is_rejected(self):
        with self.assertRaises(ValueError):
            ss.calibrate(*ss.synthetic_spectrum(start=400.0, step=1.0))


class TestLibrary(unittest.TestCase):
    def test_builtin_library_is_valid(self):
        self.assertTrue(ss.validate_library(ss.LIBRARY))

    def test_every_marker_cites_a_source(self):
        for e in ss.LIBRARY:
            self.assertTrue(all(len(s) > 20 for s in e["sources"]), e["id"])
            self.assertTrue(e.get("reported_limit"), e["id"])
        self.assertTrue(all(len(s) > 20 for s in ss.POLYSTYRENE["sources"]))

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

    def run_quiet(self, argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, out = self.run_main(argv)
        return code, out, err.getvalue()

    def test_list_and_demo(self):
        code, out = self.run_main(["--list"])
        self.assertEqual(code, 0)
        self.assertIn("840", out)
        self.assertIn("Rhodamine B", out)
        self.assertIn("Auramine O", out)
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
        code, _, err = self.run_quiet(["no-such-file.csv"])
        self.assertEqual(code, 2)
        self.assertIn("no-such-file.csv", err)

    def test_batch_csv(self):
        with tempfile.TemporaryDirectory() as d:
            pos = write_temp(spectrum_text(*ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))), d, "a.csv")
            clean = write_temp(spectrum_text(*ss.synthetic_spectrum(TURMERIC)), d, "b.csv")
            code, out = self.run_main([pos, clean, "--csv", "--exit-code"])
            self.assertEqual(code, 1)
            rows = list(csv.reader(io.StringIO(out)))
            self.assertEqual(rows[0], ["file", "result", "lead_chromate", "metanil_yellow_raman"])
            self.assertEqual(rows[1][:3], [pos, "screen-positive", "screen-positive"])
            self.assertEqual(rows[2][:3], [clean, "not-detected", "not-detected"])

    def test_batch_wildcard_and_json(self):
        with tempfile.TemporaryDirectory() as d:
            write_temp(spectrum_text(*ss.synthetic_spectrum(TURMERIC)), d, "b.csv")
            write_temp(spectrum_text(*ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))), d, "a.csv")
            code, out = self.run_main([os.path.join(d, "*.csv"), "--json"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual([os.path.basename(r["file"]) for r in data], ["a.csv", "b.csv"])
            self.assertEqual([r["result"] for r in data], ["screen-positive", "not-detected"])

    def test_batch_keeps_going_past_an_unreadable_file(self):
        with tempfile.TemporaryDirectory() as d:
            pos = write_temp(spectrum_text(*ss.synthetic_spectrum(TURMERIC + ((840.0, 40.0),))), d, "a.csv")
            code, out, _ = self.run_quiet([pos, os.path.join(d, "missing.csv"), "--csv"])
            self.assertEqual(code, 2)
            rows = list(csv.reader(io.StringIO(out)))
            self.assertEqual(rows[1][1], "screen-positive")
            self.assertTrue(rows[2][1].startswith("error:"))

    def test_calibrate_alone_and_with_a_sample(self):
        with tempfile.TemporaryDirectory() as d:
            ps = write_temp(spectrum_text(*polystyrene_like(10.0)), d, "ps.csv")
            sample = write_temp(spectrum_text(*ss.synthetic_spectrum(
                shifted(TURMERIC + ((840.0, 40.0),), 10.0))), d, "s.csv")
            code, out = self.run_main(["--calibrate", ps])
            self.assertEqual(code, 0)
            self.assertIn("polystyrene", out)
            self.assertIn("OUTSIDE", out)
            code, out = self.run_main([sample, "--calibrate", ps, "--json"])
            self.assertEqual(code, 0)
            report = json.loads(out)
            self.assertEqual(report["result"], "screen-positive")
            self.assertIn("calibration", report)
            code, out = self.run_main([sample, "--calibrate", ps])
            self.assertIn("shift axis corrected", out)

    def test_bad_calibration_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            flat = write_temp(spectrum_text(*ss.synthetic_spectrum(start=400.0, step=1.0)), d, "flat.csv")
            code, _, err = self.run_quiet(["--calibrate", flat])
            self.assertEqual(code, 2)
            self.assertIn("calibration", err)


if __name__ == "__main__":
    unittest.main()
