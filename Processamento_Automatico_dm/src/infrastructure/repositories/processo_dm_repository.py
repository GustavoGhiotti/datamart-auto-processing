from __future__ import annotations

from src.domain.interfaces.database_executor import DatabaseExecutor
from src.domain.models.cedente import Cedente
from src.infrastructure.repositories.shared_dm_queries import CedenteQueries, as_rows, filtrar_cedentes


class ProcessoDmRepository:
    def __init__(
        self,
        *,
        db_65_easycollector: DatabaseExecutor,
        db_71_dashpulse: DatabaseExecutor,
        cedente_queries: CedenteQueries,
    ) -> None:
        self._db_65_easycollector = db_65_easycollector
        self._db_71_dashpulse = db_71_dashpulse
        self._cedente_queries = cedente_queries

    async def atualizar_relatorio_carga(self) -> None:
        await self._db_65_easycollector.execute(
            query="EXEC easycollector.dbo.PRC_MIS_GERA_RELATORIO_CARGAS",
            fetch=False,
        )

    async def listar_cedentes_para_processar(self) -> list[Cedente]:
        cedentes_view = await self._buscar_ids_cedentes_processamento()
        dados_dm = await self._cedente_queries.listar_dm_dividas()
        return filtrar_cedentes(dados_dm, cedentes_view)

    async def processar_carteira(self, id_cedente: int) -> None:
        await self._db_65_easycollector.execute(
            query="EXEC dm.PROC_DATAMART_TB_DIVIDAS ?",
            parametros=(id_cedente,),
            fetch=False,
            timeout=600,
        )

    async def marcar_atualizacao_prod(self, id_cedente: int) -> None:
        await self._db_71_dashpulse.execute(
            query="""
                UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA
                SET Atualizacao_prod = GETDATE()
                WHERE ID_CEDENTE = ?
            """,
            parametros=(id_cedente,),
            fetch=False,
        )

    async def _buscar_ids_cedentes_processamento(self) -> set[int]:
        resultado = await self._db_71_dashpulse.execute(
            query="""
                SELECT ID_CEDENTE
                FROM DB_DASHPULSE.dbo.VIEW_CONTROLE_SCC WITH(NOLOCK)
                WHERE ATUALIZACAO_EXEC = 0
            """,
            fetch=True,
        )

        return {int(row["ID_CEDENTE"]) for row in as_rows(resultado)}

