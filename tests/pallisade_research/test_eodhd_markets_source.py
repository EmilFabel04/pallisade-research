from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import CAP_MARKETS
from pallisade_research.sources.eodhd_markets import EODHDMarketsSource, to_market_symbol


def test_market_symbol_mapping():
    assert to_market_symbol("USD/ZAR", "fx") == "USDZAR.FOREX"
    assert to_market_symbol("usdzar", "fx") == "USDZAR.FOREX"
    assert to_market_symbol("bitcoin", "crypto") == "BTC-USD.CC"
    assert to_market_symbol("ETH", "crypto") == "ETH-USD.CC"
    assert to_market_symbol("S&P 500", "index") == "GSPC.INDX"
    assert to_market_symbol("weird", "commodity") is None


def test_eodhd_markets_returns_record():
    captured = {}

    def fake_get(url, params):
        captured["params"] = params
        return {"code": "USDZAR.FOREX", "close": 16.45, "timestamp": 1}

    src = EODHDMarketsSource(http_get=fake_get, api_key="k")
    recs = src.fetch(ResearchQuery(question="USDZAR?", ticker=None, capabilities=(CAP_MARKETS,),
                     entity="USD/ZAR", entity_type="fx"))
    assert len(recs) == 1
    assert recs[0].capability == CAP_MARKETS
    assert recs[0].value == 16.45
    assert recs[0].provenance.source == "eodhd_markets"
    assert captured["params"]["fmt"] == "json"


def test_eodhd_markets_equity_price_and_change():
    # EOD endpoint returns daily bars, newest first (order=d)
    bars = [
        {"date": "2026-07-20", "close": 220.0, "open": 218, "high": 221, "low": 217, "volume": 1},
        {"date": "2026-07-19", "close": 200.0, "open": 199, "high": 205, "low": 198, "volume": 1},
    ]
    captured = {}

    def fake_get(url, params):
        captured["url"] = url
        return bars

    src = EODHDMarketsSource(http_get=fake_get, api_key="k")
    recs = src.fetch(ResearchQuery(question="how is SBK doing?", ticker="SBK.JO",
                     capabilities=(CAP_MARKETS,)))
    keys = {r.key: r.value for r in recs}
    assert keys["markets.price"] == 220.0
    assert keys["markets.change_pct"] == 10.0  # (220-200)/200*100
    assert all(r.capability == CAP_MARKETS for r in recs)
    assert "SBK.JSE" in captured["url"]  # exchange-mapped


def test_eodhd_markets_equity_noop_on_unmapped_ticker():
    src = EODHDMarketsSource(http_get=lambda u, p: [{"close": 1}], api_key="k")
    # Tokyo local (.T) is unmapped by to_eodhd_symbol -> []
    assert src.fetch(ResearchQuery(question="q", ticker="7203.T", capabilities=(CAP_MARKETS,))) == []


def test_eodhd_markets_noop_without_key_or_entity():
    src0 = EODHDMarketsSource(http_get=lambda u, p: {"close": 1}, api_key="")
    assert src0.fetch(ResearchQuery(question="q", ticker=None, capabilities=(CAP_MARKETS,),
                      entity="bitcoin", entity_type="crypto")) == []
    src1 = EODHDMarketsSource(http_get=lambda u, p: {"close": 1}, api_key="k")
    assert src1.fetch(ResearchQuery(question="q", ticker="AAPL", capabilities=(CAP_MARKETS,),
                      entity=None, entity_type=None)) == []
    assert src1.fetch(ResearchQuery(question="q", ticker=None, capabilities=(CAP_MARKETS,),
                      entity="gold", entity_type="commodity")) == []
