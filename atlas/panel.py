"""The time-zone-aware dataset, one row per Indian trading day.

For India's session D (previous Indian session P), every column is defined by what
was knowable when:

Known before India opens on D (usable to forecast)
  ``<m>:overnight``  overnight markets: return over their sessions dated P..D-1, i.e. from
                     the last close before P to the last close before D. A US session
                     dated P closes after India closes on P, so it is new information on D.
  ``<m>:gap``        Asian markets: from their last close on or before P to their open on D
                     (or their last close before D if they do not trade on D). Asian sessions
                     dated P closed before India did, so India already knew them.

Known only by India's close on D (explains the day, cannot forecast it)
  ``<m>:day``        Asian markets: from their last close on or before P to their close on D.

Never used to forecast (placebo and regime studies only)
  ``<m>:future``     overnight markets: their session dated D, which closes AFTER India does
  ``<m>:level``      VIX and the 10-year yield: level at the last close before D

India's own moves (the targets)
  ``<s>:gap``        open D / close P - 1     overnight gap, set at 09:15
  ``<s>:intraday``   close D / open D - 1     what happened after the open
  ``<s>:cc``         close D / close P - 1    the whole day

``synchronised()`` gives one return per market over the same window (India's close on P
to India's close on D), the input for spillover measurement.

VIX and the 10-year yield are measured as changes in points rather than returns.
Markets that did not trade in a window contribute 0 (no new information).
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date

import numpy as np

from .data import Bars
from .universe import LEVEL_CHANGE, Market

NAN = float("nan")


def _final(bars: Bars) -> Bars:
    if bars.last_final or not bars.dates:
        return bars
    return Bars(bars.key, bars.dates[:-1], bars.open[:-1], bars.close[:-1], True)


def _move(a: float, b: float, level: bool) -> float:
    """From value a to value b, as a return or (for levels) a change in points."""
    if math.isnan(a) or math.isnan(b) or (not level and a <= 0):
        return NAN
    return b - a if level else b / a - 1.0


class _Series:
    def __init__(self, bars: Bars, level: bool):
        self.d, self.o, self.c, self.level = bars.dates, bars.open, bars.close, level

    def close_before(self, day: date) -> float:          # last close strictly before day
        i = bisect_left(self.d, day) - 1
        return self.c[i] if i >= 0 else NAN

    def close_on_or_before(self, day: date) -> float:
        i = bisect_right(self.d, day) - 1
        return self.c[i] if i >= 0 else NAN

    def open_on(self, day: date) -> float:
        i = bisect_left(self.d, day)
        return self.o[i] if i < len(self.d) and self.d[i] == day else NAN

    def close_on(self, day: date) -> float:
        i = bisect_left(self.d, day)
        return self.c[i] if i < len(self.d) and self.d[i] == day else NAN

    def overnight(self, prev: date, day: date) -> float:
        return _move(self.close_before(prev), self.close_before(day), self.level)

    def asia_gap(self, prev: date, day: date) -> float:
        base = self.close_on_or_before(prev)
        opened = self.open_on(day)
        if not math.isnan(opened):
            return _move(base, opened, self.level)
        return _move(base, self.close_before(day), self.level)  # did not trade on D: any sessions in between

    def asia_day(self, prev: date, day: date) -> float:
        return _move(self.close_on_or_before(prev), self.close_on_or_before(day), self.level)


@dataclass
class Panel:
    dates: list[date]
    cols: dict[str, np.ndarray]

    def __getitem__(self, name: str) -> np.ndarray:
        return self.cols[name]

    def names(self, suffix: str) -> list[str]:
        return [n for n in self.cols if n.endswith(":" + suffix)]

    def window(self, start: date | None = None, end: date | None = None) -> "Panel":
        keep = [i for i, d in enumerate(self.dates) if (start is None or d >= start) and (end is None or d <= end)]
        return Panel([self.dates[i] for i in keep], {k: v[keep] for k, v in self.cols.items()})


def build(bars: dict[str, Bars], markets: list[Market], calendar_key: str = "nifty") -> Panel:
    """Build the panel on India's trading calendar (the dates of ``calendar_key``)."""
    if calendar_key not in bars:
        raise ValueError(f"{calendar_key} prices are needed for India's trading calendar")
    bars = {k: _final(b) for k, b in bars.items()}
    calendar = bars[calendar_key].dates
    series = {m.key: _Series(bars[m.key], m.key in LEVEL_CHANGE) for m in markets if m.key in bars}
    cols: dict[str, list[float]] = {}

    def put(name: str, value: float) -> None:
        cols.setdefault(name, []).append(value)

    for k in range(1, len(calendar)):
        prev, day = calendar[k - 1], calendar[k]
        for m in markets:
            s = series.get(m.key)
            if s is None:
                continue
            if m.timing == "overnight":
                put(f"{m.key}:overnight", s.overnight(prev, day))
                # FORBIDDEN for forecasting: the session dated D closes after India's close on D.
                # Kept only so the placebo study can show what using it would wrongly claim.
                put(f"{m.key}:future", _move(s.close_before(day), s.close_on(day), s.level)
                    if not math.isnan(s.close_on(day)) else 0.0)
                if s.level:
                    put(f"{m.key}:level", s.close_before(day))   # known before the open; used to split by regime
            elif m.timing == "asia":
                put(f"{m.key}:gap", s.asia_gap(prev, day))
                put(f"{m.key}:day", s.asia_day(prev, day))
            else:  # india: both sessions must be present in the sector's own data
                c_prev, o_day, c_day = s.close_on(prev), s.open_on(day), s.close_on(day)
                put(f"{m.key}:gap", _move(c_prev, o_day, False))
                put(f"{m.key}:intraday", _move(o_day, c_day, False))
                put(f"{m.key}:cc", _move(c_prev, c_day, False))
    return Panel(list(calendar[1:]), {k: np.array(v, dtype=float) for k, v in cols.items()})




def synchronised(panel: Panel, markets: list[Market]) -> tuple[list[str], np.ndarray, list[date]]:
    """One return per market over the same window, India's close to India's close.

    Overnight markets use their ``overnight`` column (sessions dated P..D-1 all close
    between India's two closes); Asian markets their ``day`` column; India its ``cc``.
    Rows with any missing value are dropped; the dates of the rows kept are returned.
    """
    names, columns = [], []
    for m in markets:
        col = {"overnight": "overnight", "asia": "day", "india": "cc"}[m.timing]
        name = f"{m.key}:{col}"
        if name in panel.cols:
            names.append(m.key)
            columns.append(panel[name])
    matrix = np.column_stack(columns)
    keep = np.all(np.isfinite(matrix), axis=1)
    return names, matrix[keep], [d for d, k in zip(panel.dates, keep) if k]


def forecast_features(panel: Panel, markets: list[Market]) -> list[str]:
    """Columns known before India's open: overnight markets and Asian opening gaps."""
    out = []
    for m in markets:
        if m.timing == "overnight" and f"{m.key}:overnight" in panel.cols:
            out.append(f"{m.key}:overnight")
        elif m.timing == "asia" and f"{m.key}:gap" in panel.cols:
            out.append(f"{m.key}:gap")
    return out
