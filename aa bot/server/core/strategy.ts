import type {
  EntryModel, LtaZone, MicrostructureSignal, ProductPlan, RankedSetup, VolumeProfile
} from "../types.js";

type Direction = "long" | "short";
type Model = Exclude<EntryModel, "AUTO">;

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const stageRank = { waiting: 0, touched: 1, flipped: 2, confirmed: 3 } as const;

const distanceBps = (price: number, zone: LtaZone) => {
  if (price >= zone.low && price <= zone.high) return 0;
  const edge = price < zone.low ? zone.low : zone.high;
  return Math.abs(price - edge) / price * 10_000;
};

function zoneDirection(zone: LtaZone, plan: ProductPlan): Direction | null {
  if (["VAL", "DEMAND", "LIQUIDITY_LOW"].includes(zone.kind)) return "long";
  if (["VAH", "SUPPLY", "LIQUIDITY_HIGH"].includes(zone.kind)) return "short";
  if (zone.kind !== "POC" || plan.structure === "range") return null;
  if (plan.structure === "reclaim" || plan.structure === "breakout") return "long";
  if (plan.structure === "rejection" || plan.structure === "breakdown") return "short";
  return plan.bias === "bullish" ? "long" : plan.bias === "bearish" ? "short" : null;
}

function inferModel(plan: ProductPlan, zone: LtaZone): Model | null {
  if (plan.entryModel !== "AUTO") return plan.entryModel;
  if (plan.auctionPattern === "CERC" && plan.marketPhase === "momentum") return "EM4";
  if (plan.auctionPattern === "CME" && ["breakout", "breakdown"].includes(plan.structure)) return "EM3";
  if (["SWING", "LTF_SWING"].includes(zone.source)) return "EM2";
  if (stageRank[plan.executionStage] >= stageRank.flipped) return "EM1";
  return null;
}

function modelCheck(model: Model | null, plan: ProductPlan, zone: LtaZone, structureAligned: boolean) {
  if (!model) return { passed: false, detail: "No EM confirmation selected or detected" };
  if (model === "EM1") return {
    passed: stageRank[plan.executionStage] >= stageRank.flipped,
    detail: "Double-wick flip at the key level"
  };
  if (model === "EM2") return {
    passed: ["SWING", "LTF_SWING"].includes(zone.source) && plan.executionStage === "confirmed",
    detail: "Internal swing profile plus EM1 and structure confirmation"
  };
  if (model === "EM3") return {
    passed: structureAligned && plan.executionStage === "confirmed",
    detail: plan.auctionPattern === "CME" ? "CME manipulation followed by internal structure break" : "Internal structure break after mitigation"
  };
  return {
    passed: plan.auctionPattern === "CERC" && plan.marketPhase === "momentum" && stageRank[plan.executionStage] >= stageRank.flipped,
    detail: "CERC continuation after trap/flip and controlled retest"
  };
}

function orderFlowCheck(direction: Direction, model: Model | null, micro: MicrostructureSignal) {
  const sign = direction === "long" ? 1 : -1;
  const absorption = micro.absorption === direction;
  const continuation = micro.delta30s * sign > 0
    && micro.imbalance * sign > 0.1
    && (direction === "long" ? micro.stackedBidLevels >= 1 : micro.stackedAskLevels >= 1);
  const composite = micro.score * sign >= 35;
  const passed = !micro.spoofWarning && (model === "EM4" ? continuation || composite : absorption || continuation || composite);
  const detail = micro.spoofWarning
    ? `Spoof/pull warning on ${micro.spoofSide ?? "unknown"} liquidity`
    : absorption ? `${direction === "long" ? "Sell" : "Buy"} aggression absorbed with passive refresh`
      : continuation ? `Aggressive ${direction === "long" ? "buying" : "selling"}, imbalance and stacked liquidity align`
        : composite ? `Order-book composite confirms ${direction}`
          : "Waiting for absorption or aligned delta, imbalance and stacked liquidity";
  return { passed, detail };
}

