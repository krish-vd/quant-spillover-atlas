"""Walk-forward forecasts and out-of-sample scoring.

The model is deliberately plain: a ridge regression on standardised features, refitted
every ``refit_every`` sessions on data strictly before the forecast window. There is no
tuning on the test period. The penalty is fixed in advance (``RIDGE``), not chosen by
looking at results, because choosing it by results would be a form of overfitting.

Every score is out of sample and is reported next to two baselines:
  * ``majority``: always forecast the direction that was more common in the training data
  * ``best_single_cue``: the sign of the one feature most correlated with the target in
    the training data
and a significance test against the better of 50% and the majority baseline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

RIDGE = 10.0
MIN_TRAIN = 500
REFIT_EVERY = 21


@dataclass
class WalkForward:
    pred: np.ndarray          # out-of-sample forecast (nan before the first fit)
    confident: np.ndarray     # |forecast| at or above the training set's top-third threshold
    majority: np.ndarray      # training-period majority direction (+1 / -1)
    single_cue: np.ndarray    # sign forecast from the best single training-period feature
    single_cue_name: list     # which feature that was, per row
    prob_up: np.ndarray = None  # calibrated probability that the target is positive (Platt scaling on training fits)


def _fit(X: np.ndarray, y: np.ndarray, ridge: float):
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    k = Z.shape[1]
    beta = np.linalg.solve(Z.T @ Z + ridge * np.eye(k), Z.T @ (y - y.mean()))
    return mu, sd, beta, y.mean()


def _platt(f: np.ndarray, up: np.ndarray, iterations: int = 30) -> tuple[float, float]:
    """Logistic map P(up) = 1 / (1 + exp(-(a f + b))) fitted by Newton's method on training data."""
    scale = f.std() or 1.0
    z = f / scale
    a, b = 0.0, 0.0
    for _ in range(iterations):
        p = 1.0 / (1.0 + np.exp(-(a * z + b)))
        w = p * (1 - p) + 1e-9
        g = np.array([((p - up) * z).sum(), (p - up).sum()])
        H = np.array([[(w * z * z).sum(), (w * z).sum()], [(w * z).sum(), w.sum()]]) + 1e-6 * np.eye(2)
        step = np.linalg.solve(H, g)
        a, b = a - step[0], b - step[1]
        if np.abs(step).max() < 1e-9:
            break
    return a / scale, b


def walk_forward(X: np.ndarray, y: np.ndarray, names: list[str], min_train: int = MIN_TRAIN,
                 refit_every: int = REFIT_EVERY, ridge: float = RIDGE, train_window: int | None = None,
                 fit=None) -> WalkForward:
    """Walk-forward forecasts. ``train_window`` limits training to the most recent N usable
    sessions (default: everything before the window). ``fit(Xt, yt)`` may replace the ridge
    fit; it must return a function mapping a feature matrix to forecasts."""
    n = len(y)
    ok = np.all(np.isfinite(X), axis=1) & np.isfinite(y)
    pred = np.full(n, np.nan)
    confident = np.zeros(n, dtype=bool)
    majority = np.full(n, np.nan)
    single = np.full(n, np.nan)
    single_name = [None] * n
    prob = np.full(n, np.nan)
    for start in range(min_train, n, refit_every):
        train = ok.copy()
        train[start:] = False  # strictly before the window
        if train_window:
            idx = np.flatnonzero(train)
            train[idx[:-train_window]] = False
        if train.sum() < min_train // 2:
            continue
        Xt, yt = X[train], y[train]
        if fit is None:
            mu, sd, beta, intercept = _fit(Xt, yt, ridge)
            predict = lambda M, mu=mu, sd=sd, beta=beta, intercept=intercept: ((M - mu) / sd) @ beta + intercept
        else:
            predict = fit(Xt, yt)
        fitted = predict(Xt)
        a, b = _platt(fitted, (yt > 0).astype(float))
        threshold = np.quantile(np.abs(fitted), 2 / 3)
        corr = [np.corrcoef(Xt[:, j], yt)[0, 1] if Xt[:, j].std() > 0 else 0.0 for j in range(X.shape[1])]
        best = int(np.nanargmax(np.abs(corr)))
        major = 1.0 if (yt > 0).mean() >= 0.5 else -1.0
        stop = min(start + refit_every, n)
        rows = [i for i in range(start, stop) if ok[i]]
        if rows:
            out = predict(X[rows])
            pred[rows] = out
            prob[rows] = 1.0 / (1.0 + np.exp(-(a * out + b)))
        for i in rows:
            confident[i] = abs(pred[i]) >= threshold
            majority[i] = major
            single[i] = math.copysign(1.0, corr[best]) * np.sign(X[i, best])
            single_name[i] = names[best]
    return WalkForward(pred, confident, majority, single, single_name, prob)


