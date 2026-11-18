from __future__ import annotations

from datetime import datetime

from src.domain.interfaces.dm_repository import DmRepository
from src.domain.interfaces.notifier import Notifier
from src.shared.html import sanitize_html_text
from src.shared.robot_logger import robot_logger


class TelefoneService:
    def __init__(self, *, repository: DmRepository, notifier: Notifier) -> None:
        self._repository = repository
        self._notifier = notifier

    async def executar_um(self) -> bool:
        # Reaproveita a mesma fila de transferencia para decidir quando atualizar telefones.
        fila_timer = robot_logger.start(processo="Telefones", etapa="listar_cedentes_para_telefones")
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
            processo="Telefones",
            etapa="atualizar_telefones",
            carteira=cedente.carteira,
            detalhes={"id_cedente": cedente.id_cedente},
        )

        await self._notifier.send(
            f"<b>Iniciando atualizacao de telefones apos transferencia</b>\n"
            f"Cedente: <b>{cedente.id_cedente}</b>\n"
            f"Carteira: <b>{sanitize_html_text(cedente.carteira)}</b>\n"
            f"Inicio: {inicio.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        try:
            procedure_timer = robot_logger.start(
                processo="Telefones",
                etapa="executar_proc_telefones_pos_carga",
                carteira=cedente.carteira,
                query="EXEC Easycollector.[dm].[Proc_Dm_Tb_Telefones_Pos_Carga]",
                detalhes={"id_cedente": cedente.id_cedente},
            )
            try:
                await self._repository.atualizar_telefones()
                robot_logger.success(procedure_timer)
            except Exception as error:
                robot_logger.error(
                    procedure_timer,
                    error=error,
                    query="EXEC Easycollector.[dm].[Proc_Dm_Tb_Telefones_Pos_Carga]",
                    detalhes={"id_cedente": cedente.id_cedente},
                )
                raise

            duracao = str(datetime.now() - inicio).split(".")[0]
            robot_logger.success(timer, quantidade_registros=1)
            await self._notifier.send(
                f"<b>Atualizacao dos telefones finalizada</b>\n"
                f"Duracao: <b>{duracao}</b>"
            )
        except Exception as error:
            robot_logger.error(timer, error=error, detalhes={"id_cedente": cedente.id_cedente})
            await self._notifier.send(
                f"<b>Erro na atualizacao de telefones</b>\n"
                f"Erro: <code>{sanitize_html_text(error)}</code>"
            )

        return True
