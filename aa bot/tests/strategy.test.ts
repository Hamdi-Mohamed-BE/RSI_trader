import { describe, expect, it } from "vitest";
import { rankSetup } from "../server/core/strategy";
import type { MicrostructureSignal, ProductPlan, VolumeProfile } from "../server/types";

const micro: MicrostructureSignal = {
  timestamp: Date.now(), score: 62, imbalance: 0.4, delta5s: -2, delta30s: -10,
  bidRefreshes: 4, askRefreshes: 0, absorption: "long", spoofWarning: false, spoofSide: null,
  stackedBidLevels: 3, stackedAskLevels: 0, spreadBps: 0.5, reasons: []
};
const profile: VolumeProfile = { poc: 60_500, vah: 61_000, val: 59_900, totalVolume: 100, buckets: [], startedAt: Date.now() };
const basePlan = (overrides: Partial<ProductPlan> = {}): ProductPlan => ({
  productId: "BTC-USD", bias: "bullish", structure: "reclaim", session: "New York", sessionPhase: "normal",
  newsRisk: "clear", volumeCondition: "normal", marketPhase: "momentum", auctionPattern: "UNSET",
  entryModel: "EM1", executionStage: "confirmed", zones: [], accountSize: 50_000, riskPct: 0.5,
  preferredDirection: "both", ...overrides
});

describe("book-aligned LTA setup engine", () => {
  it("requires LTA location before order-book confirmation", () => {
    expect(rankSetup(60_000, basePlan(), micro, profile).grade).toBe("NO TRADE");
  });

  it("ranks aligned EM1 demand, structure, order flow and a real target as A+", () => {
    const plan = basePlan({
      preferredDirection: "long",
      zones: [
        { id: "d1", kind: "DEMAND", low: 59_900, high: 60_100, timeframe: "H1", fresh: true, source: "HTF_ZONE", taps: 0, tookOutOpposingZone: true },
        { id: "s1", kind: "SUPPLY", low: 61_000, high: 61_200, timeframe: "H4", fresh: true, source: "HTF_ZONE", taps: 0, tookOutOpposingZone: false }
      ]
    });
    const result = rankSetup(60_000, plan, micro, profile);
    expect(result.grade).toBe("A+");
    expect(result.status).toBe("TRIGGERED");
    expect(result.entryModel).toBe("EM1");
    expect(result.targetDetails.some((target) => target.label.includes("SUPPLY"))).toBe(true);
    expect(result.rr).toBeGreaterThanOrEqual(2);
  });

  it("blocks a repeated level without EM2/EM3 reinforcement", () => {
    const plan = basePlan({ zones: [
      { id: "d1", kind: "DEMAND", low: 59_900, high: 60_100, timeframe: "H1", fresh: false, source: "HTF_ZONE", taps: 3, tookOutOpposingZone: false },
      { id: "s1", kind: "SUPPLY", low: 61_000, high: 61_200, timeframe: "H4", fresh: true, source: "HTF_ZONE", taps: 0, tookOutOpposingZone: false }
    ] });
    const result = rankSetup(60_000, plan, micro, profile);
    expect(result.gates.find((gate) => gate.name === "Qualified level")?.passed).toBe(false);
    expect(result.grade).not.toBe("A+");
  });

  it("red news prevents a trigger", () => {
    const plan = basePlan({ newsRisk: "red", zones: [
      { id: "d1", kind: "DEMAND", low: 59_900, high: 60_100, timeframe: "H1", fresh: true, source: "HTF_ZONE", taps: 0, tookOutOpposingZone: true },
      { id: "s1", kind: "SUPPLY", low: 61_000, high: 61_200, timeframe: "H4", fresh: true, source: "HTF_ZONE", taps: 0, tookOutOpposingZone: false }
    ] });
    expect(rankSetup(60_000, plan, micro, profile).status).not.toBe("TRIGGERED");
  });
});
