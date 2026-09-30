# ADR 0003: Credential vault and admin security

- **Status:** Accepted (2026-09-29)

## Context
The dashboard stores exchange, prediction-market, RPC and notification API keys. A leak could move real money.
The threat model covers: a copied SQLite file, a shoulder-surfed or screen-shared dashboard, CSRF and XSS from a
malicious page, credential stuffing, and accidental logging.

## Decision
- **Encryption at rest:** AES-256-GCM per credential, with a random 96-bit nonce. The associated data is
  `credential:<id>:<provider>`, which binds each ciphertext to its row, so swapping ciphertexts between rows fails.
- **Master key** outside the database, resolved by a Strategy chain: environment → OS keyring → a development key
  file that is never used in `production`.
- **Write-only UI:** only masked views (`…last4`) leave the service layer. Decryption happens only in
  `reveal_for_worker`, which is never called from a web route. The audit log records actions, never values.
- **Admin authentication:** Argon2id; optional TOTP 2FA (secret stored in the vault); generic errors; lockout;
  per-IP rate limit; server-side sessions storing only token digests; `HttpOnly` + `SameSite=Strict` cookies; a
  per-session CSRF token; strict CSP and anti-framing headers.
- **LIVE mode** is guarded by five independent checks: an allowed transition edge, a config flag, a paper gate,
  a typed confirmation and a 2FA code.
- **Deployment default:** bind to `127.0.0.1`; remote access only through a VPN or an HTTPS proxy.

## Alternatives considered
- *Plain `.env` secrets*: simple, but no per-key management, rotation or UI.
- *External secret manager* (Vault, AWS SM): stronger, but extra infrastructure for a single-user lab; the key
  provider chain can add one later.
- *Encrypt only with a password entered at startup*: avoids storing a master key, but unattended workers could no
  longer restart on their own.

## Consequences
- \+ A stolen SQLite file alone does not reveal secrets.
- \+ Rotation and disabling are one click and audited.
- − Losing the master key means re-entering all credentials.
- − A compromised host (with the keyring or environment available) can still decrypt, as with any online secret
  store. Exchange keys must therefore be created without withdrawal permission and with IP allow-lists.