function realTargets(direction: Direction, entry: number, risk: number, plan: ProductPlan, profile: VolumeProfile) {
  const sign = direction === "long" ? 1 : -1;
  const candidates: Array<{ price: number; label: string }> = [];
  const opposingKinds = direction === "long"
    ? ["POC", "VAH", "SUPPLY", "LIQUIDITY_HIGH"]
    : ["POC", "VAL", "DEMAND", "LIQUIDITY_LOW"];

  for (const zone of plan.zones) {
    if (!opposingKinds.includes(zone.kind)) continue;
    const price = direction === "long" ? zone.low : zone.high;
    if (sign > 0 ? price > entry : price < entry) candidates.push({ price, label: `${zone.source} ${zone.timeframe} ${zone.kind}` });
  }
  const live = direction === "long"
    ? [[profile.poc, "Live POC"], [profile.vah, "Live VAH"]] as const
    : [[profile.poc, "Live POC"], [profile.val, "Live VAL"]] as const;
  for (const [price, label] of live) if (price !== null && (sign > 0 ? price > entry : price < entry)) candidates.push({ price, label });

  const unique = new Map<number, string>();
  for (const item of candidates) if (!unique.has(item.price)) unique.set(item.price, item.label);
  return [...unique].map(([price, label]) => ({ price, label, rr: Math.abs(price - entry) / risk }))
    .sort((a, b) => sign > 0 ? a.price - b.price : b.price - a.price).slice(0, 3);
}

function empty(plan: ProductPlan, reasons: string[], gates: RankedSetup["gates"] = []): RankedSetup {
  const visibleGates = gates.length ? gates : [
    { name: "LTA location", passed: false, detail: "Add a qualified zone/profile level" },
    { name: "Macro bias", passed: plan.bias !== "neutral", detail: plan.bias },
    { name: "Qualified level", passed: false, detail: "PD, EPD, PW, fixed, swing or HTF zone required" },
    { name: "Intraday structure", passed: plan.structure !== "range", detail: plan.structure },
    { name: "Entry model", passed: false, detail: "Waiting for EM1–EM4" },
    { name: "Order-book proof", passed: false, detail: "Checked only after location" },
    { name: "Timing/news", passed: plan.newsRisk !== "red" && plan.sessionPhase !== "pre-open", detail: `${plan.sessionPhase} · news ${plan.newsRisk}` },
    { name: "Real target ≥ 2R", passed: false, detail: "Add the next opposing LTA level" }
  ];
  return {
    direction: "none", grade: "NO TRADE", score: 0, status: "NO TRADE", pattern: "Wait for LTA alignment",
    entryModel: null, marketPhase: plan.marketPhase, zone: null, entry: null, stop: null, targets: [], rr: null,
    gates: visibleGates, targetDetails: [], management: ["No order until every execution gate is explicit"], reasons,
    cancelConditions: ["No trade away from an LTA level", "Order flow cannot create a setup by itself"]
  };
}

