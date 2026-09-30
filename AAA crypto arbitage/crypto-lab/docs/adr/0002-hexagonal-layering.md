# ADR 0002: Ports-and-adapters layering

- **Status:** Accepted (2026-09-29)

## Context
Five bot models will share one codebase, and venues change their APIs often (Polymarket moved to CLOB V2 in 2026).
Trading logic must be testable without network access, and the rules must be auditable.

## Decision
Organise the code as a hexagonal architecture:

- `domain/`: pure logic and value objects (order books, fees, detectors, wallet stats, bot-mode policy, performance
  table). No I/O and no framework imports.
- `domain/<venue>/ports.py`: `Protocol` interfaces the services depend on (`MarketCatalog`, `BookSource`,
  `WalletDataSource`).
- `infrastructure/`: adapters implementing the ports (HTTP clients plus mapper modules as an anti-corruption
  layer), SQLite models and repositories.
- `services/`: use cases that orchestrate domain and adapters and own transactions (Unit of Work).
- `web/` and `workers/`: thin delivery mechanisms. `container.py` is the single composition root.

Patterns: Strategy (detectors, key providers), Chain of Responsibility (LIVE guards), Registry (providers, workers),
Repository + Unit of Work, Template Method (worker loop), value objects.

## Alternatives considered
- *Flat scripts per bot*: fastest to start, but duplicates the safety logic and cannot be tested offline.
- *Full DDD with aggregates and domain events*: too heavy for the current size; can grow into it later.

## Consequences
- \+ Services are tested with fakes; venue quirks are isolated in one mapper file each.
- \+ New venues or detectors are added by implementing an interface, not by editing callers.
- − More files and indirection than a script; mitigated by the README's pattern table and layout map.
