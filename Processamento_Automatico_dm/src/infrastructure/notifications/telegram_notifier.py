from __future__ import annotations

from telegram import Bot

from src.infrastructure.config.settings import TelegramSettings
from src.shared.exceptions import NotificationError


class TelegramNotifier:
    def __init__(self, settings: TelegramSettings) -> None:
        self._bot = Bot(token=settings.token)
        self._group_id = settings.group_id
        self._authorized_user_ids = settings.authorized_user_ids

    async def send(self, message: str) -> None:
        try:
            # Toda mensagem vai para o grupo e tambem para os usuarios autorizados.
            await self._bot.send_message(
                chat_id=self._group_id,
                text=message,
                parse_mode="HTML",
            )

            for user_id in self._authorized_user_ids:
                await self._bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML",
                )
        except Exception as error:
            raise NotificationError(f"Erro ao enviar Telegram: {error}") from error
