"""Writes run-config.json for the US100 CRT raw study (versions declared in RULES.md before any result)."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent
common = {"InpTimeframe": "0", "InpEntryMode": "1", "InpUseBias": "true", "InpSession": "0", "InpMaxTradesPerDay": "1", "InpSkipMonday": "false",
          "InpRewardRisk": "1.5", "InpRiskPercent": "1.0", "InpRandomMode": "0", "InpRandomSeed": "1", "InpServerUtcOffsetHours": "0",
          "InpMaximumDeviationPoints": "1000", "InpMagic": "2910290"}
grid = {}
for tf, tl in (("0", "ALL"), ("15", "M15"), ("30", "M30"), ("60", "H1")):
    for em, el in (("0", "D"), ("1", "R")):
        for bi, bl in (("false", "N"), ("true", "B")):
            name = 'first of M15/M30/H1' if tl == 'ALL' else tl
            grid[f"{tl}_{el}_{bl}"] = dict(label=f"{name} CRT, {'direct break' if el == 'D' else 'rebreak'}, {'H1 bias' if bl == 'B' else 'no bias'}, NY 09:30-12:00, 1/day, 1.5R",
                                           inputs=dict(InpTimeframe=tf, InpEntryMode=em, InpUseBias=bi))
controls = {f"RND{s}": dict(label=f"Control: MAIN with a random direction at each trigger, same TP/SL distances, seed {s}",
                            inputs=dict(InpRandomMode="1", InpRandomSeed=str(s))) for s in (1, 2, 3)}
controls.update({
    "S_MON": dict(label="Sensitivity: MAIN, skip Mondays", inputs=dict(InpSkipMonday="true")),
    "S_ASIA": dict(label="Sensitivity: MAIN in the Asia window 20:00-22:00 ET", inputs=dict(InpSession="1")),
    "S_TWO": dict(label="Sensitivity: MAIN, 2 trades a day", inputs=dict(InpMaxTradesPerDay="2")),
    "S_R13": dict(label="Sensitivity: MAIN at 1.3R", inputs=dict(InpRewardRisk="1.3")),
    "MAIN_M4": dict(label="Model 4 confirmation: MAIN = ALL_R_B (first TF, rebreak, H1 bias)", inputs={}),
    "SIMPLE_M4": dict(label="Model 4 confirmation: SIMPLE = ALL_D_N (first TF, direct break, no bias)", inputs=dict(InpEntryMode="0", InpUseBias="false")),
})
cfg = dict(purpose="User request 2026-10-29: raw-test the pasted CRT three-candle setup on US100 with in-sample and out-of-sample data. Research only; rules frozen in RULES.md.",
           isolated_tester="_Backtests/MT5-DMC-20260811", profile="Calyx Research Empty", login=472334559, server="Exness-MT5Trial16",
           deposit=10000, currency="USD", leverage="1:2000", model=1, execution_delay_ms=150, period="M1", timeout_seconds=14400,
           end_date="2026.10.27", periods={"6m": "2026.04.27", "1y": "2025.10.27", "3y": "2023.10.27", "5y": "2021.10.27"},
           split={"development": ["2021-10-27", "2023-10-27"], "validation": ["2023-10-27", "2024-10-27"], "oos": ["2024-10-27", "2026-10-27"]},
           expert_dir="AAA Research" + chr(92) + "US100 CRT 20261029", source="EA/US100 CRT Research EA.mq5", expert_file="US100 CRT Research EA.ex5",
           symbols=["USTEC"], common_inputs=common, variants=grid, controls=controls)
(R / 'run-config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
print(len(grid), 'grid versions,', len(controls), 'controls / sensitivities / confirmations')
