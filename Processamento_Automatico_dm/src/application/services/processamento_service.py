from __future__ import annotations

from datetime import datetime

from src.domain.interfaces.dm_repository import DmRepository
from src.domain.interfaces.notifier import Notifier
from src.shared.html import sanitize_html_text
from src.shared.robot_logger import robot_logger


class ProcessamentoService:
    def __init__(self, *, repository: DmRepository, notifier: Notifier) -> None:
        self._repository = repository
        self._notifier = notifier
        self.banco = "65"

    async def atualizar_relatorio_carga(self) -> None:
        timer = robot_logger.start(
            processo="DM",
            etapa="atualizar_relatorio_carga",
            query="EXEC easycollector.dbo.PRC_MIS_GERA_RELATORIO_CARGAS",
        )
        try:
            await self._repository.atualizar_relatorio_carga()
            robot_logger.success(timer)
        except Exception as error:
            robot_logger.error(
                timer,
                error=error,
                query="EXEC easycollector.dbo.PRC_MIS_GERA_RELATORIO_CARGAS",
            )
            raise

    async def executar_um(self) -> bool:
        # A fila retorna cedentes elegiveis; o robo trata um por ciclo.
        fila_timer = robot_logger.start(processo="DM", etapa="listar_cedentes_para_processar")
        try:
            cedentes = await self._repository.listar_cedentes_para_processar()
            robot_logger.success(fila_timer, quantidade_registros=len(cedentes))
        except Exception as error:
            robot_logger.error(fila_timer, error=error)
            raise
        if not cedentes:
            return False

        cedente = cedentes[0]
        inicio = datetime.now()
        timer = robot_logger.start(
            processo="DM",
            etapa="processar_carteira",
            carteira=cedente.carteira,
            detalhes={"id_cedente": cedente.id_cedente, "banco": self.banco},
        )

        await self._notifier.send(
            f"🚀 <b>Iniciando processamento</b>\n"
            f"🏦 Banco: <b>{self.banco}</b>\n"
            f"👤 Cedente: <b>{cedente.id_cedente}</b>\n"
            f"💼 Carteira: <b>{sanitize_html_text(cedente.carteira)}</b>\n"
            f"🕒 Inicio: <b>{inicio.strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )

        try:
            # Ordem do fluxo: procedure principal, status de producao e relatorio.
            procedure_timer = robot_logger.start(
                processo="DM",
                etapa="executar_proc_datamart_dividas",
                carteira=cedente.carteira,
                query="EXEC dm.PROC_DATAMART_TB_DIVIDAS ?",
                detalhes={"id_cedente": cedente.id_cedente},
            )
            try:
                await self._repository.processar_carteira(cedente.id_cedente)
                robot_logger.success(procedure_timer)
            except Exception as error:
                robot_logger.error(
                    procedure_timer,
                    error=error,
                    query="EXEC dm.PROC_DATAMART_TB_DIVIDAS ?",
                    detalhes={"id_cedente": cedente.id_cedente},
                )
                raise

            status_timer = robot_logger.start(
                processo="DM",
                etapa="marcar_atualizacao_prod",
                carteira=cedente.carteira,
                query="UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA SET Atualizacao_prod = GETDATE() WHERE ID_CEDENTE = ?",
                detalhes={"id_cedente": cedente.id_cedente},
            )
            try:
                await self._repository.marcar_atualizacao_prod(cedente.id_cedente)
                robot_logger.success(status_timer)
            except Exception as error:
                robot_logger.error(
                    status_timer,
                    error=error,
                    query="UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA SET Atualizacao_prod = GETDATE() WHERE ID_CEDENTE = ?",
                    detalhes={"id_cedente": cedente.id_cedente},
                )
                raise

            await self._repository.atualizar_relatorio_carga()

            duracao = str(datetime.now() - inicio).split(".")[0]
            robot_logger.success(timer, quantidade_registros=1)

            await self._notifier.send(
                f"✅ <b>Processamento finalizado</b>\n"
                f"🏦 Banco: <b>{self.banco}</b>\n"
                f"👤 Cedente: <b>{cedente.id_cedente}</b>\n"
                f"💼 Carteira: <b>{sanitize_html_text(cedente.carteira)}</b>\n"
                f"⏱️ Duracao: <b>{duracao}</b>"
            )

        except Exception as error:
            robot_logger.error(timer, error=error, detalhes={"id_cedente": cedente.id_cedente})
            await self._notifier.send(
                f"❌ <b>Erro no processamento</b>\n"
                f"🏦 Banco: <b>{self.banco}</b>\n"
                f"👤 Cedente: <b>{cedente.id_cedente}</b>\n"
                f"💼 Carteira: <b>{sanitize_html_text(cedente.carteira)}</b>\n"
                f"⚠️ Erro: <code>{sanitize_html_text(error)}</code>"
            )

        return True
