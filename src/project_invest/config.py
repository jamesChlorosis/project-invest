from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Project Invest"
    execution_mode: str = "paper"
    market_data_provider: str = "mock"
    storage_backend: str = "local"
    research_symbols: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    )
    research_interval: str = "1d"
    lookback_bars: int = 365
    live_loop_enabled: bool = False
    live_loop_seconds: int = 300

    starting_capital: float = 100000.0
    max_risk_per_trade: float = 0.01
    live_max_risk_per_trade: float = 0.005
    max_daily_loss: float = 0.03
    max_positions: int = 5
    max_gross_exposure: float = 1.0

    order_slippage_bps: float = 8.0
    fee_bps: float = 3.0

    population_size: int = 24
    generations: int = 8
    evolution_seed: int = 42

    data_root: Path = Path("runtime/data_lake")
    postgres_dsn: str | None = None
    postgres_schema: str = "project_invest"
    redis_url: str | None = None
    redis_key_prefix: str = "project_invest"
    redis_default_ttl_seconds: int | None = 900
    storage_cache_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROJECT_INVEST_",
        extra="ignore",
    )

    @field_validator("research_symbols", mode="before")
    @classmethod
    def parse_symbols(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS"]

    @field_validator("execution_mode", mode="before")
    @classmethod
    def parse_execution_mode(cls, value: str) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"paper", "live"}:
                return normalized
        return "paper"

    @field_validator("storage_backend", mode="before")
    @classmethod
    def parse_storage_backend(cls, value: str) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"local", "postgres"}:
                return normalized
        return "local"


settings = Settings()
