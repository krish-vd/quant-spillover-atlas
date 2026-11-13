"""Is anything tradable after costs? Pre-registered intraday strategies, net of costs.

Every strategy is decided at 09:15 from information available then and closed at
15:30 the same day (no overnight risk). All are evaluated on the same out-of-sample
sessions as the forecasting study. The hypotheses are fixed in ``HYPOTHESES`` before any
result is seen, and p-values are Holm-adjusted across all of them.

Costs (round trip, in basis points of notional) are an explicit, editable assumption:

  index futures (Nifty, Bank Nifty)
    STT on the sell side: 0.02% until 31 Mar 2026, 0.05% from 1 Apr 2026
    exchange, stamp duty, SEBI fee and GST: about 0.7 bps
    slippage: 1 bp per side
    -> about 4.7 bps before April 2026 and 7.7 bps after
  stock basket (Nifty Metal has no future; a basket of its stocks)
    STT 0.025% on the sell side, exchange, stamp and GST about 1 bp, slippage 2 bps per side
    -> about 7.5 bps

The results are also shown across a grid of costs, so a reader with different costs can
read off their own answer. Index levels stand in for the instruments: futures track the
index closely within a day, and a basket tracks its index less closely.
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np

from . import models
from . import panel as P
from .exposure import holm
from .robustness import features_for

STT_CHANGE = date(2026, 4, 1)
COST_GRID_BPS = (0, 2, 5, 8, 12)


def cost_bps(day: date, instrument: str) -> float:
    if instrument == "futures":
        return (2.0 if day < STT_CHANGE else 5.0) + 0.7 + 2.0
    return 2.5 + 1.0 + 4.0


HYPOTHESES = (
    # name, sector, instrument, rule, description
    ("fade_gap_bank", "bank", "futures", "fade", "Trade against Bank Nifty's opening gap every day"),
    ("fade_gap_nifty", "nifty", "futures", "fade", "Trade against the Nifty 50's opening gap every day"),
    ("fade_large_gap_bank", "bank", "futures", "fade_large", "Fade Bank Nifty's gap only when it is in the largest third (threshold from past data)"),
    ("model_nifty", "nifty", "futures", "model", "Follow the walk-forward open-to-close forecast for the Nifty 50"),
    ("model_bank", "bank", "futures", "model", "Follow the walk-forward open-to-close forecast for Bank Nifty"),
    ("model_metal", "metal", "basket", "model", "Follow the walk-forward open-to-close forecast for Nifty Metal (stock basket)"),
    ("copper_metal", "metal", "basket", "copper", "Go with copper's overnight direction in Nifty Metal (stock basket)"),
)


def _newey_west_t(x: np.ndarray, lags: int = 5) -> float:
    n = len(x)
    if n < 30:
        return float("nan")
    e = x - x.mean()
    s = (e @ e) / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")


def _signals(panel: P.Panel, sector: str, rule: str) -> np.ndarray:
    gap = panel[f"{sector}:gap"]
    n = len(gap)
    if rule == "fade":
        return -np.sign(gap)
    if rule == "fade_large":
        out = np.zeros(n)
        for start in range(models.MIN_TRAIN, n, models.REFIT_EVERY):
            past = np.abs(gap[:start])
            cut = np.nanquantile(past[np.isfinite(past)], 2 / 3)
            block = slice(start, min(start + models.REFIT_EVERY, n))
            out[block] = np.where(np.abs(gap[block]) > cut, -np.sign(gap[block]), 0.0)
        return out
    if rule == "copper":
        return np.sign(panel["copper:overnight"])
    if rule == "model":
        feats = features_for(panel, sector, "intraday")
        X = np.column_stack([panel[f] for f in feats])
        return np.sign(models.walk_forward(X, panel[f"{sector}:intraday"], feats).pred)
    raise ValueError(rule)


def evaluate(panel: P.Panel, name: str, sector: str, instrument: str, rule: str, description: str) -> dict:
    sig = _signals(panel, sector, rule)
    r = panel[f"{sector}:intraday"]
    oos = np.zeros(len(r), dtype=bool)
    oos[models.MIN_TRAIN:] = True
    ok = oos & np.isfinite(sig) & np.isfinite(r)
    traded = ok & (sig != 0)
    days = [d for d, k in zip(panel.dates, ok) if k]
    costs = np.array([cost_bps(d, instrument) for d in panel.dates]) / 1e4
    gross = np.where(traded, sig * r, 0.0)[ok]
    net = np.where(traded, sig * r - costs, 0.0)[ok]
    equity = np.cumsum(net)
    drawdown = float((np.maximum.accumulate(equity) - equity).max())
    t = _newey_west_t(net)
    by_year = {}
    for d, v in zip(days, net):
        by_year[d.year] = by_year.get(d.year, 0.0) + v
    years = len(days) / 252
    return {
        "name": name, "description": description, "sector": sector, "instrument": instrument,
        "sessions": int(ok.sum()), "trades": int(traded.sum()),
        "hit_rate": round(float((np.sign(sig[traded]) == np.sign(r[traded])).mean()), 4) if traded.any() else None,
        "gross_bps_per_trade": round(float((sig * r)[traded].mean() * 1e4), 2) if traded.any() else None,
        "assumed_cost_bps": f"{cost_bps(date(2026, 1, 1), instrument):.1f} before Apr 2026, {cost_bps(date(2026, 6, 1), instrument):.1f} after"
                            if instrument == "futures" else f"{cost_bps(date(2026, 1, 1), instrument):.1f}",
        "net_annual_return_pct": round(float(net.sum() / years * 100), 2),
        "net_sharpe": round(float(net.mean() / net.std() * math.sqrt(252)), 2) if net.std() > 0 else None,
        "t_newey_west": round(t, 2),
        "p_value": 0.5 * math.erfc(t / math.sqrt(2)) if math.isfinite(t) else None,
        "max_drawdown_pct": round(drawdown * 100, 2),
        "net_by_year_pct": {y: round(v * 100, 2) for y, v in sorted(by_year.items())},
        "net_annual_return_pct_by_cost_bps": {c: round(float(np.where(traded, sig * r - c / 1e4, 0.0)[ok].sum() / years * 100), 2)
                                              for c in COST_GRID_BPS},
        "breakeven_cost_bps": round(float((sig * r)[traded].mean() * 1e4), 2) if traded.any() else None,
    }


def run(panel: P.Panel) -> dict:
    rows = [evaluate(panel, *h) for h in HYPOTHESES]
    adjusted = holm([r["p_value"] if r["p_value"] is not None else 1.0 for r in rows])
    for r, a in zip(rows, adjusted):
        r["p_value_holm_adjusted"] = round(a, 4)
        r["significant_after_costs_and_adjustment"] = bool(a < 0.05 and r["net_annual_return_pct"] > 0)
    winners = [r["name"] for r in rows if r["significant_after_costs_and_adjustment"]]
    return {"hypotheses": rows,
            "verdict": (f"Significant after costs and multiple-testing adjustment: {', '.join(winners)}" if winners
                        else "No strategy is significant after costs and multiple-testing adjustment."),
            "notes": "Index levels proxy the instruments; costs are assumptions shown with a sensitivity grid. "
                     "Opening fills at the official open are optimistic for large orders."}


# Constituent check: a real copper effect should show up stock by stock in copper-linked
# businesses and NOT in a metal-index member whose business is not copper-linked.
METAL_STOCKS = ("TATASTEEL", "HINDALCO", "JSWSTEEL", "VEDL", "NMDC", "SAIL", "JINDALSTEL", "NATIONALUM", "HINDZINC")
CONTROL_STOCKS = ("COALINDIA",)


def constituent_check(panel: P.Panel, cue: str = "copper:overnight", stocks=METAL_STOCKS + CONTROL_STOCKS,
                      cost: float = 7.5) -> list[dict]:
    """Go with ``cue``'s overnight direction in each stock, open to close, on the study's out-of-sample sessions.

    Stock opens are the official pre-open auction prices, and the rule needs no Indian price,
    so the order can be placed in the 09:00-09:08 auction. Prices are from Yahoo.
    """
    from .data import DataUnavailable, load
    from .universe import Market
    signal = dict(zip(panel.dates, panel[cue]))
    start = panel.dates[models.MIN_TRAIN]
    out = []
    for name in stocks:
        try:
            b = load(Market(name.lower(), name, name + ".NS", "India", "india", "stock", 3.75, 10.0))
        except DataUnavailable:
            out.append({"stock": name, "error": "no data"})
            continue
        r = np.array([math.copysign(1.0, signal[d]) * (c / o - 1) for d, o, c in zip(b.dates, b.open, b.close)
                      if d >= start and d in signal and np.isfinite(signal[d]) and signal[d] != 0 and o > 0])
        by_year: dict[int, list] = {}
        days = [d for d, o in zip(b.dates, b.open) if d >= start and d in signal and np.isfinite(signal[d]) and signal[d] != 0 and o > 0]
        for d, v in zip(days, r):
            by_year.setdefault(d.year, []).append(v)
        out.append({
            "stock": name, "control": name in CONTROL_STOCKS, "sessions": len(r),
            "gross_bps_per_day": round(float(r.mean() * 1e4), 1),
            "hit_rate": round(float((r > 0).mean()), 4),
            "t_newey_west": round(_newey_west_t(r), 2),
            f"net_annual_return_pct_at_{cost:g}bps": round(float((r.mean() - cost / 1e4) * 252 * 100), 1),
            "gross_bps_by_year": {y: round(float(np.mean(v) * 1e4), 1) for y, v in sorted(by_year.items())},
        })
    return out
