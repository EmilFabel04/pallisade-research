import pytest

from tradingagents.agents.utils.agent_utils import get_house_style_instruction


@pytest.mark.unit
def test_house_style_bans_execution_hype_and_fabrication():
    s = get_house_style_instruction().lower()
    # Institutional register
    assert "emoji" in s
    assert "analyst" in s
    # No execution / portfolio construction
    assert "position size" in s
    assert "stop-loss" in s
    assert "entry price" in s
    # Anti-hallucination
    assert "invent" in s
    assert "provided reports" in s
