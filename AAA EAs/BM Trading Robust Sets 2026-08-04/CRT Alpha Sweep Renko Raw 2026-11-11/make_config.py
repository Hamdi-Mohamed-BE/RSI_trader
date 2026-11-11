"""Writes run-config.json for the CRT Alpha sweep raw study (versions declared in RULES.md before any result)."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent
common = {"InpUseRenko": "true", "InpReversalPoints": "4.5", "InpTrendPoints": "0.75", "InpBodyMinPct": "50.0", "InpStopBufferPoints": "0.5", "InpSession": "0",
          "InpRiskPercent": "1.0", "InpRandomMode": "0", "InpRandomSeed": "1", "InpServerUtcOffsetHours": "0", "InpMaximumDeviationPoints": "1000", "InpMagic": "2911110"}
variants = {
    "MAIN": dict(label="MAIN: sweep + premium/discount on a Renko reversal brick (4.5 / 0.75), all hours", inputs={}),
    "MAIN_NY": dict(label="MAIN, New York 09:30-16:00 ET only", inputs=dict(InpSession="1")),
    "PLAIN": dict(label="PLAIN: sweep + first premium/discount touch in C3 (no Renko), all hours", inputs=dict(InpUseRenko="false")),
    "PLAIN_NY": dict(label="PLAIN, New York 09:30-16:00 ET only", inputs=dict(InpUseRenko="false", InpSession="1")),
}
controls = {f"RND{s}": dict(label=f"Control: MAIN with a random direction at each trigger, same TP/SL distances, seed {s}", inputs=dict(InpRandomMode="1", InpRandomSeed=str(s))) for s in (1, 2, 3)}
controls.update(BRICK3=dict(label="Sensitivity: MAIN, reversal brick 3.0 points", inputs=dict(InpReversalPoints="3.0")),
                BRICK9=dict(label="Sensitivity: MAIN, reversal brick 9.0 points", inputs=dict(InpReversalPoints="9.0")))
cfg = dict(purpose="Owner 2026-11-11: recreate the NINZA CRT Alpha sweep video as it is. Research only; rules frozen in RULES.md.",
           isolated_tester="_Backtests/MT5-DMC-20260811", profile="Calyx Research Empty", login=472334559, server="Exness-MT5Trial16",
           deposit=10000, currency="USD", leverage="1:2000", model=4, execution_delay_ms=150, period="M1", timeout_seconds=21600,
           end_date="2026.11.11", periods={"6m": "2026.05.11", "1y": "2025.11.11", "3y": "2023.11.11", "5y": "2021.11.11"},
           split={"development": ["2021-11-11", "2023-11-11"], "validation": ["2023-11-11", "2024-11-11"], "oos": ["2024-11-11", "2026-11-11"]},
           expert_dir="AAA Research" + chr(92) + "CRT Alpha 20261111", source="EA/CRT Alpha Sweep Research EA.mq5", expert_file="CRT Alpha Sweep Research EA.ex5",
           symbols=["USTEC"], common_inputs=common, variants=variants, controls=controls)
(R / 'run-config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8'); print(len(variants), 'versions,', len(controls), 'controls / sensitivities')
