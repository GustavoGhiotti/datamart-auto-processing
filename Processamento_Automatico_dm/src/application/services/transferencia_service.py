from __future__ import annotations

from datetime import datetime

from src.domain.interfaces.dm_repository import DmRepository
from src.domain.interfaces.notifier import Notifier
from src.shared.html import sanitize_html_text
from src.shared.robot_logger import robot_logger


class TransferenciaService:
    def __init__(
        self,
        *,
        repository: DmRepository,
        telegram_notifier: Notifier,
        chat_notifier: Notifier,
    ) -> None:
        self._repository = repository
        self.banco = "71 e 72"
        self._telegram_notifier = telegram_notifier
        self._chat_notifier = chat_notifier

    async def executar_um(self) -> bool:
        # A transferencia usa a fila de cedentes com producao mais recente que espelho.
        fila_timer = robot_logger.start(processo="Transferencia", etapa="listar_cedentes_para_transferir")
        try:
            cedentes = await self._repository.listar_cedentes_para_transferir()
            robot_logger.success(fila_timer, quantidade_registros=len(cedentes))
        except Exception as error:
            robot_logger.error(fila_timer, error=error)
            raise
        if not cedentes:
            return False

        cedente = cedentes[0]
        inicio = datetime.now()
        timer = robot_logger.start(
            processo="Transferencia",
            etapa="transferir_carteira",
            carteira=cedente.carteira,
            detalhes={"id_cedente": cedente.id_cedente, "banco": self.banco},
        )

        await self._telegram_notifier.send(
            f"🚚 <b>Iniciando transferencia 🏦 Banco {self.banco}</b>\n"
            f"Cedente: <b>{cedente.id_cedente}</b>\n"
            f"Carteira: <b>{sanitize_html_text(cedente.carteira)}</b>\n"
            f"Inicio: {inicio.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        await self._chat_notifier.send(
            f"Carteira: {cedente.carteira}, Inicio: {inicio.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        try:
            # A procedure transfere a carteira no 71; depois repete no 72 e marca o espelho.
            procedure_timer_71 = robot_logger.start(
                processo="Transferencia",
                etapa="executar_proc_transferencia_carteira_71",
                carteira=cedente.carteira,
                query="EXEC DB_REPORT.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA ?",
                detalhes={"id_cedente": cedente.id_cedente, "banco": "71"},
            )
            try:
                await self._repository.transferir_carteira(cedente.id_cedente)
                robot_logger.success(procedure_timer_71)
            except Exception as error:
                robot_logger.error(
                    procedure_timer_71,
                    error=error,
                    query="EXEC DB_REPORT.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA ?",
                    detalhes={"id_cedente": cedente.id_cedente, "banco": "71"},
                )
                raise

            # Mesma procedure, servidor 72 (banco db_dm).
            procedure_timer_72 = robot_logger.start(
                processo="Transferencia",
                etapa="executar_proc_transferencia_carteira_72",
                carteira=cedente.carteira,
                query="EXEC db_dm.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA ?",
                detalhes={"id_cedente": cedente.id_cedente, "banco": "72"},
            )
            try:
                await self._repository.transferir_carteira_72(cedente.id_cedente)
                robot_logger.success(procedure_timer_72)
            except Exception as error:
                robot_logger.error(
                    procedure_timer_72,
                    error=error,
                    query="EXEC db_dm.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA ?",
                    detalhes={"id_cedente": cedente.id_cedente, "banco": "72"},
                )
                raise

            status_timer = robot_logger.start(
                processo="Transferencia",
                etapa="marcar_atualizacao_espelho",
                carteira=cedente.carteira,
                query="UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA SET Atualizacao_espelho = GETDATE() WHERE ID_CEDENTE = ?",
                detalhes={"id_cedente": cedente.id_cedente},
            )
            try:
                await self._repository.marcar_atualizacao_espelho(cedente.id_cedente)
                robot_logger.success(status_timer)
            except Exception as error:
                robot_logger.error(
                    status_timer,
                    error=error,
                    query="UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA SET Atualizacao_espelho = GETDATE() WHERE ID_CEDENTE = ?",
                    detalhes={"id_cedente": cedente.id_cedente},
                )
                raise

            duracao = str(datetime.now() - inicio).split(".")[0]
            robot_logger.success(timer, quantidade_registros=1)
            await self._telegram_notifier.send(
                f"<b>Transferencia finalizada</b>\n"
                f"Cedente: <b>{cedente.id_cedente}</b>\n"
                f"Carteira: <b>{sanitize_html_text(cedente.carteira)}</b>\n"
                f"Duracao: <b>{duracao}</b>"
            )
            await self._chat_notifier.send(f"Carteira: {cedente.carteira}, Duracao: {duracao}")
        except Exception as error:
            robot_logger.error(timer, error=error, detalhes={"id_cedente": cedente.id_cedente})
            await self._telegram_notifier.send(
                f"<b>Erro na transferencia</b>\n"
                f"Cedente: <b>{cedente.id_cedente}</b>\n"
                f"Carteira: <b>{sanitize_html_text(cedente.carteira)}</b>\n"
                f"Erro: <code>{sanitize_html_text(error)}</code>"
            )
            await self._chat_notifier.send(f"Erro na transferencia da {cedente.carteira}")

        return True
