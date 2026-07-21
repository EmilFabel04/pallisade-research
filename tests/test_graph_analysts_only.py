import unittest
from unittest.mock import MagicMock

from langgraph.graph import END
from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.setup import GraphSetup


def _setup(analysts, analysts_only):
    tool_nodes = {k: MagicMock() for k in ("market", "social", "news", "fundamentals")}
    gs = GraphSetup(MagicMock(), MagicMock(), tool_nodes, ConditionalLogic(1, 1))
    return gs.setup_graph(analysts, analysts_only=analysts_only)


class AnalystsOnlyGraphTests(unittest.TestCase):
    def test_debate_mode_routes_last_analyst_to_bull(self):
        wf = _setup(["market", "fundamentals"], analysts_only=False)
        self.assertIn(("Msg Clear Fundamentals", "Bull Researcher"), wf.edges)
        self.assertNotIn(("Msg Clear Fundamentals", END), wf.edges)

    def test_analysts_only_routes_last_analyst_to_end(self):
        wf = _setup(["market", "fundamentals"], analysts_only=True)
        self.assertIn(("Msg Clear Fundamentals", END), wf.edges)
        self.assertFalse(
            any(e[1] == "Bull Researcher" for e in wf.edges),
            "analysts_only graph must have no edge into the debate",
        )

    def test_analysts_only_single_analyst(self):
        wf = _setup(["news"], analysts_only=True)
        self.assertIn(("Msg Clear News", END), wf.edges)

    def test_analysts_only_graph_compiles(self):
        """Compiling (not just inspecting edges) catches unreachable-node
        rejections that a future langgraph upgrade might introduce."""
        analysts_only_wf = _setup(["market", "fundamentals"], analysts_only=True)
        compiled = analysts_only_wf.compile()
        self.assertIsNotNone(compiled)

        debate_wf = _setup(["market", "fundamentals"], analysts_only=False)
        compiled_debate = debate_wf.compile()
        self.assertIsNotNone(compiled_debate)
