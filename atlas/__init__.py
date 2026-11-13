"""quant-spillover-atlas: how moves in foreign markets reach Indian sectors.

Modules
  universe       markets, Indian sectors and when each one's information is available in India
  data           keyless daily prices with a disk cache
  panel          the time-zone-aware dataset: what was known before India's open, and what happened after
  models         walk-forward forecasts and honest out-of-sample scoring
  connectedness  Diebold-Yilmaz spillover index from a VAR and generalised variance decomposition
  exposure       which foreign markets each Indian sector moves with
  brief          the morning brief: what moved overnight and what it has meant historically
"""
__version__ = "0.1.0"
