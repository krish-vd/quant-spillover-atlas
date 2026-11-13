---
name: cue-backtest
description: Out-of-sample walk-forward test of whether global cues (US, Europe, Asian opening gaps, dollar, crude, copper, gold, VIX, US yields, Indian ADRs) forecast Nifty sectors - separately for the opening gap and for the open-to-close move - with hit rates, high-confidence hit rates, naive baselines, out-of-sample R-squared, a by-year breakdown and p-values corrected for multiple testing. Use when the user asks whether global cues predict the Indian market, how accurate overnight signals are, whether the US move is priced in at the open, or wants evidence before relying on pre-market cues.
---

# Cue Backtest

```bash
python scripts/backtest.py
python scripts/backtest.py --sector it,metal --by-year
```

## Design

- **Features:** only what is known before 09:15 IST. That means overnight markets since India's last close and Asian opening gaps. Asian closes are excluded, because they come after India opens.
- **Model:** ridge regression with the penalty fixed in advance, refitted monthly on past data only. The first 500 sessions are used for training only.
- **Two targets, reported separately:**
  - the **gap** (open / previous close), set at the opening auction and not tradable from the previous close;
  - the **intraday** move (close / open), which is the tradable part.
- **Scoring:** every figure is out of sample and compared with two baselines: always forecasting the training period's majority direction, and following the single best cue. p-values are Holm-adjusted across all 16 sector-target tests.

## Reading the output

| Field | Meaning |
|---|---|
| `hit_rate` | Share of sessions where the forecast direction was right |
| `confident_hit_rate` | The same on sessions where the forecast was in the top third by size, a threshold set from training data |
| `baseline_majority`, `baseline_best_single_cue` | What a naive rule scored on the same sessions |
| `p_value_holm_adjusted`, `significant_after_adjustment` | Whether the hit rate beats the better of 50% and the majority baseline, after correcting for 16 tests |
| `oos_r2` | Out-of-sample R-squared against a forecast of zero. Negative means worse than no forecast |
| `breakeven_round_trip_cost_bps` | For the intraday target, the cost per round trip that would wipe out the average gain from following the forecast |
| `drivers` | Full-sample weights, to explain the model. They are not used for scoring |

## What ten years showed (to Nov 2026)

- Gap direction was right **73–76%** of the time in every sector, and **84–89%** on high-confidence days. All are significant after adjustment.
- Open-to-close was right **50–56%** of the time. Only Nifty Metal was significant after adjustment, driven by copper. The rest is consistent with the cues being priced in by the open.

## Rules

- Always present the gap and intraday results side by side. A high gap hit rate alone is misleading, because the gap cannot be traded.
- Quote `significant_after_adjustment`, not the raw p-value.
- Never call a result an edge if `breakeven_round_trip_cost_bps` is below realistic costs. For index futures, a round trip costs about 2–5 bps plus slippage.
- Historical results do not guarantee future ones. This is research, not a recommendation.
