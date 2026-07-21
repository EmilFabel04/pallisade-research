from pallisade_core.memo_checks.extract import ExtractedFigure, extract_figures


class _Block:
    def __init__(self, inp):
        self.type = "tool_use"
        self.input = inp


class _Msg:
    def __init__(self, inp):
        self.content = [_Block(inp)]


class FakeSdk:
    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.messages = self

    def create(self, **kwargs):
        return _Msg(self._payloads.pop(0))


def test_extract_returns_structured_figures():
    memo = "Revenue is R42.1bn and margin is 18%."
    sdk = FakeSdk([{"figures": [
        {"claim_text": "Revenue is R42.1bn", "value": "42.1", "unit": "R bn",
         "char_start": 0, "char_end": 18},
        {"claim_text": "margin is 18%", "value": "18", "unit": "%",
         "char_start": 23, "char_end": 36},
    ]}])
    out = extract_figures(memo, sdk=sdk, model="m")
    assert out == [
        ExtractedFigure("Revenue is R42.1bn", "42.1", "R bn", 0, 18),
        ExtractedFigure("margin is 18%", "18", "%", 23, 36),
    ]


def test_extract_handles_no_figures():
    sdk = FakeSdk([{"figures": []}])
    assert extract_figures("No numbers here.", sdk=sdk, model="m") == []
