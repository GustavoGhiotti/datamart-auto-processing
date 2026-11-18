from __future__ import annotations

from typing import Protocol

from src.domain.models.cedente import Cedente


class DmRepository(Protocol):
    async def atualizar_relatorio_carga(self) -> None:
        ...

    async def listar_cedentes_para_processar(self) -> list[Cedente]:
        ...

    async def listar_cedentes_para_transferir(self) -> list[Cedente]:
        ...

    async def processar_carteira(self, id_cedente: int) -> None:
        ...

    async def marcar_atualizacao_prod(self, id_cedente: int) -> None:
        ...

    async def transferir_carteira(self, id_cedente: int) -> None:
        ...

    async def transferir_carteira_72(self, id_cedente: int) -> None:
        ...

    async def marcar_atualizacao_espelho(self, id_cedente: int) -> None:
        ...

    async def atualizar_telefones(self) -> None:
        ...

    async def listar_cedentes_mailing(self) -> list[int]:
        ...

    async def gerar_mailing(self, id_cedente: int) -> bool:
        ...

    async def gerar_mailing_diario(self) -> int:
        ...

    async def listar_cedentes_mailing_diario(self) -> list[int]:
        ...

    async def listar_procedures_mailing_diario(self) -> list[str]:
        ...

    async def marcar_atualizacao_mailing(self, id_cedente: int) -> None:
        ...

    async def registrar_heartbeat(self) -> None:
        ...
