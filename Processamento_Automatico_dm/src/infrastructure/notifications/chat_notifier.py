from __future__ import annotations

import asyncio

from src.domain.interfaces.database_executor import DatabaseExecutor
from src.shared.robot_logger import robot_logger


class ChatNotifier:
    def __init__(self, db: DatabaseExecutor, *, max_attempts: int = 2, retry_delay_seconds: float = 2.0) -> None:
        self._db = db
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    async def send(self, message: str) -> None:
        # O retorno para o chat interno e gravado por procedure no banco Traces.
        query = "EXEC [Traces].[dbo].[Proc_mensagem_chat] ?"

        for attempt in range(1, self._max_attempts + 1):
            try:
                await self._db.execute(
                    query=query,
                    parametros=(message,),
                )
                return
            except Exception as error:
                robot_logger.warning(
                    processo="Notificacao",
                    etapa="enviar_chat_google",
                    mensagem=(
                        "Falha ao enviar notificacao para o chat interno. "
                        "A rotina SQL Traces.dbo.Proc_mensagem_chat aciona Google_Message."
                    ),
                    query=query,
                    detalhes={
                        "tentativa": attempt,
                        "max_tentativas": self._max_attempts,
                        "erro": str(error),
                        "rotina_relacionada": "Google_Message",
                    },
                )

                if attempt == self._max_attempts:
                    raise

                await asyncio.sleep(self._retry_delay_seconds)
