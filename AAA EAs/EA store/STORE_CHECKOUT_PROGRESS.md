# Direct checkout, licenses, admin panel, installer and video — progress log

Work session 2026-09-30 (parallel to the "3 Way Gold" session; no edits to `app/catalog.py`, the portfolio
installers/BATs or anything under `BM Trading Robust Sets 2026-08-04`; no terminal64/Strategy Tester launched;
production site on :8080 untouched; preview only on :8082).

## Decisions implemented (owner, 2026-09-30)
- Every bot 40% below the catalogue list price (`app/store/pricing.py`; catalogue list prices unchanged).
- Buy 3, get 1 free: for every 4 bots in the cart the n//4 cheapest are free; stated on cart, checkout, order.
- Complete-portfolio package $1,990 → $1,194, applied automatically when every sellable EA is in the cart and it is
  cheaper than the pack-rule total.
- USDT to the owner's Binance deposit addresses (TRC20 / BEP20). No address in code; entered in `/admin/settings`.
- Unique amount per order (base + 0.01…0.99 USDT among open/late-window orders), 60-min expiry, 30-min late window.
- Payment watcher reads TronGrid REST and BSC JSON-RPC `eth_getLogs`; configurable confirmations (20 / 15).
- Online activation: one license per bot, 1 live + 1 demo account, license bound to the product slug and the
  product's SET magic number; 24 h re-check, 72 h offline grace, Strategy Tester bypass.
- Admin panel `/admin` (scrypt, optional TOTP, CSRF, lockout), not linked publicly.
- Per-bot ZIP with store-build EX5, SET with key pre-filled, INSTALL BAT + PowerShell installer, README, LICENSE.

## Log
1. Read CLAUDE.md, README, main.py, catalog.py (read only), templates, FTMO `build_package.py`.
   Baseline suite before any change: 9 failed / 183 passed (8 in test_store.py + test_standalone_news_risk).
2. Package `app/store/`: config, db (SQLite + migrations), settings, pricing, security, orders, licenses,
   chain, payments (watcher), deliverables, builds, downloads, qr, cart, web, routes_public, routes_admin,
   admin_auth, integration; MQL5 `app/store/mql/CalyxLicense.mqh`; installer `app/store/installer/Install-CalyxBot.ps1`.
   No new Python dependencies (stdlib scrypt/HMAC/urllib; own QR encoder).
3. Store builds: `tools/build_store_eas.py` → `data/store-builds/` (gitignored — wrappers embed per-build secrets).
   26 builds for 35 products (incl. the new 3 Way Gold entry), **26/26 compiled with 0 errors, 0 warnings**.
   First pass: Gold News V9 wrapper had 1 warning (local `state` hid a global) → wrapper locals renamed, rebuilt.
4. QR encoder verified module-for-module against the `qrcode` package: 480 combinations, 0 mismatches.
5. `app/main.py` hooks (import, lifespan start/stop, `install()` at the end) and price display in /pricing,
   /portfolio, /store; templates: nav/footer links, cart badge, card/detail prices, add-to-cart, pricing actions.
6. Tests added: test_store_pricing_orders (10), test_store_chain (9), test_store_licenses (12), test_store_web (14),
   test_store_installer (4, fake MT5 folders only), test_store_pages (8, 1 skipped without `qrcode`).
   Two expectations in test_store.py updated to the owner's decision (detail page add-to-cart instead of the
   WhatsApp buy link; pricing card "Buy 3, get 1 free"/$1,194 instead of "Choose 3 + bonus"/$499).
7. Full suite after the store work: 227 passed / 20 failed / 1 skipped. The 7 test_store.py failures are the
   pre-existing ones; the other 13 (test_gold_value_area, test_nasdaq_di_prompt, test_nasdaq_wide_atr,
   test_orb_comments) concern FTMO/portfolio artefacts being changed by the parallel session (13 vs 14 EAs,
   portfolio dates, "Wrong portfolio scope") and touch no store code.
