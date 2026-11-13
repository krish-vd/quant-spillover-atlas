"""Keyless daily prices from Yahoo's chart endpoint, cached on disk.

Bars are dated in each exchange's local calendar (Yahoo's ``gmtoffset``), which is
what the timing rules in ``universe`` rely on. A session that has not finished is
marked, never silently used as if it were final.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from .universe import Market

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range}&interval=1d"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
RANGES = ("1y", "2y", "5y", "10y", "max")


class DataUnavailable(RuntimeError):
    """The source returned nothing usable."""


@dataclass
class Bars:
    key: str
    dates: list[date] = field(default_factory=list)
    open: list[float] = field(default_factory=list)
    close: list[float] = field(default_factory=list)
    last_final: bool = True   # False when the last bar is a session still in progress

    def __len__(self) -> int:
        return len(self.dates)


def cache_dir() -> Path:
    root = os.environ.get("SPILLOVER_ATLAS_CACHE") or str(Path.home() / ".cache" / "quant-spillover-atlas")
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get(url: str, cache_name: str, max_age_s: float) -> bytes:
    path = cache_dir() / cache_name
    if path.exists() and time.time() - path.stat().st_mtime < max_age_s:
        return path.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            path.write_bytes(body)
            return body
        except Exception as exc:  # urllib raises several unrelated types
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    if path.exists():  # stale but usable beats nothing; the caller sees the dates
        return path.read_bytes()
    raise DataUnavailable(f"{url}: {last_error}")


def parse_chart(payload: dict, market: Market, now_utc: datetime | None = None) -> Bars:
    try:
        result = payload["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        stamps = result["timestamp"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DataUnavailable(f"no price history for {market.ticker}") from exc
    offset = result.get("meta", {}).get("gmtoffset", 0)
    bars = Bars(market.key)
    for i, ts in enumerate(stamps):
        o, c = quote["open"][i], quote["close"][i]
        if c is None or c <= 0:
            continue
        if o is None or o <= 0 or not market.use_open:
            o = float("nan")
        day = datetime.fromtimestamp(ts + offset, tz=timezone.utc).date()
        if bars.dates and day <= bars.dates[-1]:
            continue
        bars.dates.append(day)
        bars.open.append(float(o))
        bars.close.append(float(c))
    if not bars.dates:
        raise DataUnavailable(f"empty price history for {market.ticker}")
    now = now_utc or datetime.now(timezone.utc)
    last = bars.dates[-1]
    close_at = datetime(last.year, last.month, last.day, tzinfo=timezone.utc).timestamp() + (market.close_utc + 0.5) * 3600
    if market.close_utc < market.open_utc:  # session ends the next UTC day (futures, FX)
        close_at += 86400
    bars.last_final = now.timestamp() >= close_at
    return bars


def load(market: Market, range_: str = "10y", max_age_hours: float = 6.0) -> Bars:
    if range_ not in RANGES:
        raise ValueError(f"range must be one of {RANGES}")
    url = CHART_URL.format(symbol=urllib.parse.quote(market.ticker), range=range_)
    name = "yh_" + re.sub(r"[^A-Za-z0-9]", "_", market.ticker) + f"_{range_}.json"
    body = _get(url, name, max_age_hours * 3600)
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise DataUnavailable(f"unreadable response for {market.ticker}") from exc
    return parse_chart(payload, market)


def load_many(markets, range_: str = "10y") -> tuple[dict[str, Bars], list[str]]:
    out, failed = {}, []
    for m in markets:
        try:
            out[m.key] = load(m, range_)
        except DataUnavailable:
            failed.append(m.key)
    return out, failed