def _p_value(hits: int, n: int, p0: float) -> float:
    """One-sided normal approximation to the binomial: chance of this many hits if the true rate were p0."""
    if n == 0 or p0 <= 0 or p0 >= 1:
        return float("nan")
    z = (hits - n * p0) / math.sqrt(n * p0 * (1 - p0))
    return 0.5 * math.erfc(z / math.sqrt(2))


def _hit(sign_pred: np.ndarray, y: np.ndarray) -> tuple[int, int]:
    mask = np.isfinite(sign_pred) & (sign_pred != 0) & (y != 0) & np.isfinite(y)
    return int((np.sign(sign_pred[mask]) == np.sign(y[mask])).sum()), int(mask.sum())


def score(wf: WalkForward, y: np.ndarray) -> dict:
    """Out-of-sample accuracy, baselines, significance and economic value of the forecasts."""
    tested = np.isfinite(wf.pred) & np.isfinite(y)
    hits, n = _hit(wf.pred, y)
    if n == 0:
        return {"tested_sessions": 0}
    c_hits, c_n = _hit(np.where(wf.confident, wf.pred, np.nan), y)
    m_hits, m_n = _hit(wf.majority, y)
    s_hits, s_n = _hit(wf.single_cue, y)
    baseline = max(0.5, m_hits / m_n if m_n else 0.5)
    yy, pp = y[tested], wf.pred[tested]
    r2 = 1.0 - float(((yy - pp) ** 2).sum() / (yy ** 2).sum())
    corr = float(np.corrcoef(yy, pp)[0, 1]) if len(yy) > 2 else float("nan")
    follow = np.sign(pp) * yy  # return from taking the forecast's direction, before costs
    cue_names = [c for c in wf.single_cue_name if c]
    return {
        "tested_sessions": n,
        "hit_rate": round(hits / n, 4),
        "confident_hit_rate": round(c_hits / c_n, 4) if c_n else None,
        "confident_sessions": c_n,
        "baseline_majority": round(m_hits / m_n, 4) if m_n else None,
        "baseline_best_single_cue": round(s_hits / s_n, 4) if s_n else None,
        "best_single_cue_most_often": max(set(cue_names), key=cue_names.count) if cue_names else None,
        "p_value_vs_baseline": round(_p_value(hits, n, baseline), 6),
        "oos_r2": round(r2, 4),
        "forecast_correlation": round(corr, 4),
        "mean_return_following_forecast_bps": round(float(follow.mean()) * 1e4, 2),
        "breakeven_round_trip_cost_bps": round(float(follow.mean()) * 1e4, 2),
    }


def by_year(wf: WalkForward, y: np.ndarray, dates) -> list[dict]:
    rows = {}
    for i, d in enumerate(dates):
        if np.isfinite(wf.pred[i]) and np.isfinite(y[i]) and y[i] != 0:
            hit = np.sign(wf.pred[i]) == np.sign(y[i])
            r = rows.setdefault(d.year, [0, 0])
            r[0] += int(hit)
            r[1] += 1
    return [{"year": yr, "hit_rate": round(h / n, 4), "sessions": n} for yr, (h, n) in sorted(rows.items())]


def coefficients(X: np.ndarray, y: np.ndarray, names: list[str], ridge: float = RIDGE) -> list[dict]:
    """Standardised full-sample weights: for explaining the model, never for scoring it."""
    ok = np.all(np.isfinite(X), axis=1) & np.isfinite(y)
    _, _, beta, _ = _fit(X[ok], y[ok], ridge)
    order = np.argsort(-np.abs(beta))
    return [{"feature": names[j], "weight_bps_per_sd": round(float(beta[j]) * 1e4, 2)} for j in order]
