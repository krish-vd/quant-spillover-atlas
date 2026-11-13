#!/usr/bin/env python3
"""Live forward-test record: save the morning forecasts before 09:15 IST, score them after the close.

    python scripts/ledger.py record     # run the brief and save it (counts only before 09:15 IST)
    python scripts/ledger.py score      # score every saved pre-open forecast against NSE's official prices
    python scripts/ledger.py show       # list what is saved
"""
import argparse
import json
import pathlib
import sys
from datetime import date, timedelta

_here = pathlib.Path(__file__).resolve()
for _candidate in (_here.parent / "_vendor", *_here.parents):
    if (_candidate / "atlas" / "__init__.py").exists():
        sys.path.insert(0, str(_candidate))
        break
else:
    sys.exit("atlas not found: run from the repository, or install the skill with scripts/install_skills.py")

from atlas import brief, ledger, nse, study  # noqa: E402
from atlas.data import DataUnavailable  # noqa: E402


def actuals_for(sessions: list) -> dict:
    """Official gap and open-to-close move per sector for each session (needs the previous session too)."""
    if not sessions:
        return {}
    first = date.fromisoformat(min(sessions)) - timedelta(days=10)
    bars, _ = nse.load_sectors(first, date.today())
    out = {}
    for key, b in bars.items():
        for i in range(1, len(b.dates)):
            out[(key, b.dates[i].isoformat())] = (b.open[i] / b.close[i - 1] - 1, b.close[i] / b.open[i] - 1)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("action", choices=["record", "score", "show"])
    a = p.parse_args()
    try:
        if a.action == "record":
            panel, _ = study.load_panel()
            out = brief.brief(study_forecasts=study.forecasts(panel), panel=panel)
            result = ledger.record(out)
            result["session"] = out["for_session"]
            result["generated_utc"] = out["generated_utc"]
        elif a.action == "score":
            entries = ledger.load()
            result = ledger.score(actuals_for([e["session"] for e in entries if e["before_open"]]))
        else:
            result = {"path": str(ledger.ledger_path()), "entries": ledger.load()}
    except (DataUnavailable, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
