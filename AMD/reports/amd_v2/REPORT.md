# AMD v2 Robustness Report

Decision: **REJECTED**

The model was selected using only 2024-07-30 through 2026-07-30. Its parameters were frozen before the 2023-07-30 through 2024-07-30 holdout was evaluated.

| Sample | Trades | Win rate | PF | Net R | Return | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| Development | 35 | 45.71% | 1.70 | +13.28 | +43.82% | 11.94% |
| Holdout | 9 | 44.44% | 1.54 | +3.00 | +8.41% | 8.73% |
| Full three years | 44 | 45.45% | 1.67 | +16.28 | +55.92% | 11.94% |

## Frozen model

```json
{
  "name": "rev_mss2_disp1.0_gap0.0_retest6__broad_none_2r",
  "params": {
    "enable_reversal": true,
    "enable_continuation": false,
    "trade_london": true,
    "trade_new_york": false,
    "max_trades_per_day": 1,
    "reversal_rr": 2.0,
    "continuation_rr": 2.0,
    "sweep_min_fraction": 0.02,
    "sweep_max_fraction": 0.6,
    "mss_lookback_bars": 2,
    "displacement_lookahead_bars": 8,
    "displacement_range_factor": 1.0,
    "displacement_body_fraction": 0.5,
    "displacement_close_location": 0.65,
    "fvg_min_fraction": 0.0,
    "fvg_entry_fraction": 0.5,
    "fvg_retest_bars": 6,
    "breakout_min_fraction": 0.04,
    "breakout_max_fraction": 0.6,
    "breakout_retest_tolerance_fraction": 0.04,
    "breakout_retest_bars": 12,
    "breakout_hold_fraction": 0.01,
    "continuation_require_fvg": true,
    "stop_buffer_fraction": 0.03,
    "max_risk_fraction": 0.9,
    "volume_factor": 0.0,
    "require_vwap_alignment": false,
    "use_regime_filter": true,
    "london_window_minutes": 240,
    "ny_window_minutes": 180,
    "management_mode": "none",
    "protect_trigger_r": 99.0,
    "protect_profit_r": 0.0,
    "partial_fraction": 0.0,
    "trail_start_r": 99.0,
    "trail_distance_r": 1.0
  },
  "atr_min": 0.5,
  "atr_max": 1.6,
  "asia_min": 0.4,
  "asia_max": 1.2
}
```
