export interface BacktestCandle {
  time: number;
  low: number;
  high: number;
  open: number;
  close: number;
  volume: number;
}

export interface BacktestInput {
  productId: string;
  granularity: number;
  bars: number;
  direction: "long" | "short" | "both";
  model: "all" | "EM1" | "EM2" | "EM3" | "EM4";
  quality: "A" | "A+";
  lookback: number;
  targetR: number;
  riskPct: number;
  accountSize: number;
  maxHoldBars: number;
}

export interface BacktestTrade {
  id: number;
  direction: "long" | "short";
  grade: "A" | "A+";
  model: "EM1" | "EM2" | "EM3" | "EM4";
  signalTime: number;
  entryTime: number;
  exitTime: number;
  entry: number;
  stop: number;
  target: number;
  exit: number;
  resultR: number;
  pnl: number;
  exitReason: "target" | "stop" | "timeout" | "data-end";
  holdBars: number;
  profile: { poc: number; vah: number; val: number };
}

type DetectedSignal = { direction: "long" | "short"; model: BacktestTrade["model"] };

export interface BacktestResult {
  input: BacktestInput;
  data: { from: number; to: number; bars: number };
  metrics: {
    trades: number; wins: number; losses: number; winRate: number; netR: number; expectancyR: number;
    profitFactor: number | null; maxDrawdownR: number; maxConsecutiveLosses: number; averageHoldBars: number;
    startingBalance: number; endingBalance: number; returnPct: number;
  };
  equity: Array<{ time: number; balance: number; cumulativeR: number }>;
  trades: BacktestTrade[];
  notes: string[];
}

const average = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

function atr(candles: BacktestCandle[], end: number, period = 14) {
  const values: number[] = [];
  for (let i = Math.max(1, end - period + 1); i <= end; i++) {
    const candle = candles[i]!;
    const previous = candles[i - 1]!;
    values.push(Math.max(candle.high - candle.low, Math.abs(candle.high - previous.close), Math.abs(candle.low - previous.close)));
  }
  return average(values);
}

export function approximateProfile(candles: BacktestCandle[]) {
  const low = Math.min(...candles.map((candle) => candle.low));
  const high = Math.max(...candles.map((candle) => candle.high));
  const step = Math.max((high - low) / 48, high * 0.00005);
  const buckets = Array.from({ length: 49 }, (_, index) => ({ price: low + index * step, volume: 0 }));
  for (const candle of candles) {
    const first = Math.max(0, Math.floor((candle.low - low) / step));
    const last = Math.min(buckets.length - 1, Math.ceil((candle.high - low) / step));
    const count = Math.max(1, last - first + 1);
    for (let index = first; index <= last; index++) buckets[index]!.volume += candle.volume / count;
  }
  const total = buckets.reduce((sum, bucket) => sum + bucket.volume, 0);
  const pocIndex = buckets.reduce((best, bucket, index) => bucket.volume > buckets[best]!.volume ? index : best, 0);
  let left = pocIndex;
  let right = pocIndex;
  let included = buckets[pocIndex]!.volume;
  while (included < total * 0.7 && (left > 0 || right < buckets.length - 1)) {
    const below = left > 0 ? buckets[left - 1]!.volume : -1;
    const above = right < buckets.length - 1 ? buckets[right + 1]!.volume : -1;
    if (above >= below) included += buckets[++right]!.volume;
    else included += buckets[--left]!.volume;
  }
  return { poc: buckets[pocIndex]!.price, vah: buckets[right]!.price, val: buckets[left]!.price };
}

function detectSignal(candles: BacktestCandle[], index: number, profile: { poc: number; vah: number; val: number }, requested: BacktestInput["model"]): DetectedSignal | null {
  const first = candles[index - 2];
  const second = candles[index - 1];
  const current = candles[index];
  if (!first || !second || !current) return null;
  const choose = (model: BacktestTrade["model"], long: boolean, short: boolean): DetectedSignal | null => {
    if (requested !== "all" && requested !== model) return null;
    return long ? { direction: "long", model } : short ? { direction: "short", model } : null;
  };

  const em4 = choose("EM4",
    first.low <= profile.val && first.close > profile.val && second.close > second.open && current.close > Math.max(first.high, second.high),
    first.high >= profile.vah && first.close < profile.vah && second.close < second.open && current.close < Math.min(first.low, second.low));
  if (em4) return em4;

  const recent = candles.slice(Math.max(0, index - 7), index);
  const structureBars = recent.slice(0, -1);
  const internalHigh = Math.max(...structureBars.map((bar) => bar.high));
  const internalLow = Math.min(...structureBars.map((bar) => bar.low));
  const touchedDemand = recent.some((bar) => bar.low <= profile.val);
  const touchedSupply = recent.some((bar) => bar.high >= profile.vah);
  const em3 = choose("EM3", touchedDemand && current.close > internalHigh, touchedSupply && current.close < internalLow);
  if (em3) return em3;

  const internal = approximateProfile(candles.slice(Math.max(0, index - 12), index));
  const em2 = choose("EM2",
    touchedDemand && second.low <= internal.val && second.close > internal.val && current.close > second.high,
    touchedSupply && second.high >= internal.vah && second.close < internal.vah && current.close < second.low);
  if (em2) return em2;

  return choose("EM1",
    second.low <= profile.val && second.close > profile.val && current.low <= second.close && current.close > second.high,
    second.high >= profile.vah && second.close < profile.vah && current.high >= second.close && current.close < second.low);
}

