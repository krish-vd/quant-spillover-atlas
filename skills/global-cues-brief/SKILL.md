---
name: global-cues-brief
description: Morning brief on global cues for Indian markets - what the US, Europe, Japan, Korea, Taiwan, Hong Kong, China, the dollar, crude, copper, gold, VIX, US yields and Indian ADRs did since India's last close, and what such moves have historically meant for each Nifty sector (Nifty 50, IT, Bank, Metal, Pharma, Auto, Energy, FMCG) at the open and during the day, with each forecast's out-of-sample track record. Use when the user asks about global cues, how the market will open, what overnight moves mean for Indian sectors, GIFT Nifty-style pre-market context, or wants a pre-market briefing.
---

# Global Cues Brief

```bash
python scripts/brief.py                 # all sectors
python scripts/brief.py --sector it,metal
```

It works out which Indian session is next and collects only what is known before 09:15 IST:
overnight markets since India's last close, and each Asian market's opening gap once it has
opened. A ridge model fitted on ten years turns those into an expected opening gap and
open-to-close move per sector.

## Reading the output

| Field | Meaning |
|---|---|
| `overnight_moves` | Each cue: returns for markets, changes in points for VIX and the 10-year yield |
| `sectors[].gap.expected_bps` | Expected opening gap in basis points |
| `sectors[].gap.out_of_sample_hit_rate` | How often the gap's direction was right in the walk-forward test: the high-confidence rate when today's forecast is high-confidence, the overall rate otherwise |
| `sectors[].intraday` | The same for the move from the open to the close |
| `significant_after_adjustment` | Whether that forecast type beat its baseline after correcting for the many tests run |
| `main_drivers` | The three cues contributing most to today's forecast, in basis points |
| `notes` | Markets not yet open, still trading, or missing |

## How to present it

1. Lead with the overnight picture: the two or three largest moves.
2. Give the expected opening gap by sector with its hit rate ("historically right about 3 times in 4").
3. Be explicit that open-to-close forecasts are close to a coin toss unless `significant_after_adjustment` is true (historically only Metal, through copper). Do not present them as an edge.
4. Name the drivers.
5. If Asian markets have not opened yet, say the forecast uses overnight markets only and will sharpen after 06:30 IST.
6. Once India has opened, each sector shows `actual_gap_bps`. Say plainly whether the call was right.
7. `--record` saves the forecasts to the local forward-test record. They count only if made before 09:15 IST (see the `forecast-ledger` skill).

## Rules

- This is a description of historical relationships, not a recommendation. Never say "buy" or "sell"; say "has historically been associated with".
- The gap is set at 09:15 and cannot be traded from the previous close. Do not suggest it can.
- Prices come from an unofficial free source and may be delayed.
