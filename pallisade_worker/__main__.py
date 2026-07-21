from __future__ import annotations

import logging

from pallisade_worker.handlers.debate import handle_run_debate
from pallisade_worker.handlers.embed import handle_embed
from pallisade_worker.handlers.memo_check import handle_check_memo
from pallisade_worker.handlers.parse import handle_parse
from pallisade_worker.loop import run_forever


def build_handlers() -> dict:
    return {
        "parse_document": handle_parse,
        "embed_document": handle_embed,
        "run_debate": handle_run_debate,
        "check_memo": handle_check_memo,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    from pallisade_core.settings import get_settings
    s = get_settings()
    run_forever(
        handlers=build_handlers(),
        poll_seconds=s.worker_poll_seconds,
        stale_after_seconds=s.worker_heartbeat_seconds * 6,
    )


if __name__ == "__main__":
    main()
