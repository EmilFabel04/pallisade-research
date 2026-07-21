from __future__ import annotations

from typing import Any


def build_memo_sdk() -> Any:
    import anthropic
    from pallisade_core.settings import get_settings
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
