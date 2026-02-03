"""Configuration management with YAML + environment variable support."""

import os
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv


@dataclass
class AiAssistConfig:
    """AiAssist API configuration."""
    api_key: str = ""
    api_url: str = "https://api.aiassist.net"
    model: str = "gpt-4o"
    provider: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout: int = 30
    retry_attempts: int = 3


@dataclass
class DiscordConfig:
    """Discord platform configuration."""
    enabled: bool = False
    mode: str = "assistant"
    bot_token: str = ""
    command_prefix: str = "!"
    respond_to_mentions: bool = True
    respond_to_dms: bool = True
    respond_to_replies: bool = True
    typing_indicator: bool = True
    rate_limit_messages: int = 10
    rate_limit_window: int = 60
    allowed_channels: list = field(default_factory=list)
    blocked_channels: list = field(default_factory=list)
    allowed_users: list = field(default_factory=list)
    blocked_users: list = field(default_factory=list)
    admin_users: list = field(default_factory=list)


@dataclass
class TelegramConfig:
    """Telegram platform configuration."""
    enabled: bool = False
    mode: str = "assistant"
    bot_token: str = ""
    respond_to_private: bool = True
    respond_to_groups: bool = True
    require_mention_in_groups: bool = True
    typing_indicator: bool = True
    rate_limit_messages: int = 20
    rate_limit_window: int = 60
    allowed_chats: list = field(default_factory=list)
    blocked_chats: list = field(default_factory=list)
    allowed_users: list = field(default_factory=list)
    blocked_users: list = field(default_factory=list)
    admin_users: list = field(default_factory=list)


@dataclass
class MemoryConfig:
    """Memory and storage configuration."""
    enabled: bool = True
    database: str = "data/aias.db"
    max_history: int = 100


@dataclass
class ServerConfig:
    """Management API server configuration."""
    host: str = "127.0.0.1"
    port: int = 8080
    api_enabled: bool = True
    api_key: str = ""
    log_level: str = "INFO"


@dataclass
class Config:
    """Main configuration container."""
    aiassist: AiAssistConfig = field(default_factory=AiAssistConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def _get_env(key: str, default: Any = None) -> Any:
    """Get environment variable with type preservation."""
    value = os.getenv(key)
    if value is None:
        return default
    if isinstance(default, bool):
        return value.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return value


def _merge_dict(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.
    
    Priority: Environment variables > config.yaml > defaults
    """
    load_dotenv()
    
    config_file = Path(config_path) if config_path else Path("config.yaml")
    
    yaml_config = {}
    if config_file.exists():
        with open(config_file, "r") as f:
            yaml_config = yaml.safe_load(f) or {}
    
    aiassist_yaml = yaml_config.get("aiassist", {})
    aiassist = AiAssistConfig(
        api_key=_get_env("AIASSIST_API_KEY", aiassist_yaml.get("api_key", "")),
        api_url=_get_env("AIASSIST_API_URL", aiassist_yaml.get("api_url", "https://api.aiassist.net")),
        model=_get_env("AIASSIST_MODEL", aiassist_yaml.get("model", "gpt-4o")),
        provider=_get_env("AIASSIST_PROVIDER", aiassist_yaml.get("provider", "")),
        temperature=aiassist_yaml.get("temperature", 0.7),
        max_tokens=aiassist_yaml.get("max_tokens", 1024),
        timeout=aiassist_yaml.get("timeout", 30),
        retry_attempts=aiassist_yaml.get("retry_attempts", 3),
    )
    
    platforms_yaml = yaml_config.get("platforms", {})
    discord_yaml = platforms_yaml.get("discord", {})
    discord = DiscordConfig(
        enabled=discord_yaml.get("enabled", False),
        mode="assistant",
        bot_token=_get_env("DISCORD_BOT_TOKEN", discord_yaml.get("bot_token", "")),
        command_prefix=discord_yaml.get("command_prefix", "!"),
        respond_to_mentions=discord_yaml.get("respond_to_mentions", True),
        respond_to_dms=discord_yaml.get("respond_to_dms", True),
        respond_to_replies=discord_yaml.get("respond_to_replies", True),
        typing_indicator=discord_yaml.get("typing_indicator", True),
        rate_limit_messages=discord_yaml.get("rate_limit_messages", 10),
        rate_limit_window=discord_yaml.get("rate_limit_window", 60),
        allowed_channels=discord_yaml.get("allowed_channels", []),
        blocked_channels=discord_yaml.get("blocked_channels", []),
        allowed_users=discord_yaml.get("allowed_users", []),
        blocked_users=discord_yaml.get("blocked_users", []),
        admin_users=discord_yaml.get("admin_users", []),
    )
    
    telegram_yaml = platforms_yaml.get("telegram", {})
    telegram = TelegramConfig(
        enabled=telegram_yaml.get("enabled", False),
        mode="assistant",
        bot_token=_get_env("TELEGRAM_BOT_TOKEN", telegram_yaml.get("bot_token", "")),
        respond_to_private=telegram_yaml.get("respond_to_private", True),
        respond_to_groups=telegram_yaml.get("respond_to_groups", True),
        require_mention_in_groups=telegram_yaml.get("require_mention_in_groups", True),
        typing_indicator=telegram_yaml.get("typing_indicator", True),
        rate_limit_messages=telegram_yaml.get("rate_limit_messages", 20),
        rate_limit_window=telegram_yaml.get("rate_limit_window", 60),
        allowed_chats=telegram_yaml.get("allowed_chats", []),
        blocked_chats=telegram_yaml.get("blocked_chats", []),
        allowed_users=telegram_yaml.get("allowed_users", []),
        blocked_users=telegram_yaml.get("blocked_users", []),
        admin_users=telegram_yaml.get("admin_users", []),
    )
    
    memory_yaml = yaml_config.get("memory", {})
    memory = MemoryConfig(
        enabled=memory_yaml.get("enabled", True),
        database=memory_yaml.get("database", "data/aias.db"),
        max_history=memory_yaml.get("max_history", 100),
    )
    
    server_yaml = yaml_config.get("server", {})
    server = ServerConfig(
        host=server_yaml.get("host", "127.0.0.1"),
        port=server_yaml.get("port", 8080),
        api_enabled=server_yaml.get("api_enabled", True),
        api_key=_get_env("AIAS_API_KEY", server_yaml.get("api_key", "")),
        log_level=_get_env("LOG_LEVEL", server_yaml.get("log_level", "INFO")),
    )
    
    return Config(
        aiassist=aiassist,
        discord=discord,
        telegram=telegram,
        memory=memory,
        server=server,
    )
