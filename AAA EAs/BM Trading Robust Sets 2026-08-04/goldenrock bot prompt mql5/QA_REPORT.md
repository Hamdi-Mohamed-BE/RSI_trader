# GOLDENROCK MQL5 PROMPT LIBRARY - QA REPORT

## Library Summary

Templates: 18

Validation Status: PASS

Average Overall Prompt Quality: 87/100

Critical Issues: 1

Moderate Issues: 3

Minor Issues: 5

## Validator Result

The existing validator passed cleanly:

- Number of templates discovered: 18
- Number of prompt files: 18
- Duplicate files: none
- Empty or short files: none
- Wrong platform references: none detected in a way that blocks use
- Pine Script contamination: none as active target
- MQL4 contamination: none as active target
- Missing direct-code instruction: none
- Missing Blueprint: none
- Missing risk logic: none
- Missing non-repainting requirements: none
- Missing compilation requirements: none

## Semantic Audit Summary

The library is materially better than a generic 18-file rename pack. The prompts are strategy-specific, contain complete blueprints, preserve setup variants, and consistently push the downstream model toward native MQL5 EAs rather than tutorial output.

The strongest area is the repeated enforcement of:

- immediate code generation
- no clarification round
- non-repainting behavior
- strategy tester compatibility
- explicit stop / target / risk / session / invalidation logic
- setup-variant preservation

The main weakness is not missing structure, but uneven data realism across the hardest automation domains, especially full order flow.

## Cross-Template Contamination Check

No severe contamination was found.

Observed patterns:

- Harmonic prompts stay anchored to Fibonacci, PRZ, ratios, pivots, and repaint-safe swing confirmation.
- Liquidity sweep prompts stay anchored to sweep, reclaim, structure shift, and target liquidity.
- VWAP prompts stay anchored to session timing, VWAP bias, deviation, and session reset.
- Trend and breakout prompts retain their own directional and expansion logic.

Universal MQL5 engineering instructions are repeated across files, but that repetition is acceptable because it is part of the prompt architecture.

## Automation Realism Classification

### 03 - Liquidity Sweep Reversal

- external liquidity: PROXY
- confirmed swing high / low: NATIVE
- swing strength: PROXY
- liquidity age: PROXY
- sweep penetration: NATIVE
- wick behavior: NATIVE
- close-back-inside: NATIVE
- reclaim: PROXY
- displacement: PROXY
- structure shift: PROXY
- confirmation window: NATIVE
- setup expiry: NATIVE
- invalidation: NATIVE
- duplicate sweep protection: NATIVE
- opposing liquidity target: PROXY

### 14 - Harmonic + PRZ Reversal Model

- pivot algorithm: NATIVE
- confirmed swings: PROXY
- XABCD geometry: NATIVE
- Fibonacci calculations: NATIVE
- pattern ratios: NATIVE
- ratio tolerance: NATIVE
- supported pattern types: NATIVE
- PRZ calculation: NATIVE
- PRZ tolerance: NATIVE
- pattern completion: NATIVE
- confirmation: NATIVE
- invalidation: NATIVE
- stop location: NATIVE
- target ratios: NATIVE
- maximum pattern age: NATIVE
- duplicate pattern prevention: NATIVE
- repaint-safe swing confirmation: NATIVE, with confirmation delay acknowledged

### 15 - Full Order Flow Execution Model

- native MT5 data: NATIVE
- tick-volume proxy: PROXY
- DOM proxy: PROXY
- genuine external order-flow data: EXTERNAL DATA
- bid/ask footprint: UNSUPPORTED unless external feed is added
- centralized delta: UNSUPPORTED in standard MT5
- true absorption: PROXY unless external data exists
- futures order-book history: EXTERNAL DATA

### 18 - VWAP - Session Bias Scalping Model

- VWAP calculation: NATIVE
- session reset: NATIVE
- server-time handling: NATIVE
- price source: NATIVE
- volume source: PROXY if true volume is unavailable; otherwise NATIVE where supported
- session anchors: NATIVE
- bias threshold: NATIVE
- deviation bands: NATIVE
- entry confirmation: NATIVE / PROXY depending on structure rule
- session transitions: NATIVE
- spread: NATIVE
- volatility: PROXY
- duplicate entries: NATIVE
- session expiry: NATIVE

## Deep Prompt Review

### 03 - Liquidity Sweep Reversal

Status: PASS

Strengths:

- Forces explicit sweep variants.
- Uses completed-bar and confirmation-window language.
- Includes duplicate-sweep protection, expiry, and trade-management state.
- Repeats measurable failure logging and backtest rules.

