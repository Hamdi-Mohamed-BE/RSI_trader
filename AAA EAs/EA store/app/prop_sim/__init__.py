"""Prop-firm challenge simulator: rules as data, cached native MT5 trades as evidence, vectorised Monte Carlo.

Modules
-------
rules    programme registry (data/prop-rules/*.json) and EA compatibility checks
ledger   cached trades -> R ledger -> risk sizing, lot rounding, entry guards -> daily features
engine   calendar-block bootstrap / rolling starts and the vectorised phase / breach / payout state machine
metrics  standard statistics of the selected combination (historical ledger at the chosen risk)
service  request validation, caching and orchestration used by the web routes and the suggestion tool
"""
