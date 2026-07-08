import { describe, expect, it } from "vitest";
import { approximateProfile, runBacktest, type BacktestCandle, type BacktestInput } from "../server/core/backtest";

const baseInput: BacktestInput = {
  productId: "BTC-USD", granularity: 3600, bars: 100, direction: "both", quality: "A",
  model: "all",
  lookback: 20, targetR: 2, riskPct: 0.5, accountSize: 50_000, maxHoldBars: 12
};

describe("LTA backtest", () => {
  it("builds a bounded 70% profile approximation", () => {
    const candles: BacktestCandle[] = Array.from({ length: 30 }, (_, index) => ({
      time: index, open: 100, close: 100, high: 101, low: 99, volume: 10
    }));
    const profile = approximateProfile(candles);
    expect(profile.val).toBeGreaterThanOrEqual(99);
    expect(profile.vah).toBeLessThanOrEqual(101.1);
    expect(profile.poc).toBeGreaterThanOrEqual(profile.val);
    expect(profile.poc).toBeLessThanOrEqual(profile.vah);
  });

  it("returns auditable metrics and never reports more than a 1R stop loss", () => {
    const candles: BacktestCandle[] = Array.from({ length: 100 }, (_, index) => ({
      time: 1_700_000_000 + index * 3600,
      open: 100 + Math.sin(index / 4) * 0.3,
      close: 100 + Math.sin((index + 1) / 4) * 0.3,
      high: 100.7,
      low: 99.3,
      volume: 10
    }));
    candles[25] = { ...candles[25]!, open: 99.6, close: 100.7, high: 100.8, low: 98.5, volume: 30 };
    candles[26] = { ...candles[26]!, open: 100.7, close: 101.8, high: 102.5, low: 100.6, volume: 20 };
    const result = runBacktest(candles, baseInput);
    expect(result.data.bars).toBe(100);
    expect(result.metrics.startingBalance).toBe(50_000);
    expect(result.notes.length).toBeGreaterThan(0);
    expect(result.trades.every((trade) => trade.resultR >= -1)).toBe(true);
  });
});
