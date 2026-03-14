# Architecture Notes

This repository implements the first runnable slice of a larger quant research operating system.

## Current live modules

- `src/project_invest/providers/`
  - pluggable market data providers
- `src/project_invest/storage/`
  - repository protocols, local file backend, Postgres backend, and optional Redis cache layer
- `src/project_invest/services/feature_engineering.py`
  - feature store generation for common indicators
- `src/project_invest/services/strategy_signals.py`
  - signal logic for strategy genomes
- `src/project_invest/services/strategy_evolution.py`
  - genetic strategy discovery loop
- `src/project_invest/services/backtesting.py`
  - backtests with slippage, fees, stop loss, and take profit
- `src/project_invest/services/risk.py`
  - portfolio risk controls
- `src/project_invest/services/paper_trading.py`
  - simulated exchange and portfolio updates
- `src/project_invest/execution/`
  - execution mode boundary between paper and live
- `src/project_invest/api/`
  - FastAPI control center and dashboard
- `src/project_invest/runtime.py`
  - explicit runtime entrypoints for API, run-once, and worker modes

## Execution boundary

The research stack stays the same in both modes:

```text
data -> features -> strategy evolution -> backtesting -> signal
```

Only the execution engine changes:

```text
paper mode: signal -> PaperExecutionEngine -> local simulated portfolio
live mode:  signal -> LiveExecutionEngine  -> broker adapter
```

`LiveExecutionEngine` is intentionally present now even though no broker adapter is wired yet. That keeps the interface stable for future Zerodha or Angel One integrations.

## Storage boundary

The service layer now talks to repository interfaces instead of concrete file storage:

```text
services -> repository protocols -> storage backend
```

Backends currently available:

- `local`
  - JSON files under `runtime/data_lake`
- `postgres`
  - tables for candles, features, trades, portfolio state, and reports
- optional Redis cache
  - wraps either backend without changing service code

## Production topology

Recommended deployment for one VM:

```text
nginx -> api -> repository layer -> postgres
                     |
                     -> optional redis cache

worker -> research loop -> same repository layer -> postgres
```

The API should not own the continuous worker loop in production. Run the worker as a separate process or container.

## What should deepen next

- object storage for large historical datasets
- migration/versioning support for Postgres schemas
- mock/yahoo provider mix -> dedicated collectors for news, fundamentals, and options data
- live execution stub -> broker adapter implementation
- simple portfolio optimizer -> multi-strategy allocator with richer covariance/risk modeling

## Suggested next build order

1. Add storage migrations and repository-level integration tests.
2. Persist evolved strategies and research runs as first-class datasets.
3. Add multi-source ingestion for news and fundamentals.
4. Add model training jobs and ensemble predictors.
5. Expand allocation logic across multiple champion strategies.
6. Implement a real broker adapter behind `LiveExecutionEngine`.
