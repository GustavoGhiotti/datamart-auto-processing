from __future__ import annotations

from src.domain.interfaces.notifier import Notifier
from src.shared.robot_logger import robot_logger


class SafeNotifier:
    def __init__(self, notifier: Notifier, *, name: str) -> None:
        self._notifier = notifier
        self._name = name

    async def send(self, message: str) -> None:
        try:
            await self._notifier.send(message)
        except Exception as error:
            robot_logger.warning(
                processo="Notificacao",
                etapa=f"enviar_{self._name}",
                mensagem="Falha isolada no envio de notificacao. Fluxo principal nao sera interrompido.",
                detalhes={"canal": self._name, "erro": str(error)},
            )
            print(f"[AVISO_NOTIFICACAO] Falha ao enviar via {self._name}: {error}")
