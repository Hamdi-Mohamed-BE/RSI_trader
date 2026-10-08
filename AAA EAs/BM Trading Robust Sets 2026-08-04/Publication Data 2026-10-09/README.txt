Publication data packaging - 9 October 2026

Six large raw research CSVs are published as adjacent .csv.gz files. They are
lossless copies, not shortened samples. Original files are retained locally.
Compression manifest.json records SHA-256 hashes and byte lengths of both the
original CSVs and the compressed copies. One raw CSV exceeded GitHub's 100 MiB
file limit. The website and portfolio calculators use the published JSON
ledgers and do not need these raw CSVs to serve results.

To reproduce research that reads the original CSV paths, decompress the listed
.csv.gz files first. A .csv.gz file becomes the same path without the .gz suffix.
Verify the reconstructed file against the original_sha256 in the manifest.
Do not commit the uncompressed copies: those six paths are intentionally ignored.

Machine-specific run-config.json, tester.ini, owned-process.json and raw tester
journals remain private/local. They are not portable strategy or preset files.
