#!/usr/bin/env python3
"""Run the RRUFF audit (audit.py) on a local spice_screen.py instead of the
released v0.4.0 file, for example to audit a new release with the same script.

    python tools/rruff-audit/audit_local.py --spice-screen spice_screen.py --data-dir /data --out-dir /out

Every other option is passed on to audit.py. audit.py is taken from this
folder if it is there, else from the repository below. Linux only (the
workers are forked so that they share the loaded spice_screen.py).

Made by MV2 of Munim, Inc. with AI agents working in his name. Apache-2.0.
"""
import argparse
import hashlib
import importlib.util
import multiprocessing as mp
import os
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_URL = ("https://raw.githubusercontent.com/munimtechnologies/spice-screen/main/"
             "tools/rruff-audit/audit.py")
USER_AGENT = "spice-screen RRUFF audit (MV2 of Munim, Inc.; munimversion2@gmail.com)"


def load_module(name, path):
    """Import a file as module `name` and register it, so forked workers find it."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def audit_path():
    path = os.path.join(HERE, "audit.py")
    if os.path.exists(path):
        return path
    path = os.path.join(tempfile.mkdtemp(), "audit.py")
    req = urllib.request.Request(AUDIT_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp, open(path, "wb") as fh:
        fh.write(resp.read())
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spice-screen", required=True, help="the spice_screen.py to audit")
    args, rest = ap.parse_known_args(argv)
    mp.set_start_method("fork", force=True)
    audit = load_module("audit", audit_path())
    spice = load_module("spice_screen_release", os.path.abspath(args.spice_screen))
    with open(args.spice_screen, "rb") as fh:
        spice.SHA256 = hashlib.sha256(fh.read()).hexdigest()
    audit._SPICE = spice
    print("auditing spice-screen %s, noise %s" % (spice.__version__, getattr(spice, "NOISE", "diff")),
          flush=True)
    return audit.main(rest)


if __name__ == "__main__":
    sys.exit(main())
