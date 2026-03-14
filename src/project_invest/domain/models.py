from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderStatus(str, Enum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class Candle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class FeatureRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    timestamp: datetime
    close: float
    sma_5: float | None = None
    sma_20: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    rsi_14: float | None = None
    momentum_5: float | None = None
    volatility_10: float | None = None
    volume_zscore_20: float | None = None


class StrategyGenome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(default_factory=lambda: f"strat-{uuid4().hex[:10]}")
    short_window: int = 8
    long_window: int = 21
    momentum_threshold: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.05
    risk_fraction: float = 0.1


class TradeSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    action: SignalAction
    confidence: float
    reason: str
    strategy_id: str
    timestamp: datetime = Field(default_factory=utc_now)


class BacktestTrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    strategy_id: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    return_pct: float


class BacktestMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades: int
    final_equity: float


class BacktestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    genome: StrategyGenome
    metrics: BacktestMetrics
    trades: list[BacktestTrade] = Field(default_factory=list)


class StrategyEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    genome: StrategyGenome
    metrics: BacktestMetrics
    score: float


class EvolutionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    population_size: int
    generations: int
    champion: StrategyEvaluation
    leaderboard: list[StrategyEvaluation] = Field(default_factory=list)
    latest_signal: TradeSignal


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    quantity: int
    average_price: float
    opened_at: datetime
    last_price: float
    strategy_id: str


class PortfolioSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    starting_capital: float
    cash: float
    realized_pnl: float = 0.0
    daily_pnl: float = 0.0
    open_exposure: float = 0.0
    total_equity: float
    positions: dict[str, Position] = Field(default_factory=dict)

    @classmethod
    def bootstrap(cls, starting_capital: float) -> "PortfolioSnapshot":
        return cls(
            as_of=utc_now(),
            starting_capital=starting_capital,
            cash=starting_capital,
            total_equity=starting_capital,
        )


class RiskLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_risk_per_trade: float
    max_daily_loss: float
    max_positions: int
    max_gross_exposure: float


class RiskDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    allowed_quantity: int
    reason: str


class ExecutionOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trade_id: str = Field(default_factory=lambda: f"order-{uuid4().hex[:10]}")
    mode: ExecutionMode
    symbol: str
    action: SignalAction
    status: OrderStatus
    quantity: int
    requested_price: float
    fill_price: float
    fee_paid: float
    note: str
    strategy_id: str
    timestamp: datetime = Field(default_factory=utc_now)


class SymbolResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    candles_collected: int
    feature_rows: int
    evolution: EvolutionReport
    latest_order: ExecutionOrder


class ResearchCycleReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at: datetime
    finished_at: datetime
    provider: str
    interval: str
    symbols: list[str]
    results: list[SymbolResearchResult]
    portfolio: PortfolioSnapshot
