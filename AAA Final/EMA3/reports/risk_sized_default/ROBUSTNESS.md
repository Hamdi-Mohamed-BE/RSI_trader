# EMA3 Robustness Check

Configuration: XAUUSD H4, pivot 5, EMA200 six-bar slope filter, one leg,
structural pivot stop, trailing activated at +1R with a 1R distance.

## Consecutive quarters at 1% risk

| Quarter | Trades | Win rate | PF | Net R | Max DD |
|---|---:|---:|---:|---:|---:|
| Q1 | 11 | 54.55% | 3.90 | +12.79R | 2.39% |
| Q2 | 7 | 57.14% | 5.00 | +11.99R | 1.00% |
| Q3 | 7 | 57.14% | 2.81 | +5.42R | 2.97% |
| Q4 unseen | 14 | 64.29% | 2.09 | +5.44R | 2.97% |

The quarter totals differ slightly from one continuous annual run because each
quarter closes any open position at its own boundary. The untouched final
quarter remained profitable, but its 14 trades are not enough to establish
future certainty. Forward-test on demo before relying on it live.
