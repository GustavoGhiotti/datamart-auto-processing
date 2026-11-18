from __future__ import annotations

from src.domain.interfaces.database_executor import DatabaseExecutor
from src.domain.models.cedente import Cedente
from src.infrastructure.repositories.shared_dm_queries import CedenteQueries, as_rows, filtrar_cedentes


class TransferenciaRepository:
    def __init__(
        self,
        *,
        db_71_dashpulse: DatabaseExecutor,
        db_71_report: DatabaseExecutor,
        cedente_queries: CedenteQueries,
        db_72_dm: DatabaseExecutor,
    ) -> None:
        self._db_71_dashpulse = db_71_dashpulse
        self._db_71_report = db_71_report
        self._cedente_queries = cedente_queries
        self._db_72_dm = db_72_dm

    async def listar_cedentes_para_transferir(self) -> list[Cedente]:
        cedentes_view = await self._buscar_ids_cedentes_transferencia()
        dados_dm = await self._cedente_queries.listar_dm_dividas()
        return filtrar_cedentes(dados_dm, cedentes_view)

    async def transferir_carteira(self, id_cedente: int) -> None:
        await self._db_71_report.execute(
            query="EXEC DB_REPORT.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA ?",
            parametros=(id_cedente,),
            fetch=False,
            timeout=600,
        )

    async def transferir_carteira_72(self, id_cedente: int) -> None:
        await self._db_72_dm.execute(
            query="EXEC db_dm.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA ?",
            parametros=(id_cedente,),
            fetch=False,
            timeout=600,
        )

    async def marcar_atualizacao_espelho(self, id_cedente: int) -> None:
        await self._db_71_dashpulse.execute(
            query="""
                UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA
                SET Atualizacao_espelho = GETDATE()
                WHERE ID_CEDENTE = ?
            """,
            parametros=(id_cedente,),
            fetch=False,
        )

    async def _buscar_ids_cedentes_transferencia(self) -> set[int]:
        resultado = await self._db_71_dashpulse.execute(
            query="""
                SELECT ID_CEDENTE
                FROM (
                    SELECT *
                    FROM DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA WITH(NOLOCK)
                    WHERE Atualizacao_prod > Atualizacao_Espelho
                ) A
            """,
            fetch=True,
        )

        return {int(row["ID_CEDENTE"]) for row in as_rows(resultado)}

