from __future__ import annotations

import asyncio
import os
import time


async def heartbeat_loop(path: str, interval_seconds: float = 10.0) -> None:
    while True:
        temporary_path = f"{path}.tmp"
        with open(temporary_path, "w", encoding="ascii") as heartbeat_file:
            heartbeat_file.write(str(time.time()))
        os.replace(temporary_path, path)
        await asyncio.sleep(interval_seconds)

