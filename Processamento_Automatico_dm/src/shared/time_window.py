from __future__ import annotations

from datetime import datetime


def dentro_horario_bloqueado(agora: datetime, inicio: int = 21, fim: int = 4) -> bool:
    hora = agora.hour
    return hora >= inicio or hora < fim

