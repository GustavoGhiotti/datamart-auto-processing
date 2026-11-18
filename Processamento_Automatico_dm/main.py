from __future__ import annotations

import asyncio

from src.infrastructure.config.factories import criar_servicos
from src.infrastructure.config.settings import obter_runtime_settings
from src.runners.processamento_dm import executar_loops


async def main() -> None:
    # Ponto de entrada: monta dependencias e entrega os servicos para os loops.
    (
        processamento_service,
        transferencia_service,
        mailing_service,
        telefone_service,
        heartbeat_service,
    ) = criar_servicos()

    await executar_loops(
        processamento_service=processamento_service,
        transferencia_service=transferencia_service,
        mailing_service=mailing_service,
        telefone_service=telefone_service,
        heartbeat_service=heartbeat_service,
        runtime_settings=obter_runtime_settings(),
    )


if __name__ == "__main__":
    asyncio.run(main())
