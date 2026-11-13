---
name: forecast-ledger
description: Keep a live forward-test record of the global-cues model - save each morning's sector forecasts before 09:15 IST with a timestamp, then score them against NSE's official open and close. Only forecasts made before the open count, so the record cannot be improved with hindsight. Use when the user wants to start tracking the model live, record today's forecast, see how the live forecasts have done, or compare live accuracy with the backtest.
---

# Forecast Ledger

```bash
python scripts/ledger.py record    # before 09:15 IST: run the brief and save it
python scripts/ledger.py score     # any time after the close: score all saved pre-open forecasts
python scripts/ledger.py show      # list the record
```

The record is a JSON-lines file in `~/.quant-spillover-atlas/forecast_ledger.jsonl`, or in `SPILLOVER_ATLAS_HOME`. It stays on the user's machine, outside the repository.

## Rules the record enforces

- A forecast counts only if it was made before 09:15 IST on the session it forecasts. Later ones are stored, marked as late, and never scored.
- The first pre-open forecast for a session stands. A second one is refused, so a forecast cannot be replaced by a better one.
- Scoring uses NSE's official index file: gap = open ÷ previous close − 1, and open-to-close = close ÷ open − 1.

## How to present the score

- Give the gap and open-to-close hit rates with the number of sessions, alongside the walk-forward rates from `cue-backtest` (gap about 75%, open-to-close about 50–55%).
- Under about 60 sessions, say the record is too short to judge. One bad week at a 75% hit rate is expected.
- For a weekday routine: run `record` between 06:30 IST (Asia open) and 09:10 IST, and `score` in the evening.
