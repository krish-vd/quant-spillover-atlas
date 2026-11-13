"""The full study in one call: forecasts, pass-through, spillover network and their history.

Everything the skills and the showcase display comes from ``run()``. Each number in its
output can be traced to one function in this package.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from . import connectedness as C
from . import data, exposure, inference, models, nse
from . import panel as P
from . import universe as U

TARGETS = ("gap", "intraday")
PASS_THROUGH_CUES = ("spx:overnight", "ndx:overnight", "sox:overnight", "sx5e:overnight", "kospi:gap",
                     "twse:gap", "hsi:gap", "nky:gap", "shcomp:gap", "copper:overnight", "brent:overnight",
                     "usdinr:overnight", "dxy:overnight", "infy_adr:overnight", "hdb_adr:overnight")


SOURCE_NOTE = {}


def load_panel(range_: str = "10y", india_source: str = "nse") -> tuple[P.Panel, list[str]]:
    """Foreign markets from Yahoo; Indian sectors from NSE's official index files by default
    (Yahoo as a fallback if NSE cannot be reached)."""
    markets = list(U.ALL)
    foreign = [m for m in markets if m.timing != "india"]
    bars, failed = data.load_many(foreign, range_)
    sectors = [m for m in markets if m.timing == "india"]
    if india_source == "nse":
        years = {"1y": 1, "2y": 2, "5y": 5, "10y": 10, "max": 10}[range_]
        try:
            official, info = nse.load_sectors(date.today() - timedelta(days=int(years * 365.25)), date.today())
            if info["sessions"] < 100:
                raise data.DataUnavailable("too few NSE index files")
            bars.update({k: b for k, b in official.items() if len(b)})
            SOURCE_NOTE.update(india="NSE official index files", sessions=info["sessions"])
        except data.DataUnavailable as exc:
            india_source = "yahoo"
            SOURCE_NOTE.update(india=f"Yahoo (NSE unavailable: {exc})")
    if india_source == "yahoo":
        more, more_failed = data.load_many(sectors, range_)
        bars.update(more)
        failed += more_failed
        SOURCE_NOTE.setdefault("india", "Yahoo")
    return P.build(bars, [m for m in markets if m.key in bars]), failed


def forecasts(panel: P.Panel, sectors=None) -> list[dict]:
    from .robustness import features_for
    rows = []
    for s in sectors or [m.key for m in U.SECTORS]:
        for t in TARGETS:
            feats = features_for(panel, s, t)   # open-to-close also sees the sector's own 09:15 gap
            X = np.column_stack([panel[f] for f in feats])
            y = panel[f"{s}:{t}"]
            wf = models.walk_forward(X, y, feats)
            sc = models.score(wf, y)
            pt = inference.pesaran_timmermann(wf.pred, y)
            lo, hi = inference.block_bootstrap_ci(inference.hits_in_order(wf.pred, y))
            sc.update(sector=s, target=t, by_year=models.by_year(wf, y, panel.dates),
                      drivers=models.coefficients(X, y, feats)[:5],
                      hit_rate_95ci=[round(lo, 4), round(hi, 4)],
                      pesaran_timmermann_z=pt.get("statistic"), pesaran_timmermann_p=pt.get("p_value"))
            rows.append(sc)
    adjusted = exposure.holm([r["p_value_vs_baseline"] for r in rows])
    for r, a in zip(rows, adjusted):
        r["p_value_holm_adjusted"] = round(a, 6)
        r["significant_after_adjustment"] = a < 0.05
    return rows


def pass_through(panel: P.Panel) -> list[dict]:
    return [exposure.pass_through(panel, m.key, cue) for m in U.SECTORS for cue in PASS_THROUGH_CUES if cue in panel.cols]


def network(panel: P.Panel) -> dict:
    sector_level = [m for m in U.ALL if m.kind in ("equity", "sector") and m.key != "nifty"]
    names, Y, dates = P.synchronised(panel, sector_level)
    theta, summary = C.connectedness(Y, names)
    foreign = [n for n in names if U.get(n).timing != "india"]
    india = [n for n in names if U.get(n).timing == "india"]
    fi = [names.index(n) for n in foreign]
    received = {n: round(float(theta[names.index(n), fi].sum() * 100), 2) for n in india}
    country = [m for m in U.ALL if m.kind == "equity"] + [U.get("nifty")]
    cn, cY, cdates = P.synchronised(panel, country)
    ctheta, csummary = C.connectedness(cY, cn)
    return {
        "sector_level": {**summary, "names": names, "matrix_pct": np.round(theta * 100, 3).tolist(),
                         "from_abroad_pct": received, "edges": C.pairwise_net(theta, names, top=40)},
        "country_level": {**csummary, "names": cn, "edges": C.pairwise_net(ctheta, cn, top=30),
                          "rolling_total": C.rolling_total(cY, cdates, window=500, step=21)},
        "sessions": len(Y), "method": "VAR(1), 10-day generalised variance decomposition, standardised returns",
        "co_movement": exposure.co_movement(names, Y, india, foreign),
    }


def run(range_: str = "10y", deep: bool = False) -> dict:
    from . import tradable
    panel, failed = load_panel(range_)
    it_ndx = exposure.rolling_corr(panel["ndx:overnight"], panel["it:cc"], panel.dates)
    return {
        "generated": date.today().isoformat(),
        "sample": {"first": panel.dates[0].isoformat(), "last": panel.dates[-1].isoformat(), "sessions": len(panel.dates)},
        "markets": [{"key": m.key, "name": m.name, "region": m.region, "timing": m.timing, "kind": m.kind,
                     "open_utc": m.open_utc, "close_utc": m.close_utc} for m in U.ALL],
        "unavailable": failed,
        "india_source": dict(SOURCE_NOTE),
        "forecasts": forecasts(panel),
        "pass_through": pass_through(panel),
        "network": network(panel),
        "rolling_it_vs_nasdaq": it_ndx,
        **({"robustness": robustness_summary(panel), "tradability": tradable.run(panel)} if deep else {}),
    }


def robustness_summary(panel: P.Panel, permutations: int = 30) -> dict:
    from .robustness import audit
    return {f"{s}:{t}": audit(panel, s, t, permutations) for s, t in (("nifty", "gap"), ("nifty", "intraday"), ("bank", "intraday"), ("metal", "intraday"))}
