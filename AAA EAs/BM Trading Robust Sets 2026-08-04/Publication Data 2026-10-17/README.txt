LOSSLESS RESEARCH PUBLICATION - 17 OCTOBER 2026

Large new JSON/CSV/TSV research data is published as adjacent .gz files.
The original files remain untouched locally. Compression manifest.json records
both byte counts and SHA-256 hashes, with a complete decompression/hash check.
No trades, paths, simulations or data rows are truncated to fit GitHub.

After cloning, verify the archives (read-only, standard-library Python):
  python restore.py

To recreate missing original data for research scripts:
  python restore.py --restore

Run these commands from this directory, or pass this script's full path.
Existing originals are never overwritten. These commands do not access MT5.
Raw account-bound configurations, test fixtures and runtime logs are not public
research artifacts. The source code, final reports and eligible data are retained.
