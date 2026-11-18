from __future__ import annotations

from src.domain.interfaces.dm_repository import DmRepository


class HeartbeatService:
    def __init__(self, *, repository: DmRepository) -> None:
        self._repository = repository

    async def executar(self) -> None:
        await self._repository.registrar_heartbeat()

