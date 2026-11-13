"""The morning brief: what moved since India's last close, and what such moves have meant.

For the next Indian session D it gathers everything knowable before 09:15 IST:
overnight markets (sessions after India's last close) and, once Asia has opened, each
Asian market's opening gap. A ridge model fitted on the full history turns those into an
expected opening gap and open-to-close move for each sector, and each figure is shown
with the model's out-of-sample record from the walk-forward study, so a reader can see
how often such a forecast has been right.

This describes historical relationships. It is not a recommendation to trade.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np

from . import data, models
from . import panel as P
from . import universe as U

INDIA_OPEN_UTC = 3.75
INDIA_CLOSE_UTC = 10.0


def next_session(now: datetime) -> date:
    """The Indian session the brief is for: today until India closes, else the next weekday."""
    day = now.date()
    if now.weekday() < 5 and now.hour + now.minute / 60 < INDIA_CLOSE_UTC:
        return day
    day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def live_features(bars: dict, session: date, last_india: date) -> tuple[dict[str, float], list[str]]:
    feats, notes = {}, []
    for m in U.ALL:
        b = bars.get(m.key)
        if b is None or m.timing == "india":
            continue
        level = m.key in U.LEVEL_CHANGE
        if m.timing == "overnight":
            if not b.last_final:
                notes.append(f"{m.name} is still trading; its last completed session is used")
            s = P._Series(P._final(b), level)
            feats[f"{m.key}:overnight"] = s.overnight(last_india, session)
        else:  # Asia: today's open is final as soon as the market opens
            s = P._Series(b, level)
            value = s.asia_gap(last_india, session)
            if np.isnan(s.open_on(session)):
                notes.append(f"{m.name} has not opened for {session.isoformat()}; its gap is taken as 0")
                value = 0.0
            feats[f"{m.key}:gap"] = value
    return feats, notes


def brief(range_: str = "10y", now: datetime | None = None, study_forecasts: list[dict] | None = None,
          panel: P.Panel | None = None) -> dict:
    """``panel`` is the history the models are fitted on (default: the study's, with NSE's official
    Indian prices). Live overnight and Asian moves always come from the latest quotes."""
    from .robustness import features_for
    from .study import load_panel
    now = now or datetime.now(timezone.utc)
    bars, failed = data.load_many(list(U.ALL), range_)
    if panel is None:
        panel, _ = load_panel(range_)
    session = next_session(now)
    last_india = max(d for d in panel.dates if d < session)
    feats, notes = live_features(bars, session, last_india)
    names = P.forecast_features(panel, list(U.ALL))
    x = np.array([feats.get(n, np.nan) for n in names])
    missing = [n for n, v in zip(names, x) if not np.isfinite(v)]
    x = np.where(np.isfinite(x), x, 0.0)
    if missing:
        notes.append(f"no data for {', '.join(missing)}; taken as 0")
    record = {(f["sector"], f["target"]): f for f in (study_forecasts or [])}

    sectors = []
    for m in U.SECTORS:
        row = {"sector": m.key, "name": m.name}
        own = bars.get(m.key)
        actual_gap = None
        if own is not None and own.dates and own.dates[-1] == session and len(own.dates) > 1 and own.dates[-2] == last_india:
            actual_gap = own.open[-1] / own.close[-2] - 1          # the open is final once set
        for target in ("gap", "intraday"):
            fnames = features_for(panel, m.key, target)
            X = np.column_stack([panel[n] for n in fnames])
            xt = x
            if target == "intraday":   # the open-to-close model also uses the sector's own 09:15 gap
                own_gap = actual_gap if actual_gap is not None else row["gap"]["expected_bps"] / 1e4
                xt = np.append(x, own_gap)
            y = panel[f"{m.key}:{target}"]
            ok = np.all(np.isfinite(X), axis=1) & np.isfinite(y)
            mu, sd, beta, intercept = models._fit(X[ok], y[ok], models.RIDGE)
            z = (xt - mu) / sd
            forecast = float(z @ beta + intercept)
            fitted = ((X[ok] - mu) / sd) @ beta + intercept
            confident = abs(forecast) >= float(np.quantile(np.abs(fitted), 2 / 3))
            contrib = sorted(((fnames[j], float(z[j] * beta[j])) for j in range(len(fnames))), key=lambda c: -abs(c[1]))[:3]
            past = record.get((m.key, target), {})
            row[target] = {
                "expected_bps": round(forecast * 1e4, 1),
                "direction": "up" if forecast > 0 else "down",
                "high_confidence": bool(confident),
                "out_of_sample_hit_rate": past.get("confident_hit_rate" if confident else "hit_rate"),
                "significant_after_adjustment": past.get("significant_after_adjustment"),
                "main_drivers": [{"cue": c, "bps": round(v * 1e4, 1)} for c, v in contrib],
            }
            if target == "intraday":
                row[target]["uses_gap"] = "actual 09:15 gap" if actual_gap is not None else "expected gap (India not open yet)"
        if actual_gap is not None:
            row["actual_gap_bps"] = round(actual_gap * 1e4, 1)
        sectors.append(row)

    moves = [{"market": U.get(n.split(":")[0]).name, "cue": n,
              "move": round(float(feats[n]), 4) if np.isfinite(feats.get(n, np.nan)) else None,
              "unit": "points" if n.split(":")[0] in U.LEVEL_CHANGE else "return"} for n in names]
    return {
        "for_session": session.isoformat(),
        "since_india_close": last_india.isoformat(),
        "generated_utc": now.strftime("%Y-%m-%d %H:%M"),
        "overnight_moves": moves,
        "sectors": sectors,
        "notes": notes + ([f"unavailable: {', '.join(failed)}"] if failed else []),
        "reading": "Opening-gap forecasts have a strong out-of-sample record; open-to-close forecasts are close to a coin toss "
                   "except where marked significant. Historical relationships only; not a recommendation.",
    }
