"""Robustness audit for one sector and target.

1. Inference     Pesaran-Timmermann test, block-bootstrap confidence interval, calibration
                 of probabilities (Brier skill against climatology), hit rate by forecast size.
2. Placebos      Results that MUST collapse if the study is honest, and one that shows
                 what a careless study would claim:
                   shuffled   foreign data reordered at random (time link destroyed), many draws
                   lagged     every cue one session late (yesterday's news)
                   naive      same-date closes everywhere, including sessions that close after
                              India does: the common mistake, shown only to measure its inflation
3. Challengers   A model is only replaced if a challenger wins out of sample:
                 recent-window ridge (last 750 sessions), logistic classifier, ridge with
                 non-linear terms.
4. Regimes       Hit rate split by VIX level and by the size of the US overnight move.

Every forecast in this module comes from the same walk-forward procedure as the main study.
"""
from __future__ import annotations

import numpy as np

from . import inference as I
from . import models
from . import panel as P
from . import universe as U


def features_for(panel: P.Panel, sector: str, target: str) -> list[str]:
    """Cues known before 09:15. For the open-to-close target the sector's own opening gap is
    known too (it is set at 09:15), so it is included."""
    feats = P.forecast_features(panel, list(U.ALL))
    if target == "intraday":
        feats = feats + [f"{sector}:gap"]
    return feats


def summarise(wf: models.WalkForward, y: np.ndarray, dates=None) -> dict:
    sc = models.score(wf, y)
    pt = I.pesaran_timmermann(wf.pred, y)
    lo, hi = I.block_bootstrap_ci(I.hits_in_order(wf.pred, y))
    major = float(np.nanmean(wf.majority > 0)) if np.isfinite(wf.majority).any() else None
    return {
        "hit_rate": sc.get("hit_rate"),
        "hit_rate_95ci": [round(lo, 4), round(hi, 4)],
        "confident_hit_rate": sc.get("confident_hit_rate"),
        "baseline_majority": sc.get("baseline_majority"),
        "baseline_best_single_cue": sc.get("baseline_best_single_cue"),
        "pesaran_timmermann": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in pt.items()},
        "oos_r2": sc.get("oos_r2"),
        "calibration": I.calibration(wf.prob_up, y),
        "confidence_curve": I.confidence_curve(wf.pred, y),
        "tested_sessions": sc.get("tested_sessions"),
    }


def _hit(wf, y) -> float:
    h = I.hits_in_order(wf.pred, y)
    return float(h.mean()) if len(h) else float("nan")


# ---------- challengers ----------

def _logistic_fit(Xt: np.ndarray, yt: np.ndarray, l2: float = 10.0, iterations: int = 40):
    mu, sd = Xt.mean(axis=0), Xt.std(axis=0)
    sd[sd == 0] = 1.0
    Z = np.hstack([np.ones((len(Xt), 1)), (Xt - mu) / sd])
    up = (yt > 0).astype(float)
    w = np.zeros(Z.shape[1])
    penalty = l2 * np.eye(Z.shape[1])
    penalty[0, 0] = 0
    for _ in range(iterations):
        p = 1 / (1 + np.exp(-Z @ w))
        g = Z.T @ (p - up) + penalty @ w
        H = (Z * (p * (1 - p))[:, None]).T @ Z + penalty + 1e-9 * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return lambda M: np.hstack([np.ones((len(M), 1)), (M - mu) / sd]) @ w


def _nonlinear_fit(Xt: np.ndarray, yt: np.ndarray):
    expand = lambda M: np.hstack([M, M * np.abs(M), np.abs(M)])
    E = expand(Xt)
    mu, sd, beta, intercept = models._fit(E, yt, models.RIDGE * 3)
    return lambda M: ((expand(M) - mu) / sd) @ beta + intercept


