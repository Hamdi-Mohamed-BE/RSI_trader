import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const assets = [
  ["node_modules/htmx.org/dist/htmx.min.js", "static/vendor/htmx.min.js"],
  ["node_modules/alpinejs/dist/cdn.min.js", "static/vendor/alpine.min.js"],
  ["assets/js/app.js", "static/js/app.js"],
];

for (const [source, destination] of assets) {
  const outputPath = resolve(projectRoot, destination);
  await mkdir(dirname(outputPath), { recursive: true });
  await copyFile(resolve(projectRoot, source), outputPath);
}

console.log("Frontend JavaScript assets built.");
