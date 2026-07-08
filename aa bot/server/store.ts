import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import type { ProductPlan } from "./types.js";
import { config } from "./config.js";

const file = resolve(process.cwd(), "data", "plans.json");

const defaultPlan = (productId: string): ProductPlan => ({
  productId,
  bias: "neutral",
  structure: "range",
  session: "Off-hours",
  sessionPhase: "normal",
  newsRisk: "clear",
  volumeCondition: "normal",
  marketPhase: "momentum",
  auctionPattern: "UNSET",
  entryModel: "AUTO",
  executionStage: "waiting",
  zones: [],
  accountSize: config.defaultAccountSize,
  riskPct: config.maxRiskPct,
  preferredDirection: "both"
});

const normalizePlan = (plan: ProductPlan): ProductPlan => ({
  ...defaultPlan(plan.productId),
  ...plan,
  zones: (plan.zones ?? []).map((zone) => {
    const legacy = zone as Partial<typeof zone>;
    return {
      ...zone,
      source: legacy.source ?? (zone.kind === "DEMAND" || zone.kind === "SUPPLY" ? "HTF_ZONE" : "LIVE"),
      taps: legacy.taps ?? (zone.fresh ? 0 : 2),
      tookOutOpposingZone: legacy.tookOutOpposingZone ?? false
    };
  })
});

export class PlanStore {
  private plans = new Map<string, ProductPlan>();

  async load(products: string[]) {
    try {
      const parsed = JSON.parse(await readFile(file, "utf8")) as ProductPlan[];
      for (const plan of parsed) this.plans.set(plan.productId, normalizePlan(plan));
    } catch { /* first run */ }
    for (const product of products) if (!this.plans.has(product)) this.plans.set(product, defaultPlan(product));
  }

  get(productId: string) {
    return this.plans.get(productId) ?? defaultPlan(productId);
  }

  async set(plan: ProductPlan) {
    const normalized = normalizePlan(plan);
    this.plans.set(plan.productId, normalized);
    await mkdir(dirname(file), { recursive: true });
    await writeFile(file, JSON.stringify([...this.plans.values()], null, 2), "utf8");
    return normalized;
  }
}
