from __future__ import annotations

from src.application.services.heartbeat_service import HeartbeatService
from src.application.services.mailing_service import MailingService
from src.application.services.processamento_service import ProcessamentoService
from src.application.services.telefone_service import TelefoneService
from src.application.services.transferencia_service import TransferenciaService
from src.domain.interfaces.dm_repository import DmRepository
from src.infrastructure.config.settings import (
    obter_database_65,
    obter_database_71,
    obter_database_72,
    obter_telegram_settings,
)
from src.infrastructure.databases.sql_server_executor import SQLServerExecutor
from src.infrastructure.notifications.chat_notifier import ChatNotifier
from src.infrastructure.notifications.safe_notifier import SafeNotifier
from src.infrastructure.notifications.telegram_notifier import TelegramNotifier
from src.infrastructure.repositories.dm_repository import SQLDmRepository


def criar_repositorio_dm() -> DmRepository:
    # Cada executor aponta para o banco usado por um grupo de procedures/consultas.
    return SQLDmRepository(
        db_65_easycollector=SQLServerExecutor(obter_database_65("easycollector")),
        db_71_dashpulse=SQLServerExecutor(obter_database_71("DB_DASHPULSE")),
        db_71_report=SQLServerExecutor(obter_database_71("DB_REPORT")),
        db_71_traces=SQLServerExecutor(obter_database_71("Traces")),
        db_71_planejamento=SQLServerExecutor(obter_database_71("DB_PLANEJAMENTO")),
        db_72_dm=SQLServerExecutor(obter_database_72("db_dm")),
    )


def criar_servicos() -> tuple[
    ProcessamentoService,
    TransferenciaService,
    MailingService,
    TelefoneService,
    HeartbeatService,
]:
    repository = criar_repositorio_dm()
    # SafeNotifier evita que falhas de Telegram ou chat interrompam o robo.
    telegram_notifier = SafeNotifier(
        TelegramNotifier(obter_telegram_settings()),
        name="telegram",
    )
    chat_notifier = SafeNotifier(
        ChatNotifier(SQLServerExecutor(obter_database_71("Traces"))),
        name="chat",
    )

    return (
        ProcessamentoService(repository=repository, notifier=telegram_notifier),
        TransferenciaService(
            repository=repository,
            telegram_notifier=telegram_notifier,
            chat_notifier=chat_notifier,
        ),
        MailingService(repository=repository, notifier=telegram_notifier),
        TelefoneService(repository=repository, notifier=telegram_notifier),
        HeartbeatService(repository=repository),
    )
