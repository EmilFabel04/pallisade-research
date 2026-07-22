from pallisade_research.chat import converse
from pallisade_research.sources.registry import ClientConfig


class _Block:
    def __init__(self, **kw): self.__dict__.update(kw)


class _SDK:
    """Planner→fixed plan; auditor→report_issues; narrator→text. Dispatch by kwargs."""
    def __init__(self, audit_issues, narr_text="Fundamentals look stable."):
        self._audit_issues = audit_issues
        self._narr_text = narr_text
        self.messages = self

    def create(self, **kw):
        tools = kw.get("tools") or []
        names = {t["name"] for t in tools}
        if kw.get("tool_choice", {}).get("name") == "plan_research":
            return type("M", (), {"content": [_Block(type="tool_use",
                input={"ticker": None, "standalone_question": "q", "capabilities": ["fundamentals"]})]})()
        if "report_issues" in names:
            return type("M", (), {"content": [_Block(type="tool_use",
                input={"issues": self._audit_issues})]})()
        return type("M", (), {"content": [_Block(type="text", text=self._narr_text)]})()


def _converse(sdk):
    return converse([], "how is it", config=ClientConfig(client_id="c", enabled_sources=frozenset()),
                    registry={}, known_tickers=frozenset(), sdk=sdk,
                    plan_model="p", narrate_model="n", verify_model="v")


def test_converse_returns_verified_when_auditor_clean():
    turn = _converse(_SDK(audit_issues=[]))
    assert turn["verification"] == "verified"
    assert turn["assistant"] == "Fundamentals look stable."


def test_converse_falls_back_when_auditor_flags_and_regen_still_bad():
    # auditor always flags; narrator keeps returning the same flagged text → fallback to template
    turn = _converse(_SDK(audit_issues=[{"span": "stable", "kind": "unsupported", "why": "no basis"}]))
    assert turn["verification"] == "fallback"
    # template text is deterministic and grounded (no claims here → the no-findings template)
    assert "grounded findings" in turn["assistant"].lower()


def test_converse_no_sdk_is_template():
    turn = converse([], "hi", config=ClientConfig(client_id="c", enabled_sources=frozenset()),
                    registry={}, known_tickers=frozenset(), sdk=None,
                    plan_model="p", narrate_model="n")
    assert turn["verification"] == "template"
