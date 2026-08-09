const fs = require("fs");
const path = require("path");
const { getHistoricalRates } = require("dukascopy-node");

const manifestPath = process.argv[2];
const outputDir = process.argv[3];
const concurrency = Math.max(1, Number(process.argv[4] || 6));

if (!manifestPath || !outputDir) {
  throw new Error("Usage: node download_news_ticks.js manifest.json output_dir [concurrency]");
}

const events = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
fs.mkdirSync(outputDir, { recursive: true });

function fileName(event) {
  const release = new Date(event.release_utc);
  const hhmm = `${String(release.getUTCHours()).padStart(2, "0")}${String(release.getUTCMinutes()).padStart(2, "0")}`;
  return `xauusd-tick-${event.release_utc.slice(0, 10)}-${hhmm}-${event.event.toLowerCase()}.json`;
}

async function download(event) {
  const outputPath = path.join(outputDir, fileName(event));
  if (fs.existsSync(outputPath) && fs.statSync(outputPath).size > 500) {
    const cached = JSON.parse(fs.readFileSync(outputPath, "utf8"));
    if (Array.isArray(cached.ticks) && cached.ticks.length > 20) {
      return { status: "cached", rows: cached.ticks.length, event: event.event, release_utc: event.release_utc };
    }
  }

  const release = new Date(event.release_utc);
  const from = new Date(release.getTime() - 90_000);
  const to = new Date(release.getTime() + 301_000);
  const ticks = await getHistoricalRates({
    instrument: "xauusd",
    dates: { from, to },
    timeframe: "tick",
    format: "json",
    batchSize: 2,
    pauseBetweenBatchesMs: 20,
  });
  if (!Array.isArray(ticks) || ticks.length < 20) {
    throw new Error(`Incomplete ticks: ${Array.isArray(ticks) ? ticks.length : "invalid"}`);
  }
  fs.writeFileSync(outputPath, JSON.stringify({ ...event, from: from.toISOString(), to: to.toISOString(), ticks }));
  return { status: "downloaded", rows: ticks.length, event: event.event, release_utc: event.release_utc };
}

let cursor = 0;
let completed = 0;
let failures = 0;

async function worker() {
  while (cursor < events.length) {
    const event = events[cursor++];
    try {
      const result = await download(event);
      completed += 1;
      if (result.status === "downloaded" || completed % 25 === 0) {
        process.stdout.write(`${JSON.stringify({ completed, total: events.length, ...result })}\n`);
      }
    } catch (error) {
      failures += 1;
      process.stderr.write(`${JSON.stringify({ event: event.event, release_utc: event.release_utc, error: String(error) })}\n`);
    }
  }
}

Promise.all(Array.from({ length: concurrency }, worker)).then(() => {
  process.stdout.write(`${JSON.stringify({ status: "complete", completed, failures, total: events.length })}\n`);
  if (failures > 0) process.exitCode = 2;
});
