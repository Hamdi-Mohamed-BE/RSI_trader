const fs = require("fs");
const path = require("path");
const { getHistoricalRates } = require("dukascopy-node");

const inputPath = process.argv[2];
const outputDir = process.argv[3];
const concurrency = Number(process.argv[4] || 8);

if (!inputPath || !outputDir) {
  throw new Error("Usage: node download_event_data.js event_dates.json output_dir [concurrency]");
}

const dates = JSON.parse(fs.readFileSync(inputPath, "utf8"));
fs.mkdirSync(outputDir, { recursive: true });

async function download(date, priceType) {
  const outputPath = path.join(outputDir, `xauusd-m1-${priceType}-${date}.json`);
  if (fs.existsSync(outputPath) && fs.statSync(outputPath).size > 100) {
    const cached = JSON.parse(fs.readFileSync(outputPath, "utf8"));
    if (Array.isArray(cached) && cached.length > 100) {
      return { date, priceType, status: "cached", rows: cached.length };
    }
  }

  const from = new Date(`${date}T00:00:00.000Z`);
  const to = new Date(from);
  to.setUTCDate(to.getUTCDate() + 1);
  const data = await getHistoricalRates({
    instrument: "xauusd",
    dates: { from, to },
    timeframe: "m1",
    priceType,
    volumes: true,
    format: "json",
    batchSize: 24,
    pauseBetweenBatchesMs: 25,
  });
  if (!Array.isArray(data) || data.length < 100) {
    throw new Error(`Incomplete ${priceType} data for ${date}: ${Array.isArray(data) ? data.length : "invalid"} rows`);
  }
  fs.writeFileSync(outputPath, JSON.stringify(data));
  return { date, priceType, status: "downloaded", rows: data.length };
}

const work = dates;
let cursor = 0;
let completed = 0;

async function worker() {
  while (cursor < work.length) {
    const date = work[cursor++];
    for (const priceType of ["bid", "ask"]) {
      try {
        const result = await download(date, priceType);
        completed += 1;
        if (completed % 25 === 0 || result.status === "downloaded") {
          process.stdout.write(`${JSON.stringify({ completed, total: work.length * 2, ...result })}\n`);
        }
      } catch (error) {
        process.stderr.write(`${JSON.stringify({ date, priceType, error: String(error) })}\n`);
      }
    }
  }
}

Promise.all(Array.from({ length: concurrency }, worker)).then(() => {
  process.stdout.write(`${JSON.stringify({ status: "complete", completed, total: work.length * 2 })}\n`);
});