export function runBacktest(candles: BacktestCandle[], input: BacktestInput): BacktestResult {
  if (candles.length < input.lookback + 20) throw new Error("Not enough candles for this lookback");
  const trades: BacktestTrade[] = [];
  let nextAvailableIndex = input.lookback + 1;

  for (let index = input.lookback + 1; index < candles.length - 1; index++) {
    if (index < nextAvailableIndex) continue;
    const candle = candles[index]!;
    const history = candles.slice(index - input.lookback, index);
    const profile = approximateProfile(history);
    const currentAtr = atr(candles, index);
    const avgVolume = average(history.slice(-20).map((item) => item.volume));
    const range = Math.max(candle.high - candle.low, currentAtr * 0.1);
    const closeLocation = (candle.close - candle.low) / range;
    const volumeExpansion = avgVolume > 0 && candle.volume >= avgVolume * 1.25;

    const detected = detectSignal(candles, index, profile, input.model);
    if (!detected) continue;
    const { direction } = detected;
    if (input.direction !== "both" && input.direction !== direction) continue;
    const strict = volumeExpansion && (direction === "long" ? closeLocation >= 0.65 : closeLocation <= 0.35);
    if (input.quality === "A+" && !strict) continue;
    const grade: "A" | "A+" = strict ? "A+" : "A";

    const entryIndex = index + 1;
    const entry = candles[entryIndex]!.open;
    const stop = direction === "long"
      ? Math.min(candle.low, profile.val) - currentAtr * 0.15
      : Math.max(candle.high, profile.vah) + currentAtr * 0.15;
    const risk = Math.abs(entry - stop);
    if (!Number.isFinite(risk) || risk <= 0 || (direction === "long" ? stop >= entry : stop <= entry)) continue;
    const opposingTargets = direction === "long" ? [profile.poc, profile.vah] : [profile.poc, profile.val];
    const target = opposingTargets
      .filter((value) => direction === "long" ? value > entry : value < entry)
      .sort((a, b) => direction === "long" ? a - b : b - a)[0];
    if (target === undefined || Math.abs(target - entry) / risk < input.targetR) continue;
    const lastIndex = Math.min(candles.length - 1, entryIndex + input.maxHoldBars);
    let exitIndex = lastIndex;
    let exit = candles[lastIndex]!.close;
    let exitReason: BacktestTrade["exitReason"] = lastIndex === candles.length - 1 ? "data-end" : "timeout";

    for (let cursor = entryIndex; cursor <= lastIndex; cursor++) {
      const bar = candles[cursor]!;
      const stopHit = direction === "long" ? bar.low <= stop : bar.high >= stop;
      const targetHit = direction === "long" ? bar.high >= target : bar.low <= target;
      if (stopHit) { exitIndex = cursor; exit = stop; exitReason = "stop"; break; }
      if (targetHit) { exitIndex = cursor; exit = target; exitReason = "target"; break; }
    }
    const rawR = direction === "long" ? (exit - entry) / risk : (entry - exit) / risk;
    const resultR = Math.max(-1, rawR);
    const riskAmount = input.accountSize * input.riskPct / 100;
    trades.push({
      id: trades.length + 1, direction, grade, model: detected.model, signalTime: candle.time, entryTime: candles[entryIndex]!.time,
      exitTime: candles[exitIndex]!.time, entry, stop, target, exit, resultR, pnl: resultR * riskAmount,
      exitReason, holdBars: exitIndex - entryIndex + 1, profile
    });
    nextAvailableIndex = exitIndex + 1;
  }

  let balance = input.accountSize;
  let cumulativeR = 0;
  let peakR = 0;
  let maxDrawdownR = 0;
  let consecutiveLosses = 0;
  let maxConsecutiveLosses = 0;
  const equity = trades.map((trade) => {
    const riskAmount = balance * input.riskPct / 100;
    balance += trade.resultR * riskAmount;
    cumulativeR += trade.resultR;
    peakR = Math.max(peakR, cumulativeR);
    maxDrawdownR = Math.max(maxDrawdownR, peakR - cumulativeR);
    if (trade.resultR < 0) { consecutiveLosses++; maxConsecutiveLosses = Math.max(maxConsecutiveLosses, consecutiveLosses); }
    else consecutiveLosses = 0;
    return { time: trade.exitTime, balance, cumulativeR };
  });
  const wins = trades.filter((trade) => trade.resultR > 0);
  const losses = trades.filter((trade) => trade.resultR <= 0);
  const grossWins = wins.reduce((sum, trade) => sum + trade.resultR, 0);
  const grossLosses = Math.abs(losses.reduce((sum, trade) => sum + trade.resultR, 0));
  const netR = trades.reduce((sum, trade) => sum + trade.resultR, 0);

  return {
    input,
    data: { from: candles[0]!.time, to: candles.at(-1)!.time, bars: candles.length },
    metrics: {
      trades: trades.length, wins: wins.length, losses: losses.length, winRate: trades.length ? wins.length / trades.length * 100 : 0,
      netR, expectancyR: trades.length ? netR / trades.length : 0, profitFactor: grossLosses ? grossWins / grossLosses : wins.length ? null : 0,
      maxDrawdownR, maxConsecutiveLosses, averageHoldBars: trades.length ? average(trades.map((trade) => trade.holdBars)) : 0,
      startingBalance: input.accountSize, endingBalance: balance, returnPct: (balance / input.accountSize - 1) * 100
    },
    equity,
    trades,
    notes: [
      "Historical profile is approximated by distributing candle volume across each candle range.",
      "EM1–EM4 are conservative candle approximations of the book rules; EM2 uses an internal 12-bar swing profile.",
      "Targets use the nearest real opposing profile level. Trades are skipped when that level offers less than the selected minimum R:R.",
      "If stop and target touch in the same candle, the stop is assumed first.",
      "Historical Coinbase MBO is not included; live MBO must be recorded before it can be replayed."
    ]
  };
}
