"""The markets studied and the rule for when each one's information reaches India.

India trades 09:15-15:30 IST (03:45-10:00 UTC). Every other market falls into one of
three timing classes relative to that window:

* ``overnight``: closes after India closes and before India opens next day (the
  Americas, Europe, futures, the dollar). Its session dated D is fully known before
  India's session dated D+1 opens.
* ``asia``: opens before India opens and closes before India closes (Japan, Korea,
  Taiwan, Hong Kong, China). On day D its OPEN is known at India's open; its CLOSE is
  known only during India's session, so it can explain India's day but cannot be used
  to forecast it from the open.
* ``india``: the targets.

The hours below are standard (non-daylight-saving) local times converted to UTC and
are used for display only. The forecasting rules use session dates, not clock times.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Market:
    key: str
    name: str
    ticker: str
    region: str
    timing: str           # overnight | asia | india
    kind: str             # equity | sector | fx | commodity | rates | volatility | adr
    open_utc: float       # hours, display only
    close_utc: float      # hours, display only
    use_open: bool = True  # False where the source's open price is unreliable


GLOBAL = (
    Market("spx", "S&P 500", "^GSPC", "United States", "overnight", "equity", 14.5, 21.0),
    Market("ndx", "Nasdaq Composite", "^IXIC", "United States", "overnight", "equity", 14.5, 21.0),
    Market("sox", "Philadelphia Semiconductor", "^SOX", "United States", "overnight", "equity", 14.5, 21.0),
    Market("sx5e", "Euro Stoxx 50", "^STOXX50E", "Euro area", "overnight", "equity", 8.0, 16.5),
    Market("nky", "Nikkei 225", "^N225", "Japan", "asia", "equity", 0.0, 6.5),
    Market("kospi", "KOSPI", "^KS11", "South Korea", "asia", "equity", 0.0, 6.5),
    Market("twse", "Taiwan Weighted", "^TWII", "Taiwan", "asia", "equity", 1.0, 5.5),
    Market("hsi", "Hang Seng", "^HSI", "Hong Kong", "asia", "equity", 1.5, 8.0),
    Market("shcomp", "Shanghai Composite", "000001.SS", "China", "asia", "equity", 1.5, 7.0),
)

MACRO = (
    Market("dxy", "US Dollar Index", "DX-Y.NYB", "United States", "overnight", "fx", 0.0, 22.0),
    Market("usdinr", "US dollar / rupee", "INR=X", "India", "overnight", "fx", 0.0, 22.0, use_open=False),
    Market("brent", "Brent crude", "BZ=F", "Global", "overnight", "commodity", 1.0, 22.0),
    Market("copper", "Copper", "HG=F", "Global", "overnight", "commodity", 23.0, 22.0),
    Market("gold", "Gold", "GC=F", "Global", "overnight", "commodity", 23.0, 22.0),
    Market("vix", "CBOE VIX", "^VIX", "United States", "overnight", "volatility", 14.5, 21.0),
    Market("ust10", "US 10-year yield", "^TNX", "United States", "overnight", "rates", 14.5, 21.0),
    Market("infy_adr", "Infosys ADR", "INFY", "United States", "overnight", "adr", 14.5, 21.0),
    Market("hdb_adr", "HDFC Bank ADR", "HDB", "United States", "overnight", "adr", 14.5, 21.0),
)

SECTORS = (
    Market("nifty", "Nifty 50", "^NSEI", "India", "india", "sector", 3.75, 10.0),
    Market("it", "Nifty IT", "^CNXIT", "India", "india", "sector", 3.75, 10.0),
    Market("bank", "Nifty Bank", "^NSEBANK", "India", "india", "sector", 3.75, 10.0),
    Market("metal", "Nifty Metal", "^CNXMETAL", "India", "india", "sector", 3.75, 10.0),
    Market("pharma", "Nifty Pharma", "^CNXPHARMA", "India", "india", "sector", 3.75, 10.0),
    Market("auto", "Nifty Auto", "^CNXAUTO", "India", "india", "sector", 3.75, 10.0),
    Market("energy", "Nifty Energy", "^CNXENERGY", "India", "india", "sector", 3.75, 10.0),
    Market("fmcg", "Nifty FMCG", "^CNXFMCG", "India", "india", "sector", 3.75, 10.0),
)

# Yields and volatility move in points, not percent: their change, not their return, is the signal.
LEVEL_CHANGE = {"vix", "ust10"}

ALL = GLOBAL + MACRO + SECTORS
BY_KEY = {m.key: m for m in ALL}


def get(key: str) -> Market:
    try:
        return BY_KEY[key]
    except KeyError:
        raise KeyError(f"unknown market {key!r}; known: {', '.join(sorted(BY_KEY))}") from None
