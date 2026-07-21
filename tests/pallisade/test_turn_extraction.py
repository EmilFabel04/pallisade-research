"""Pure turn extraction from langgraph 'values'-mode chunks. No DB, no LLM."""
from __future__ import annotations

from pallisade_core.runs.turns import Turn, extract_turns


def _invest(count: int, current: str) -> dict:
    return {"investment_debate_state": {"count": count, "current_response": current}}


def _risk(count: int, speaker: str, **responses) -> dict:
    state = {"count": count, "latest_speaker": speaker}
    state.update(responses)
    return {"risk_debate_state": state}


def test_no_change_yields_nothing():
    prev = _invest(2, "Bear Analyst: nope")
    assert extract_turns(prev, _invest(2, "Bear Analyst: nope")) == []


def test_first_bull_turn():
    turns = extract_turns({}, _invest(1, "Bull Analyst: services margin is the story"))
    assert turns == [Turn(phase="invest", speaker="bull", round=1,
                          text="services margin is the story")]


def test_bear_turn_same_round():
    prev = _invest(1, "Bull Analyst: up")
    turns = extract_turns(prev, _invest(2, "Bear Analyst: china decline"))
    assert turns == [Turn(phase="invest", speaker="bear", round=1, text="china decline")]


def test_round_increments_on_third_turn():
    prev = _invest(2, "Bear Analyst: down")
    turns = extract_turns(prev, _invest(3, "Bull Analyst: priced in"))
    assert turns[0].round == 2


def test_prefix_is_stripped():
    turns = extract_turns({}, _invest(1, "Bull Analyst:    leading space"))
    assert turns[0].text == "leading space"


def test_unknown_prefix_ignored():
    assert extract_turns({}, _invest(1, "Mystery Analyst: hello")) == []


def test_empty_response_ignored():
    assert extract_turns({}, _invest(1, "   ")) == []


def test_none_prev_treated_as_empty():
    assert extract_turns(None, _invest(1, "Bull Analyst: x"))[0].speaker == "bull"


def test_risk_aggressive_turn():
    curr = _risk(1, "Aggressive", current_aggressive_response="Aggressive Analyst: send it")
    assert extract_turns({}, curr) == [
        Turn(phase="risk", speaker="aggressive", round=1, text="send it")
    ]


def test_risk_conservative_turn():
    prev = _risk(1, "Aggressive", current_aggressive_response="Aggressive Analyst: a")
    curr = _risk(2, "Conservative", current_conservative_response="Conservative Analyst: careful")
    assert extract_turns(prev, curr) == [
        Turn(phase="risk", speaker="conservative", round=1, text="careful")
    ]


def test_risk_round_increments_after_three():
    prev = _risk(3, "Neutral", current_neutral_response="Neutral Analyst: c")
    curr = _risk(4, "Aggressive", current_aggressive_response="Aggressive Analyst: again")
    assert extract_turns(prev, curr)[0].round == 2


def test_risk_unknown_speaker_ignored():
    curr = _risk(1, "Wildcard", current_aggressive_response="Aggressive Analyst: x")
    assert extract_turns({}, curr) == []


def test_both_debates_can_advance_in_one_chunk():
    curr = {
        "investment_debate_state": {"count": 1, "current_response": "Bull Analyst: b"},
        "risk_debate_state": {
            "count": 1, "latest_speaker": "Aggressive",
            "current_aggressive_response": "Aggressive Analyst: r",
        },
    }
    turns = extract_turns({}, curr)
    assert [t.phase for t in turns] == ["invest", "risk"]


def test_as_payload_shape():
    t = Turn(phase="invest", speaker="bull", round=2, text="hi")
    assert t.as_payload() == {"phase": "invest", "speaker": "bull", "round": 2, "text": "hi"}
