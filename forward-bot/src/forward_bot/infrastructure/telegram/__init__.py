"""Telegram infrastructure package."""
from forward_bot.infrastructure.telegram.client import telegram_client, TelegramClientHolder

__all__ = ["telegram_client", "TelegramClientHolder"]