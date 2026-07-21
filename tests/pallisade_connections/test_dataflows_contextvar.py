from __future__ import annotations

import threading

from tradingagents.dataflows.config import get_config, run_config


def test_run_config_scopes_data_vendors():
    base = get_config()["data_vendors"]["core_stock_apis"]
    with run_config({"data_vendors": {"core_stock_apis": "alpha_vantage"}}):
        assert get_config()["data_vendors"]["core_stock_apis"] == "alpha_vantage"
    # restored outside the context
    assert get_config()["data_vendors"]["core_stock_apis"] == base


def test_run_config_var_resets_after_exit():
    from tradingagents.dataflows.config import run_config_var
    assert run_config_var.get() is None
    with run_config({"data_vendors": {"core_stock_apis": "alpha_vantage"}}):
        assert run_config_var.get() is not None
    # context cleanly torn down — no leak to the next run
    assert run_config_var.get() is None


def test_run_config_deepcopies_overrides():
    overrides = {"data_vendors": {"core_stock_apis": "alpha_vantage"}}
    with run_config(overrides):
        # Mutating the caller's dict after entering must not leak into the
        # snapshot stored by run_config (aliasing would otherwise let this
        # mutation change the effective config mid-run).
        overrides["data_vendors"]["core_stock_apis"] = "polygon"
        assert get_config()["data_vendors"]["core_stock_apis"] == "alpha_vantage"

        # Mutating a nested dict returned by get_config() must not affect a
        # subsequent get_config() call either.
        snapshot = get_config()
        snapshot["data_vendors"]["core_stock_apis"] = "yfinance"
        assert get_config()["data_vendors"]["core_stock_apis"] == "alpha_vantage"


def test_run_config_nested_restores_outer():
    default = get_config()["data_vendors"]["core_stock_apis"]
    with run_config({"data_vendors": {"core_stock_apis": "alpha_vantage"}}):
        assert get_config()["data_vendors"]["core_stock_apis"] == "alpha_vantage"
        with run_config({"data_vendors": {"core_stock_apis": "polygon"}}):
            assert get_config()["data_vendors"]["core_stock_apis"] == "polygon"
        # outer value restored after inner block exits
        assert get_config()["data_vendors"]["core_stock_apis"] == "alpha_vantage"
    # process default restored after both blocks exit
    assert get_config()["data_vendors"]["core_stock_apis"] == default


def test_run_config_isolated_between_threads():
    barrier = threading.Barrier(2)
    failures: list[str] = []

    def worker(value: str):
        try:
            with run_config({"data_vendors": {"core_stock_apis": value}}):
                # Wait until both threads are simultaneously inside their
                # own run_config block before asserting isolation.
                barrier.wait(timeout=5)
                actual = get_config()["data_vendors"]["core_stock_apis"]
                if actual != value:
                    failures.append(f"expected {value!r}, got {actual!r}")
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(f"exception for {value!r}: {exc!r}")

    threads = [
        threading.Thread(target=worker, args=("alpha_vantage",)),
        threading.Thread(target=worker, args=("polygon",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not failures, failures
