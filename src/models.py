"""Data models for Malachi the AiAS Bot."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum


class Platform(str, Enum):
    """Supported platforms."""
    DISCORD = "discord"
    TELEGRAM = "telegram"


class MessageRole(str, Enum):
    """Message roles for chat context."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Normalized message from any platform."""
    id: str
    platform: Platform
    channel_id: str
    author_id: str
    author_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reply_to: Optional[str] = None
    attachments: List[Any] = field(default_factory=list)
    is_dm: bool = False
    is_mention: bool = False
    raw_data: Optional[Any] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "platform": self.platform.value,
            "channel_id": self.channel_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "is_dm": self.is_dm,
            "is_mention": self.is_mention,
        }


@dataclass
class Conversation:
    """A conversation thread."""
    id: str
    platform: Platform
    channel_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "platform": self.platform.value,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ChatMessage:
    """A message in a conversation (stored in DB)."""
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role.value,
            "content": self.content,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_openai_format(self) -> dict:
        """Convert to OpenAI message format."""
        return {
            "role": self.role.value,
            "content": self.content,
        }


@dataclass
class Memory:
    """A user memory entry."""
    id: str
    user_id: str
    platform: Platform
    key: str
    value: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "platform": self.platform.value,
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class BotStatus:
    """Current bot status."""
    is_running: bool = False
    connected_platforms: List[str] = field(default_factory=list)
    uptime_seconds: float = 0
    messages_processed: int = 0
    last_message_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "is_running": self.is_running,
            "connected_platforms": self.connected_platforms,
            "uptime_seconds": self.uptime_seconds,
            "messages_processed": self.messages_processed,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }
