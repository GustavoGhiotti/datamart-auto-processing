from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from src.application.services.heartbeat_service import HeartbeatService
from src.application.services.mailing_service import MailingService
from src.application.services.processamento_service import ProcessamentoService
from src.application.services.telefone_service import TelefoneService
from src.application.services.transferencia_service import TransferenciaService
from src.infrastructure.config.settings import RuntimeSettings
from src.shared.time_window import dentro_horario_bloqueado


async def executar_loops(
    *,
    processamento_service: ProcessamentoService,
    transferencia_service: TransferenciaService,
    mailing_service: MailingService,
    telefone_service: TelefoneService,
    heartbeat_service: HeartbeatService,
    runtime_settings: RuntimeSettings,
) -> None:
    # Os fluxos rodam em paralelo; cada loop tem sua propria cadencia de espera.
    tasks = [
        asyncio.create_task(
            loop_atualizacao(processamento_service, heartbeat_service, runtime_settings),
            name="loop_atualizacao",
        ),
        asyncio.create_task(
            loop_transferencia(transferencia_service, runtime_settings),
            name="loop_transferencia",
        ),
        asyncio.create_task(
            loop_mailing(mailing_service, runtime_settings),
            name="loop_mailing",
        ),
        asyncio.create_task(
            loop_mailing_diario(mailing_service, runtime_settings),
            name="loop_mailing_diario",
        ),
        asyncio.create_task(
            loop_heartbeat(heartbeat_service, runtime_settings),
            name="loop_heartbeat",
        ),
    ]

    if runtime_settings.enable_phone_loop:
        # Fluxo opcional, desligado por padrao via HABILITAR_LOOP_TELEFONES.
        tasks.append(
            asyncio.create_task(
                loop_telefones(telefone_service, runtime_settings),
                name="loop_telefones",
            )
        )

    await asyncio.gather(*tasks)


async def loop_atualizacao(
    service: ProcessamentoService,
    heartbeat_service: HeartbeatService,
    settings: RuntimeSettings,
) -> None:
    while True:
        agora = datetime.now()

        if dentro_horario_bloqueado(agora):
            print(f"[{_timestamp(agora)}] Loop atualizacao em pausa entre 21h e 4h.")
            await _executar_sem_quebrar(heartbeat_service.executar)
            await asyncio.sleep(settings.idle_seconds)
            continue

        print(f"[{_timestamp(agora)}] Verificando fila de atualizacoes.")
        # O relatorio de carga e atualizado antes da fila e novamente apos sucesso.
        await _executar_sem_quebrar(service.atualizar_relatorio_carga)
        fez_algo = await _executar_bool_sem_quebrar(service.executar_um)
        await asyncio.sleep(settings.active_retry_seconds if fez_algo else settings.idle_seconds)


async def loop_transferencia(
    service: TransferenciaService,
    settings: RuntimeSettings,
) -> None:
    while True:
        agora = datetime.now()

        if dentro_horario_bloqueado(agora):
            print(f"[{_timestamp(agora)}] Loop transferencia em pausa entre 21h e 4h.")
            await asyncio.sleep(settings.idle_seconds)
            continue

        print(f"[{_timestamp(agora)}] Verificando fila de transferencias.")
        # Processa somente o primeiro cedente elegivel por ciclo.
        fez_algo = await _executar_bool_sem_quebrar(service.executar_um)
        await asyncio.sleep(settings.active_retry_seconds if fez_algo else settings.idle_seconds)


async def loop_mailing(service: MailingService, settings: RuntimeSettings) -> None:
    while True:
        agora = datetime.now()

        if _deve_pausar_fluxo_padrao(agora):
            print(f"[{_timestamp(agora)}] Loop mailing padrao pausado entre 04:00 e 05:30.")
            await asyncio.sleep(settings.idle_seconds)
            continue

        if dentro_horario_bloqueado(agora):
            print(f"[{_timestamp(agora)}] Loop mailing em pausa entre 21h e 4h.")
            await asyncio.sleep(settings.idle_seconds)
            continue

        print(f"[{_timestamp(agora)}] Verificando fila de mailing.")
        # O service percorre todos os cedentes retornados pela fila de mailing.
        await _executar_sem_quebrar(service.executar_pendentes)
        await asyncio.sleep(settings.idle_seconds)


async def loop_mailing_diario(service: MailingService, settings: RuntimeSettings) -> None:
    ultima_execucao: str | None = None

    while True:
        agora = datetime.now()
        data_execucao = agora.strftime("%Y-%m-%d")

        if _dentro_intervalo(agora, inicio="03:00", fim="05:00"):
            if ultima_execucao != data_execucao:
                executou = await _rodar_mailing_diario(service)
                if executou:
                    ultima_execucao = data_execucao

            await asyncio.sleep(settings.idle_seconds)
            continue

        espera = min(_segundos_ate_horario(agora, horario="04:30"), settings.idle_seconds)
        await asyncio.sleep(espera)


async def loop_telefones(service: TelefoneService, settings: RuntimeSettings) -> None:
    while True:
        agora = datetime.now()

        if dentro_horario_bloqueado(agora):
            print(f"[{_timestamp(agora)}] Loop telefones em pausa entre 21h e 4h.")
            await asyncio.sleep(settings.idle_seconds)
            continue

        print(f"[{_timestamp(agora)}] Verificando atualizacao de telefones.")
        fez_algo = await _executar_bool_sem_quebrar(service.executar_um)
        await asyncio.sleep(settings.active_retry_seconds if fez_algo else settings.phone_idle_seconds)


async def loop_heartbeat(service: HeartbeatService, settings: RuntimeSettings) -> None:
    while True:
        await _executar_sem_quebrar(service.executar)
        await asyncio.sleep(settings.idle_seconds)


async def _executar_sem_quebrar(funcao: Callable[[], Awaitable[object]]) -> None:
    try:
        await funcao()
    except Exception as error:
        print(f"[AVISO] Falha em execucao auxiliar: {error}")


async def _executar_bool_sem_quebrar(funcao: Callable[[], Awaitable[bool]]) -> bool:
    try:
        return await funcao()
    except Exception as error:
        print(f"[AVISO] Falha no ciclo principal: {error}")
        return False


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


async def _rodar_mailing_diario(service: MailingService) -> bool:
    agora = datetime.now()
    print(f"[{_timestamp(agora)}] Iniciando mailing diario.")
    try:
        await service.executar_diario()
        return True
    except Exception as error:
        print(f"[AVISO] Falha no mailing diario: {error}")
        return False


def _deve_pausar_fluxo_padrao(agora: datetime) -> bool:
    return _dentro_intervalo(agora, inicio="03:00", fim="05:00")


def _dentro_intervalo(agora: datetime, *, inicio: str, fim: str) -> bool:
    horario_atual = agora.time()
    horario_inicio = datetime.strptime(inicio, "%H:%M").time()
    horario_fim = datetime.strptime(fim, "%H:%M").time()

    if horario_inicio <= horario_fim:
        return horario_inicio <= horario_atual < horario_fim

    return horario_atual >= horario_inicio or horario_atual < horario_fim


def _segundos_ate_horario(agora: datetime, *, horario: str) -> int:
    horario_alvo = datetime.strptime(horario, "%H:%M").time()
    proxima_execucao = agora.replace(
        hour=horario_alvo.hour,
        minute=horario_alvo.minute,
        second=0,
        microsecond=0,
    )

    if proxima_execucao <= agora:
        proxima_execucao = proxima_execucao + timedelta(days=1)

    return max(int((proxima_execucao - agora).total_seconds()), 1)
