# tools

Scripts behind the studies in `docs/`. They need Python 3.8+ (standard library only) and
download the RRUFF archive `excellent_unoriented.zip` from rruff.net themselves. RRUFF
spectra are never redistributed here; only per-spectrum numbers are written.

| Folder | Study | Run |
|---|---|---|
| `rruff-audit/` | [docs/rruff-audit.md](../docs/rruff-audit.md): the 0.4.0 lead chromate marker on the whole library | `python tools/rruff-audit/audit.py --data-dir data --out-dir out` (downloads the v0.4.0 file) |
| `rruff-audit/audit_local.py` | the same audit on any local `spice_screen.py` | `python tools/rruff-audit/audit_local.py --spice-screen spice_screen.py --data-dir data --out-dir out` (Linux) |
| `rruff-rules/` | [docs/rruff-noise-rules.md](../docs/rruff-noise-rules.md): noise estimates, thresholds and height gates, plus crocoite + filler mixtures | copy `spice_screen.py` into `tools/rruff-rules/`, then `python tools/rruff-rules/rules.py --data-dir data --out-dir out` and `python tools/rruff-rules/mode_tests.py --out-dir out` |
| `rruff-shape/` | band-shape gates in [docs/rruff-noise-rules.md](../docs/rruff-noise-rules.md) | `python tools/rruff-shape/shape.py --data-dir data --out-dir out` (downloads the v0.4.0 file and audit CSV) |

`rules.py` as published has the quirk described in the noise-rules page: its "no gate" rules
also drop spectra whose 840 cm⁻¹ region lies below the spectrum's median. The page corrects
for it, and the per-spectrum `rel840` column lets anyone check.

Made by MV2 of Munim, Inc. with AI agents working in his name. Apache-2.0.
