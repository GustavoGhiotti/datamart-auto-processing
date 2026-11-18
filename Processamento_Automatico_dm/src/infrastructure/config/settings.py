from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.config.env import obter_inteiros_csv, obter_variavel


@dataclass(slots=True, frozen=True)
class DatabaseSettings:
    server: str
    database: str
    user: str
    password: str


@dataclass(slots=True, frozen=True)
class TelegramSettings:
    token: str
    group_id: str
    authorized_user_ids: list[int]


@dataclass(slots=True, frozen=True)
class RuntimeSettings:
    idle_seconds: int = 300
    active_retry_seconds: int = 2
    phone_idle_seconds: int = 1200
    enable_phone_loop: bool = False


def obter_database_65(database: str) -> DatabaseSettings:
    return DatabaseSettings(
        server=str(obter_variavel("DB_65")),
        database=database,
        user=str(obter_variavel("DB_USUARIO_65")),
        password=str(obter_variavel("DB_SENHA_65")),
    )


def obter_database_71(database: str) -> DatabaseSettings:
    return DatabaseSettings(
        server=str(obter_variavel("DB_71")),
        database=database,
        user=str(obter_variavel("DB_USUARIO_71")),
        password=str(obter_variavel("DB_SENHA_71")),
    )


def obter_database_72(database: str) -> DatabaseSettings:
    return DatabaseSettings(
        server=str(obter_variavel("DB_72")),
        database=database,
        user=str(obter_variavel("DB_USUARIO_72")),
        password=str(obter_variavel("DB_SENHA_72")),
    )


def obter_telegram_settings() -> TelegramSettings:
    return TelegramSettings(
        token=str(obter_variavel("TELEGRAM_TOKEN")),
        group_id=str(obter_variavel("GRUPO_DADOS")),
        authorized_user_ids=obter_inteiros_csv(
            "TELEGRAM_IDS_AUTORIZADOS",
            padrao="6753444201,1680667103",
        ),
    )


def obter_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings(
        enable_phone_loop=_obter_bool("HABILITAR_LOOP_TELEFONES", padrao=True),
    )


def _obter_bool(nome: str, *, padrao: bool) -> bool:
    valor = obter_variavel(nome, obrigatoria=False)
    if valor is None:
        return padrao

    return valor.strip().lower() in {"1", "true", "sim", "s", "yes"}

