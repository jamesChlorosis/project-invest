from __future__ import annotations

from project_invest.config import Settings


def test_settings_parse_csv_symbols_and_storage_backend() -> None:
    configured = Settings(
        research_symbols="RELIANCE.NS,TCS.NS,INFY.NS",
        execution_markets="NSE,US",
        storage_backend="POSTGRES",
        execution_mode="LIVE",
        allow_mock_fallback=True,
    )

    assert configured.research_symbols == ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    assert configured.execution_markets == ["NSE", "US"]
    assert configured.storage_backend == "postgres"
    assert configured.execution_mode == "live"
    assert configured.allow_mock_fallback is True
