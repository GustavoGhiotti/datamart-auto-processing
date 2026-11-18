from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import pyodbc

from src.domain.interfaces.database_executor import DatabaseRow
from src.infrastructure.config.settings import DatabaseSettings
from src.shared.exceptions import DatabaseExecutionError


class SQLServerExecutor:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings

    async def execute(
        self,
        *,
        query: str,
        parametros: Sequence[Any] = (),
        fetch: bool = False,
        timeout: int = 300,
        autocommit: bool = False,
    ) -> list[DatabaseRow] | int:
        # pyodbc e bloqueante; to_thread evita travar o event loop principal.
        return await asyncio.to_thread(
            self._execute_sync,
            query,
            tuple(parametros),
            fetch,
            timeout,
            autocommit,
        )

    def _execute_sync(
        self,
        query: str,
        parametros: tuple[Any, ...],
        fetch: bool,
        timeout: int,
        autocommit: bool,
    ) -> list[DatabaseRow] | int:
        conexao: pyodbc.Connection | None = None

        try:
            conexao = pyodbc.connect(
                "DRIVER={SQL Server};"
                f"SERVER={self._settings.server};"
                f"DATABASE={self._settings.database};"
                f"UID={self._settings.user};"
                f"PWD={self._settings.password};"
                "TrustServerCertificate=YES;",
                timeout=timeout,
                autocommit=autocommit,
            )

            with conexao.cursor() as cursor:
                cursor.execute(query, *parametros)

                if fetch:
                    colunas = [coluna[0] for coluna in cursor.description]
                    return [
                        dict(zip(colunas, linha, strict=False))
                        for linha in cursor.fetchall()
                    ]

                if not autocommit:
                    conexao.commit()
                return int(cursor.rowcount)

        except pyodbc.Error as error:
            if conexao is not None and not autocommit:
                conexao.rollback()

            raise DatabaseExecutionError(
                f"Erro ao executar query no banco {self._settings.database}: {error}"
            ) from error

        finally:
            if conexao is not None:
                conexao.close()