def audit(panel: P.Panel, sector: str, target: str, permutations: int = 50, seed: int = 11) -> dict:
    feats = features_for(panel, sector, target)
    X = np.column_stack([panel[f] for f in feats])
    y = panel[f"{sector}:{target}"]
    base = models.walk_forward(X, y, feats)
    out = {"sector": sector, "target": target, "features": len(feats), "model": summarise(base, y)}
    true_hit = _hit(base, y)

    # ---- placebos
    rng = np.random.default_rng(seed)
    foreign = [j for j, f in enumerate(feats) if not f.startswith(f"{sector}:")]
    shuffled = []
    for _ in range(permutations):
        Xs = X.copy()
        perm = rng.permutation(len(X))
        Xs[:, foreign] = X[perm][:, foreign]
        shuffled.append(_hit(models.walk_forward(Xs, y, feats), y))
    shuffled = np.array(shuffled)
    lagged = np.vstack([np.full((1, X.shape[1]), np.nan), X[:-1]])
    if target == "intraday":   # the sector's own gap is known on the day; only foreign cues are lagged
        own = feats.index(f"{sector}:gap")
        lagged[:, own] = X[:, own]
    naive_cols = []
    for f in feats:
        key, kind = f.split(":")
        if kind == "overnight" and f"{key}:future" in panel.cols:
            naive_cols.append(panel[f"{key}:future"])     # the session dated D: closes after India
        elif kind == "gap" and f"{key}:day" in panel.cols and key != sector:
            naive_cols.append(panel[f"{key}:day"])        # Asia's close on D: after India opens
        else:
            naive_cols.append(panel[f])
    naive = np.column_stack(naive_cols)
    out["placebos"] = {
        "true_model": round(true_hit, 4),
        "shuffled_mean": round(float(shuffled.mean()), 4),
        "shuffled_95th_pct": round(float(np.quantile(shuffled, 0.95)), 4),
        "shuffled_max": round(float(shuffled.max()), 4),
        "permutation_p_value": round(float((1 + (shuffled >= true_hit).sum()) / (permutations + 1)), 4),
        "permutations": permutations,
        "lagged_one_session": round(_hit(models.walk_forward(lagged, y, feats), y), 4),
        "naive_same_date_closes": round(_hit(models.walk_forward(naive, y, feats), y), 4),
        "reading": "shuffled and lagged must fall to the baseline; 'naive' uses information India could not have at 09:15 "
                   "and shows how much a careless study would overstate accuracy.",
    }

    # ---- challengers
    chal = {
        "recent_window_750": models.walk_forward(X, y, feats, train_window=750),
        "logistic_classifier": models.walk_forward(X, y, feats, fit=_logistic_fit),
        "nonlinear_ridge": models.walk_forward(X, y, feats, fit=_nonlinear_fit),
    }
    out["challengers"] = {name: {"hit_rate": round(_hit(wf, y), 4),
                                 "pesaran_timmermann_p": I.pesaran_timmermann(wf.pred, y).get("p_value"),
                                 "oos_r2": models.score(wf, y).get("oos_r2")} for name, wf in chal.items()}
    best = max(out["challengers"].items(), key=lambda kv: kv[1]["hit_rate"])
    out["challengers"]["verdict"] = (f"champion kept: no challenger beat it by a full percentage point (best: {best[0]} "
                                     f"{best[1]['hit_rate']:.1%})" if best[1]["hit_rate"] < true_hit + 0.01 else
                                     f"{best[0]} beats the champion by {best[1]['hit_rate'] - true_hit:.1%}: worth a closer look")

    # ---- regimes (descriptive splits of the out-of-sample sessions)
    regimes = {}
    tested = np.isfinite(base.pred) & np.isfinite(y) & (y != 0)
    if "vix:level" in panel.cols:
        vix = panel["vix:level"]
        cut = float(np.nanmedian(vix[tested]))
        for label, m in ((f"VIX above {cut:.0f}", vix > cut), (f"VIX at or below {cut:.0f}", vix <= cut)):
            regimes[label] = _split(base, y, tested & m)
    if "spx:overnight" in panel.cols:
        mag = np.abs(panel["spx:overnight"])
        q1, q2 = np.nanquantile(mag[tested], [1 / 3, 2 / 3])
        regimes["US move small"] = _split(base, y, tested & (mag <= q1))
        regimes["US move medium"] = _split(base, y, tested & (mag > q1) & (mag <= q2))
        regimes["US move large"] = _split(base, y, tested & (mag > q2))
    out["regimes"] = regimes
    return out


def _split(wf, y, mask) -> dict:
    if mask.sum() < 30:
        return {"sessions": int(mask.sum())}
    hits = np.sign(wf.pred[mask]) == np.sign(y[mask])
    return {"hit_rate": round(float(hits.mean()), 4), "sessions": int(mask.sum())}
