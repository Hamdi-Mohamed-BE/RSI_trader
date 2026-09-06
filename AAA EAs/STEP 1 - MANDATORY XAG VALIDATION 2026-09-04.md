# Step 1 — Mandatory XAG validation

Status: Complete on 4 September 2026.

## Goal

Require every new EA idea and every material EA revision to be validated on silver, even when another market is the strategy's primary instrument.

## Applied changes

- XAG is now an unconditional cross-market validation requirement in `EA RESEARCH BASE FLOW.md`.
- The frozen primary-market configuration must be tested on XAG before any XAG-specific optimization. This separates portability evidence from fitted silver settings.
- Broker-symbol discovery must resolve `XAGUSD`, suffix variants such as `XAGUSDm`, or aliases such as `SILVER`.
- Every final report must show an XAG row and XAG equity curve. Negative evidence must not be hidden.
- A machine-readable policy is stored in `EA RESEARCH REQUIRED MARKETS.json`.
- `Assert-EAResearchMarkets.ps1` blocks final sign-off when a summary CSV has no XAG result.

## Verification

- The gate passed an existing Trend Progression audit containing three XAG rows.
- The gate correctly blocked an existing Asia Sweep results file that had no XAG validation.
- The policy JSON parses successfully and the PowerShell validation script has no syntax errors.

## Deployment boundary

This step does not add an XAG EA to the live BAT portfolio or public store. An XAG instance is eligible for deployment only after its own locked out-of-sample evidence passes and the user approves it.
