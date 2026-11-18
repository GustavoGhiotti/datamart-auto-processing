from __future__ import annotations

from src.domain.interfaces.database_executor import DatabaseExecutor, DatabaseRow
from src.domain.models.cedente import Cedente


class CedenteQueries:
    def __init__(self, *, db_65_easycollector: DatabaseExecutor) -> None:
        self._db_65_easycollector = db_65_easycollector

    async def listar_dm_dividas(self) -> list[DatabaseRow]:
        resultado = await self._db_65_easycollector.execute(
            query="""
                SELECT
                    ID_CEDENTE,
                    CARTEIRA,
                    COUNT(*) AS QTD_CONTRATOS,
                    MAX(DT_HR_ATUALIZACAO) AS DT_HR_ATUALIZACAO,
                    CASE
                        WHEN MAX(DT_ATUALIZACAO) = CAST(GETDATE() AS DATE)
                        THEN 1
                        ELSE 0
                    END AS FLAG
                FROM easycollector.dm.TB_DIVIDAS WITH(NOLOCK)
                WHERE STATUS_ATUAL = 1
                GROUP BY ID_CEDENTE, CARTEIRA
            """,
            fetch=True,
        )

        return as_rows(resultado)


def filtrar_cedentes(rows: list[DatabaseRow], ids_validos: set[int]) -> list[Cedente]:
    cedentes = [
        Cedente(
            id_cedente=int(row["ID_CEDENTE"]),
            carteira=str(row["CARTEIRA"]),
        )
        for row in rows
        if int(row["ID_CEDENTE"]) in ids_validos
    ]

    return sorted(cedentes, key=lambda item: item.id_cedente)


def as_rows(resultado: list[DatabaseRow] | int) -> list[DatabaseRow]:
    if isinstance(resultado, list):
        return resultado

    return []

