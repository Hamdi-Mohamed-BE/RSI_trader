import type { TradePrint, VolumeProfile } from "../types.js";

export class RollingVolumeProfile {
  private trades: TradePrint[] = [];
  constructor(private readonly windowMs = 4 * 60 * 60 * 1000, private readonly bucketBps = 1) {}

  ingest(trade: TradePrint) {
    this.trades.push(trade);
    this.prune(trade.time);
  }

  private prune(now: number) {
    const cutoff = now - this.windowMs;
    let firstValid = 0;
    while (firstValid < this.trades.length && this.trades[firstValid]!.time < cutoff) firstValid++;
    if (firstValid > 0) this.trades.splice(0, firstValid);
  }

  calculate(): VolumeProfile {
    if (this.trades.length === 0) return { poc: null, vah: null, val: null, totalVolume: 0, buckets: [], startedAt: null };
    const reference = this.trades.at(-1)!.price;
    const step = Math.max(reference * this.bucketBps / 10_000, reference < 100 ? 0.01 : 0.1);
    const map = new Map<number, number>();
    let totalVolume = 0;
    for (const trade of this.trades) {
      const bucket = Math.round(trade.price / step) * step;
      map.set(bucket, (map.get(bucket) ?? 0) + trade.size);
      totalVolume += trade.size;
    }
    const buckets = [...map.entries()]
      .map(([price, volume]) => ({ price, volume }))
      .sort((a, b) => a.price - b.price);
    const pocIndex = buckets.reduce((best, item, index) => item.volume > buckets[best]!.volume ? index : best, 0);
    let low = pocIndex;
    let high = pocIndex;
    let included = buckets[pocIndex]!.volume;
    const target = totalVolume * 0.7;
    while (included < target && (low > 0 || high < buckets.length - 1)) {
      const below = low > 0 ? buckets[low - 1]!.volume : -1;
      const above = high < buckets.length - 1 ? buckets[high + 1]!.volume : -1;
      if (above >= below) included += buckets[++high]!.volume;
      else included += buckets[--low]!.volume;
    }
    return {
      poc: buckets[pocIndex]!.price,
      vah: buckets[high]!.price,
      val: buckets[low]!.price,
      totalVolume,
      buckets: buckets.slice(Math.max(0, low - 20), Math.min(buckets.length, high + 21)),
      startedAt: this.trades[0]!.time
    };
  }
}
