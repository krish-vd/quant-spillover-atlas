"""The timing rules, checked by hand on small synthetic markets.

India trades Mon 6, Tue 7 and Thu 9 January (Wed 8 is an Indian holiday).
"""
from datetime import date

import math

from atlas.data import Bars
from atlas.panel import build, forecast_features, synchronised
from atlas.universe import Market

D = date
INDIA = Market("nifty", "India", "^X", "India", "india", "sector", 3.75, 10.0)
US = Market("spx", "US", "^U", "US", "overnight", "equity", 14.5, 21.0)
ASIA = Market("kospi", "Korea", "^K", "Korea", "asia", "equity", 0.0, 6.5)
VIX = Market("vix", "VIX", "^V", "US", "overnight", "volatility", 14.5, 21.0)


def bars(key, rows):
    b = Bars(key)
    for d, o, c in rows:
        b.dates.append(d)
        b.open.append(o)
        b.close.append(c)
    return b


def sample():
    india = bars("nifty", [(D(2025, 1, 6), 100, 101), (D(2025, 1, 7), 102, 103), (D(2025, 1, 9), 105, 104)])
    # US trades every weekday including the Indian holiday on the 8th.
    us = bars("spx", [(D(2025, 1, 3), 0, 1000), (D(2025, 1, 6), 0, 1010), (D(2025, 1, 7), 0, 1020),
                      (D(2025, 1, 8), 0, 1030), (D(2025, 1, 9), 0, 1040)])
    korea = bars("kospi", [(D(2025, 1, 6), 199, 200), (D(2025, 1, 7), 202, 204), (D(2025, 1, 8), 206, 208),
                           (D(2025, 1, 9), 210, 212)])
    vix = bars("vix", [(D(2025, 1, 3), 0, 15.0), (D(2025, 1, 6), 0, 16.0), (D(2025, 1, 7), 0, 18.5),
                       (D(2025, 1, 8), 0, 17.0), (D(2025, 1, 9), 0, 20.0)])
    return build({"nifty": india, "spx": us, "kospi": korea, "vix": vix}, [US, ASIA, VIX, INDIA])


def test_india_targets():
    p = sample()
    assert p.dates == [D(2025, 1, 7), D(2025, 1, 9)]
    assert math.isclose(p["nifty:gap"][0], 102 / 101 - 1)        # open on the 7th over close on the 6th
    assert math.isclose(p["nifty:intraday"][0], 103 / 102 - 1)
    assert math.isclose(p["nifty:cc"][1], 104 / 103 - 1)          # across the holiday


def test_us_session_dated_the_previous_indian_day_is_new_information():
    p = sample()
    # For India's 7th: US sessions dated 6th (closes after India's close on the 6th) -> from US close on the 3rd to the 6th.
    assert math.isclose(p["spx:overnight"][0], 1010 / 1000 - 1)
    # For India's 9th (after the Indian holiday): US sessions dated 7th and 8th -> 1010 to 1030.
    assert math.isclose(p["spx:overnight"][1], 1030 / 1010 - 1)


def test_us_session_of_the_same_day_is_never_used():
    # The US session dated the 9th closes after India's session on the 9th: it must not appear on the 9th's row.
    p = sample()
    assert not math.isclose(p["spx:overnight"][1], 1040 / 1030 - 1)


def test_asia_gap_uses_todays_open_and_skips_what_india_already_knew():
    p = sample()
    # India's 7th: Korea closed at 200 on the 6th (before India's close, already known); opened 202 on the 7th.
    assert math.isclose(p["kospi:gap"][0], 202 / 200 - 1)
    # India's 9th: Korea's session on the 8th (Indian holiday) is new information, so from 204 to the 9th's open 210.
    assert math.isclose(p["kospi:gap"][1], 210 / 204 - 1)
    # Korea's full day on the 9th closes before India does: it explains India's day.
    assert math.isclose(p["kospi:day"][1], 212 / 204 - 1)


def test_level_series_use_changes_in_points():
    p = sample()
    assert math.isclose(p["vix:overnight"][0], 16.0 - 15.0)
    assert math.isclose(p["vix:overnight"][1], 17.0 - 16.0)


def test_forecast_features_exclude_anything_known_only_after_the_open():
    p = sample()
    feats = forecast_features(p, [US, ASIA, VIX, INDIA])
    assert feats == ["spx:overnight", "kospi:gap", "vix:overnight"]
    assert not any(f.endswith(":day") or f.startswith("nifty") for f in feats)


def test_synchronised_window_assigns_each_market_once():
    names, Y, dates = synchronised(sample(), [US, ASIA, INDIA])
    assert names == ["spx", "kospi", "nifty"] and dates == [D(2025, 1, 7), D(2025, 1, 9)]
    assert math.isclose(Y[1, 1], 212 / 204 - 1) and math.isclose(Y[1, 2], 104 / 103 - 1)


def test_unfinished_session_is_dropped_before_use():
    from atlas.panel import _final
    us = bars("spx", [(D(2025, 1, 3), 0, 1000), (D(2025, 1, 6), 0, 1010)])
    us.last_final = False   # the 6th is still trading
    kept = _final(us)
    assert kept.dates == [D(2025, 1, 3)] and kept.close == [1000]
    us.last_final = True
    assert _final(us).dates == [D(2025, 1, 3), D(2025, 1, 6)]


def test_forbidden_columns_exist_for_placebos_but_never_reach_a_forecast():
    p = sample()
    # The US session dated the 9th closes after India's close on the 9th: present only as ':future'.
    assert math.isclose(p["spx:future"][1], 1040 / 1030 - 1)
    assert math.isclose(p["vix:level"][1], 17.0)
    feats = forecast_features(p, [US, ASIA, VIX, INDIA])
    assert not any(f.endswith((":future", ":level", ":day")) for f in feats)
