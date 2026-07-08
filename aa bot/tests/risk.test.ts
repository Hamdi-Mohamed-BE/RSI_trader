import { describe, expect, it } from "vitest";
import { calculateRisk } from "../server/core/risk";

describe("calculateRisk", () => {
  it("sizes a spot position from fixed account risk", () => {
    const result = calculateRisk({ accountSize: 50_000, riskPct: 0.5, entry: 60_000, stop: 59_500, target: 61_500 });
    expect(result.riskAmount).toBe(250);
    expect(result.quantity).toBe(0.5);
    expect(result.rr).toBe(3);
    expect(result.oneRPrice).toBe(60_500);
  });

  it("calculates short R levels in the correct direction", () => {
    const result = calculateRisk({ accountSize: 10_000, riskPct: 1, entry: 100, stop: 105 });
    expect(result.oneRPrice).toBe(95);
    expect(result.threeRPrice).toBe(85);
  });
});
