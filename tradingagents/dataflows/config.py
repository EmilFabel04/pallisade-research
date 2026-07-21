from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from typing import Dict, Optional

import tradingagents.default_config as default_config

# Use default config but allow it to be overridden
_config: Optional[Dict] = None

# Per-run config overrides, scoped to the current execution context (e.g. an
# asyncio task or thread). Keeps concurrent per-org runs from stomping on the
# module-global ``_config`` singleton.
run_config_var: ContextVar[dict | None] = ContextVar("tradingagents_run_config", default=None)


def initialize_config():
    """Initialize the configuration with default values."""
    global _config
    if _config is None:
        _config = deepcopy(default_config.DEFAULT_CONFIG)


def set_config(config: Dict):
    """Update the configuration with custom values.

    Dict-valued keys (e.g. ``data_vendors``) are merged one level deep so a
    partial update like ``{"data_vendors": {"core_stock_apis": "alpha_vantage"}}``
    keeps the other nested keys from the default; scalar keys are replaced.
    """
    global _config
    initialize_config()
    incoming = deepcopy(config)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(_config.get(key), dict):
            _config[key].update(value)
        else:
            _config[key] = value


def get_config() -> Dict:
    """Get the current configuration (per-run overrides applied when set)."""
    if _config is None:
        initialize_config()
    base = deepcopy(_config)
    overrides = run_config_var.get()
    if overrides:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key].update(value)
            else:
                base[key] = value
    return base


@contextmanager
def run_config(overrides: dict):
    """Scope per-run config overrides to the current execution context."""
    token = run_config_var.set(deepcopy(overrides))
    try:
        yield
    finally:
        run_config_var.reset(token)


# Initialize with default config
initialize_config()
