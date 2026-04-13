from __future__ import annotations

from datetime import timedelta

from project_invest.providers.yahoo import YahooFinanceProvider


def test_yahoo_history_window_expands_intraday_requests() -> None:
    provider = YahooFinanceProvider()

    history_15m = provider._history_window("15m", 365)
    history_1h = provider._history_window("1h", 365)
    history_1d = provider._history_window("1d", 365)

    assert history_15m >= timedelta(days=20)
    assert history_1h >= timedelta(days=80)
    assert history_1d >= timedelta(days=500)


def test_yahoo_intraday_history_window_is_bounded() -> None:
    provider = YahooFinanceProvider()

    history_1m = provider._history_window("1m", 5_000)
    history_5m = provider._history_window("5m", 5_000)

    assert history_1m <= timedelta(days=60)
    assert history_5m <= timedelta(days=60)
