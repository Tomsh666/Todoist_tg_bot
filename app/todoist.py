from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp



class TodoistError(Exception):
    """Base class for Todoist failures."""


class TodoistUserError(TodoistError):
    """Todoist rejected the submitted task as invalid user input."""


class TodoistSystemError(TodoistError):
    """Todoist or the network could not complete the request."""


@dataclass(frozen=True, slots=True)
class TodoistClient:
    api_token: str
    base_url: str = "https://api.todoist.com/api/v1"
    attempts: int = 3
    budget_seconds: float = 10.0
    request_timeout_seconds: float = 5.0

    async def check_connection(self) -> None:
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        headers = {"Authorization": f"Bearer {self.api_token}"}
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/projects?limit=1", headers=headers) as response:
                    if response.status in (401, 403):
                        raise TodoistSystemError("todoist_authentication_failed")
                    if response.status >= 400:
                        raise TodoistSystemError(f"todoist_healthcheck_{response.status}")
        except TodoistSystemError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise TodoistSystemError("todoist_healthcheck_unreachable") from exc

    async def create_task(self, text: str, username: str, request_id: str) -> None:
        payload = {"text": f"@{username} {text}"}
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
        }
        deadline = time.monotonic() + self.budget_seconds
        retryable_statuses = {408, 429, 500, 502, 503, 504}
        last_error: Exception | None = None

        for attempt in range(self.attempts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            timeout = aiohttp.ClientTimeout(total=min(self.request_timeout_seconds, remaining))
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(f"{self.base_url}/tasks/quick", json=payload, headers=headers) as response:
                        if 200 <= response.status < 300:
                            return
                        if response.status == 400:
                            raise TodoistUserError("todoist_rejected_task")
                        if response.status not in retryable_statuses:
                            raise TodoistSystemError(f"todoist_http_{response.status}")
                        retry_after = response.headers.get("Retry-After")
                        try:
                            delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                        except ValueError:
                            delay = 0.5 * (2**attempt)
                        last_error = TodoistSystemError(f"todoist_retryable_http_{response.status}")
            except TodoistUserError:
                raise
            except TodoistSystemError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                delay = 0.5 * (2**attempt)

            if attempt + 1 < self.attempts:
                await asyncio.sleep(min(delay, max(0.0, deadline - time.monotonic())))

        raise TodoistSystemError("todoist_request_failed") from last_error

