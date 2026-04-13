from __future__ import annotations

from project_invest.services.universe import (
    build_universe,
    market_for_symbol,
    resolve_symbol_groups,
    resolve_symbols,
    symbol_market_map,
)


def test_build_universe_combines_markets() -> None:
    symbols = build_universe(["NSE", "NASDAQ"])
    assert "RELIANCE.NS" in symbols
    assert "AAPL" in symbols


def test_resolve_symbols_falls_back_to_base() -> None:
    base = ["ONLYBASE"]
    resolved = resolve_symbols(base, True, ["UNKNOWN"])
    assert resolved == base


def test_resolve_symbol_groups_respects_group_size() -> None:
    groups = resolve_symbol_groups(["A", "B", "C", "D", "E"], [], 2)
    assert groups == [["A", "B"], ["C", "D"], ["E"]]


def test_market_for_symbol_classifies_supported_markets() -> None:
    assert market_for_symbol("RELIANCE.NS") == "NSE"
    assert market_for_symbol("BTC-USD") == "CRYPTO"
    assert market_for_symbol("USDINR=X") == "FOREX"
    assert market_for_symbol("AAPL") == "NASDAQ"
    assert market_for_symbol("JNJ") == "NYSE"
    assert market_for_symbol("SOMEUNKNOWNUS") == "US"


def test_symbol_market_map_returns_exchange_labels() -> None:
    mapping = symbol_market_map(["RELIANCE.NS", "AAPL", "JNJ", "BTC-USD"])
    assert mapping == {
        "RELIANCE.NS": "NSE",
        "AAPL": "NASDAQ",
        "JNJ": "NYSE",
        "BTC-USD": "CRYPTO",
    }
