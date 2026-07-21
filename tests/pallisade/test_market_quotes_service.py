"""Unit tests for the market-quotes service. No network: yfinance is injected."""
from __future__ import annotations

import pandas as pd
import pytest

from web.api.services.market_quotes import (
    MAX_SYMBOLS,
    downsample_spark,
    fetch_quotes,
    format_market_cap,
    normalize_symbols,
    quote_one,
)


class FakeTicker:
    """Stands in for yfinance.Ticker: .info dict + .history() DataFrame."""

    def __init__(self, info: dict, closes: list[float] | None = None, raises: bool = False):
        self._info = info
        self._closes = closes if closes is not None else [1.0, 2.0]
        self._raises = raises

    @property
    def info(self) -> dict:
        if self._raises:
            raise RuntimeError("yfinance exploded")
        return self._info

    def history(self, period: str = "1mo") -> pd.DataFrame:
        return pd.DataFrame({"Close": self._closes})


def factory_for(mapping: dict[str, FakeTicker]):
    def _factory(symbol: str) -> FakeTicker:
        return mapping[symbol]

    return _factory


# --- normalize_symbols -------------------------------------------------------

def test_normalize_symbols_uppercases_strips_and_dedupes():
    assert normalize_symbols(" aapl , nvda,aapl ,, msft ") == ["AAPL", "NVDA", "MSFT"]


def test_normalize_symbols_empty_string_yields_empty_list():
    assert normalize_symbols("   ") == []


def test_normalize_symbols_caps_batch_at_max():
    raw = ",".join(f"SYM{i}" for i in range(MAX_SYMBOLS + 10))
    assert len(normalize_symbols(raw)) == MAX_SYMBOLS


# --- format_market_cap -------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [
        (3_450_000_000_000, "3.45T"),
        (45_600_000_000, "45.6B"),
        (789_000_000, "789M"),
        (12_345, "12345"),
        (None, "—"),
        (0, "—"),
        (999_600_000_000, "1T"),  # rounds to 1000B -> promoted, not "1e+03B"
        (999_600_000, "1B"),  # rounds to 1000M -> promoted, not "1e+03M"
        (2_000_000_000, "2B"),  # no trailing zeros: not "2.00B"
    ],
)
def test_format_market_cap(value, expected):
    assert format_market_cap(value) == expected


# --- downsample_spark --------------------------------------------------------

def test_downsample_spark_leaves_short_series_untouched():
    assert downsample_spark([1.0, 2.0, 3.0], limit=30) == [1.0, 2.0, 3.0]


def test_downsample_spark_caps_long_series_and_keeps_endpoints():
    out = downsample_spark([float(i) for i in range(100)], limit=30)
    assert len(out) <= 30
    assert out[0] == 0.0
    assert out[-1] == 99.0


# --- quote_one ---------------------------------------------------------------

def test_quote_one_maps_all_fields():
    t = FakeTicker(
        {
            "longName": "Apple Inc.",
            "regularMarketPrice": 228.52,
            "previousClose": 226.62,
            "marketCap": 3_450_000_000_000,
            "trailingPE": 34.1,
        },
        closes=[212.0, 215.0, 228.52],
    )
    q = quote_one("AAPL", ticker_factory=factory_for({"AAPL": t}))
    assert q["ok"] is True
    assert q["ticker"] == "AAPL"
    assert q["name"] == "Apple Inc."
    assert q["price"] == 228.52
    assert q["changePct"] == pytest.approx(0.8384, abs=1e-3)
    assert q["marketCap"] == "3.45T"
    assert q["pe"] == 34.1
    assert q["spark"] == [212.0, 215.0, 228.52]


def test_quote_one_falls_back_to_previous_close_when_no_live_price():
    t = FakeTicker({"shortName": "Zeta", "previousClose": 10.0})
    q = quote_one("ZETA", ticker_factory=factory_for({"ZETA": t}))
    assert q["price"] == 10.0
    assert q["changePct"] == 0.0


def test_quote_one_falls_back_to_current_price_when_no_regular_market_price():
    t = FakeTicker({"shortName": "Iota", "currentPrice": 15.0, "previousClose": 10.0})
    q = quote_one("IOTA", ticker_factory=factory_for({"IOTA": t}))
    assert q["price"] == 15.0
    assert q["changePct"] == pytest.approx(50.0)


def test_quote_one_raises_lookup_error_when_unresolvable():
    t = FakeTicker({})
    with pytest.raises(LookupError):
        quote_one("ZZZZ", ticker_factory=factory_for({"ZZZZ": t}))


def test_quote_one_tolerates_history_failure_with_empty_spark():
    class NoHistory(FakeTicker):
        def history(self, period: str = "1mo"):
            raise RuntimeError("no history")

    t = NoHistory({"longName": "Beta", "regularMarketPrice": 5.0, "previousClose": 5.0})
    q = quote_one("BETA", ticker_factory=factory_for({"BETA": t}))
    assert q["ok"] is True
    assert q["spark"] == []


def test_quote_one_with_history_false_skips_history_call():
    class TrackedTicker(FakeTicker):
        def __init__(self, info):
            super().__init__(info)
            self.history_called = False

        def history(self, period: str = "1mo"):
            self.history_called = True
            return super().history(period)

    t = TrackedTicker(
        {"longName": "Gamma", "regularMarketPrice": 50.0, "previousClose": 49.0}
    )
    q = quote_one("GAMMA", ticker_factory=factory_for({"GAMMA": t}), with_history=False)
    assert q["ok"] is True
    assert q["spark"] == []
    assert t.history_called is False


# --- fetch_quotes ------------------------------------------------------------

def test_fetch_quotes_one_failure_does_not_sink_the_batch():
    mapping = {
        "AAPL": FakeTicker(
            {"longName": "Apple Inc.", "regularMarketPrice": 228.52, "previousClose": 226.62},
            closes=[220.0, 228.52],
        ),
        "ZZZZ": FakeTicker({}),
        "BOOM": FakeTicker({}, raises=True),
    }
    out = fetch_quotes(["AAPL", "ZZZZ", "BOOM"], ticker_factory=factory_for(mapping))

    assert [q["ticker"] for q in out] == ["AAPL", "ZZZZ", "BOOM"]
    assert out[0]["ok"] is True
    assert out[1] == {"ticker": "ZZZZ", "ok": False, "error": "not_found"}
    assert out[2] == {"ticker": "BOOM", "ok": False, "error": "fetch_failed"}


def test_fetch_quotes_empty_input_returns_empty_list():
    assert fetch_quotes([], ticker_factory=factory_for({})) == []
