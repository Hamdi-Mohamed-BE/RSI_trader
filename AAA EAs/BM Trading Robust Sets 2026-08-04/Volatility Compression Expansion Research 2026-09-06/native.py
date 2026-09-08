"""Compile and natively validate every frozen compression-expansion candidate."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
SOURCE = ROOT / "EA" / "Calyx Volatility Compression Expansion EA.mq5"
EXPERT_DIR = "Calyx Volatility Compression Expansion"
SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "US30", "USTEC", "GBPJPY")
TF = {"M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16388}
SESSION = {"all-day": 0, "asia": 1, "london": 2, "new-york": 3, "overlap": 4, "london-new-york": 5}
COMPRESSION = {"atr-ratio": 0, "bb-percentile": 1, "narrow-range": 2, "bb-keltner": 3}
CONFIRMATION = {"close": 0, "body": 1, "volume": 2, "body-volume": 3}
TREND = {"none": 0, "ema50": 1, "ema200": 2, "ema50-200": 3}
DIRECTION = {"both": 0, "long-only": 1, "short-only": 2}
STOP = {"range": 0, "atr": 1, "signal": 2, "swing5": 3}
MANAGEMENT = {"none": 0, "breakeven": 1, "atr-trail": 2, "dynamic-m15-50-20": 3}
spec = importlib.util.spec_from_file_location("report_parser", PACKAGE / "US100 Momentum Continuation Research 2026-08-31" / "Analyze-Reports.py")
parser = importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def compile_ea() -> None:
    log = SOURCE.with_suffix(".compile.log")
    subprocess.run(f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"', timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = log.read_text(encoding="utf-16") if log.exists() else ""
    if "0 errors, 0 warnings" not in text or not SOURCE.with_suffix(".ex5").exists():
        raise RuntimeError("EA compilation failed:\n" + text[-6000:])
    target = TESTER / "MQL5" / "Experts" / EXPERT_DIR; target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE.with_suffix(".ex5"), target / SOURCE.with_suffix(".ex5").name)
    (ROOT / "EA" / "compile.log").write_text(text, encoding="utf-8")
    print("COMPILE 0 errors, 0 warnings", flush=True)


def inputs(config: dict, symbol: str) -> dict:
    return dict(
        InpSignalTimeframe=TF[config["timeframe"]], InpSession=SESSION[config["session"]], InpCompression=COMPRESSION[config["compression"]],
        InpCompressionValue=config["compression_value"], InpRangeBars=config["range_bars"], InpArmBars=config["arm_bars"],
        InpBreakoutBufferATR=config["breakout_buffer_atr"], InpConfirmation=CONFIRMATION[config["confirmation"]],
        InpTrendFilter=TREND[config["trend"]], InpDirection=DIRECTION[config["direction"]], InpMaximumTradesPerDay=2,
        InpMaximumHoldBars=config["maximum_hold_bars"], InpStopMode=STOP[config["stop_mode"]], InpStopValue=config["stop_value"],
        InpRewardRisk=config["rr"], InpManagement=MANAGEMENT[config["management"]], InpRiskPercent=1.0,
        InpMaximumSpreadRiskPercent=20.0, InpMaximumDeviationPoints=100, InpMagic=969060600 + SYMBOLS.index(symbol),
        InpTesterOnly=True, InpTesterServerUTCOffsetHours=0, InpUseAutomaticLiveServerOffset=True, InpManualLiveServerUTCOffsetHours=0,
    )


def trade_audit(report: Path) -> list[dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(report.read_text(encoding="utf-16"), "html.parser"); inside = False; opened = None; trades = []
    for row in soup.find_all("tr"):
        if row.get_text(" ", strip=True) == "Deals": inside = True; continue
        if not inside: continue
        cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in row.find_all("td")]
        if len(cells) != 13 or cells[4] not in ("in", "out"): continue
        when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"); cash = sum(float(cells[index].replace(" ", "")) for index in (8, 9, 10)); balance = float(cells[11].replace(" ", ""))
        if cells[4] == "in":
            if opened is not None: raise RuntimeError("Overlapping native positions")
            opened = dict(entry_time=when.isoformat(), entry_price=float(cells[6].replace(" ", "")), side=cells[3], volume=float(cells[5]), cash=cash, before=balance-cash)
        else:
            if opened is None: raise RuntimeError("Unmatched native exit")
            net = opened.pop("cash") + cash; before = opened.pop("before")
            trades.append(dict(**opened, exit_time=when.isoformat(), exit_price=float(cells[6].replace(" ", "")), net=net, return_fraction=net/before)); opened = None
    return trades


def run(symbol: str, config: dict, stage: str, model: int, timeout=1200) -> dict:
    start, end = {"locked": ("2025.09.01", "2026.09.01"), "full": ("2023.09.01", "2026.09.01")}[stage]
    case = f"{symbol.lower()}-frozen-{stage}-model{model}"; params = inputs(config, symbol)
    fingerprint = hashlib.sha256((SOURCE.read_text(encoding="utf-8") + json.dumps(params, sort_keys=True) + start + end + str(model)).encode()).hexdigest()
    output = ROOT / "Native" / case; output.mkdir(parents=True, exist_ok=True); result_path = output / "result.json"
    if result_path.exists():
        old = json.loads(result_path.read_text(encoding="utf-8"))
        if old.get("fingerprint") == fingerprint: return old
    set_name = case + ".set"; sets = ROOT / "Sets"; sets.mkdir(exist_ok=True)
    set_text = "\n".join(f"{key}={str(value).lower() if isinstance(value, bool) else value}" for key, value in params.items()) + "\n"
    (sets / set_name).write_text(set_text, encoding="utf-8")
    tester_sets = TESTER / "MQL5" / "Profiles" / "Tester"; tester_sets.mkdir(parents=True, exist_ok=True); (tester_sets / set_name).write_text(set_text, encoding="utf-8")
    report_dir = TESTER / "reports" / "calyx-volatility-compression"; report_dir.mkdir(parents=True, exist_ok=True); report = report_dir / (case + ".htm")
    if report.exists(): report.rename(report.with_name(case + f".old-{time.time_ns()}.htm"))
    jobs = TESTER / "backtest-configs" / "calyx-volatility-compression"; jobs.mkdir(parents=True, exist_ok=True); ini = jobs / (case + ".ini")
    ini.write_text(f"""[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
[Tester]
Expert={EXPERT_DIR}\\Calyx Volatility Compression Expansion EA
ExpertParameters={set_name}
Symbol={symbol}
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=-1
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\calyx-volatility-compression\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
""", encoding="utf-8-sig")
    print("NATIVE START", case, flush=True); began = time.monotonic()
    try:
        subprocess.run(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired:
        dump(output / "unavailable.json", dict(case=case, status="bounded_timeout", seconds=timeout)); raise
    if not report.exists(): raise RuntimeError("MT5 produced no report for " + case)
    for path in report_dir.glob(case + "*"):
        if ".old-" not in path.name: shutil.copy2(path, output / path.name)
    row = parser.parse_report(output / report.name); trades = trade_audit(output / report.name)
    if len(trades) != row["trades"] or abs(sum(item["net"] for item in trades) - row["net_profit"]) > .06:
        raise RuntimeError(f"{case}: ledger mismatch")
    dump(output / "trades.json", trades)
    row.update(symbol=symbol, stage=stage, model=model, config=config, inputs=params, fingerprint=fingerprint, elapsed_seconds=round(time.monotonic()-began, 2), audit=dict(trades=len(trades)))
    dump(result_path, row); print("NATIVE DONE", case, {key: row[key] for key in ("return_pct", "profit_factor", "win_rate", "equity_dd_pct", "trades", "history_quality_pct", "elapsed_seconds")}, flush=True); return row


def main() -> None:
    compile_ea(); selections = json.loads((ROOT / "selection-lock.json").read_text(encoding="utf-8")); rows = []
    for symbol in SYMBOLS: rows.append(run(symbol, selections[symbol]["config"], "locked", 0))
    for symbol in SYMBOLS: rows.append(run(symbol, selections[symbol]["config"], "full", 0))
    dump(ROOT / "native-results.json", rows)
    import pandas as pd
    pd.DataFrame([{key: value for key, value in row.items() if key not in ("config", "inputs", "audit", "series")} | {"config": json.dumps(row["config"], sort_keys=True)} for row in rows]).to_csv(ROOT / "native-results.csv", index=False)


if __name__ == "__main__":
    main()
