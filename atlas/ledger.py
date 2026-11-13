"""A live forward-test record: forecasts written down before the outcome exists.

``record()`` appends the morning brief's forecasts to a local JSON-lines file with the time
they were made. Only forecasts made before India opens (09:15 IST = 03:45 UTC) on the
session they forecast count as forward tests; later ones are stored but marked late and
never scored, so the record cannot be improved with hindsight.

``score()`` matches each counted forecast with NSE's official open and close for that
session and reports hit rates. This is the strongest evidence a model can give: these
forecasts did not exist when the walk-forward study was designed.

The file lives in ~/.quant-spillover-atlas/ (or SPILLOVER_ATLAS_HOME), outside the
repository and outside the price cache.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

INDIA_OPEN_UTC_HOURS = 3.75


def ledger_path() -> Path:
    root = Path(os.environ.get("SPILLOVER_ATLAS_HOME") or Path.home() / ".quant-spillover-atlas")
    root.mkdir(parents=True, exist_ok=True)
    return root / "forecast_ledger.jsonl"


def _before_open(session: str, generated_utc: str) -> bool:
    made = datetime.strptime(generated_utc, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    d = date.fromisoformat(session)
    open_at = datetime(d.year, d.month, d.day, 3, 45, tzinfo=timezone.utc)
    return made < open_at


def record(brief: dict, path: Path | None = None) -> dict:
    path = path or ledger_path()
    entry = {
        "session": brief["for_session"],
        "generated_utc": brief["generated_utc"],
        "before_open": _before_open(brief["for_session"], brief["generated_utc"]),
        "notes": brief.get("notes", []),
        "forecasts": {s["sector"]: {"gap_bps": s["gap"]["expected_bps"], "gap_high_confidence": s["gap"]["high_confidence"],
                                    "intraday_bps": s["intraday"]["expected_bps"]} for s in brief["sectors"]},
    }
    existing = load(path)
    if any(e["session"] == entry["session"] and e["before_open"] for e in existing) and entry["before_open"]:
        return {"recorded": False, "reason": f"a pre-open forecast for {entry['session']} is already recorded; the first one stands"}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"recorded": True, "counts_as_forward_test": entry["before_open"], "path": str(path),
            "reason": None if entry["before_open"] else "made after 09:15 IST: stored but never scored"}


def load(path: Path | None = None) -> list[dict]:
    path = path or ledger_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(actuals: dict, path: Path | None = None) -> dict:
    """``actuals``: {(sector, session_iso): (gap, intraday)} from official prices."""
    entries = [e for e in load(path) if e["before_open"]]
    first = {}
    for e in entries:
        first.setdefault(e["session"], e)        # the first pre-open forecast for a session stands
    rows, tallies = [], {}
    for session, e in sorted(first.items()):
        for sector, f in e["forecasts"].items():
            actual = actuals.get((sector, session))
            if actual is None:
                continue
            gap, intraday = actual
            row = {"session": session, "sector": sector,
                   "gap_forecast_bps": f["gap_bps"], "gap_actual_bps": round(gap * 1e4, 1),
                   "gap_right": (f["gap_bps"] > 0) == (gap > 0) if gap != 0 else None,
                   "intraday_forecast_bps": f["intraday_bps"], "intraday_actual_bps": round(intraday * 1e4, 1),
                   "intraday_right": (f["intraday_bps"] > 0) == (intraday > 0) if intraday != 0 else None,
                   "high_confidence": f["gap_high_confidence"]}
            rows.append(row)
            for key in ("gap", "intraday") + (("gap_high_confidence",) if f["gap_high_confidence"] else ()):
                field = "gap_right" if key.startswith("gap") else "intraday_right"
                if row[field] is not None:
                    t = tallies.setdefault(key, [0, 0])
                    t[0] += int(row[field])
                    t[1] += 1
    return {
        "forward_sessions": len({r["session"] for r in rows}),
        "pending_sessions": sorted(s for s in first if not any(r["session"] == s for r in rows)),
        "hit_rates": {k: {"hit_rate": round(h / n, 4), "forecasts": n} for k, (h, n) in tallies.items()},
        "rows": rows,
        "reading": "Forward-test record: every forecast here was written before 09:15 IST on its session. "
                   "Fewer than about 60 sessions is too few to judge; compare with the walk-forward rates.",
    }