Risks:

- Some liquidity concepts remain proxy-based, which is appropriate but should be acknowledged in the downstream EA implementation.

Score:

- Strategy Specificity: 94
- Automation Precision: 93
- MQL5 Implementation Readiness: 92
- Ambiguity Control: 90
- Data Realism: 86
- Overall Prompt Quality: 92

### 14 - Harmonic + PRZ Reversal Model

Status: PASS

Strengths:

- Forces pivot confirmation and ratio tolerance.
- Preserves setup variants rather than collapsing them into one vague pattern prompt.
- Includes duplicate pattern prevention and repaint-safe swing confirmation.

Risks:

- Harmonic logic is still pattern-detection-heavy and therefore sensitive to implementation choice.
- The downstream EA will need carefully chosen deterministic swing logic to avoid false pattern inflation.

Score:

- Strategy Specificity: 96
- Automation Precision: 95
- MQL5 Implementation Readiness: 90
- Ambiguity Control: 89
- Data Realism: 88
- Overall Prompt Quality: 93

### 15 - Full Order Flow Execution Model

Status: REVIEW

Strengths:

- Explicitly distinguishes native MT5 data from external order-flow data.
- Warns against fabricated footprint, cluster, DOM, and delta data.
- Includes proxy and external-data fallback language.

Risks:

- Highest data dependency in the library.
- The prompt is realistic, but the downstream EA may still be forced into proxy logic unless an external data feed is integrated.
- This is the highest automation-risk prompt because the model space depends on data MT5 does not natively guarantee.

Score:

- Strategy Specificity: 92
- Automation Precision: 90
- MQL5 Implementation Readiness: 79
- Ambiguity Control: 84
- Data Realism: 74
- Overall Prompt Quality: 84

### 18 - VWAP - Session Bias Scalping Model

Status: PASS

Strengths:

- Uses session reset, server-time handling, session anchors, and deviation bands.
- Forces the downstream implementation to distinguish continuation from mean reversion.
- Covers duplicate entries and session expiry clearly.

Risks:

- VWAP logic can still become vague if the implementation does not choose a precise source and reset rule.

Score:

- Strategy Specificity: 90
- Automation Precision: 91
- MQL5 Implementation Readiness: 92
- Ambiguity Control: 88
- Data Realism: 89
- Overall Prompt Quality: 90

## Prompt Differentiation Analysis

The prompts are not generic clones. They differ materially by:

- setup variants
- model-specific market models
- strategy-specific automation requirements
- data realism warnings
- unique failure modes
- distinct first-code objectives

The most differentiated prompts are:

- 03 - Liquidity Sweep Reversal
- 14 - Harmonic + PRZ Reversal Model
- 15 - Full Order Flow Execution Model
- 18 - VWAP - Session Bias Scalping Model

## Issues Found

### Critical

1. Full Order Flow Execution Model has an unavoidable data realism constraint. Standard MT5 cannot guarantee centralized footprint, true delta, or historical DOM availability. The prompt handles this correctly by requiring proxy and external-data branches, but downstream EA generation must remain conservative.

### Moderate

1. Several prompts reuse a shared engineering scaffold, which is acceptable, but it slightly reduces perceived uniqueness in the low-complexity templates.
2. Some strategy names and categories are broad, so the downstream AI must still choose concrete thresholds carefully.
3. The order-flow prompt is excellent as a prompt, but is the hardest to execute faithfully without external data.

### Minor

1. Repeated universal sections make the library long, which is intentional but visually dense.
2. The strongest prompts are clearer than the broad institutional prompts.
3. The validator checks structural presence well, but semantic quality still needs human review.
4. A few prompts lean on proxy language more heavily than others.
5. Some strategy-specific sections are necessarily conservative because the source strategy itself is partly conceptual.

## Strongest Prompt

14 - Harmonic + PRZ Reversal Model

## Weakest Prompt

15 - Full Order Flow Execution Model

## Highest Automation Risk

15 - Full Order Flow Execution Model

## Highest Data Dependency

15 - Full Order Flow Execution Model

## First Prompt Recommended for EA Generation Test

03 - Liquidity Sweep Reversal

Reason:

- clear structure
- measurable entries and invalidation
- moderate complexity
- easier to compile and backtest safely than the order-flow or harmonic prompts

## Final Assessment

The prompt library is suitable for downstream EA generation work.

The strongest templates are technically well-formed and strategy-specific.

The only material caution is the order-flow family, which correctly warns about MT5 data limits and must remain proxy-aware unless external feeds are added.
