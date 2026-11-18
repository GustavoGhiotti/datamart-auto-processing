from __future__ import annotations

from src.domain.interfaces.database_executor import DatabaseExecutor


class TelefoneRepository:
    def __init__(self, *, db_65_easycollector: DatabaseExecutor) -> None:
        self._db_65_easycollector = db_65_easycollector

    async def atualizar_telefones(self) -> None:
        await self._db_65_easycollector.execute(
            query="EXEC Easycollector.[dm].[Proc_Dm_Tb_Telefones_Pos_Carga]",
            fetch=False,
            timeout=600,
        )

