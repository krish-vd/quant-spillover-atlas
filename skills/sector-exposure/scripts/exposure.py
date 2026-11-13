#!/usr/bin/env python3
"""Which foreign markets each Nifty sector moves with, and how much is priced at the open.

    python scripts/exposure.py --sector it
    python scripts/exposure.py --sector metal --cue copper:overnight --rolling
    python scripts/exposure.py --list-cues
"""
import argparse
import json
import pathlib
import sys

_here = pathlib.Path(__file__).resolve()
for _candidate in (_here.parent / "_vendor", *_here.parents):
    if (_candidate / "atlas" / "__init__.py").exists():
        sys.path.insert(0, str(_candidate))
        break
else:
    sys.exit("atlas not found: run from the repository, or install the skill with scripts/install_skills.py")

from atlas import exposure, study  # noqa: E402
from atlas import panel as P  # noqa: E402
from atlas import universe as U  # noqa: E402
from atlas.data import DataUnavailable  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sector", default="nifty", help="nifty, it, bank, metal, pharma, auto, energy, fmcg")
    p.add_argument("--cue", help="one cue, e.g. ndx:overnight or kospi:gap (default: all)")
    p.add_argument("--rolling", action="store_true", help="one-year rolling correlation of the sector's day with --cue")
    p.add_argument("--list-cues", action="store_true")
    a = p.parse_args()
    try:
        panel, failed = study.load_panel()
    except (DataUnavailable, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    cues = P.forecast_features(panel, list(U.ALL))
    if a.list_cues:
        print(json.dumps({c: U.get(c.split(":")[0]).name for c in cues}, indent=2))
        return 0
    if f"{a.sector}:cc" not in panel.cols:
        p.error(f"unknown sector {a.sector!r}")
    chosen = [a.cue] if a.cue else cues
    unknown = [c for c in chosen if c not in panel.cols]
    if unknown:
        p.error(f"unknown cue(s) {unknown}; see --list-cues")
    rows = sorted((exposure.pass_through(panel, a.sector, c) for c in chosen), key=lambda r: -abs(r["corr_cc"] or 0))
    out = {
        "sector": U.get(a.sector).name,
        "sample": {"first": panel.dates[0].isoformat(), "last": panel.dates[-1].isoformat()},
        "pass_through": rows,
        "reading": "beta_x: sector move per 1.0 move in the cue (per point for VIX and the 10-year yield). "
                   "priced_at_open_pct: share of the whole-day response already in the 09:15 price; above 100 means the "
                   "open overshoots and part reverses during the day.",
        "unavailable": failed,
    }
    if a.rolling:
        if not a.cue:
            p.error("--rolling needs --cue")
        out["rolling_one_year_corr"] = exposure.rolling_corr(panel[a.cue], panel[f"{a.sector}:cc"], panel.dates)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
