from __future__ import annotations

from collections.abc import Sequence

from src.domain.interfaces.notifier import Notifier


class MultiNotifier:
    def __init__(self, notifiers: Sequence[Notifier]) -> None:
        self._notifiers = list(notifiers)

    async def send(self, message: str) -> None:
        for notifier in self._notifiers:
            await notifier.send(message)

