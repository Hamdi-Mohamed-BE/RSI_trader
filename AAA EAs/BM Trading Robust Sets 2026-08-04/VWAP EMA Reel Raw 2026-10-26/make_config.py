"""Writes run-config.json from the frozen RULES.md versions (run once, before any test)."""
import json
from pathlib import Path

cfg = {
    "purpose": "User request 2026-10-26: backtest the 'Trading with VWAP & EMA' reel. Research only; rules frozen in RULES.md.",
    "isolated_tester": "_Backtests/MT5-DMC-20260811", "profile": "Calyx Research Empty", "login": 472334559, "server": "Exness-MT5Trial16",
    "deposit": 10000, "currency": "USD", "leverage": "1:2000", "model": 4, "execution_delay_ms": 150, "period": "M5", "timeout_seconds": 3600,
    "end_date": "2026.10.26", "periods": {"6m": "2026.04.26", "1y": "2025.10.26", "3y": "2023.10.26", "5y": "2021.10.26"},
    "expert_dir": "AAA Research\\VWAP EMA Reel 20261026", "source": "EA/VWAP EMA Reel Research EA.mq5", "expert_file": "VWAP EMA Reel Research EA.ex5",
    "symbols": ["USTEC", "US500", "US30", "XAUUSD"],
    "common_inputs": {"InpRiskPercent": "1.0", "InpMode": "0", "InpEMAPeriod": "20", "InpStopATR": "2.0", "InpATRPeriod": "14",
                      "InpStartHourNY": "9", "InpStartMinuteNY": "30", "InpLastEntryHourNY": "15", "InpLastEntryMinuteNY": "30",
                      "InpFlatHourNY": "15", "InpFlatMinuteNY": "55", "InpServerUtcOffsetHours": "0", "InpMaximumDeviationPoints": "50", "InpMagic": "2610260"},
    "variants": {
        "M5": {"tf": "M5", "label": "Main: close vs VWAP & EMA20, M5", "inputs": {}},
        "M15": {"tf": "M15", "label": "Main: close vs VWAP & EMA20, M15", "inputs": {}}},
    "controls": {}, "sensitivity": {}}
for tf in ('M5', 'M15'):
    cfg["controls"][f"VWAPONLY_{tf}"] = {"of": tf, "tf": tf, "label": f"Control: close vs VWAP only, {tf}", "inputs": {"InpMode": "1"}}
    cfg["controls"][f"EMAONLY_{tf}"] = {"of": tf, "tf": tf, "label": f"Control: close vs EMA20 only, {tf}", "inputs": {"InpMode": "2"}}
    cfg["sensitivity"][f"EMA9_{tf}"] = {"of": tf, "tf": tf, "label": f"Sensitivity: EMA 9, {tf}", "inputs": {"InpEMAPeriod": "9"}}
    cfg["sensitivity"][f"EMA50_{tf}"] = {"of": tf, "tf": tf, "label": f"Sensitivity: EMA 50, {tf}", "inputs": {"InpEMAPeriod": "50"}}
out = Path(__file__).with_name('run-config.json')
assert not out.exists(), 'run-config.json already frozen'
out.write_text(json.dumps(cfg, indent=2), encoding='utf-8'); print('config written')