export function rankSetup(
  price: number | null,
  plan: ProductPlan,
  micro: MicrostructureSignal,
  profile: VolumeProfile
): RankedSetup {
  if (!price) return empty(plan, ["Waiting for live price"]);
  if (!plan.zones.length) return empty(plan, ["Add HTF supply/demand and PD, EPD, PW, fixed or swing profile levels"]);

  const directional = plan.zones.map((zone) => ({ zone, direction: zoneDirection(zone, plan) }))
    .filter((item): item is { zone: LtaZone; direction: Direction } => item.direction !== null)
    .filter((item) => plan.preferredDirection === "both" || plan.preferredDirection === item.direction)
    .sort((a, b) => distanceBps(price, a.zone) - distanceBps(price, b.zone));
  if (!directional.length) return empty(plan, ["No zone agrees with the planned direction", "POC needs a reclaim or rejection, not range conditions"]);

  const { zone, direction } = directional[0]!;
  const distance = distanceBps(price, zone);
  const location = distance <= 20;
  const biasAligned = (direction === "long" && plan.bias === "bullish") || (direction === "short" && plan.bias === "bearish");
  const structureAligned = direction === "long"
    ? ["reclaim", "breakout"].includes(plan.structure)
    : ["rejection", "breakdown"].includes(plan.structure);
  const model = inferModel(plan, zone);
  const modelGate = modelCheck(model, plan, zone, structureAligned);
  const mbo = orderFlowCheck(direction, model, micro);
  const completedReference = zone.source !== "LIVE" || plan.sessionPhase === "late";
  const repeatProtected = zone.taps <= 1 || zone.tookOutOpposingZone || ["EM2", "EM3"].includes(model ?? "");
  const zoneQualified = completedReference && repeatProtected;
  const safeTiming = plan.newsRisk !== "red" && plan.sessionPhase !== "pre-open";
  const width = Math.max(zone.high - zone.low, price * 0.0005);
  const plannedEntry = direction === "long" ? zone.high : zone.low;
  const entry = plan.executionStage === "confirmed" && location ? price : plannedEntry;
  const stop = direction === "long" ? zone.low - width * 0.25 : zone.high + width * 0.25;
  const risk = Math.abs(entry - stop);
  const validRisk = risk > 0 && (direction === "long" ? stop < entry : stop > entry);
  const targetDetails = validRisk ? realTargets(direction, entry, risk, plan, profile) : [];
  const nearestTarget = targetDetails[0];
  const rewardPassed = Boolean(nearestTarget && nearestTarget.rr >= 2);

  const gates: RankedSetup["gates"] = [
    { name: "LTA location", passed: location, detail: location ? `At ${zone.source} ${zone.timeframe} ${zone.kind}` : `${distance.toFixed(1)} bps from ${zone.kind}` },
    { name: "Macro bias", passed: biasAligned, detail: `${plan.bias} bias vs ${direction} idea` },
    { name: "Qualified level", passed: zoneQualified, detail: `${completedReference ? "Completed" : "Developing current"} reference · ${zone.taps} tap(s)${zone.tookOutOpposingZone ? " · control zone" : ""}` },
    { name: "Intraday structure", passed: structureAligned, detail: plan.structure },
    { name: "Entry model", passed: modelGate.passed, detail: model ? `${model} · ${modelGate.detail}` : modelGate.detail },
    { name: "Order-book proof", passed: mbo.passed, detail: mbo.detail },
    { name: "Timing/news", passed: safeTiming, detail: `${plan.session} · ${plan.sessionPhase} · news ${plan.newsRisk}` },
    { name: "Real target ≥ 2R", passed: rewardPassed, detail: nearestTarget ? `${nearestTarget.label} at ${nearestTarget.rr.toFixed(2)}R` : "Add the next opposing LTA level" }
  ];

  let score = 0;
  const weights = [18, 12, 12, 14, 16, 16, 5, 7];
  gates.forEach((gate, index) => { if (gate.passed) score += weights[index] ?? 0; });
  if (zone.fresh && zone.taps === 0) score += 3;
  if (zone.tookOutOpposingZone) score += 3;
  if (plan.volumeCondition === "high" && plan.marketPhase === "momentum") score += 2;
  if (plan.volumeCondition === "low" && plan.executionStage !== "confirmed") score -= 8;
  if (micro.spreadBps > 5) score -= 8;
  score = clamp(Math.round(score), 0, 100);

  const critical = location && biasAligned && zoneQualified && structureAligned && modelGate.passed && safeTiming && rewardPassed && validRisk;
  const allPassed = critical && mbo.passed;
  const grade: RankedSetup["grade"] = allPassed && score >= 90 ? "A+" : critical && score >= 72 ? "A" : location && score >= 50 ? "B" : "NO TRADE";
  const status: RankedSetup["status"] = allPassed && grade === "A+" ? "TRIGGERED"
    : critical && (grade === "A" || grade === "A+") ? "ARMED"
      : grade === "B" ? "PRE-IDEA" : "NO TRADE";

  const modelNames: Record<Model, string> = {
    EM1: "Double Wick at key level",
    EM2: "Internal Swing profile confirmation",
    EM3: "Internal Structure / CME confirmation",
    EM4: "CERC continuation after liquidity trap"
  };
  const reasons = gates.filter((gate) => gate.passed).map((gate) => `${gate.name}: ${gate.detail}`);
  const missing = gates.filter((gate) => !gate.passed).map((gate) => `${gate.name} missing: ${gate.detail}`);
  const management = plan.marketPhase === "contrarian"
    ? ["Book rule: risk no more than 1% in contrarian conditions", "Move stop to breakeven at 1R while the macro trend has not shifted"]
    : ["Book rule: momentum risk may reach 2% only after proven consistency", "Allow the structure room; do not force breakeven mechanically at 1R"];

  return {
    direction,
    grade,
    score,
    status,
    pattern: model ? `${model} · ${modelNames[model]}` : "Waiting for named entry model",
    entryModel: model,
    marketPhase: plan.marketPhase,
    zone,
    entry,
    stop,
    targets: targetDetails.map((target) => target.price),
    rr: nearestTarget?.rr ?? null,
    gates,
    targetDetails,
    management,
    reasons: [...reasons, ...missing],
    cancelConditions: direction === "long"
      ? [`Execution timeframe accepts below ${zone.low}`, "Bid absorption/continuation disappears", "Red news or pre-open conditions", "Nearest opposing level falls below 2R"]
      : [`Execution timeframe accepts above ${zone.high}`, "Ask absorption/continuation disappears", "Red news or pre-open conditions", "Nearest opposing level falls below 2R"]
  };
}
