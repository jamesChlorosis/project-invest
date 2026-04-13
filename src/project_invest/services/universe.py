from __future__ import annotations


def market_for_symbol(symbol: str) -> str:
    normalized = symbol.upper().strip()
    if normalized.endswith(".NS"):
        return "NSE"
    if normalized.endswith("-USD"):
        return "CRYPTO"
    if normalized.endswith("=X"):
        return "FOREX"
    exchange = DEFAULT_MARKET_LOOKUP.get(normalized)
    if exchange is not None:
        return exchange
    return "US"


def default_nse_universe() -> list[str]:
    return [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "ITC.NS",
        "LT.NS",
        "AXISBANK.NS",
        "HCLTECH.NS",
        "KOTAKBANK.NS",
        "BHARTIARTL.NS",
        "ASIANPAINT.NS",
        "MARUTI.NS",
        "SUNPHARMA.NS",
        "ULTRACEMCO.NS",
        "WIPRO.NS",
        "BAJFINANCE.NS",
        "BAJAJFINSV.NS",
        "TITAN.NS",
        "ADANIENT.NS",
        "NTPC.NS",
        "POWERGRID.NS",
        "ONGC.NS",
        "COALINDIA.NS",
        "INDUSINDBK.NS",
        "HINDUNILVR.NS",
        "NESTLEIND.NS",
        "JSWSTEEL.NS",
        "TATASTEEL.NS",
    ]


def default_nasdaq_universe() -> list[str]:
    return [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "AVGO",
        "ADBE",
        "CSCO",
        "INTC",
        "AMD",
    ]


def default_nyse_universe() -> list[str]:
    return [
        "BRK-B",
        "JNJ",
        "JPM",
        "V",
        "PG",
        "XOM",
        "UNH",
        "HD",
        "KO",
        "DIS",
        "PFE",
        "WMT",
    ]


def default_crypto_universe() -> list[str]:
    return [
        "BTC-USD",
        "ETH-USD",
        "BNB-USD",
        "SOL-USD",
        "XRP-USD",
        "ADA-USD",
    ]


def default_forex_universe() -> list[str]:
    return [
        "EURUSD=X",
        "GBPUSD=X",
        "USDJPY=X",
        "AUDUSD=X",
        "USDCAD=X",
        "USDINR=X",
    ]


def build_universe(markets: list[str]) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    for market in markets:
        name = market.upper().strip()
        if name == "NSE":
            source = default_nse_universe()
        elif name == "NASDAQ":
            source = default_nasdaq_universe()
        elif name == "NYSE":
            source = default_nyse_universe()
        elif name == "CRYPTO":
            source = default_crypto_universe()
        elif name == "FOREX":
            source = default_forex_universe()
        else:
            source = []

        for symbol in source:
            if symbol not in seen:
                symbols.append(symbol)
                seen.add(symbol)
    return symbols


def resolve_symbols(
    base_symbols: list[str],
    use_market_universes: bool,
    market_universes: list[str],
) -> list[str]:
    if use_market_universes:
        universe_symbols = build_universe(market_universes)
        return universe_symbols or base_symbols
    return base_symbols


def resolve_symbol_groups(
    symbols: list[str],
    explicit_groups: list[list[str]],
    group_size: int,
) -> list[list[str]]:
    if explicit_groups:
        return [group for group in explicit_groups if group]
    if group_size <= 0:
        return []
    groups: list[list[str]] = []
    for index in range(0, len(symbols), group_size):
        chunk = symbols[index : index + group_size]
        if chunk:
            groups.append(chunk)
    return groups


def symbol_market_map(symbols: list[str]) -> dict[str, str]:
    return {symbol: market_for_symbol(symbol) for symbol in symbols}


DEFAULT_MARKET_LOOKUP = {
    **{symbol.upper(): "NASDAQ" for symbol in default_nasdaq_universe()},
    **{symbol.upper(): "NYSE" for symbol in default_nyse_universe()},
}
