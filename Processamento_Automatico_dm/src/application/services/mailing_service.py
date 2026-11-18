from __future__ import annotations

from src.domain.interfaces.dm_repository import DmRepository
from src.domain.interfaces.notifier import Notifier
from src.shared.html import sanitize_html_text
from src.shared.robot_logger import robot_logger


class MailingService:
    def __init__(self, *, repository: DmRepository, notifier: Notifier) -> None:
        self._repository = repository
        self._notifier = notifier

    async def executar_diario(self) -> int:
        timer = robot_logger.start(
            processo="Mailing",
            etapa="gerar_mailing_diario",
            carteira="diario",
        )

        try:
            procedures = await self._repository.listar_procedures_mailing_diario()
            if not procedures:
                robot_logger.warning_from_timer(
                    timer,
                    mensagem="Mailing diario nao possui procedures para executar.",
                )
                return 0

            total_processado = await self._repository.gerar_mailing_diario()
            cedentes = await self._repository.listar_cedentes_mailing_diario()
            robot_logger.success(
                timer,
                quantidade_registros=total_processado,
                detalhes={
                    "cedentes_considerados": cedentes,
                    "total_procedures_mapeadas": len(procedures),
                },
            )
            await self._notifier.send(
                f"<b>Mailing diario finalizado</b>\n"
                f"Procedures executadas com sucesso: <b>{total_processado}</b>"
            )
            return total_processado
        except Exception as error:
            robot_logger.error(timer, error=error)
            await self._notifier.send(
                f"<b>Erro no mailing diario</b>\n"
                f"Erro: <code>{sanitize_html_text(error)}</code>"
            )
            raise

    async def executar_pendentes(self) -> int:
        # Diferente dos outros fluxos, mailing percorre todos os pendentes do ciclo.
        fila_timer = robot_logger.start(processo="Mailing", etapa="listar_cedentes_mailing")
        try:
            cedentes = await self._repository.listar_cedentes_mailing()
            robot_logger.success(fila_timer, quantidade_registros=len(cedentes))
        except Exception as error:
            robot_logger.error(fila_timer, error=error)
            raise
        total_processado = 0

        for id_cedente in cedentes:
            timer = robot_logger.start(
                processo="Mailing",
                etapa="gerar_mailing_cedente",
                carteira=id_cedente,
                detalhes={"id_cedente": id_cedente},
            )
            try:
                gerou_mailing = await self._repository.gerar_mailing(id_cedente)
                if not gerou_mailing:
                    robot_logger.warning_from_timer(
                        timer,
                        mensagem="Cedente pendente nao possui procedure de mailing mapeada.",
                        detalhes={"id_cedente": id_cedente},
                    )
                    continue

                status_timer = robot_logger.start(
                    processo="Mailing",
                    etapa="marcar_atualizacao_mailing",
                    carteira=id_cedente,
                    query="UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA SET Atualizacao_mailing = GETDATE() WHERE ID_CEDENTE = ?",
                    detalhes={"id_cedente": id_cedente},
                )
                try:
                    await self._repository.marcar_atualizacao_mailing(id_cedente)
                    robot_logger.success(status_timer)
                except Exception as error:
                    robot_logger.error(
                        status_timer,
                        error=error,
                        query="UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA SET Atualizacao_mailing = GETDATE() WHERE ID_CEDENTE = ?",
                        detalhes={"id_cedente": id_cedente},
                    )
                    raise
                robot_logger.success(timer, quantidade_registros=1)
                await self._notifier.send(
                    f"<b>Mailing gerado com sucesso</b>\n"
                    f"Cedente: <b>{id_cedente}</b>"
                )
                total_processado += 1
            except Exception as error:
                robot_logger.error(timer, error=error, detalhes={"id_cedente": id_cedente})
                await self._notifier.send(
                    f"<b>Erro ao gerar mailing</b>\n"
                    f"Cedente: <b>{id_cedente}</b>\n"
                    f"Erro: <code>{sanitize_html_text(error)}</code>"
                )

        return total_processado
