from __future__ import annotations

from typing import Protocol


class Notifier(Protocol):
    async def send(self, message: str) -> None:
        ...

