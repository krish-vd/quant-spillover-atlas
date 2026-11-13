#!/usr/bin/env python3
"""Morning brief: what moved abroad since India's last close and what it has historically meant
for each Nifty sector's opening gap and open-to-close move.

    python scripts/brief.py
    python scripts/brief.py --sector it,metal
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

from atlas import brief, ledger, study  # noqa: E402
from atlas.data import DataUnavailable  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sector", help="comma-separated: nifty, it, bank, metal, pharma, auto, energy, fmcg")
    p.add_argument("--record", action="store_true", help="also save the forecasts to the local forward-test record (counts only before 09:15 IST)")
    a = p.parse_args()
    try:
        panel, _ = study.load_panel()
        record = study.forecasts(panel)
        out = brief.brief(study_forecasts=record)
    except (DataUnavailable, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    if a.record:
        out["forward_test_record"] = ledger.record(out)
    if a.sector:
        keep = {s.strip() for s in a.sector.split(",")}
        out["sectors"] = [s for s in out["sectors"] if s["sector"] in keep]
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
