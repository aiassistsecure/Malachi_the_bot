"""Platform handlers for Discord, Telegram, etc."""

from .base import PlatformHandler
from .discord import DiscordHandler
from .telegram import TelegramHandler

__all__ = ["PlatformHandler", "DiscordHandler", "TelegramHandler"]
