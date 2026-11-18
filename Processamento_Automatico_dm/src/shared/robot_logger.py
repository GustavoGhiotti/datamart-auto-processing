from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import traceback
from typing import Any
from uuid import uuid4


LOG_DIR = Path("logs")
PROCESS_LOG_FILES = {
    "DM": "dm_log.jsonl",
    "Mailing": "mailing_log.jsonl",
    "Telefones": "telefone_log.jsonl",
    "Transferencia": "transferencia_log.jsonl",
    "Notificacao": "notificacao_log.jsonl",
}


@dataclass(slots=True, frozen=True)
class ExecutionTimer:
    id_execucao: str
    processo: str
    etapa: str
    inicio: datetime
    carteira: str | None = None


class RobotLogger:
    """Logger central do robo.

    A camada de logger grava eventos estruturados em JSONL. A etapa real do
    processo fica no campo `etapa_processo`, deixando claro quando o evento e
    apenas registro e quando ele representa uma fase de negocio.
    """

    # ---------------------------------------------------------------------
    # Eventos publicos usados pelos fluxos de negocio
    # ---------------------------------------------------------------------

    def start(
        self,
        *,
        processo: str,
        etapa: str,
        carteira: str | int | None = None,
        query: str | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> ExecutionTimer:
        timer = ExecutionTimer(
            id_execucao=str(uuid4()),
            processo=processo,
            etapa=etapa,
            inicio=datetime.now(),
            carteira=str(carteira) if carteira is not None else None,
        )
        self.info(
            processo=processo,
            etapa=etapa,
            status="iniciado",
            carteira=carteira,
            id_execucao=timer.id_execucao,
            inicio=timer.inicio,
            query=query,
            detalhes=detalhes,
        )
        return timer

    def success(
        self,
        timer: ExecutionTimer,
        *,
        quantidade_registros: int | None = None,
        query: str | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        self.info(
            processo=timer.processo,
            etapa=timer.etapa,
            status="sucesso",
            carteira=timer.carteira,
            id_execucao=timer.id_execucao,
            inicio=timer.inicio,
            fim=datetime.now(),
            quantidade_registros=quantidade_registros,
            query=query,
            detalhes=detalhes,
        )

    def warning(
        self,
        *,
        processo: str,
        etapa: str,
        mensagem: str,
        carteira: str | int | None = None,
        query: str | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        self.info(
            processo=processo,
            etapa=etapa,
            status="aviso",
            carteira=carteira,
            mensagem=mensagem,
            query=query,
            detalhes=detalhes,
        )

    def warning_from_timer(
        self,
        timer: ExecutionTimer,
        *,
        mensagem: str,
        query: str | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        self.info(
            processo=timer.processo,
            etapa=timer.etapa,
            status="aviso",
            carteira=timer.carteira,
            id_execucao=timer.id_execucao,
            inicio=timer.inicio,
            fim=datetime.now(),
            mensagem=mensagem,
            query=query,
            detalhes=detalhes,
        )

    def error(
        self,
        timer: ExecutionTimer,
        *,
        error: BaseException,
        query: str | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        self.info(
            processo=timer.processo,
            etapa=timer.etapa,
            status="erro",
            carteira=timer.carteira,
            id_execucao=timer.id_execucao,
            inicio=timer.inicio,
            fim=datetime.now(),
            mensagem=str(error),
            erro_tipo=type(error).__name__,
            stack_trace=traceback.format_exc(),
            query=query,
            detalhes=detalhes,
        )

    # ---------------------------------------------------------------------
    # Escrita estruturada: camada logger x etapa de processo
    # ---------------------------------------------------------------------

    def info(
        self,
        *,
        processo: str,
        etapa: str,
        status: str,
        carteira: str | int | None = None,
        id_execucao: str | None = None,
        inicio: datetime | None = None,
        fim: datetime | None = None,
        quantidade_registros: int | None = None,
        mensagem: str | None = None,
        erro_tipo: str | None = None,
        stack_trace: str | None = None,
        query: str | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        evento = {
            "camada": "logger",
            "tipo_evento": "registro_execucao",
            "processo": processo,
            "etapa_processo": etapa,
            "status": status,
            "carteira": _mask_sensitive(carteira),
            "inicio": _format_datetime(inicio),
            "fim": _format_datetime(fim),
            "duracao_segundos": _duration_seconds(inicio, fim),
            "quantidade_registros": quantidade_registros,
            "mensagem": _mask_sensitive(mensagem),
            "id_execucao": id_execucao,
            "erro_tipo": erro_tipo,
            "stack_trace": _mask_sensitive(stack_trace),
            "query_ou_rotina": _mask_sensitive(query),
            "detalhes": _mask_dict(detalhes or {}),
            "data_hora_log": datetime.now().isoformat(timespec="seconds"),
        }
        _write_jsonl(processo, evento)


robot_logger = RobotLogger()


# -------------------------------------------------------------------------
# Persistencia em arquivo
# -------------------------------------------------------------------------


def _write_jsonl(processo: str, evento: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_name = PROCESS_LOG_FILES.get(processo, f"{_normalize_process_name(processo)}_log.jsonl")
    with (LOG_DIR / file_name).open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(evento, ensure_ascii=False, default=str) + "\n")


def _normalize_process_name(processo: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", processo.strip().lower()).strip("_")
    return normalized or "processo"


# -------------------------------------------------------------------------
# Formatacao e mascaramento
# -------------------------------------------------------------------------


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds")


def _duration_seconds(inicio: datetime | None, fim: datetime | None) -> float | None:
    if inicio is None or fim is None:
        return None
    return round((fim - inicio).total_seconds(), 3)


def _mask_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _mask_sensitive(item) for key, item in value.items()}


def _mask_sensitive(value: Any) -> Any:
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    masked = re.sub(r"(\b\d{3})\d{5}(\d{3}\b)", r"\1*****\2", value)
    masked = re.sub(r"(\b\d{2})\d{7}(\d{2}\b)", r"\1*******\2", masked)
    masked = re.sub(r"([\w.\-+%]+)@([\w.\-]+\.\w+)", r"***@\2", masked)
    return masked
