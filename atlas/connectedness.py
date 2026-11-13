"""Diebold-Yilmaz spillover (connectedness) measures.

Method (Diebold and Yilmaz, 2012, "Better to give than to receive"):

1. Fit a vector autoregression of order p to N return series (least squares, with intercept).
2. Compute the H-step generalised forecast-error variance decomposition (Pesaran and Shin,
   1998), which does not depend on the order of the variables:

       theta_ij(H) = sigma_jj^-1 * sum_h (e_i' A_h S e_j)^2 / sum_h (e_i' A_h S A_h' e_i)

   where A_h are the moving-average coefficients and S the residual covariance.
3. Normalise each row to sum to one. Entry (i, j) is then the share of i's forecast-error
   variance that comes from shocks to j.

From the normalised matrix:
  total index        mean off-diagonal share across all variables, in percent
  to_j (given)       sum over i != j of theta_ij: how much j drives the others
  from_i (received)  sum over j != i of theta_ij: how much i is driven by the others
  net_i              to_i - from_i: positive = transmitter, negative = receiver
  pairwise net_ij    theta_ji - theta_ij: positive = i drives j more than j drives i
"""
from __future__ import annotations

import numpy as np


def fit_var(Y: np.ndarray, p: int = 1) -> tuple[list[np.ndarray], np.ndarray]:
    """Least-squares VAR(p). Returns ([Phi_1..Phi_p], residual covariance)."""
    T, N = Y.shape
    if T <= N * p + 1:
        raise ValueError(f"need more than {N * p + 1} observations for a VAR({p}) in {N} variables")
    X = np.hstack([np.ones((T - p, 1))] + [Y[p - k - 1:T - k - 1] for k in range(p)])
    target = Y[p:]
    B, *_ = np.linalg.lstsq(X, target, rcond=None)
    resid = target - X @ B
    sigma = resid.T @ resid / (T - p - X.shape[1])
    phis = [B[1 + k * N:1 + (k + 1) * N].T for k in range(p)]
    return phis, sigma


def ma_coefficients(phis: list[np.ndarray], horizon: int) -> list[np.ndarray]:
    N = phis[0].shape[0]
    A = [np.eye(N)]
    for h in range(1, horizon):
        A.append(sum(phis[k] @ A[h - k - 1] for k in range(len(phis)) if h - k - 1 >= 0))
    return A


def gfevd(phis: list[np.ndarray], sigma: np.ndarray, horizon: int = 10) -> np.ndarray:
    """Row-normalised generalised forecast-error variance decomposition."""
    A = ma_coefficients(phis, horizon)
    N = sigma.shape[0]
    num = np.zeros((N, N))
    den = np.zeros(N)
    for Ah in A:
        AS = Ah @ sigma
        num += AS ** 2
        den += np.einsum("ij,jk,ik->i", Ah, sigma, Ah)
    theta = num / np.diag(sigma)[None, :] / den[:, None]
    return theta / theta.sum(axis=1, keepdims=True)


def summarise(theta: np.ndarray, names: list[str]) -> dict:
    N = len(names)
    off = theta - np.diag(np.diag(theta))
    to = off.sum(axis=0)
    frm = off.sum(axis=1)
    return {
        "total_index_pct": round(float(off.sum() / N * 100), 2),
        "to_others_pct": {n: round(float(v * 100), 2) for n, v in zip(names, to)},
        "from_others_pct": {n: round(float(v * 100), 2) for n, v in zip(names, frm)},
        "net_pct": {n: round(float((t - f) * 100), 2) for n, t, f in zip(names, to, frm)},
    }


def pairwise_net(theta: np.ndarray, names: list[str], top: int | None = None) -> list[dict]:
    """Directed edges i -> j where i drives j more than the reverse, strongest first."""
    edges = []
    N = len(names)
    for i in range(N):
        for j in range(N):
            if i != j:
                net = theta[j, i] - theta[i, j]
                if net > 0:
                    edges.append({"source": names[i], "target": names[j], "net_pct": round(float(net * 100), 3),
                                  "gross_pct": round(float(theta[j, i] * 100), 3)})
    edges.sort(key=lambda e: -e["net_pct"])
    return edges[:top] if top else edges


def connectedness(Y: np.ndarray, names: list[str], p: int = 1, horizon: int = 10) -> tuple[np.ndarray, dict]:
    # Standardising does not change the decomposition's shares but keeps the solve well conditioned.
    Z = (Y - Y.mean(axis=0)) / Y.std(axis=0)
    phis, sigma = fit_var(Z, p)
    theta = gfevd(phis, sigma, horizon)
    return theta, summarise(theta, names)


def rolling_total(Y: np.ndarray, dates: list, window: int = 500, step: int = 21, p: int = 1, horizon: int = 10) -> list[dict]:
    out = []
    for end in range(window, len(Y) + 1, step):
        Z = Y[end - window:end]
        _, s = connectedness(Z, [str(i) for i in range(Y.shape[1])], p, horizon)
        out.append({"date": dates[end - 1].isoformat(), "total_index_pct": s["total_index_pct"]})
    return out
