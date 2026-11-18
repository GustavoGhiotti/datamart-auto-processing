from __future__ import annotations

import os

from dotenv import load_dotenv

from src.shared.exceptions import ConfigurationError


load_dotenv()


def obter_variavel(nome: str, *, obrigatoria: bool = True, padrao: str | None = None) -> str | None:
    valor = os.getenv(nome, padrao)

    if obrigatoria and not valor:
        raise ConfigurationError(f"Variavel de ambiente nao encontrada: {nome}")

    return valor


def obter_inteiros_csv(nome: str, *, padrao: str = "") -> list[int]:
    valor = obter_variavel(nome, obrigatoria=False, padrao=padrao) or ""
    ids: list[int] = []

    for item in valor.split(","):
        item_limpo = item.strip()
        if item_limpo:
            ids.append(int(item_limpo))

    return ids

