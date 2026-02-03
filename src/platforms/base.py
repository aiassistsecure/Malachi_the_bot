"""Base platform handler interface."""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import time

from ..models import Message as BotMessage, Platform


@dataclass
class RateLimitState:
    """Track rate limiting per user."""
    message_times: list = field(default_factory=list)


class PlatformHandler(ABC):
    """Abstract base class for platform handlers."""
    
    name: str = "base"
    
    def __init__(self):
        self._message_callback: Optional[Callable[[BotMessage], Awaitable[str]]] = None
        self._clear_callback: Optional[Callable[[Platform, str, str], Awaitable[None]]] = None
        self._rate_limits: dict = defaultdict(RateLimitState)
        self._is_connected: bool = False
    
    @property
    def is_connected(self) -> bool:
        """Check if platform is connected."""
        return self._is_connected
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the platform."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully disconnect from the platform."""
        pass
    
    @abstractmethod
    async def send_message(self, channel_id: str, content: str, reply_to: Optional[str] = None) -> None:
        """Send a message to a channel/chat."""
        pass
    
    def on_message(self, callback: Callable[[BotMessage], Awaitable[str]]) -> None:
        """Register the message handler callback."""
        self._message_callback = callback
    
    def on_clear(self, callback: Callable[[Platform, str, str], Awaitable[None]]) -> None:
        """Register the clear history callback."""
        self._clear_callback = callback
    
    def check_rate_limit(
        self, 
        user_id: str, 
        max_messages: int, 
        window_seconds: int
    ) -> bool:
        """
        Check if user is within rate limits.
        
        Returns True if the message should be processed, False if rate limited.
        """
        now = time.time()
        state = self._rate_limits[user_id]
        
        state.message_times = [
            t for t in state.message_times 
            if now - t < window_seconds
        ]
        
        if len(state.message_times) >= max_messages:
            return False
        
        state.message_times.append(now)
        return True
    
    def clear_rate_limits(self) -> None:
        """Clear all rate limit tracking."""
        self._rate_limits.clear()


