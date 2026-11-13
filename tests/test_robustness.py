"""Inference, placebos, tradability, the forward-test record and the NSE parser."""
import math
from datetime import date, timedelta

import numpy as np
import pytest

from atlas import inference as I
from atlas import ledger, models, nse, tradable
from atlas.data import Bars


# ---------- inference ----------

def test_pesaran_timmermann_by_hand():
    # 100 sessions: forecasts up 60 times, outcomes up 60 times, 50 agree up and 30 agree down.
    pred = np.array([1] * 50 + [1] * 10 + [-1] * 10 + [-1] * 30, dtype=float)
    y = np.array([1] * 50 + [-1] * 10 + [1] * 10 + [-1] * 30, dtype=float)
    out = I.pesaran_timmermann(pred, y)
    # P = 0.80; P* = 0.6*0.6 + 0.4*0.4 = 0.52
    assert out["hit_rate"] == pytest.approx(0.80) and out["expected_under_independence"] == pytest.approx(0.52)
    v_p = 0.52 * 0.48 / 100
    v_s = (0.2 ** 2 * 0.24 / 100) * 2 + 4 * 0.6 * 0.6 * 0.4 * 0.4 / 100 ** 2
    assert out["statistic"] == pytest.approx((0.80 - 0.52) / math.sqrt(v_p - v_s), abs=1e-3)


def test_always_up_has_no_directional_skill_even_in_a_rising_market():
    rng = np.random.default_rng(0)
    y = np.where(rng.random(1000) < 0.65, 1.0, -1.0)      # 65% up days
    out = I.pesaran_timmermann(np.ones(1000), y)
    assert out["statistic"] is None or abs(out["statistic"]) < 1e-9 or out["p_value"] > 0.3


def test_block_bootstrap_interval_covers_the_rate_and_widens_with_dependence():
    rng = np.random.default_rng(1)
    iid = (rng.random(2000) < 0.7).astype(float)
    lo, hi = I.block_bootstrap_ci(iid, block=10, reps=1000)
    assert lo < 0.7 < hi and hi - lo < 0.06
    sticky = np.repeat((rng.random(200) < 0.7).astype(float), 10)   # runs of 10 identical outcomes
    lo2, hi2 = I.block_bootstrap_ci(sticky, block=20, reps=1000)
    assert hi2 - lo2 > hi - lo


def test_calibration_rewards_honest_probabilities():
    rng = np.random.default_rng(2)
    p = rng.random(5000)
    y = np.where(rng.random(5000) < p, 1.0, -1.0)
    out = I.calibration(p, y)
    assert out["brier_skill_score"] > 0.2
    assert all(abs(r["forecast"] - r["observed"]) < 0.06 for r in out["reliability"])


def test_platt_scaling_recovers_a_logistic_relationship():
    rng = np.random.default_rng(3)
    f = rng.standard_normal(20000)
    up = (rng.random(20000) < 1 / (1 + np.exp(-(2 * f + 0.5)))).astype(float)
    a, b = models._platt(f, up)
    assert a == pytest.approx(2.0, abs=0.1) and b == pytest.approx(0.5, abs=0.06)


# ---------- placebo sanity on synthetic data ----------

def test_shuffled_features_lose_the_signal():
    from atlas.panel import Panel
    from atlas.robustness import audit
    rng = np.random.default_rng(4)
    n = 1300
    cue = rng.standard_normal(n)
    gap = 0.8 * cue + 0.5 * rng.standard_normal(n)
    days = [date(2018, 1, 1) + timedelta(days=i) for i in range(n)]
    cols = {"spx:overnight": cue, "spx:future": rng.standard_normal(n), "nifty:gap": gap,
            "nifty:intraday": rng.standard_normal(n), "nifty:cc": gap}
    out = audit(Panel(days, cols), "nifty", "gap", permutations=10)
    assert out["model"]["hit_rate"] > 0.8
    assert out["placebos"]["shuffled_max"] < 0.6
    assert out["placebos"]["lagged_one_session"] < 0.6
    assert out["placebos"]["permutation_p_value"] == pytest.approx(1 / 11, abs=1e-4)


