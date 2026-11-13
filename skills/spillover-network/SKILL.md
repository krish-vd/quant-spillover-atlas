---
name: spillover-network
description: Measure how strongly world markets and Indian sectors transmit shocks to each other using the Diebold-Yilmaz connectedness (spillover) index - total spillover, which markets are net transmitters or receivers, the strongest directed links, what share of each Nifty sector's movement comes from abroad, and how connectedness changed over time (it jumps in crises). Covers the US (S&P 500, Nasdaq, semiconductors), Euro Stoxx, Japan, Korea, Taiwan, Hong Kong, China and Nifty sectors. Use when the user asks about market contagion, spillovers, interconnectedness, which country drives India, how exposed a sector is to global markets, or how linked markets were in a period such as 2020.
---

# Spillover Network

```bash
python scripts/network.py                                  # world markets + Nifty sectors, ten years
python scripts/network.py --level country                  # world markets + Nifty 50
python scripts/network.py --history                        # rolling index, to see crises
python scripts/network.py --start 2020-01-01 --end 2020-12-31
```

## Method

Returns are aligned to India's close: each market contributes the sessions that finished
between two Indian closes (the US session of the previous evening, today's Asian session,
today's Indian session). A VAR(1) is fitted on the standardised returns. The generalised
forecast-error variance decomposition at 10 sessions then gives, for each market, the share
of its uncertainty that comes from shocks elsewhere. The decomposition does not depend on
the order of the variables.

## Reading the output

| Field | Meaning |
|---|---|
| `total_index_pct` | Average share of a market's variance explained by the others. Higher means more tightly linked |
| `to_others_pct`, `from_others_pct` | How much each market gives to and receives from the rest |
| `net_pct` | Positive means a net transmitter, negative a net receiver |
| `share_from_abroad_pct` | For each Nifty sector, the share coming from foreign markets rather than other Indian sectors |
| `strongest_links` | Directed links where `source` explains `target` more than the reverse |
| `rolling_total_index` | The index over a 500-session window, recalculated monthly |

## How to present it

- Give the total index with context: about 63% at the country level over ten years, and about 72% at its peak in mid-2020 (rolling 500 sessions). The sector-level index runs higher, around 68%, because Indian sectors share domestic shocks.
- Name the top transmitters and receivers and explain the time-zone logic: markets that trade earlier in each 24-hour cycle tend to show as transmitters.
- For a sector question, lead with `share_from_abroad_pct` and the links into that sector.
- State plainly that this ranks markets by who moves first and who follows. It does not prove causation, and a period with few sessions (under about 300) gives unstable numbers.
