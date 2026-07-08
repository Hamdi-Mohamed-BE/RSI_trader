export interface RiskInput {
  accountSize: number;
  riskPct: number;
  entry: number;
  stop: number;
  target?: number;
}

export interface RiskResult {
  direction: "long" | "short";
  riskAmount: number;
  riskPerUnit: number;
  quantity: number;
  notional: number;
  rr: number | null;
  oneRPrice: number;
  twoRPrice: number;
  threeRPrice: number;
}

export function calculateRisk(input: RiskInput): RiskResult {
  if (input.accountSize <= 0 || input.riskPct <= 0 || input.entry <= 0 || input.stop <= 0 || input.entry === input.stop) {
    throw new Error("Account, risk, entry and stop must be valid positive values");
  }
  const direction = input.entry > input.stop ? "long" : "short";
  const riskAmount = input.accountSize * input.riskPct / 100;
  const riskPerUnit = Math.abs(input.entry - input.stop);
  const quantity = riskAmount / riskPerUnit;
  const sign = direction === "long" ? 1 : -1;
  const reward = input.target ? Math.abs(input.target - input.entry) : null;
  return {
    direction,
    riskAmount,
    riskPerUnit,
    quantity,
    notional: quantity * input.entry,
    rr: reward === null ? null : reward / riskPerUnit,
    oneRPrice: input.entry + sign * riskPerUnit,
    twoRPrice: input.entry + sign * riskPerUnit * 2,
    threeRPrice: input.entry + sign * riskPerUnit * 3
  };
}
