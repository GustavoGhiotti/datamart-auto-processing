from __future__ import annotations

from src.domain.interfaces.database_executor import DatabaseExecutor
from src.domain.models.cedente import Cedente
from src.infrastructure.repositories.heartbeat_repository import HeartbeatRepository
from src.infrastructure.repositories.mailing_repository import MailingRepository
from src.infrastructure.repositories.processo_dm_repository import ProcessoDmRepository
from src.infrastructure.repositories.shared_dm_queries import CedenteQueries
from src.infrastructure.repositories.telefone_repository import TelefoneRepository
from src.infrastructure.repositories.transferencia_repository import TransferenciaRepository


class SQLDmRepository:
    """Fachada compativel com os services existentes.

    Os metodos continuam iguais para preservar os pontos de chamada atuais,
    mas cada responsabilidade fica delegada para um repositorio especifico.
    """

    def __init__(
        self,
        *,
        db_65_easycollector: DatabaseExecutor,
        db_71_dashpulse: DatabaseExecutor,
        db_71_report: DatabaseExecutor,
        db_71_traces: DatabaseExecutor,
        db_71_planejamento: DatabaseExecutor,
        db_72_dm: DatabaseExecutor,
    ) -> None:
        cedente_queries = CedenteQueries(db_65_easycollector=db_65_easycollector)
        self._processo_dm = ProcessoDmRepository(
            db_65_easycollector=db_65_easycollector,
            db_71_dashpulse=db_71_dashpulse,
            cedente_queries=cedente_queries,
        )
        self._transferencia = TransferenciaRepository(
            db_71_dashpulse=db_71_dashpulse,
            db_71_report=db_71_report,
            cedente_queries=cedente_queries,
            db_72_dm=db_72_dm,
        )
        self._telefone = TelefoneRepository(db_65_easycollector=db_65_easycollector)
        self._mailing = MailingRepository(
            db_71_dashpulse=db_71_dashpulse,
            db_71_planejamento=db_71_planejamento,
        )
        self._heartbeat = HeartbeatRepository(db_71_traces=db_71_traces)

    async def atualizar_relatorio_carga(self) -> None:
        await self._processo_dm.atualizar_relatorio_carga()

    async def listar_cedentes_para_processar(self) -> list[Cedente]:
        return await self._processo_dm.listar_cedentes_para_processar()

    async def processar_carteira(self, id_cedente: int) -> None:
        await self._processo_dm.processar_carteira(id_cedente)

    async def marcar_atualizacao_prod(self, id_cedente: int) -> None:
        await self._processo_dm.marcar_atualizacao_prod(id_cedente)

    async def listar_cedentes_para_transferir(self) -> list[Cedente]:
        return await self._transferencia.listar_cedentes_para_transferir()

    async def transferir_carteira(self, id_cedente: int) -> None:
        await self._transferencia.transferir_carteira(id_cedente)

    async def transferir_carteira_72(self, id_cedente: int) -> None:
        await self._transferencia.transferir_carteira_72(id_cedente)

    async def marcar_atualizacao_espelho(self, id_cedente: int) -> None:
        await self._transferencia.marcar_atualizacao_espelho(id_cedente)

    async def atualizar_telefones(self) -> None:
        await self._telefone.atualizar_telefones()

    async def listar_cedentes_mailing(self) -> list[int]:
        return await self._mailing.listar_cedentes_mailing()

    async def gerar_mailing(self, id_cedente: int) -> bool:
        return await self._mailing.gerar_mailing(id_cedente)

    async def gerar_mailing_diario(self) -> int:
        return await self._mailing.gerar_mailing_diario()

    async def listar_cedentes_mailing_diario(self) -> list[int]:
        return await self._mailing.listar_cedentes_mailing_diario()

    async def listar_procedures_mailing_diario(self) -> list[str]:
        return await self._mailing.listar_procedures_mailing_diario()

    async def marcar_atualizacao_mailing(self, id_cedente: int) -> None:
        await self._mailing.marcar_atualizacao_mailing(id_cedente)

    async def registrar_heartbeat(self) -> None:
        await self._heartbeat.registrar_heartbeat()
