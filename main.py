from __future__ import annotations

import asyncio
import logging
import sys

from app.bot import run
from app.config import ConfigError, Settings
from app.heartbeat import heartbeat_loop


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


def main() -> None:
    configure_logging()
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        logging.getLogger(__name__).error("invalid_configuration: %s", exc)
        raise SystemExit(2) from exc
    asyncio.run(run(settings, heartbeat_loop))


if __name__ == "__main__":
    main()

