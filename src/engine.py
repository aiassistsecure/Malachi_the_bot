"""Core bot engine with message routing and context building."""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

from .config import Config
from .models import Message, Platform, MessageRole, BotStatus
from .memory import MemoryManager
from .aiassist import AiAssistClient
from .platforms.base import PlatformHandler
from .platforms.discord import DiscordHandler
from .platforms.telegram import TelegramHandler


logger = logging.getLogger(__name__)

MALACHI_ASCII = r"""
███╗   ███╗ █████╗ ██╗      █████╗  ██████╗██╗  ██╗██╗
████╗ ████║██╔══██╗██║     ██╔══██╗██╔════╝██║  ██║██║
██╔████╔██║███████║██║     ███████║██║     ███████║██║
██║╚██╔╝██║██╔══██║██║     ██╔══██║██║     ██╔══██║██║
██║ ╚═╝ ██║██║  ██║███████╗██║  ██║╚██████╗██║  ██║██║
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝
          The AiAS Bot - Powered by AiAssist
               https://AiASSIST.net
"""


class BotEngine:
    """Core bot engine that orchestrates platforms, memory, and AI."""
    
    def __init__(self, config: Config):
        self.config = config
        self.memory = MemoryManager(config.memory.database)
        self.aiassist = AiAssistClient(config.aiassist)
        self.platforms: Dict[str, PlatformHandler] = {}
        
        self._start_time: Optional[float] = None
        self._messages_processed: int = 0
        self._last_message_at: Optional[datetime] = None
        self._running: bool = False
    
    async def start(self) -> None:
        """Start the bot engine and connect to platforms."""
        print(MALACHI_ASCII)
        logger.info("Starting Malachi the AiAS Bot engine...")
        
        await self.memory.connect()
        await self.aiassist.connect()
        
        if self.config.discord.enabled:
            handler = DiscordHandler(self.config.discord)
            handler.on_message(self._handle_message)
            handler.on_imagine(self._handle_imagine)
            self.platforms["discord"] = handler
        
        if self.config.telegram.enabled:
            handler = TelegramHandler(self.config.telegram)
            handler.on_message(self._handle_message)
            handler.on_clear(self._handle_clear)
            self.platforms["telegram"] = handler
        
        for name, handler in self.platforms.items():
            logger.info(f"Connecting to {name}...")
            asyncio.create_task(self._connect_platform(name, handler))
        
        self._start_time = time.time()
        self._running = True
        logger.info("Bot engine started")
    
    async def _connect_platform(self, name: str, handler: PlatformHandler) -> None:
        """Connect a platform handler with error handling."""
        try:
            await handler.connect()
        except Exception as e:
            logger.error(f"Failed to connect to {name}: {e}")
    
    async def stop(self) -> None:
        """Stop the bot engine and disconnect from platforms."""
        logger.info("Stopping Malachi the AiAS Bot engine...")
        self._running = False
        
        for name, handler in self.platforms.items():
            try:
                await handler.disconnect()
                logger.info(f"Disconnected from {name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")
        
        await self.aiassist.disconnect()
        await self.memory.disconnect()
        
        logger.info("Bot engine stopped")
    
    async def _handle_message(self, message: Message) -> str:
        """Process an incoming message and generate a response."""
        logger.debug(f"Processing message from {message.author_name} on {message.platform.value}")
        
        conversation = await self.memory.get_or_create_conversation(
            message.platform,
            message.channel_id
        )
        
        await self.memory.add_message(
            conversation.id,
            MessageRole.USER,
            message.content,
            author_id=message.author_id,
            author_name=message.author_name,
        )
        
        context = await self._build_context(conversation.id, message)
        
        try:
            response = await self.aiassist.chat(context)
            
            await self.memory.add_message(
                conversation.id,
                MessageRole.ASSISTANT,
                response,
            )
            
            self._messages_processed += 1
            self._last_message_at = datetime.utcnow()
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error processing your message. Please try again."
    
    async def _build_context(
        self, 
        conversation_id: str, 
        current_message: Message
    ) -> List[Dict[str, str]]:
        """Build the context for the AI request."""
        messages = []
        
        system_prompt = await self._build_system_prompt(current_message)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        history = await self.memory.get_conversation_history(
            conversation_id,
            limit=self.config.memory.max_history
        )
        
        for msg in history:
            messages.append(msg.to_openai_format())
        
        return messages
    
    async def _build_system_prompt(self, message: Message) -> str:
        """Build the system prompt."""
        parts = []
        
        parts.append("You are Malachi, a helpful AI assistant powered by AiAssist.")
        parts.append(f"You are chatting with {message.author_name} on {message.platform.value}.")
        
        user_memories = await self.memory.get_memory(message.author_id, message.platform)
        if user_memories:
            parts.append(f"\n## About {message.author_name}:")
            for mem in user_memories:
                parts.append(f"- {mem.key}: {mem.value}")
        
        return "\n".join(parts)
    
    async def _handle_imagine(self, prompt: str) -> Optional[str]:
        """Handle image generation request."""
        try:
            image_url = await self.aiassist.imagine(prompt)
            return image_url
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None
    
    async def _handle_clear(self, platform: Platform, channel_id: str, user_id: str) -> None:
        """Handle a clear history request."""
        conversation = await self.memory.get_or_create_conversation(platform, channel_id)
        await self.memory.clear_conversation(conversation.id)
        logger.info(f"Cleared conversation {conversation.id} for user {user_id}")
    
    
    def get_status(self) -> BotStatus:
        """Get current bot status."""
        connected_platforms = [
            name for name, handler in self.platforms.items()
            if handler.is_connected
        ]
        
        uptime = time.time() - self._start_time if self._start_time else 0
        
        return BotStatus(
            is_running=self._running,
            connected_platforms=connected_platforms,
            uptime_seconds=uptime,
            messages_processed=self._messages_processed,
            last_message_at=self._last_message_at,
        )
    
    async def send_message(
        self, 
        platform: str, 
        channel_id: str, 
        content: str
    ) -> bool:
        """Send a message to a specific platform/channel."""
        handler = self.platforms.get(platform)
        if not handler or not handler.is_connected:
            return False
        
        try:
            await handler.send_message(channel_id, content)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
