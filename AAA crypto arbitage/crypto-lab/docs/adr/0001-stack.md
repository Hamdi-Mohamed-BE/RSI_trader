# ADR 0001: Application stack

- **Status:** Accepted (2026-09-29)
- **Deciders:** project owner, implementation agent

## Context
The lab hosts several research bots (CEX arbitrage, Polymarket, Solana) plus an admin dashboard that manages API keys
and bot modes. It must run on one Windows or Linux machine, be cheap (paper phase: $0/month), and be easy for
open-source contributors to set up.

## Decision
- **Python 3.12, managed with uv** (`pyproject.toml` + `uv.lock`): reproducible installs, one tool for Python
  versions, virtualenvs and locking.
- **FastAPI + Jinja2** server-rendered pages, with typed `Annotated` dependencies and no SPA build step.
- **SQLite** through **SQLAlchemy 2 async** (aiosqlite) with **Alembic** migrations (batch mode). WAL journal,
  foreign keys on.
- **Tailwind CSS v4** built with the **standalone CLI** (via `pytailwindcss`), using the Calyx website's design tokens.
- **httpx** for outbound HTTP; **segno** for 2FA QR codes; **argon2-cffi**, **cryptography**, **pyotp**, **keyring**.

## Alternatives considered
- *Postgres/Timescale*: better for concurrent writers and large time series, but an extra service for a single-user
  lab. Deferred; the ORM keeps migration cheap.
- *Django*: batteries included, but heavier and less natural for async workers and the existing FastAPI code at Calyx.
- *React/Vite SPA*: richer UI, but adds a Node.js toolchain and a larger attack surface for an admin tool.
- *Tailwind CDN script* (as on the public site): no build step, but not suitable for production and it needs a
  looser CSP.

## Consequences
- \+ One-command setup (`uv sync`), fast tests, a strict CSP (no inline scripts), and no Node.js.
- \+ Money is stored as exact decimals in text columns (`DecimalText`), because SQLite has no decimal type.
- − SQLite allows a single writer. Workers and the web app write small transactions, which is fine at this scale.
  High-frequency order-book recording must go to compressed files, not SQLite.
- − Server-rendered pages refresh on navigation; live-updating widgets would need SSE/HTMX later.
