# Calyx Research Pipeline

This folder adds a common evidence audit and an optional point-in-time macro-data connector to the existing MT5 research flow. It does not change, install or promote any EA by itself.

## What changed

- Win rate now includes a 95% Wilson confidence interval.
- Profit factor, return and drawdown receive a 10,000-path block-bootstrap distribution.
- The audit reports 95% daily Expected Shortfall, recent-half PF and three chronological subperiods.
- Sharpe is corrected for the number of configurations tried with a Deflated Sharpe probability. Every tested configuration must be counted, including rejected experiments.
- Prop-firm daily and total loss probabilities are estimated from closed P&L. This is only a proxy; native MT5 equity-path evidence remains mandatory because open-position drawdown is absent from summary reports.
- Broker cost stress is a required promotion gate. Pass `--extra-cost-per-trade` using measured spread/slippage evidence; the tool will not invent a cost.
- FXMacroData is optional. It records fetch time, source URL and response SHA-256, and only permits `announcement_datetime` for point-in-time joins.
- News Pulse tester calendars can now be generated from exact FXMacroData UTC release epochs. The EA requires the tester's requested start/end dates and rejects any window outside the generated manifest instead of silently running a partial calendar.

## Run an enhanced audit

```powershell
python .\calyx_pipeline.py `
  --report "C:\path\to\locked-report.htm" `
  --label "EA name — locked" `
  --output "C:\path\to\Enhanced Audit" `
  --tested-configurations 120 `
  --extra-cost-per-trade 1.50
```

`--tested-configurations` is not optional in practice: use the total number of parameter/settings combinations inspected before the frozen result. The default of 1 is only valid for a genuinely unoptimized raw replication.

## FXMacroData

Codex is configured to use the public streamable-HTTP MCP endpoint:

```text
https://mcp.fxmacrodata.com
```

The public tier supports USD discovery/recent data. Set the private environment variable `FXMD_API_KEY` only if a paid key is obtained; never place a real key in this repository.

Useful checks:

```powershell
python .\fxmacrodata.py health

python .\fxmacrodata.py calendar `
  --currency USD --start 2026-09-10 --end 2026-10-10 `
  --high-impact-only --output .\Snapshots\usd-high-impact-calendar.json

python .\fxmacrodata.py audit-coverage `
  --currency USD --start 2023-09-01 --end 2026-09-01 `
  --indicators inflation,employment,non_farm_payrolls,policy_rate `
  --output .\Snapshots\usd-3y-coverage-audit.json
```

The free tier is deliberately rejected for multi-year macro backtests because anonymous USD history is limited to the recent window. Macro filters must never be optimized on revised values that were not available at the original decision time.

### Generate a News Pulse tester calendar

```powershell
python .\news_pulse_calendar.py `
  --start 2026-06-12 --end 2026-09-10 `
  --include "C:\path\to\AAA Final News Pulse EA\NewsPulseTesterCalendar.mqh" `
  --manifest "C:\path\to\evidence\generated-calendar-manifest.json" `
  --raw "C:\path\to\evidence\generated-calendar-mcp-raw.json"
```

The corresponding tester set must contain matching `InpTesterFromDateUTC` and `InpTesterToDateUTC` values in `YYYYMMDD` form. The research runner writes these automatically and asserts that the EA's `OnTester` event count equals the manifest count. Missing inputs, an uncovered date range, inconsistent generated arrays, a runtime boundary escape, or a skipped release makes the test fail closed.

Live trading is deliberately unchanged: News Pulse continues to use MT5's built-in broker-server economic calendar and a fresh broker-stamped quote. FXMacroData is used for tester reproducibility, not as the live execution clock.

## Promotion rule

An EA reaches `PASS_FOR_FORWARD_TEST` only when the frozen report clears every statistical, stability, bootstrap, prop-risk and supplied cost-stress gate. This means “eligible for isolated demo forward testing,” not “install in the recommended portfolio.” Portfolio/website/BAT changes still require the existing full pipeline and explicit user approval.

## Sources behind the additions

The statistical additions implement the practical parts of the Quant Developers Resources material: econometrics, Monte Carlo, portfolio/risk management and overfitting control. FXMacroData is used as an official-source, point-in-time macro layer, not as a signal generator by default.

- Quant Developers Resources: https://github.com/cybergeekgyan/Quant-Developers-Resources
- FXMacroData MCP documentation: https://fxmacrodata.com/documentation/mcp-server
- Codex MCP documentation: https://developers.openai.com/codex/mcp
