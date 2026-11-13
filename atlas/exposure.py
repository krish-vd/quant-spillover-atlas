"""How each Indian sector responds to each foreign market.

``pass_through``: regress a sector's gap, its open-to-close move and its whole-day move
on one overnight cue. The slopes add up (gap + intraday = whole day, approximately), so

    priced_at_open = beta_gap / beta_whole_day

is the share of the sector's eventual response that is already in the 09:15 price. A
value near 100% means nothing is left to trade after the open; above 100% means the open
overshoots and part of it reverses during the day.

``co_movement``: correlation of each sector's whole day with each foreign market over the
same close-to-close window (see ``panel.synchronised``), for the exposure heatmap.

``holm``: Holm-Bonferroni adjustment, applied whenever many tests are reported together.
"""
from __future__ import annotations

import numpy as np

from .panel import Panel


def _beta(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 30 or x.std() == 0:
        return float("nan"), float("nan"), int(len(x))
    xc = x - x.mean()
    beta = float((xc * (y - y.mean())).sum() / (xc ** 2).sum())
    corr = float(np.corrcoef(x, y)[0, 1])
    return beta, corr, int(len(x))


def pass_through(panel: Panel, sector: str, cue: str) -> dict:
    x = panel[cue]
    out = {"sector": sector, "cue": cue}
    for part in ("gap", "intraday", "cc"):
        beta, corr, n = _beta(x, panel[f"{sector}:{part}"])
        out[f"beta_{part}"] = round(beta, 4)
        out[f"corr_{part}"] = round(corr, 4)
        out["sessions"] = n
    if np.isfinite(out["beta_cc"]) and abs(out["beta_cc"]) > 1e-9:
        out["priced_at_open_pct"] = round(out["beta_gap"] / out["beta_cc"] * 100, 1)
    else:
        out["priced_at_open_pct"] = None
    return out


def co_movement(names: list[str], Y: np.ndarray, sectors: list[str], foreign: list[str]) -> list[dict]:
    corr = np.corrcoef(Y, rowvar=False)
    idx = {n: i for i, n in enumerate(names)}
    return [{"sector": s, "market": f, "corr": round(float(corr[idx[s], idx[f]]), 4)}
            for s in sectors for f in foreign if s in idx and f in idx]


def rolling_corr(x: np.ndarray, y: np.ndarray, dates: list, window: int = 250, step: int = 21) -> list[dict]:
    ok = np.isfinite(x) & np.isfinite(y)
    xs, ys = x[ok], y[ok]
    ds = [d for d, k in zip(dates, ok) if k]
    return [{"date": ds[e - 1].isoformat(), "corr": round(float(np.corrcoef(xs[e - window:e], ys[e - window:e])[0, 1]), 4)}
            for e in range(window, len(xs) + 1, step)]


def holm(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, in the original order."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [1.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted
