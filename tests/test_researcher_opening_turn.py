"""Bull/bear researchers must OPEN with a thesis, not rebut a phantom opponent.

The Bull always speaks first (graph edge: analysts -> Bull Researcher), so on
its first turn no Bear has argued yet. The old prompt still instructed it to
"counter bearish arguments" and handed it an empty `Last bear argument:`, so the
model invented a bear to rebut ("here's what the bears want you to forget...").
To an institutional viewer watching the transcript, a bull rebutting a bear who
never spoke reads as staged.

These tests lock in role-aware framing: an opening thesis when the other side is
silent, a rebuttal once it has actually spoken. The load-bearing marker is the
`Last <opponent> argument:` line — that empty injection is the exact mechanism
of the bug, so the tests key on its presence/absence.
"""
import unittest
from unittest.mock import MagicMock

from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents.agents.researchers.bull_researcher import create_bull_researcher


def _state(investment_debate_state: dict) -> dict:
    return {
        "investment_debate_state": investment_debate_state,
        "market_report": "MKT",
        "sentiment_report": "SENT",
        "news_report": "NEWS",
        "fundamentals_report": "FUND",
        "asset_type": "stock",
    }


def _capture(factory, investment_debate_state: dict):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="argument body")
    node = factory(llm)
    result = node(_state(investment_debate_state))
    prompt = llm.invoke.call_args.args[0]
    return prompt, result


class BullOpeningTurnTests(unittest.TestCase):
    def test_first_turn_opens_and_does_not_rebut_a_phantom_bear(self):
        prompt, result = _capture(
            create_bull_researcher,
            {"history": "", "bull_history": "", "bear_history": "",
             "current_response": "", "count": 0},
        )
        self.assertIn("No bear analyst has spoken yet", prompt)
        self.assertNotIn("Last bear argument:", prompt)
        # The node still advances the debate exactly as before.
        self.assertEqual(result["investment_debate_state"]["count"], 1)
        self.assertTrue(
            result["investment_debate_state"]["bull_history"].strip().startswith("Bull Analyst:")
        )

    def test_later_turn_rebuts_the_actual_bear_argument(self):
        prompt, _ = _capture(
            create_bull_researcher,
            {"history": "Bull Analyst: a\nBear Analyst: the bear case",
             "bull_history": "Bull Analyst: a",
             "bear_history": "Bear Analyst: the bear case",
             "current_response": "Bear Analyst: the bear case",
             "count": 2},
        )
        self.assertIn("Last bear argument: Bear Analyst: the bear case", prompt)
        self.assertNotIn("No bear analyst has spoken yet", prompt)


class BearRoleAwarenessTests(unittest.TestCase):
    def test_rebuts_the_bull_when_the_bull_has_spoken(self):
        # The normal case: bear always follows the bull, so it has a real target.
        prompt, _ = _capture(
            create_bear_researcher,
            {"history": "Bull Analyst: the bull case",
             "bull_history": "Bull Analyst: the bull case",
             "bear_history": "",
             "current_response": "Bull Analyst: the bull case",
             "count": 1},
        )
        self.assertIn("Last bull argument: Bull Analyst: the bull case", prompt)
        self.assertNotIn("No bull analyst has spoken yet", prompt)

    def test_opens_if_it_ever_speaks_first(self):
        # Defensive symmetry: if the flow ever puts the bear first, it must not
        # rebut a phantom bull either.
        prompt, _ = _capture(
            create_bear_researcher,
            {"history": "", "bull_history": "", "bear_history": "",
             "current_response": "", "count": 0},
        )
        self.assertIn("No bull analyst has spoken yet", prompt)
        self.assertNotIn("Last bull argument:", prompt)


if __name__ == "__main__":
    unittest.main()
