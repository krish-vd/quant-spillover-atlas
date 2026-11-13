---
name: tradability-test
description: Test whether global-cue strategies on Indian sectors make money after realistic costs - fading the Nifty and Bank Nifty opening gap, following walk-forward open-to-close forecasts, and copper's overnight move into Nifty Metal - with net returns, Sharpe, Newey-West t-statistics, Holm-adjusted p-values across all strategies, results by year, a cost-sensitivity grid, and a stock-by-stock check with a control stock. Use when the user asks if a global-cues edge is tradable, whether gap fading works, what the copper-metal effect is worth, or how robust a strategy is to costs.
---

# Tradability Test

```bash
python scripts/tradability.py
python scripts/tradability.py --constituents
```

## Design

- **Fixed hypotheses:** seven intraday strategies, fixed in the code (`atlas/tradable.py`), each entered at 09:15 and exited at 15:30. They are scored on the same out-of-sample sessions as the forecasting study.
- **Costs:** an explicit, round-trip assumption.
  - Index futures: about 4.7 bps before April 2026 and 7.7 bps after, because STT rose from 0.02% to 0.05% that month.
  - Stock baskets: about 7.5 bps.
  - A grid of 0–12 bps lets a reader apply their own costs.
- **Significance:** Newey-West t-statistics with 5 lags, then Holm adjustment across all seven strategies.
- **`--constituents`:** applies the copper rule to each metal stock, with Coal India as a control, since it is a metal-index member whose business is not copper-linked. A real effect should appear stock by stock and not in the control.

## What it showed (to Nov 2026)

- **No edge after costs:** fading the opening gap (Nifty and Bank), and following the open-to-close forecast for Nifty or Bank. The Bank fade is 52% right but loses about 5% a year after costs.
- **The copper rule:** going with copper's overnight direction in Nifty Metal made about 18 bps a day gross and about 26% a year after costs. It has a Sharpe of 1.1 and is significant after adjustment. It holds stock by stock: Tata Steel, Hindalco, JSW, Vedanta, NMDC, SAIL, Jindal and Nalco each make 19–27 bps a day, while the Coal India control makes about 3 bps.
- **But it is decaying:** after costs it made 45%, 69% and 43% in 2020–22, then 5% in 2025 and 2% in 2026 to date. A live forward test (`forecast-ledger`) is needed before believing any of it remains.

## Rules

- Lead with the verdict and the year-by-year figures. Never quote the full-period return alone for a decaying effect.
- The index stands in for the instrument. Fills at the official open are realistic only through the 09:00–09:08 pre-open auction, and only for rules that need no Indian price, which the copper rule satisfies. They are optimistic for large orders.
- The Metal hypotheses were chosen after the forecasting study had shown Metal to be the one significant sector. The Holm correction across 16 forecasting tests covers that selection, but say it plainly.
- This is research, not a recommendation to trade.
