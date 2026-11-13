"""Connectedness against a closed-form case, and walk-forward discipline."""
import math

import numpy as np
import pytest

from atlas import connectedness as C
from atlas import exposure, models


def test_gfevd_closed_form_two_variables():
    # No dynamics (Phi = 0), unit variances, correlation rho. Raw theta_11 = 1, theta_12 = rho^2,
    # so after normalising each row the cross share is rho^2 / (1 + rho^2).
    rho = 0.6
    theta = C.gfevd([np.zeros((2, 2))], np.array([[1.0, rho], [rho, 1.0]]), horizon=10)
    assert theta[0, 1] == pytest.approx(rho ** 2 / (1 + rho ** 2))
    s = C.summarise(theta, ["a", "b"])
    assert s["total_index_pct"] == pytest.approx(rho ** 2 / (1 + rho ** 2) * 100, abs=0.01)
    assert s["net_pct"]["a"] == pytest.approx(0.0, abs=1e-9)   # symmetric: nobody is a net transmitter


def test_independent_series_have_no_spillover():
    theta = C.gfevd([np.diag([0.3, -0.2, 0.1])], np.eye(3), horizon=10)
    assert np.allclose(theta, np.eye(3))


def test_a_leader_is_a_net_transmitter():
    # x_t drives y_{t+1}; y never drives x.
    rng = np.random.default_rng(1)
    x = rng.standard_normal(3000)
    y = np.empty(3000)
    y[0] = 0
    y[1:] = 0.8 * x[:-1] + 0.6 * rng.standard_normal(2999)
    theta, s = C.connectedness(np.column_stack([x, y]), ["x", "y"])
    assert s["net_pct"]["x"] > 10 and s["net_pct"]["y"] < -10
    assert C.pairwise_net(theta, ["x", "y"])[0]["source"] == "x"


def test_ma_coefficients_var1():
    phi = np.array([[0.5, 0.1], [0.0, 0.2]])
    A = C.ma_coefficients([phi], 3)
    assert np.allclose(A[2], phi @ phi)


def test_walk_forward_never_sees_the_future():
    rng = np.random.default_rng(7)
    n = 900
    X = rng.standard_normal((n, 3))
    y = 0.5 * X[:, 0] + rng.standard_normal(n) * 0.5
    first = models.walk_forward(X, y, ["a", "b", "c"], min_train=400, refit_every=50)
    # Change every value after row 600: forecasts up to row 600 must not move.
    y2, X2 = y.copy(), X.copy()
    y2[600:] = rng.standard_normal(n - 600) * 10
    X2[600:] = rng.standard_normal((n - 600, 3))
    second = models.walk_forward(X2, y2, ["a", "b", "c"], min_train=400, refit_every=50)
    assert np.allclose(first.pred[:600], second.pred[:600], equal_nan=True)
    assert np.isnan(first.pred[:400]).all()


def test_score_on_a_real_signal_beats_baselines_and_noise_does_not():
    rng = np.random.default_rng(3)
    n = 2000
    X = rng.standard_normal((n, 2))
    signal = 0.7 * X[:, 0] + 0.3 * rng.standard_normal(n)
    s = models.score(models.walk_forward(X, signal, ["a", "b"]), signal)
    assert s["hit_rate"] > 0.8 and s["p_value_vs_baseline"] < 1e-6
    noise = rng.standard_normal(n)
    s = models.score(models.walk_forward(X, noise, ["a", "b"]), noise)
    assert 0.45 < s["hit_rate"] < 0.55 and s["oos_r2"] < 0.01


def test_holm_adjustment_by_hand():
    # Sorted 0.01, 0.02, 0.04 -> 3 x 0.01 = 0.03, 2 x 0.02 = 0.04, 1 x 0.04 = 0.04 (monotone).
    assert exposure.holm([0.04, 0.01, 0.02]) == pytest.approx([0.04, 0.03, 0.04])


def test_pass_through_share_priced_at_open():
    from datetime import date, timedelta
    from atlas.panel import Panel
    rng = np.random.default_rng(5)
    n = 500
    cue = rng.standard_normal(n) * 0.01
    gap = 0.3 * cue + rng.standard_normal(n) * 0.001
    intraday = 0.1 * cue + rng.standard_normal(n) * 0.001
    p = Panel([date(2020, 1, 1) + timedelta(days=i) for i in range(n)],
              {"spx:overnight": cue, "s:gap": gap, "s:intraday": intraday, "s:cc": (1 + gap) * (1 + intraday) - 1})
    out = exposure.pass_through(p, "s", "spx:overnight")
    assert out["priced_at_open_pct"] == pytest.approx(75.0, abs=2.0)   # 0.3 of a total 0.4
    assert math.isclose(out["beta_gap"], 0.3, abs_tol=0.01)
