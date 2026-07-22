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


class _MetricSDK:
    """Like `_SDK`, but the plan targets a ticker + "metrics" capability so the
    fake fundamentals source below fires and a real derived record flows
    through the pipeline. Narrator returns the same fixed text on every call
    (including regeneration retries), so a flagged draft can never "fix
    itself" — it either passes immediately or exhausts retries into fallback,
    same shape as `_SDK`/`test_converse_falls_back_...` above."""
    def __init__(self, narr_text, audit_issues=()):
        self._narr_text = narr_text
        self._audit_issues = list(audit_issues)
        self.messages = self

    def create(self, **kw):
        tools = kw.get("tools") or []
        names = {t["name"] for t in tools}
        if kw.get("tool_choice", {}).get("name") == "plan_research":
            return type("M", (), {"content": [_Block(type="tool_use",
                input={"ticker": "AAPL", "standalone_question": "has revenue grown?",
                       "capabilities": ["metrics"]})]})()
        if "report_issues" in names:
            return type("M", (), {"content": [_Block(type="tool_use",
                input={"issues": self._audit_issues})]})()
        return type("M", (), {"content": [_Block(type="text", text=self._narr_text)]})()


def test_converse_verifies_correct_derived_metric_and_catches_tampered():
    from datetime import date

    from pallisade_research.metrics.compute import yoy
    from pallisade_research.models import Provenance, Record
    from pallisade_research.sources.base import CAP_METRICS

    series_points = ((date(2024, 12, 31), 100.0), (date(2025, 12, 31), 120.0))
    true_yoy = round(yoy(series_points), 2)  # 20.0

    class FakeFundamentals:
        source = "eodhd_fundamentals"
        tier = 3
        capabilities = frozenset({CAP_METRICS})

        def fetch(self, query):
            return [Record(id="s1", capability=CAP_METRICS, key="metrics.revenue.series",
                           value=series_points,
                           provenance=Provenance(source="eodhd_fundamentals", locator="", as_of=None),
                           evidence_only=True)]

    registry = {"eodhd_fundamentals": FakeFundamentals()}
    config = ClientConfig(client_id="c", enabled_sources=frozenset({"eodhd_fundamentals"}))

    # A narrator that states the TRUE derived value -> verified.
    good_sdk = _MetricSDK(narr_text=f"Revenue grew {true_yoy:g}% year on year.")
    out = converse([], "has AAPL revenue grown?", config=config, registry=registry,
                   known_tickers=frozenset({"AAPL"}), sdk=good_sdk,
                   plan_model="m", narrate_model="m")
    assert out["verification"] in ("verified", "regenerated")
    assert f"{true_yoy:g}" in out["assistant"]

    # A narrator that fabricates a different growth number -> unsupported -> fallback.
    bad_sdk = _MetricSDK(narr_text="Revenue grew 87% year on year.")
    out2 = converse([], "has AAPL revenue grown?", config=config, registry=registry,
                    known_tickers=frozenset({"AAPL"}), sdk=bad_sdk,
                    plan_model="m", narrate_model="m")
    assert out2["verification"] == "fallback"
    assert "87%" not in out2["assistant"]
