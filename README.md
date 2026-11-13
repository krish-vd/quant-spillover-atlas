# quant-spillover-atlas

[![tests](https://github.com/krish-vd/quant-spillover-atlas/actions/workflows/tests.yml/badge.svg)](https://github.com/krish-vd/quant-spillover-atlas/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Data](https://img.shields.io/badge/data-NSE%20official%20%2B%20free%20%26%20keyless-brightgreen)

### Cross-market information transmission into Indian equity sectors: a time-zone-aware, out-of-sample, adversarially tested study, with Claude skills on top.

> **Global cues tell you where India will open. They do not tell you where it will close.**
> Information available before 09:15 IST calls the direction of the opening gap **73.5–75.8%** of the time out of sample across eight Nifty sectors, rising to **93%** on the model's most confident mornings. It calls the open-to-close move no better than chance, with one exception: copper into metal stocks. That anomaly was real, survived costs and a control test, and has since been largely arbitraged away.

---

## Contents

1. [Abstract](#abstract)
2. [Headline results](#headline-results)
3. [Out-of-sample backtest](#out-of-sample-backtest)
4. [Trying to break it: robustness](#trying-to-break-it-robustness)
5. [Is any of it tradable?](#is-any-of-it-tradable)
6. [Live forward test](#live-forward-test)
7. [Research design](#research-design)
8. [Spillover architecture](#spillover-architecture)
9. [Data provenance](#data-provenance)
10. [Skills](#skills) · [Showcase](#showcase) · [Reproduce](#reproduce)
11. [Threats to validity](#threats-to-validity)
12. [References](#references)

---

## Abstract

Indian equities open each morning after the US and Europe have closed, and while Asia is already trading. This makes the "global cues" problem a question of **information sets**: what is knowable at 09:15 IST, and how much of it has already been priced in by the opening auction?

The study builds a session-level panel on India's trading calendar from NSE's official index files. Every foreign series enters only through the information it carried **before** India's open:
- overnight returns for markets that close after India;
- opening gaps for Asian markets that open before India.

Asian closes, which arrive during India's session, are never used to forecast.

A ridge model is re-estimated monthly on past data only. It forecasts two separate targets for eight Nifty sectors: the **opening gap** and the **open-to-close** move. The results are then tested in five further ways:

1. directional-accuracy inference (Pesaran-Timmermann, block bootstrap, calibration);
2. placebos (shuffled, lagged and deliberately mis-timed data);
3. challenger models;
4. pre-registered intraday strategies after costs, with a stock-level control;
5. a live forward-test record that only accepts forecasts made before the open.

**Findings:**
- The opening gap is highly and stably predictable.
- The intraday move is not, which is consistent with global cues being absorbed efficiently at the open.
- A careless timing convention would overstate open-to-close accuracy by about 15 points: 67% claimed, against 52% honest.
- The single surviving intraday effect, copper into metal stocks, was economically coherent and significant after costs, but has decayed to near zero since 2025.

---

## Headline results

*Sample: 16 Nov 2016 to 12 Nov 2026, 2,468 Indian sessions, Indian prices from NSE's official index files. Out of sample: about 1,960 sessions from late 2018. Figures are regenerated on every run.*

| | |
|---|---|
| **Opening-gap direction, Nifty 50** | **75.7%** (95% block-bootstrap interval 73.7–77.7%). The always-up baseline is 64.9%, and the best single cue 71.9% |
| **Directional skill** | Pesaran-Timmermann **z = 20.3**. Brier skill score of the probabilities **+0.27** |
| **By confidence** | Hit rate by forecast-size quintile: **56% → 65% → 80% → 86% → 93%** |
| **Placebos** | Shuffled foreign data scores 63.7% (the best of 30 draws: 64.7%). Cues one session late score 61.0%. The model beat every placebo |
| **All 8 sectors, opening gap** | **73.5–75.8%**, all significant after a Holm correction across 16 tests |
| **Open-to-close direction** | **50.0–54.3%**. Significant only for Nifty Metal (55.5%, adjusted p = 0.046) |
| **The timing mistake** | Same-date closes would "show" **66.7%** open-to-close accuracy for Nifty 50 and **67.2%** for Bank. The honest figures are 52.4% and 50.6% |
| **Pass-through at the open** | Nifty Bank's open carries **123%** of its whole-day response to an S&P 500 move (it overshoots), and Nifty IT's **89%** of its response to the Nasdaq. Nifty Metal's carries only **37%** of its response to copper |
| **Tradable after costs?** | Six of seven pre-registered strategies are not. The copper rule in Nifty Metal is (+26.8% a year net, Sharpe 1.12, Holm p = 0.004), and it holds stock by stock (t = 4.0–5.3) but not in the Coal India control (t = 0.7). **It has decayed:** +69% in 2021, +5% in 2025, +2% in 2026 to date |
| **Exposure to the world** | Share of each sector's variance from abroad: IT 22.8%, Metal 22.1%, Auto 17.9%, Bank 17.8%, Energy 15.3%, FMCG 12.8%, Pharma 11.6% |
| **Global connectedness** | 63.2% (9 markets and the Nifty 50), peaking at 71.5% in July 2020 |

---

## Out-of-sample backtest

### Accuracy by sector and target

Direction hit rate on sessions the model never saw. The intervals are 95% circular block bootstraps with 10-session blocks. PT is the Pesaran-Timmermann statistic, and the p-values are Holm-adjusted across all 16 tests.

| Sector | Gap hit (95% CI) | Gap, high-conf. | Best baseline¹ | Gap PT z | Gap OOS R² | Open-to-close hit | O-to-C adj. p |
|---|---|---:|---:|---:|---:|---:|---:|
| Nifty 50 | **75.7%** (73.7–77.7) | 88.8% | 71.9% | 20.3 | 0.38 | 52.4% | 1.00 |
| IT | **75.8%** (73.8–77.7) | 87.6% | 70.3% | 21.3 | 0.41 | 50.0% | 1.00 |
| Bank | **73.8%** (71.5–75.9) | 86.9% | 70.4% | 19.6 | 0.34 | 50.6% | 1.00 |
| Metal | **74.9%** (73.0–76.8) | 87.5% | 71.0% | 18.6 | 0.41 | **55.5%** | **0.046** |
| Pharma | **75.4%** (73.4–77.4) | 88.4% | 70.6% | 16.6 | 0.31 | 54.3% | 1.00 |
| Auto | **75.4%** (73.6–77.2) | 86.5% | 69.6% | 18.3 | 0.34 | 53.2% | 1.00 |
| Energy | **75.2%** (73.1–77.3) | 88.2% | 70.0% | 17.6 | 0.32 | 53.9% | 1.00 |
| FMCG | **73.5%** (71.3–75.6) | 84.0% | 70.0% | 15.2 | 0.29 | 54.2% | 1.00 |

¹ The stronger of two baselines: always forecasting the training-period majority direction, and following the single best cue.

### Stability through time (Nifty 50 opening gap)

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 74.2% | 78.8% | 73.0% | 79.4% | 75.9% | 74.8% | 77.8% | 70.8% |

### Robustness to settings (not tuned on the test period)

| Ridge penalty → / refit every ↓ | 1 | 10 (default) | 100 |
|---|---:|---:|---:|
| 5 sessions | 75.9% | 75.9% | 76.0% |
| 21 sessions (default) | 75.9% | **75.9%** | 76.1% |
| 63 sessions | 75.5% | 76.0% | 75.9% |

Nifty 50 gap hit rate. The grid was run on Yahoo prices before the switch to official files; the spread is 0.6 points across a 100-fold range of the penalty.

---

## Trying to break it: robustness

`robustness-audit` runs every check below for any sector and target.

### Placebos

A real result must collapse when its information is destroyed. A careless study's result inflates when information leaks.

| Nifty 50 | Opening gap | Open to close |
|---|---:|---:|
| **Model** | **75.7%** | **52.4%** |
| Shuffled foreign data (mean of 30 draws / best draw) | 63.7% / 64.7% | 51.2% / 53.3% |
| Every cue one session late | 61.0% | 49.6% |
| Naive same-date closes (**invalid**, shown to measure the error) | 74.6% | **66.7%** |

- **The gap result is real.** It vanishes when the time link is broken.
- **The open-to-close result is not.** The model does no better than shuffled data.
- **The naive convention invents about 15 points of open-to-close "skill".** It pairs India's day with US and Asian sessions that close after India's open, information no trader has at 09:15. Most published "global cues" correlations make this mistake.

### Calibration and confidence

- **Brier skill score:** +0.27 against always forecasting the base rate.
- **Reliability:** the reliability bins track the diagonal.
- **Confidence:** the hit rate rises steadily with forecast size, from 56% in the smallest-forecast quintile to 93% in the largest. The forecast's size is informative, not just its sign.

### Challengers

A model is replaced only if a challenger wins out of sample by more than a percentage point:
- **Nifty 50 gap:** a logistic classifier scored 76.8% (+1.1 points), and non-linear ridge 76.4%. These gains fall inside the confidence interval, and neither challenger repeats them on IT, so the champion stays and the challengers are reported.
- **Open to close:** every challenger stays at 51–53%.

### Regimes

| Nifty 50 gap hit rate | |
|---|---:|
| US overnight move: small / medium / large | 69.5% / 74.7% / **82.9%** |
| VIX at or below 18 / above 18 | 72.8% / **78.7%** |

The cues matter most when markets are moving.

---

## Is any of it tradable?

`tradability-test` evaluates seven intraday strategies that are fixed in code, each entered at 09:15 and exited at 15:30 on the out-of-sample sessions:

- **Costs** are an explicit assumption: index futures at about 4.7 bps per round trip before April 2026 and 7.7 bps after (STT on futures sales rose from 0.02% to 0.05%), and stock baskets at about 7.5 bps.
- **Significance** uses Newey-West t-statistics, Holm-adjusted across all seven strategies.

| Strategy | Hit | Gross / trade | Net a year | Sharpe | Holm p |
|---|---:|---:|---:|---:|---:|
| Fade Bank Nifty's opening gap | 52.2% | 2.8 bps | −5.3% | −0.28 | 1.00 |
| Fade Nifty's opening gap | 49.8% | 1.8 bps | −7.9% | −0.57 | 1.00 |
| Fade only large Bank Nifty gaps | 52.8% | 6.2 bps | +1.2% | 0.08 | 1.00 |
| Follow the open-to-close model, Nifty | 52.4% | 5.1 bps | +0.3% | 0.02 | 1.00 |
| Follow the open-to-close model, Bank Nifty | 50.6% | 1.3 bps | −9.2% | −0.49 | 1.00 |
| Follow the open-to-close model, Nifty Metal (basket) | 55.5% | 17.9 bps | +26.2% | 1.07 | 0.007 |
| **Copper's overnight direction, Nifty Metal (basket)** | 55.3% | **18.6 bps** | **+26.8%** | **1.12** | **0.004** |

**The control test.** A genuine copper effect should appear in copper-linked businesses and not in a metal-index member that isn't one:

| Stock | Gross bps / day | Newey-West t |
|---|---:|---:|
| Nalco, Hindalco, Tata Steel, SAIL, Jindal Steel, Vedanta, NMDC, JSW Steel | 20.3–28.0 | 4.0–5.3 |
| Hindustan Zinc | 10.5 | 2.3 |
| **Coal India (control)** | **3.0** | **0.7** |

**Decay.** Net return of the copper rule by year: 2018 +3%, 2019 −7%, 2020 +45%, 2021 +69%, 2022 +43%, 2023 +13%, 2024 +35%, 2025 **+5%**, 2026 YTD **+2%**.

**Verdict.** This was a real, economically coherent anomaly. Its signal is known before NSE's 09:00–09:08 pre-open auction, so it was executable at the official open. It is now mostly arbitraged away. Two caveats:
- Nifty Metal was chosen for this test after it emerged as the one significant sector in the forecasting study. The Holm correction across 16 forecasting tests covers that selection, but it is stated plainly here.
- Only a live forward record can show whether anything remains.

---

## Live forward test

`forecast-ledger` writes the morning forecasts to a local, timestamped record. Three rules keep it honest:
- Only forecasts made **before 09:15 IST** on the session they forecast count.
- The first pre-open forecast for a session stands, and later ones are refused.
- Scoring uses NSE's official open and close.

The record cannot be improved with hindsight, and it stays on the user's machine, outside the repository.

```bash
python skills/forecast-ledger/scripts/ledger.py record   # weekdays, 06:30–09:10 IST (after Asia opens)
python skills/forecast-ledger/scripts/ledger.py score    # after the close
```

The morning brief also prints the actual gap next to the forecast once India opens. On **13 Nov 2026** all eight sector calls were wrong. Korea opened 2.1% higher, but India followed the weaker US close down. At a 76% hit rate, roughly one morning in four looks like this.

---

## Research design

### Information sets

India trades 09:15 to 15:30 IST (03:45 to 10:00 UTC). For Indian session *D* with previous session *P*:

| Class | Markets | Enters a forecast for *D* as | Why |
|---|---|---|---|
| Overnight | S&P 500, Nasdaq, SOX, Euro Stoxx 50, Brent, copper, gold, DXY, USD/INR, VIX, UST 10y, Infosys and HDFC Bank ADRs | close before *D* ÷ close before *P* − 1 | Sessions dated *P* … *D*−1 all close after India's close on *P* and before its open on *D* |
| Asia | Nikkei 225, KOSPI, Taiwan Weighted, Hang Seng, Shanghai Composite | open on *D* ÷ close on or before *P* − 1 | Asia opens before India; its session on *P* closed before India's did |
| Asia, contemporaneous | the same | close on *D* ÷ close on or before *P* − 1 | Arrives during India's session. **Never a forecast input** |
| The sector's own gap | the sector itself | open *D* ÷ close *P* − 1 | Known at 09:15, so it is an input for the open-to-close target only |
| Targets | Nifty 50 and 7 sector indices | gap = O*D*/C*P* − 1 · open-to-close = C*D*/O*D* − 1 · day = C*D*/C*P* − 1 | |

Further rules:
- A market that didn't trade in a window contributes zero.
- News from an Indian holiday accumulates into the next Indian session.
- VIX and yields enter as changes in points.
- An unfinished session is never used.
- Columns that are deliberately mis-timed exist only for the placebo study, and a unit test proves they cannot reach a forecast.

### Estimation and evaluation

| Step | Choice |
|---|---|
| Model | Ridge regression on standardised features, penalty fixed in advance (λ = 10) |
| Re-estimation | Every 21 sessions, on data strictly before the forecast window; the first 500 sessions train only. A test confirms that changing future data leaves past forecasts unchanged |
| Probabilities | Platt scaling fitted on each training window |
| High confidence | \|forecast\| at or above the training set's 67th percentile |
| Baselines | Training-majority direction; sign of the single best training-period cue |
| Inference | Pesaran-Timmermann test; binomial test against the stronger baseline, Holm-adjusted across 16 tests; circular block bootstrap intervals |
| Economic value | Strategies decided at 09:15, with explicit costs, Newey-West t-statistics, Holm-adjusted |

### Pass-through

For sector *s* and cue *x*, separate least-squares slopes are estimated for the gap, the open-to-close move and the whole day. The share of the response priced at the open is **β(gap) / β(day)**:
- **below 100%:** the response continues through the session;
- **above 100%:** the open overshoots and partly reverses.

---

## Spillover architecture

The Diebold and Yilmaz (2012) framework:

1. Every market's return is measured over the same window, from India's close on *P* to its close on *D*.
2. A VAR(1) is fitted to standardised returns.
3. A 10-session **generalised** forecast-error variance decomposition is computed (Pesaran and Shin, 1998). It does not depend on the order of the variables, and each row is normalised to sum to one.
4. From it come total connectedness, what each market gives, receives and nets, pairwise net spillovers, and a rolling 500-session index.

The implementation is tested against the closed form: with no dynamics and correlation ρ, the cross share is ρ²/(1+ρ²). A simulated leader-follower pair is also checked.

The network is a statistical ordering in time, not a causal claim. India's session ends before Europe's begins, so Indian sectors lead Euro Stoxx, while the US and North Asia lead India.

---

## Data provenance

| Series | Source | Check |
|---|---|---|
| Nifty 50 and 7 sector indices (the targets) | **NSE's official daily all-indices file** (`ind_close_all_DDMMYYYY.csv`), cached permanently | Against Yahoo: opens agree on **100%** of about 2,450 common sessions in 7 sectors and 99.96% in Pharma (one day). Closes agree on 99.96%. NSE has 11–27 sessions per sector that Yahoo lacks |
| World indices, futures, FX, VIX, yields, ADRs | Yahoo chart endpoint (unofficial, keyless), cached for 6 hours | USD/INR opens are unreliable, so only its closes are used. China is covered by the Shanghai Composite, because Yahoo has no CSI 300 history |
| Metal stocks (control test) | Yahoo, NSE-listed shares | Opens are the official pre-open auction prices |

If NSE cannot be reached, the study falls back to Yahoo for India and says so in its output (`india_source`). Each clone downloads its own data, so results are always current.

---

## Skills

Seven Claude skills sit on the engine. Each installs as a self-contained folder carrying its own copy of `atlas`.

| Skill | Answers |
|---|---|
| [`global-cues-brief`](skills/global-cues-brief/SKILL.md) | "What do last night's global cues mean for Indian sectors this morning?" Gives forecasts with their out-of-sample record, the actual gap once India opens, and an optional `--record` |
| [`cue-backtest`](skills/cue-backtest/SKILL.md) | "Do global cues really predict Nifty IT?" Gives the full walk-forward table with intervals, PT tests and adjusted p-values |
| [`robustness-audit`](skills/robustness-audit/SKILL.md) | "Is this accuracy real or overfit?" Runs the placebos, calibration, challengers and regimes |
| [`tradability-test`](skills/tradability-test/SKILL.md) | "Can any of this be traded after costs?" Runs the seven strategies, the cost grid and the control-stock test |
| [`forecast-ledger`](skills/forecast-ledger/SKILL.md) | "Start tracking the model live" and "How has it done since?" |
| [`sector-exposure`](skills/sector-exposure/SKILL.md) | "How sensitive is Metal to copper, and how much is priced in at 09:15?" |
| [`spillover-network`](skills/spillover-network/SKILL.md) | "Which countries drive the Indian market? How connected were markets in 2020?" |

## Showcase

```bash
python scripts/build_showcase.py --open        # add ?still to the URL for a static render
```

The command builds `showcase/index.html`, a single self-contained, animated page computed from the live study. It shows:
- the 24-hour relay of trading sessions;
- the spillover network, with particles moving along each link;
- the connectedness index through time;
- the out-of-sample scoreboard;
- pass-through at 09:15;
- the placebo tests;
- the confidence curve;
- the copper anomaly and its control;
- the co-movement heatmap;
- this morning's brief, scored against the actual open.

## Reproduce

```bash
git clone https://github.com/krish-vd/quant-spillover-atlas.git
cd quant-spillover-atlas
python -m pip install -r requirements.txt                       # numpy

python skills/cue-backtest/scripts/backtest.py --by-year
python skills/robustness-audit/scripts/audit.py --sector nifty --target gap
python skills/tradability-test/scripts/tradability.py --constituents
python skills/spillover-network/scripts/network.py --level country --history
python skills/global-cues-brief/scripts/brief.py

python scripts/install_skills.py                                # into ~/.claude/skills
python scripts/package_skills.py                                # zips for claude.ai in dist/
python -m pip install "pytest>=8,<9" && python -m pytest -q     # 30 tests
```

The first run downloads about 2,600 official NSE index files and ten years of 26 foreign series, which takes about 3 minutes. Later runs read from the cache.

---

## Threats to validity

| Concern | How it is handled |
|---|---|
| **Look-ahead** | Information sets are defined by session timing and unit-tested on hand-built calendars with a holiday. Deliberately mis-timed columns are proven never to reach a forecast. The walk-forward fits only on past data, and the confidence threshold and probability calibration come from training data |
| **Data snooping** | Settings were fixed before scoring and barely matter (robustness grid). All 16 forecasting tests and all 7 strategies are reported, with Holm adjustment. Placebos give the null distribution directly |
| **Serial dependence** | Block-bootstrap intervals and Newey-West t-statistics |
| **Base-rate illusions** | Pesaran-Timmermann tests, and baselines that already exploit the share of up days |
| **Tradability** | Gap accuracy is not a trading result. Strategies are decided at 09:15, with explicit costs and a sensitivity grid. The surviving one passes a stock-level control and is reported with its decay |
| **Execution** | Index levels stand in for instruments. Official-open fills are realistic only through the pre-open auction, and only for rules that need no Indian price. Large orders would do worse |
| **Data quality** | Indian targets come from NSE's official files, cross-checked against a second source. Foreign series come from a free, unofficial source |
| **Non-stationarity** | Ten years include a pandemic and a rate cycle. By-year results, a recent-window challenger and rolling connectedness show how relationships change. The copper effect's decay is the clearest example |
| **Causality** | Connectedness and pass-through are reduced-form. They describe ordering and co-movement, not structural transmission |

---

## References

- Diebold, F. X. and Yilmaz, K. (2009). Measuring financial asset return and volatility spillovers, with application to global equity markets. *Economic Journal*, 119(534), 158–171.
- Diebold, F. X. and Yilmaz, K. (2012). Better to give than to receive: predictive directional measurement of volatility spillovers. *International Journal of Forecasting*, 28(1), 57–66.
- Pesaran, H. H. and Shin, Y. (1998). Generalized impulse response analysis in linear multivariate models. *Economics Letters*, 58(1), 17–29.
- Pesaran, M. H. and Timmermann, A. (1992). A simple nonparametric test of predictive performance. *Journal of Business & Economic Statistics*, 10(4), 461–465.
- Politis, D. N. and Romano, J. P. (1992). A circular block-resampling procedure for stationary data. In *Exploring the Limits of Bootstrap*, Wiley, 263–270.
- Newey, W. K. and West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703–708.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65–70.
- Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In *Advances in Large Margin Classifiers*, MIT Press.
- Hoerl, A. E. and Kennard, R. W. (1970). Ridge regression: biased estimation for nonorthogonal problems. *Technometrics*, 12(1), 55–67.
- Hamao, Y., Masulis, R. W. and Ng, V. (1990). Correlations in price changes and volatility across international stock markets. *Review of Financial Studies*, 3(2), 281–307.
- King, M. A. and Wadhwani, S. (1990). Transmission of volatility between stock markets. *Review of Financial Studies*, 3(1), 5–33.
- Forbes, K. J. and Rigobon, R. (2002). No contagion, only interdependence: measuring stock market comovements. *Journal of Finance*, 57(5), 2223–2261.

---

## Disclaimer

This is for education and research. It is not investment advice, and not a recommendation to buy, sell or hold any security. The author is not registered with SEBI, the SEC or any other regulator as an investment adviser or research analyst. Historical relationships between markets, including any strategy result above, do not guarantee future ones. See [DISCLAIMER.md](DISCLAIMER.md).

Sister project: [claude-quant-skills](https://github.com/krish-vd/claude-quant-skills), with 50 Claude skills for Indian and US markets.

## Licence

MIT. See [LICENSE](LICENSE).
