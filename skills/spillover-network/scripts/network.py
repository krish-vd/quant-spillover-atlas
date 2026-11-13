#!/usr/bin/env python3
"""Diebold-Yilmaz spillover network between world markets and Nifty sectors.

    python scripts/network.py                      # sector level: 9 world markets + 7 Nifty sectors
    python scripts/network.py --level country      # 9 world markets + Nifty 50
    python scripts/network.py --history            # add the rolling total index
    python scripts/network.py --start 2020-01-01 --end 2020-12-31   # one period only
"""
import argparse
import json
import pathlib
import sys
from datetime import date

_here = pathlib.Path(__file__).resolve()
for _candidate in (_here.parent / "_vendor", *_here.parents):
    if (_candidate / "atlas" / "__init__.py").exists():
        sys.path.insert(0, str(_candidate))
        break
else:
    sys.exit("atlas not found: run from the repository, or install the skill with scripts/install_skills.py")

from atlas import connectedness as C  # noqa: E402
from atlas import panel as P  # noqa: E402
from atlas import study  # noqa: E402
from atlas import universe as U  # noqa: E402
from atlas.data import DataUnavailable  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--level", choices=["sector", "country"], default="sector")
    p.add_argument("--start", help="YYYY-MM-DD")
    p.add_argument("--end", help="YYYY-MM-DD")
    p.add_argument("--lags", type=int, default=1, help="VAR order (default 1)")
    p.add_argument("--horizon", type=int, default=10, help="forecast horizon in sessions (default 10)")
    p.add_argument("--history", action="store_true", help="rolling total index (500-session window, monthly)")
    p.add_argument("--edges", type=int, default=20, help="strongest directed links to list")
    a = p.parse_args()
    try:
        panel, failed = study.load_panel()
        panel = panel.window(date.fromisoformat(a.start) if a.start else None, date.fromisoformat(a.end) if a.end else None)
        if a.level == "country":
            markets = [m for m in U.ALL if m.kind == "equity"] + [U.get("nifty")]
        else:
            markets = [m for m in U.ALL if m.kind in ("equity", "sector") and m.key != "nifty"]
        names, Y, dates = P.synchronised(panel, markets)
        theta, summary = C.connectedness(Y, names, a.lags, a.horizon)
    except (DataUnavailable, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    foreign = [i for i, n in enumerate(names) if U.get(n).timing != "india"]
    out = {
        "level": a.level,
        "sample": {"first": dates[0].isoformat(), "last": dates[-1].isoformat(), "sessions": len(dates)},
        "method": f"VAR({a.lags}) on standardised close-to-close returns aligned to India's close; "
                  f"{a.horizon}-session generalised variance decomposition (Diebold-Yilmaz 2012)",
        **summary,
        "share_from_abroad_pct": {names[i]: round(float(theta[i, foreign].sum() * 100), 2)
                                  for i in range(len(names)) if U.get(names[i]).timing == "india"},
        "strongest_links": C.pairwise_net(theta, names, a.edges),
        "names": {n: U.get(n).name for n in names},
        "unavailable": failed,
        "reading": "Shares of forecast-error variance. 'Net' measures who moves first in each 24-hour cycle and who follows; "
                   "it is a statistical ordering, not proof that one market causes another's move.",
    }
    if a.history:
        out["rolling_total_index"] = C.rolling_total(Y, dates, 500, 21, a.lags, a.horizon)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
