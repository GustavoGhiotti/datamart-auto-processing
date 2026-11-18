from __future__ import annotations


class RobotError(Exception):
    """Erro base do robo."""


class ConfigurationError(RobotError):
    """Erro de configuracao do ambiente."""


class DatabaseExecutionError(RobotError):
    """Erro ao executar comandos no banco de dados."""


class NotificationError(RobotError):
    """Erro ao enviar notificacoes."""

