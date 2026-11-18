from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.infrastructure.config.factories import criar_repositorio_dm, criar_servicos


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa somente o fluxo de mailing uma vez.",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista os cedentes pendentes de mailing sem executar procedures.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.listar:
        repository = criar_repositorio_dm()
        cedentes = await repository.listar_cedentes_mailing()
        print(f"Cedentes pendentes de mailing: {cedentes}")
        return

    (
        _processamento_service,
        _transferencia_service,
        mailing_service,
        _telefone_service,
        _heartbeat_service,
    ) = criar_servicos()

    total = await mailing_service.executar_pendentes()
    print(f"Fluxo de mailing finalizado. Total gerado: {total}")


if __name__ == "__main__":
    asyncio.run(main())
