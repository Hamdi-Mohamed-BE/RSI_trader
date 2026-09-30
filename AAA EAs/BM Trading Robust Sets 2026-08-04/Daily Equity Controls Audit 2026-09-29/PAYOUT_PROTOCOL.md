# FTMO 2-Step Swing reward follow-up — frozen before results

Research only. No broker orders, EA deployment, account configuration or running services will be changed.

Compare the exact current 13-EA source basket at fixed maximum $50 initial-stop risk per entry on $10,000. Test all seven previously specified policies without selecting a new EA subset. These policies replace, rather than stack with, the BAT package's original governors.

Use each Monday from 29 September 2025 with at least 30 days of remaining data. Report only starts with full observation for each 30/60/90/120/180-day horizon; use the same 180-day-complete cohort for conditional timing comparisons. Overlapping starts are scenarios, not independent trials or estimated future probabilities. Data end 25 September 2026 UTC; source signal history is not an untouched holdout.

Reference costs and the previous audit's adverse execution/carry costs are retained. Add a clearly hypothetical deterioration case: the adverse costs plus 10% less positive gross trade/marked P&L and 10% larger negative gross P&L. Separately test five-minute forced-liquidation delay. This is sensitivity analysis, not a calibrated probability distribution.

Lifecycle: +$1,000 flat phase 1, +$500 flat phase 2, four distinct Prague opening-trade days in each. Pause new entries once closed balance qualifies and minimum days are met, letting existing positions finish. Do not invent a liquidation at the phase profit target. Assume two weekdays after phase 1 and five weekdays after phase 2 before the next account is ready, at the same local clock time. Holidays and user KYC delays are not modeled.

Funded: earliest request after 14 full calendar days from the first funded entry in each cycle, flat, at least $50 closed profit (chosen to satisfy the currently published crypto minimum as well as the bank-wire minimum). Pause new entries when the balance and age qualify and wait until flat. Withdraw all gross profit; 80% is the trader's modeled reward, 20% is the firm's share; the next cycle restarts at $10,000 after a two-weekday processing pause. No compounding. No fee refund, purchase fee, tax, transfer fee or FX conversion is included. Request amounts are not cash already received or guaranteed approved. Actual payment review/dispatch is separate.

FTMO breaches absorb the path: $9,000 static total floor, and midnight Prague balance minus $500 daily floor, including floating P&L and costs. Record adverse M1-bar envelope flags separately because per-symbol extremes need not occur simultaneously. Minute sampling cannot prove tick-level compliance.

Retain the earlier source-overlay limitations: signals are not regenerated after skips/early closes; Exness price paths are translated using public FTMO contract, cost and leverage assumptions, not native FTMO tick tests; swap timing is approximated from native total trade swap. Do not infer that every source EA is currently attached on the user's terminal.
