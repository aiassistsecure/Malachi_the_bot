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
from .platforms.devnetwork import DevNetworkHandler


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
            handler.on_clear(self._handle_clear)
            handler.on_review(self._handle_review)
            handler.on_deepsearch(self._handle_deepsearch)
            self.platforms["discord"] = handler
        
        if self.config.telegram.enabled:
            handler = TelegramHandler(self.config.telegram)
            handler.on_message(self._handle_message)
            handler.on_clear(self._handle_clear)
            handler.on_review(self._handle_review)
            handler.on_deepsearch(self._handle_deepsearch)
            self.platforms["telegram"] = handler
        
        if self.config.devnetwork.enabled:
            handler = DevNetworkHandler(self.config.devnetwork)
            handler.on_message(self._handle_message)
            handler.on_clear(self._handle_clear)
            handler.on_imagine(self._handle_imagine)
            handler.on_review(self._handle_review)
            handler.on_deepsearch(self._handle_deepsearch)
            self.platforms["devnetwork"] = handler
        
        for name, handler in self.platforms.items():
            logger.info(f"Connecting to {name}...")
            asyncio.create_task(self._connect_platform(name, handler))
        
        self._start_time = time.time()
        self._running = True
        logger.info("Bot engine started")
    
    async def _connect_platform(self, name: str, handler: PlatformHandler) -> None:
        """Connect a platform handler with retry on failure."""
        delay = 5
        max_delay = 120
        attempt = 0
        while self._running:
            attempt += 1
            try:
                await handler.connect()
                logger.info(f"Connected to {name}")
                return
            except Exception as e:
                logger.warning(f"Failed to connect to {name} (attempt {attempt}): {e}")
                logger.info(f"Retrying {name} in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, max_delay)
    
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
        
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        parts.append("You are Malachi, a helpful AI assistant powered by AiAssist.")
        parts.append(f"Current date and time: {current_time}")
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
    
    async def _handle_review(self, url: str) -> str:
        """Handle /review command - single page website analysis."""
        logger.info(f"[REVIEW] Starting review for URL: '{url}'")
        try:
            logger.info(f"[REVIEW] Calling web_extract...")
            extracted = await self.aiassist.web_extract(url, extract_links=False)
            logger.info(f"[REVIEW] web_extract returned: success={extracted.get('success')}, content_len={len(extracted.get('content', ''))}")
            
            content = extracted.get("content", "")
            if not content or len(content) < 50:
                return f"Could not extract meaningful content from {url}. The page may be blocking bots or require JavaScript."
            
            review_prompt = self._build_review_prompt(extracted)
            
            messages = [
                {"role": "system", "content": self._get_review_system_prompt()},
                {"role": "user", "content": review_prompt}
            ]
            
            response = await self.aiassist.chat(messages, max_tokens=2048)
            return response
            
        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            logger.error(f"Review failed for {url}: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Failed to review {url}: {error_msg}"
    
    async def _handle_deepsearch(self, url: str) -> str:
        """Handle /deepsearch command - multi-page website analysis."""
        try:
            extracted = await self.aiassist.web_extract(url, extract_links=True)
            
            if not extracted.get("success"):
                return f"Failed to extract content from {url}"
            
            all_content = [extracted]
            
            links = extracted.get("links", [])
            priority_keywords = ["about", "pricing", "features", "product", "solution", "team", "company"]
            priority_links = []
            
            for link in links[:20]:
                link_lower = link.lower()
                if any(kw in link_lower for kw in priority_keywords):
                    priority_links.append(link)
            
            for link in priority_links[:4]:
                try:
                    link_content = await self.aiassist.web_extract(link, extract_links=False, max_content_length=8000)
                    if link_content.get("success"):
                        all_content.append(link_content)
                except Exception as e:
                    logger.warning(f"Failed to extract {link}: {e}")
            
            review_prompt = self._build_deepsearch_prompt(all_content)
            
            messages = [
                {"role": "system", "content": self._get_review_system_prompt()},
                {"role": "user", "content": review_prompt}
            ]
            
            response = await self.aiassist.chat(messages, max_tokens=3000)
            return response
            
        except Exception as e:
            logger.error(f"Deepsearch failed for {url}: {e}")
            return f"Failed to deep search {url}: {str(e)}"
    
    def _get_review_system_prompt(self) -> str:
        """Get the system prompt for website reviews."""
        return """You are Malachi, an expert product analyst and GTM strategist for AiAssist.

Your job is to review websites/applications and provide:
1. A concise product overview
2. CTA (Call-to-Action) analysis
3. Target audience identification
4. Basic GTM (Go-to-Market) insights
5. AI integration recommendations using AiAssist

Always end with specific, actionable suggestions for how the founder could integrate AI features using AiAssist's API (chat completions, knowledge bases, AI agents, etc.).

Be professional, insightful, and constructive. Format your response with clear sections."""
    
    def _build_review_prompt(self, extracted: dict) -> str:
        """Build the review prompt from extracted content."""
        return f"""Please review this website/application:

**URL:** {extracted.get('url', 'N/A')}
**Title:** {extracted.get('title', 'N/A')}
**Domain:** {extracted.get('domain', 'N/A')}

**Content:**
{extracted.get('content', 'No content extracted')[:12000]}

Provide a comprehensive review including:
1. Product/Service Overview
2. CTA Analysis
3. Target Audience
4. GTM Insights
5. AI Integration Opportunities with AiAssist"""
    
    def _build_deepsearch_prompt(self, pages: list) -> str:
        """Build the deepsearch prompt from multiple extracted pages."""
        content_parts = []
        for i, page in enumerate(pages):
            content_parts.append(f"""
--- Page {i+1}: {page.get('title', 'Untitled')} ---
URL: {page.get('url', 'N/A')}
{page.get('content', '')[:6000]}
""")
        
        all_content = "\n".join(content_parts)
        
        return f"""Please perform a comprehensive review of this website/application based on multiple pages:

{all_content}

Provide an in-depth analysis including:
1. Complete Product/Service Overview
2. Value Proposition & CTA Analysis
3. Target Audience & Market Positioning
4. Pricing Strategy (if visible)
5. Competitive Insights
6. GTM Recommendations
7. AI Integration Opportunities with AiAssist (be specific about which AiAssist features would add value)"""
    
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
