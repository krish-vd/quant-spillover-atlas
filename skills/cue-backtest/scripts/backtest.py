#!/usr/bin/env python3
"""Walk-forward test: can global cues known before 09:15 IST forecast Nifty sectors?

    python scripts/backtest.py                          # every sector, gap and open-to-close
    python scripts/backtest.py --sector it --by-year
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

from atlas import models, study  # noqa: E402
from atlas.data import DataUnavailable  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sector", help="comma-separated: nifty, it, bank, metal, pharma, auto, energy, fmcg (default all)")
    p.add_argument("--by-year", action="store_true", help="include the hit rate for each year")
    a = p.parse_args()
    try:
        panel, failed = study.load_panel()
        rows = study.forecasts(panel)   # always all sectors: the multiple-testing adjustment covers every test run
    except (DataUnavailable, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    tests_run = len(rows)
    if a.sector:
        keep = {s.strip() for s in a.sector.split(",")}
        rows = [r for r in rows if r["sector"] in keep]
    if not a.by_year:
        for r in rows:
            r.pop("by_year", None)
    print(json.dumps({
        "sample": {"first": panel.dates[0].isoformat(), "last": panel.dates[-1].isoformat(), "sessions": len(panel.dates)},
        "design": {
            "features": "overnight returns of US, European, commodity, currency, VIX, yield and ADR markets since India's "
                        "last close, plus each Asian market's opening gap; nothing known only after 09:15",
            "model": f"ridge regression (penalty {models.RIDGE}, fixed in advance), refitted every {models.REFIT_EVERY} "
                     f"sessions on data strictly before the forecast window; first {models.MIN_TRAIN} sessions train only",
            "targets": "gap = open / previous close - 1 (set at 09:15, not tradable from the open); "
                       "intraday = close / open - 1 (the tradable part)",
            "multiple_testing": f"Holm-Bonferroni across all {tests_run} sector-target tests",
        },
        "results": rows,
        "unavailable": failed,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
