---
name: sector-exposure
description: Measure how each Nifty sector (IT, Bank, Metal, Pharma, Auto, Energy, FMCG, Nifty 50) responds to each foreign market or macro cue - S&P 500, Nasdaq, semiconductors, Euro Stoxx, Nikkei, KOSPI, Taiwan, Hang Seng, Shanghai, dollar, rupee, crude, copper, gold, VIX, US yields, Infosys and HDFC Bank ADRs - with betas for the opening gap, the open-to-close move and the whole day, the share already priced at the 09:15 open, and how the link has changed over time. Use when the user asks which global market drives a sector, how sensitive Indian IT is to the Nasdaq, whether metals follow copper, how much of a US move India absorbs at the open, or whether a link is strengthening.
---

# Sector Exposure

```bash
python scripts/exposure.py --sector it
python scripts/exposure.py --sector metal --cue copper:overnight --rolling
python scripts/exposure.py --list-cues
```

## Reading the output

| Field | Meaning |
|---|---|
| `beta_gap`, `beta_intraday`, `beta_cc` | The sector's move per unit move in the cue, at the open, during the day and for the whole day |
| `corr_*` | The matching correlations, which show how reliable each beta is |
| `priced_at_open_pct` | `beta_gap / beta_cc`. Near 100: fully priced at 09:15. Below 100: the response continues during the day. Above 100: the open overshoots and part reverses |
| `rolling_one_year_corr` | How the link has strengthened or weakened |

## What ten years showed

- Nifty IT moves about 0.28% per 1% Nasdaq move over the day, and about 89% of that is in the opening price.
- The open overshoots on US moves for Nifty Bank (123% priced at the open) and Nifty 50 (113%).
- Copper is the exception for Metal. Only about 37% of copper's effect is in the opening price, and the rest comes during the day. This is the one open-to-close link that survived the multiple-testing correction in `cue-backtest`.

## Rules

- Betas are averages over ten years. Use `--rolling` before claiming a link holds today.
- Cues are dated by when India could know them: `:overnight` for markets that close after India, `:gap` for Asian opening gaps.
- This describes historical behaviour and is not a recommendation.
