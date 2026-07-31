const fs = require("fs");
const path = require("path");
const { getHistoricalRates } = require("dukascopy-node");

const inputPath = process.argv[2];
const outputDir = process.argv[3];
const instrument = String(process.argv[4] || "").trim().toLowerCase();
const concurrency = Number(process.argv[5] || 6);
const startDate = process.argv[6] || "";
const endDate = process.argv[7] || "";

if (!inputPath || !outputDir || !instrument) {
  throw new Error(
    "Usage: node download_symbol_event_data.js event_dates.json output_dir instrument [concurrency] [start] [end]",
  );
}

const dates = JSON.parse(fs.readFileSync(inputPath, "utf8")).filter(
  (date) => (!startDate || date >= startDate) && (!endDate || date < endDate),
);
fs.mkdirSync(outputDir, { recursive: true });

async function download(date, priceType) {
  const outputPath = path.join(
    outputDir,
    `${instrument}-m1-${priceType}-${date}.json`,
  );
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
    instrument,
    dates: { from, to },
    timeframe: "m1",
    priceType,
    volumes: true,
    format: "json",
    batchSize: 24,
    pauseBetweenBatchesMs: 25,
  });
  if (!Array.isArray(data) || data.length < 100) {
    throw new Error(
      `Incomplete ${instrument} ${priceType} data for ${date}: ${
        Array.isArray(data) ? data.length : "invalid"
      } rows`,
    );
  }
  fs.writeFileSync(outputPath, JSON.stringify(data));
  return { date, priceType, status: "downloaded", rows: data.length };
}

let cursor = 0;
let completed = 0;

async function worker() {
  while (cursor < dates.length) {
    const date = dates[cursor++];
    for (const priceType of ["bid", "ask"]) {
      try {
        const result = await download(date, priceType);
        completed += 1;
        if (completed % 20 === 0 || result.status === "downloaded") {
          process.stdout.write(
            `${JSON.stringify({
              completed,
              total: dates.length * 2,
              instrument,
              ...result,
            })}\n`,
          );
        }
      } catch (error) {
        process.stderr.write(
          `${JSON.stringify({
            date,
            priceType,
            instrument,
            error: String(error),
          })}\n`,
        );
      }
    }
  }
}

Promise.all(Array.from({ length: concurrency }, worker)).then(() => {
  process.stdout.write(
    `${JSON.stringify({
      status: "complete",
      instrument,
      completed,
      total: dates.length * 2,
    })}\n`,
  );
});
