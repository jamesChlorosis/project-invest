# Project Invest

Project Invest is a personal quantitative research platform designed to act like an always-on trading laboratory rather than a single strategy bot.

The initial foundation in this repository focuses on five things:

- continuous market data ingestion through pluggable providers
- repository-backed storage that can run on local files today and switch to Postgres later
- automatic strategy evolution and historical backtesting
- an execution-agnostic trading layer with paper mode active by default
- realistic paper trading, risk controls, and an API dashboard

## Current architecture

```text
Market Data Providers
        ->
Ingestion + Normalization
        ->
Repository Layer
        ->
Storage Backend (Local Files or Postgres)
        ->
Optional Redis Cache
        ->
Feature Engineering
        ->
Strategy Evolution
        ->
Backtesting
        ->
Execution Engine + Risk
        ->
FastAPI Control Center
```

This version is intentionally modular so a future broker adapter can replace the paper broker without changing the research pipeline.

## What is implemented

- `mock` and `yahoo` market data providers behind a shared interface
- repository abstractions for candles, features, portfolio state, trades, and reports
- local-file storage plus backend selection for future Postgres/Redis deployment
- feature engineering for moving averages, RSI, momentum, volatility, and volume z-score
- a genetic strategy evolution engine that mutates strategy genomes
- a backtester with slippage, fees, stop loss, take profit, and Sharpe/drawdown metrics
- a paper broker with capital tracking, exposure controls, and order rejection logic
- an execution layer abstraction with `paper` and `live` modes
- a FastAPI app with endpoints for health, market data, features, portfolio state, and research runs
- a lightweight dashboard served from the API root

## Quick start

1. Create a virtual environment and install the project:

   ```powershell
   pip install -e .[dev]
   ```

2. Copy the example environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Run the API:

   ```powershell
   uvicorn project_invest.api.app:app --reload
   ```

4. Open [http://localhost:8000](http://localhost:8000)

5. Trigger a research cycle:

   ```powershell
   Invoke-RestMethod -Method Post http://localhost:8000/api/research/run
   ```

## Runtime entrypoints

- API server

  ```powershell
  python -m project_invest api --host 0.0.0.0 --port 8000
  ```

- One research cycle

  ```powershell
  python -m project_invest run-once
  ```

- Continuous worker

  ```powershell
  python -m project_invest worker
  ```

## Docker

- Local stack:

  ```powershell
  docker compose up --build
  ```

- Oracle-style production stack:

  ```powershell
  docker compose -f docker-compose.prod.yml up --build -d
  ```

Production deployment guidance lives in [DEPLOY_ORACLE.md](DEPLOY_ORACLE.md).

## Environment knobs

- `PROJECT_INVEST_MARKET_DATA_PROVIDER`: `mock` or `yahoo`
- `PROJECT_INVEST_EXECUTION_MODE`: `paper` or `live`
- `PROJECT_INVEST_STORAGE_BACKEND`: `local` or `postgres`
- `PROJECT_INVEST_STORAGE_CACHE_ENABLED`: `true` or `false`
- `PROJECT_INVEST_POSTGRES_DSN`: Postgres connection string when using the Postgres backend
- `PROJECT_INVEST_POSTGRES_SCHEMA`: schema used for repository tables
- `PROJECT_INVEST_REDIS_URL`: Redis URL for the optional cache layer
- `PROJECT_INVEST_RESEARCH_SYMBOLS`: comma-separated symbols
- `PROJECT_INVEST_RESEARCH_INTERVAL`: `1d`, `1h`, `1m`, etc.
- `PROJECT_INVEST_LIVE_LOOP_ENABLED`: run the research loop automatically
- `PROJECT_INVEST_LIVE_LOOP_SECONDS`: interval between research cycles
- `PROJECT_INVEST_STARTING_CAPITAL`: paper portfolio capital
- `PROJECT_INVEST_MAX_RISK_PER_TRADE`: risk budget per position
- `PROJECT_INVEST_LIVE_MAX_RISK_PER_TRADE`: tighter live risk cap
- `PROJECT_INVEST_MAX_DAILY_LOSS`: blocks new buys once breached

## Storage modes

- Default mode: `local`
  - stores everything in `runtime/data_lake`
- Durable mode: `postgres`
  - stores candles, features, portfolio state, trades, and reports in Postgres
- Optional cache: enable Redis on top of either backend with `PROJECT_INVEST_STORAGE_CACHE_ENABLED=true`

## Production recommendation

- API and worker should run as separate processes
- use `PROJECT_INVEST_STORAGE_BACKEND=postgres`
- use Redis as an optional cache layer
- keep `PROJECT_INVEST_LIVE_LOOP_ENABLED=false` when a dedicated worker container is running

## Roadmap

- add migration/versioning support for storage schemas
- add options chains, earnings, macro factors, and sentiment ingestion
- add portfolio allocation across multiple evolved strategies
- add broker adapters for Zerodha and Angel One
- split the dashboard into a dedicated frontend when the API surface stabilizes