# ---------- tradability ----------

def test_costs_follow_the_april_2026_stt_change():
    assert tradable.cost_bps(date(2026, 3, 31), "futures") == pytest.approx(4.7)
    assert tradable.cost_bps(date(2026, 4, 1), "futures") == pytest.approx(7.7)
    assert tradable.cost_bps(date(2026, 4, 1), "basket") == pytest.approx(7.5)


def test_newey_west_matches_plain_t_for_independent_data_roughly():
    rng = np.random.default_rng(5)
    x = 0.1 + rng.standard_normal(5000)
    plain = x.mean() / (x.std() / math.sqrt(len(x)))
    assert tradable._newey_west_t(x) == pytest.approx(plain, rel=0.1)


# ---------- forward-test record ----------

def brief_for(session, generated, gap=10.0, intraday=-5.0):
    return {"for_session": session, "generated_utc": generated, "notes": [],
            "sectors": [{"sector": "nifty", "gap": {"expected_bps": gap, "high_confidence": True},
                         "intraday": {"expected_bps": intraday}}]}


def test_only_pre_open_forecasts_count_and_the_first_one_stands(tmp_path):
    path = tmp_path / "ledger.jsonl"
    assert ledger.record(brief_for("2026-11-16", "2026-11-16 03:30"), path)["counts_as_forward_test"] is True
    second = ledger.record(brief_for("2026-11-16", "2026-11-16 03:40", gap=-50.0), path)
    assert second["recorded"] is False                                   # cannot be replaced
    late = ledger.record(brief_for("2026-11-17", "2026-11-17 03:45"), path)   # 09:15 IST exactly: too late
    assert late["counts_as_forward_test"] is False


def test_scoring_against_actuals(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger.record(brief_for("2026-11-16", "2026-11-16 02:00", gap=10.0, intraday=-5.0), path)
    ledger.record(brief_for("2026-11-17", "2026-11-17 02:00", gap=-8.0, intraday=4.0), path)
    actuals = {("nifty", "2026-11-16"): (0.002, -0.001),    # gap right, intraday right
               ("nifty", "2026-11-17"): (0.003, -0.002)}    # gap wrong, intraday wrong
    out = ledger.score(actuals, path)
    assert out["forward_sessions"] == 2
    assert out["hit_rates"]["gap"] == {"hit_rate": 0.5, "forecasts": 2}
    assert out["hit_rates"]["intraday"]["hit_rate"] == 0.5


# ---------- official NSE files ----------

SAMPLE = b"""Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change
Nifty 50,12-11-2026,25213.5,25384.8,25142.95,25299.35,44.3
Nifty 50,12-11-2026,25213.5,25384.8,25142.95,25299.35,44.3
NIFTY IT,12-11-2026,32065.7,32334.15,31794.35,32163.55,-132.05
Nifty Broken,12-11-2026,-,-,-,-,-
"""


def test_nse_parser_reads_open_and_close_and_ignores_duplicates_and_blanks():
    table = nse.parse(SAMPLE)
    assert table["nifty 50"] == (25213.5, 25384.8, 25142.95, 25299.35)
    assert table["nifty it"][3] == 32163.55            # names are matched case-insensitively
    assert "nifty broken" not in table


def test_load_sectors_with_a_holiday(monkeypatch):
    files = {date(2026, 11, 11): SAMPLE, date(2026, 11, 12): SAMPLE}   # the 10th is a holiday
    bars, info = nse.load_sectors(date(2026, 11, 10), date(2026, 11, 12), fetch=lambda d: files.get(d), workers=1)
    assert info["sessions"] == 2 and bars["nifty"].dates == [date(2026, 11, 11), date(2026, 11, 12)]
    assert bars["bank"].dates == []


def test_compare_reports_agreement():
    a = Bars("x", [date(2026, 1, 1), date(2026, 1, 2)], [100.0, 101.0], [100.5, 101.5])
    b = Bars("x", [date(2026, 1, 1), date(2026, 1, 2)], [100.0, 101.2], [100.5, 101.5])
    out = nse.compare(a, b)
    assert out["open_mismatch"] == 1 and out["close_match_pct"] == 100.0
