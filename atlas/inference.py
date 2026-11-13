"""Statistical inference for direction forecasts.

pesaran_timmermann   The standard test of directional accuracy (Pesaran and Timmermann,
                     1992). It compares the hit rate with the rate expected if forecasts
                     and outcomes were independent, given how often each is positive, so
                     a forecast cannot look skilful merely by saying "up" in a rising market.
block_bootstrap_ci   Confidence interval for a hit rate that respects serial dependence:
                     circular block bootstrap (Politis and Romano, 1992), blocks of
                     consecutive sessions resampled together.
calibration          Brier score of probability forecasts against the climatological
                     forecast (always the training-period frequency), reliability by
                     probability bin, and hit rate by forecast-size quintile.
"""
from __future__ import annotations

import math

import numpy as np


def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2))


def pesaran_timmermann(pred: np.ndarray, y: np.ndarray) -> dict:
    mask = np.isfinite(pred) & np.isfinite(y) & (y != 0) & (pred != 0)
    f, a = pred[mask] > 0, y[mask] > 0
    n = int(mask.sum())
    if n < 30:
        return {"n": n, "statistic": None, "p_value": None}
    p_hat = float((f == a).mean())
    py, px = float(a.mean()), float(f.mean())
    p_star = py * px + (1 - py) * (1 - px)
    v_p = p_star * (1 - p_star) / n
    v_star = ((2 * py - 1) ** 2 * px * (1 - px) / n + (2 * px - 1) ** 2 * py * (1 - py) / n
              + 4 * py * px * (1 - py) * (1 - px) / n ** 2)
    denom = v_p - v_star
    if denom <= 0:
        return {"n": n, "statistic": None, "p_value": None}
    stat = (p_hat - p_star) / math.sqrt(denom)
    return {"n": n, "hit_rate": round(p_hat, 4), "expected_under_independence": round(p_star, 4),
            "statistic": round(stat, 3), "p_value": _norm_sf(stat)}


def block_bootstrap_ci(hits: np.ndarray, block: int = 10, reps: int = 2000, level: float = 0.95, seed: int = 0) -> tuple[float, float]:
    """Circular block bootstrap interval for the mean of a 0/1 series kept in time order."""
    x = np.asarray(hits, dtype=float)
    n = len(x)
    if n < 2 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    k = math.ceil(n / block)
    starts = rng.integers(0, n, size=(reps, k))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    means = x[idx.reshape(reps, -1)[:, :n]].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)


def hits_in_order(pred: np.ndarray, y: np.ndarray) -> np.ndarray:
    mask = np.isfinite(pred) & np.isfinite(y) & (y != 0) & (pred != 0)
    return (np.sign(pred[mask]) == np.sign(y[mask])).astype(float)


def calibration(prob: np.ndarray, y: np.ndarray, majority_rate: np.ndarray | None = None, bins: int = 10) -> dict:
    """Brier score of ``prob`` (P(y > 0)) against a climatological forecast, plus reliability bins."""
    mask = np.isfinite(prob) & np.isfinite(y) & (y != 0)
    p, up = prob[mask], (y[mask] > 0).astype(float)
    if len(p) < 30:
        return {}
    brier = float(((p - up) ** 2).mean())
    clim = float(up.mean()) if majority_rate is None else majority_rate
    brier_clim = float(((clim - up) ** 2).mean())
    edges = np.linspace(0, 1, bins + 1)
    rel = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.sum() >= 15:
            rel.append({"forecast": round(float(p[m].mean()), 3), "observed": round(float(up[m].mean()), 3), "sessions": int(m.sum())})
    return {"brier": round(brier, 4), "brier_climatology": round(brier_clim, 4),
            "brier_skill_score": round(1 - brier / brier_clim, 4) if brier_clim else None, "reliability": rel}


def confidence_curve(pred: np.ndarray, y: np.ndarray, groups: int = 5) -> list[dict]:
    """Hit rate by quintile of forecast size: a well-behaved model is more often right when it says more."""
    mask = np.isfinite(pred) & np.isfinite(y) & (y != 0)
    f, a = pred[mask], y[mask]
    if len(f) < groups * 20:
        return []
    edges = np.quantile(np.abs(f), np.linspace(0, 1, groups + 1))
    out = []
    for g in range(groups):
        m = (np.abs(f) >= edges[g]) & (np.abs(f) <= edges[g + 1] if g == groups - 1 else np.abs(f) < edges[g + 1])
        out.append({"quintile": g + 1, "hit_rate": round(float((np.sign(f[m]) == np.sign(a[m])).mean()), 4),
                    "sessions": int(m.sum()), "mean_abs_forecast_bps": round(float(np.abs(f[m]).mean() * 1e4), 1)})
    return out
