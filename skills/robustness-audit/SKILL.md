---
name: robustness-audit
description: Stress-test a global-cue forecast for a Nifty sector - Pesaran-Timmermann directional test, block-bootstrap confidence interval, probability calibration (Brier skill), hit rate by forecast size, placebo tests (shuffled foreign data, one-session-late cues, and the naive same-date-close mistake), challenger models (recent window, logistic, non-linear) and splits by VIX regime and size of the US move. Use when the user asks whether a forecast is real or overfit, how confident to be in an accuracy number, whether results hold in volatile markets, or wants a sceptic's review of the cue-backtest results.
---

# Robustness Audit

```bash
python scripts/audit.py --sector nifty --target gap
python scripts/audit.py --sector metal --target intraday --permutations 100
```

Targets: `gap` (opening gap, set at 09:15) or `intraday` (open to close, which also uses the sector's own 09:15 gap).

## Reading the output

| Section | What it checks | What a sound result looks like |
|---|---|---|
| `model.hit_rate_95ci` | Block-bootstrap interval, resampling 10-session blocks so serial dependence is respected | Lower bound above the baseline |
| `model.pesaran_timmermann` | Directional skill beyond what the base rates of up and down days imply | p below 0.05 |
| `model.calibration` | Brier skill score of the probabilities against always forecasting the base rate; reliability bins | Skill above 0, and observed close to forecast in each bin |
| `model.confidence_curve` | Hit rate by quintile of forecast size | Rising from the smallest to the largest quintile |
| `placebos.shuffled_*` | Foreign data reordered at random, many draws | The true model beats every draw (`permutation_p_value` at its minimum, 1/(draws+1)) |
| `placebos.lagged_one_session` | Every cue one session late | Falls back to the baseline |
| `placebos.naive_same_date_closes` | Uses closes India could not know at 09:15 | Shows how much a careless study overstates accuracy. **Not a valid result** |
| `challengers` | Recent-window ridge, logistic, non-linear ridge | No challenger wins by more than about 1 point; if one does, say so |
| `regimes` | Hit rate when VIX is high or low, and for small, medium and large US moves | Where the forecast is most and least useful |

## What it showed (to Nov 2026)

- **Nifty 50 gap:** 75.7% (95% interval 73.7–77.7%), Pesaran-Timmermann z = 20. Shuffled data scores 63.7% and one-session-late cues 61%. The hit rate rises from 56% in the smallest-forecast quintile to 93% in the largest, and is 83% when the US move is large.
- **Open to close:** a naive study would report 67% for Nifty 50 and Bank. The honest figures are 52% and 51%, and shuffled data does as well. Only Metal is significant (55.5%, Pesaran-Timmermann p ≈ 4e-6, above every shuffled draw).

## Rules

- Present `naive_same_date_closes` only as the cost of getting timing wrong, never as achievable accuracy.
- With 50 draws, the smallest possible permutation p-value is about 0.02. Say "beat all 50 shuffles" rather than quoting it as weak.
- Regime splits are descriptive: they use the full out-of-sample period to pick thresholds.
