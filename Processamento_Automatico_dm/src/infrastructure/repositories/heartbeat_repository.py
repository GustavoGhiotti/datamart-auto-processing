from __future__ import annotations

from src.domain.interfaces.database_executor import DatabaseExecutor


class HeartbeatRepository:
    def __init__(self, *, db_71_traces: DatabaseExecutor) -> None:
        self._db_71_traces = db_71_traces

    async def registrar_heartbeat(self) -> None:
        await self._db_71_traces.execute(
            query="""
                UPDATE traces.dbo.TB_PROCESSOS_DADOS
                SET   DT_ATUALIZACAO    = CAST(GETDATE() AS DATE)
                    , DT_HR_ATUALIZACAO = GETDATE()
                    , Status            = 1
                WHERE ID_PROCESSO = 2
            """,
            fetch=False,
        )

