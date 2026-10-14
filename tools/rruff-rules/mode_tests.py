#!/usr/bin/env python3
"""Run spice-screen's unit tests once per noise mode, with that mode as the
default, and write mode_tests.json: which tests would fail if it shipped as
the default. Always exits 0 so the job goes on to the data run.
Made by MV2 of Munim, Inc. with AI agents working in his name. Apache-2.0."""
import argparse
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spice_screen as ss  # noqa: E402
import test_spice_screen  # noqa: E402


def run_mode(mode):
    ss.NOISE = mode
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_spice_screen)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=1).run(suite)
    bad = result.failures + result.errors
    return {"mode": mode, "run": result.testsRun, "failed": len(bad),
            "tests": [str(t) for t, _ in bad], "details": [tb[-1200:] for _, tb in bad]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    default = ss.NOISE
    out = [run_mode(m) for m in ss.NOISE_MODES]
    ss.NOISE = default
    with open(os.path.join(args.out_dir, "mode_tests.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    for r in out:
        print("%-8s %d tests, %d failed %s" % (r["mode"], r["run"], r["failed"], r["tests"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
