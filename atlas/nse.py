"""Official NSE index prices: the daily all-indices file from NSE's archive.

Each trading day NSE publishes ``ind_close_all_DDMMYYYY.csv`` with the open, high, low
and close of every index it computes. This module builds the Indian sector series from
those files, so the study's targets come from the exchange, not from a third party.

A published file never changes, so it is cached forever. A day with no file (holiday)
is remembered only when NSE answered "not found" and the day is more than a week old,
so a dropped connection is never mistaken for a holiday.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Callable, Optional

from .data import USER_AGENT, Bars, DataUnavailable, cache_dir

URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{dmy}.csv"
REFERER = "https://www.nseindia.com/"

# atlas sector key -> index name as NSE writes it (matched case-insensitively)
INDEX_NAMES = {
    "nifty": "nifty 50", "it": "nifty it", "bank": "nifty bank", "metal": "nifty metal",
    "pharma": "nifty pharma", "auto": "nifty auto", "energy": "nifty energy", "fmcg": "nifty fmcg",
}


def _fetch(day: date) -> Optional[bytes]:
    """The file's bytes, or None when NSE has no file for that day."""
    dmy = day.strftime("%d%m%Y")
    path = cache_dir() / f"nse_ind_{dmy}.csv"
    marker = cache_dir() / f"nse_ind_none_{dmy}"
    if path.exists():
        return path.read_bytes()
    if marker.exists():
        return None
    request = urllib.request.Request(URL.format(dmy=dmy), headers={"User-Agent": USER_AGENT, "Referer": REFERER})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            if not body.lstrip().lower().startswith(b"index name"):
                raise DataUnavailable(f"unexpected content for {day}")
            path.write_bytes(body)
            return body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                if day < date.today() - timedelta(days=7):
                    marker.write_text("no session", encoding="utf-8")
                return None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    raise DataUnavailable(f"could not download the NSE index file for {day.isoformat()}")


def parse(body: bytes) -> dict[str, tuple[float, float, float, float]]:
    """{lower-case index name: (open, high, low, close)} from one day's file."""
    out = {}
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig", errors="replace"))):
        name = (row.get("Index Name") or "").strip().lower()
        try:
            o, h, l, c = (float(row[k]) for k in ("Open Index Value", "High Index Value", "Low Index Value", "Closing Index Value"))
        except (KeyError, TypeError, ValueError):
            continue
        if name and c > 0 and name not in out:
            out[name] = (o, h, l, c)
    return out


def load_sectors(start: date, end: date, fetch: Callable[[date], Optional[bytes]] = _fetch,
                 workers: int = 6, progress: bool = False) -> tuple[dict[str, Bars], dict]:
    """Official daily bars for every sector in ``INDEX_NAMES`` from ``start`` to ``end``."""
    days, cursor = [], start
    while cursor <= end:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    bars = {k: Bars(k) for k in INDEX_NAMES}
    sessions, errors = 0, []

    def load(day):
        try:
            return day, fetch(day), None
        except DataUnavailable as exc:
            return day, None, str(exc)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, (day, body, err) in enumerate(pool.map(load, days), 1):
            if err:
                errors.append(err)
            if body is None:
                continue
            table = parse(body)
            if not table:
                continue
            sessions += 1
            for key, name in INDEX_NAMES.items():
                row = table.get(name)
                if row and row[0] > 0:
                    bars[key].dates.append(day)
                    bars[key].open.append(row[0])
                    bars[key].close.append(row[3])
            if progress and n % 500 == 0:
                print(f"  NSE index files: {n}/{len(days)}", file=sys.stderr, flush=True)
    for b in bars.values():
        b.last_final = True   # NSE publishes the file only after the close
    return bars, {"sessions": sessions, "download_errors": errors}


def compare(official: Bars, other: Bars, tolerance: float = 0.0005) -> dict:
    """How closely a second source agrees with the official series (relative tolerance)."""
    o = {d: (op, cl) for d, op, cl in zip(official.dates, official.open, official.close)}
    s = {d: (op, cl) for d, op, cl in zip(other.dates, other.open, other.close)}
    common = sorted(set(o) & set(s))
    open_bad = [d for d in common if abs(s[d][0] / o[d][0] - 1) > tolerance]
    close_bad = [d for d in common if abs(s[d][1] / o[d][1] - 1) > tolerance]
    return {
        "common_sessions": len(common),
        "only_official": len(set(o) - set(s)),
        "only_other": len(set(s) - set(o)),
        "open_mismatch": len(open_bad),
        "close_mismatch": len(close_bad),
        "open_match_pct": round(100 * (1 - len(open_bad) / len(common)), 2) if common else None,
        "close_match_pct": round(100 * (1 - len(close_bad) / len(common)), 2) if common else None,
        "first_mismatched_opens": [d.isoformat() for d in open_bad[:5]],
    }
