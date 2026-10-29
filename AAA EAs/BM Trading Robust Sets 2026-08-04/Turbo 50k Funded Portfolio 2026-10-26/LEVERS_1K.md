# Turbo 20 + guard (0.75%): levers toward $1k / month (generated from LEVERS_1K.json, levers_1k.py)

Each lever changed alone from the chosen profile, plus combinations. All-period, IN-SAMPLE: the guard was tuned on development, so this is not a new validation.
Income = 80% trader share unless stated; per month = total paid ÷ 36 (3-year MC) or ÷ 12 (history, weekday starts 2021-10 → 2025-10). Breach = all open stops hit.

| Lever | 3y MC mean / median per month | History 1y / month | Dev 1y / month | Validation 1y / month | Breach 3y MC / history ≤1y | Frozen 3y | Worst day MC | Max closed DD MC worst | Trades / month | / day |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chosen profile (80% share, 14-day rewards) | $581 / $556 | $775 | $208 | $1,013 | 0.0% / 0.0% | 0% | $-1,000 | $2,676 | 76.97 | 2.529 |
| 95% profit share | $690 / $660 | $920 | $247 | $1,203 | 0.0% / 0.0% | 0% | $-1,000 | $2,676 | 76.97 | 2.529 |
| 5-day rewards | $581 / $556 | $775 | $208 | $1,013 | 0.0% / 0.0% | 0% | $-1,000 | $2,676 | 76.97 | 2.529 |
| 5-day rewards + 95% share | $690 / $660 | $920 | $247 | $1,203 | 0.0% / 0.0% | 0% | $-1,000 | $2,676 | 76.97 | 2.529 |
| Taper 10% of room | $351 / $194 | $896 | $141 | $1,160 | 1.0% / 0.0% | 1% | $-1,244 | $3,071 | 54.95 | 1.805 |
| Taper 15% of room | $212 / $0 | $887 | $97 | $986 | 2.7% / 3.5% | 40% | $-1,370 | $3,196 | 47.87 | 1.573 |
| Taper 20% of room | $133 / $0 | $549 | $76 | $798 | 3.2% / 2.7% | 97% | $-1,455 | $3,238 | 54.12 | 1.778 |
| Taper 10% + profit cap 1.0% | $357 / $187 | $1,005 | $134 | $1,269 | 0.8% / 0.0% | 1% | $-1,244 | $3,064 | 69.13 | 2.271 |
| Taper 10% + profit cap 1.0% + 5-day + 95% | $424 / $222 | $1,194 | $159 | $1,507 | 0.8% / 0.0% | 1% | $-1,244 | $3,064 | 69.13 | 2.271 |
| No daily profit cap | $547 / $508 | $876 | $172 | $914 | 0.0% / 0.0% | 0% | $-1,002 | $2,835 | 87.06 | 2.86 |
| Floor does NOT trail (static $47k; firm-rule sensitivity) | $1,217 / $1,289 | $1,118 | $288 | $1,537 | 0.0% / 0.0% | 0% | $-1,455 | $20,311 | 57.04 | 1.874 |
| Static floor + 5-day + 95% | $1,445 / $1,530 | $1,327 | $342 | $1,825 | 0.0% / 0.0% | 0% | $-1,455 | $20,311 | 57.04 | 1.874 |

- **5-day rewards change nothing:** the 20% consistency rule (cycle profit ≥ 5 × the best day) and the 3 profitable days decide when a reward is possible, and that takes more than 14 days.
- **Static floor closed DD:** the worst closed DD under a static floor ($20k) comes from balances that grew while no reward was allowed (consistency rule), then fell back.
- **Two accounts:** a second $50k account (or one $100k account with the same % limits) doubles the dollars, about $1,160 / month at 80%. Not simulated separately. The two accounts carry identical trades, so the same bad days hit both. Check the firm's rules on multiple accounts and copy trading.
