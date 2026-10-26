import unittest

import pytest

# normalize_ticker_symbol lives in the upstream TradingAgents CLI, which was not carried into this repo.
pytest.importorskip("cli", reason="upstream TradingAgents CLI is not part of this repo")

from cli.utils import normalize_ticker_symbol  # noqa: E402
from tradingagents.agents.utils.agent_utils import build_instrument_context  # noqa: E402


@pytest.mark.unit
class TickerSymbolHandlingTests(unittest.TestCase):
    def test_normalize_ticker_symbol_preserves_exchange_suffix(self):
        self.assertEqual(normalize_ticker_symbol(" cnc.to "), "CNC.TO")

    def test_build_instrument_context_mentions_exact_symbol(self):
        context = build_instrument_context("7203.T")
        self.assertIn("7203.T", context)
        self.assertIn("exchange suffix", context)


if __name__ == "__main__":
    unittest.main()
