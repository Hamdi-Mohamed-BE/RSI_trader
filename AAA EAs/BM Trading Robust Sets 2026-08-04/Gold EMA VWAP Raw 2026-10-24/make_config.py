"""Writes run-config.json from the frozen RULES.md versions (run once, before any test)."""
import json
from pathlib import Path

A = {"InpMode": "0", "InpFastEMA": "5", "InpSlowEMA": "13", "InpUseVwapFilter": "true", "InpUseAdx": "true", "InpUseSeparation": "true", "InpStopMode": "0", "InpRR": "2.0"}
Bv = {"InpMode": "1", "InpFastEMA": "9", "InpSlowEMA": "21", "InpUseTrend": "true", "InpUseSlope": "true", "InpStopMode": "1", "InpStopAtr": "1.5", "InpRR": "2.0"}
cfg = {
    "purpose": "User request 2026-10-24: find and backtest an EMA + VWAP combo on gold. Research only; rules frozen in RULES.md.",
    "isolated_tester": "_Backtests/MT5-DMC-20260811", "profile": "Calyx Research Empty", "login": 472334559, "server": "Exness-MT5Trial16",
    "deposit": 10000, "currency": "USD", "leverage": "1:2000", "model": 4, "execution_delay_ms": 150, "period": "M15", "timeout_seconds": 3600,
    "end_date": "2026.10.24", "periods": {"6m": "2026.04.24", "1y": "2025.10.24", "3y": "2023.10.24", "5y": "2021.10.24"},
    "expert_dir": "AAA Research\\Gold EMA VWAP 20261024", "source": "EA/Gold EMA VWAP Research EA.mq5", "expert_file": "Gold EMA VWAP Research EA.ex5",
    "symbols": ["XAUUSD"],
    "common_inputs": {"InpRiskPercent": "1.0", "InpMode": "0", "InpFastEMA": "5", "InpSlowEMA": "13", "InpUseVwapFilter": "true", "InpUseAdx": "true",
                      "InpAdxPeriod": "14", "InpAdxMin": "20.0", "InpUseSeparation": "true", "InpSepAtr": "0.10", "InpUseTrend": "true", "InpUseSlope": "true",
                      "InpSlopePct": "0.01", "InpStopMode": "0", "InpStopAtr": "1.5", "InpMinStopAtr": "0.25", "InpRR": "2.0", "InpAtrPeriod": "14",
                      "InpVwapAnchor": "0", "InpRandomDirection": "false", "InpRandomSeed": "1", "InpMaximumDeviationPoints": "50", "InpMagic": "2410260"},
    "variants": {
        "A15": {"tf": "M15", "label": "A: EMA 5/13 cross + VWAP/ADX/separation filters, stop at EMA intersection, 2R (M15)", "inputs": A},
        "B5": {"tf": "M5", "label": "B: EMA 9 crosses session VWAP, EMA 9/21 trend, VWAP slope >= 0.01%, 1.5 ATR stop, 2R (M5)", "inputs": Bv}},
    "controls": {
        "A15_NOVWAP": {"of": "A15", "tf": "M15", "label": "Control: A without the VWAP filter", "inputs": {**A, "InpUseVwapFilter": "false"}},
        "A15_NOFILT": {"of": "A15", "tf": "M15", "label": "Control: pure EMA 5/13 cross (no VWAP, ADX or separation)",
                       "inputs": {**A, "InpUseVwapFilter": "false", "InpUseAdx": "false", "InpUseSeparation": "false"}},
        "B5_NOSLOPE": {"of": "B5", "tf": "M5", "label": "Control: B without the VWAP slope filter", "inputs": {**Bv, "InpUseSlope": "false"}}},
    "sensitivity": {
        "A15_TP15": {"of": "A15", "tf": "M15", "label": "Sensitivity: A with 1.5R target", "inputs": {**A, "InpRR": "1.5"}},
        "A15_TP3": {"of": "A15", "tf": "M15", "label": "Sensitivity: A with 3R target", "inputs": {**A, "InpRR": "3.0"}},
        "A15_DAY": {"of": "A15", "tf": "M15", "label": "Sensitivity: A with VWAP reset at server midnight", "inputs": {**A, "InpVwapAnchor": "1"}},
        "B5_TP15": {"of": "B5", "tf": "M5", "label": "Sensitivity: B with 1.5R target", "inputs": {**Bv, "InpRR": "1.5"}},
        "B5_TP3": {"of": "B5", "tf": "M5", "label": "Sensitivity: B with 3R target", "inputs": {**Bv, "InpRR": "3.0"}},
        "B5_ATR1": {"of": "B5", "tf": "M5", "label": "Sensitivity: B with 1.0 ATR stop", "inputs": {**Bv, "InpStopAtr": "1.0"}},
        "B5_ATR25": {"of": "B5", "tf": "M5", "label": "Sensitivity: B with 2.5 ATR stop", "inputs": {**Bv, "InpStopAtr": "2.5"}},
        "B5_DAY": {"of": "B5", "tf": "M5", "label": "Sensitivity: B with VWAP reset at server midnight", "inputs": {**Bv, "InpVwapAnchor": "1"}},
        "B15": {"of": "B5", "tf": "M15", "label": "Sensitivity: B on M15", "inputs": Bv}}}
for s in (1, 2, 3):
    cfg["controls"][f"RND{s}_A15"] = {"of": "A15", "tf": "M15", "label": f"Control: A signals, coin-flip direction, seed {s}", "inputs": {**A, "InpRandomDirection": "true", "InpRandomSeed": str(s)}}
    cfg["controls"][f"RND{s}_B5"] = {"of": "B5", "tf": "M5", "label": f"Control: B signals, coin-flip direction, seed {s}", "inputs": {**Bv, "InpRandomDirection": "true", "InpRandomSeed": str(s)}}
out = Path(__file__).with_name('run-config.json')
assert not out.exists(), 'run-config.json already frozen'
out.write_text(json.dumps(cfg, indent=2), encoding='utf-8'); print('config', len(cfg['variants']), len(cfg['controls']), len(cfg['sensitivity']))
