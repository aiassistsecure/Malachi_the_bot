"""Telegram platform handler using python-telegram-bot."""

import logging
import re
from typing import Optional
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode

from .base import PlatformHandler
from ..models import Message as BotMessage, Platform
from ..config import TelegramConfig


logger = logging.getLogger(__name__)


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def markdown_to_telegram(text: str) -> str:
    """
    Convert standard markdown to Telegram MarkdownV2 format.
    Handles GFM-style markdown including headers, bold, italic, code, links, etc.
    """
    lines = text.split('\n')
    result_lines = []
    in_code_block = False
    code_block_content = []
    
    for line in lines:
        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End code block
                code_content = '\n'.join(code_block_content)
                result_lines.append(f'```\n{code_content}\n```')
                code_block_content = []
                in_code_block = False
            else:
                # Start code block
                in_code_block = True
            continue
        
        if in_code_block:
            code_block_content.append(line)
            continue
        
        # Convert headers to bold (Telegram doesn't support headers)
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            header_text = header_match.group(2)
            escaped = escape_markdown_v2(header_text)
            result_lines.append(f'*{escaped}*')
            continue
        
        # Process inline formatting
        processed = line
        
        # Temporarily protect already formatted content
        placeholders = {}
        counter = [0]
        
        def make_placeholder(match, fmt_func):
            key = f"__PH{counter[0]}__"
            counter[0] += 1
            placeholders[key] = fmt_func(match)
            return key
        
        # Handle inline code first (protect from escaping)
        def handle_code(m):
            return f'`{m.group(1)}`'
        processed = re.sub(r'`([^`]+)`', lambda m: make_placeholder(m, handle_code), processed)
        
        # Handle links
        def handle_link(m):
            text = escape_markdown_v2(m.group(1))
            url = m.group(2)
            return f'[{text}]({url})'
        processed = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: make_placeholder(m, handle_link), processed)
        
        # Escape special characters in remaining text
        parts = re.split(r'(__PH\d+__)', processed)
        escaped_parts = []
        for part in parts:
            if part in placeholders:
                escaped_parts.append(placeholders[part])
            else:
                # Handle bold **text** or __text__
                part = re.sub(r'\*\*(.+?)\*\*', lambda m: f'*{escape_markdown_v2(m.group(1))}*', part)
                part = re.sub(r'__(.+?)__', lambda m: f'*{escape_markdown_v2(m.group(1))}*', part)
                # Handle italic *text* or _text_
                part = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', lambda m: f'_{escape_markdown_v2(m.group(1))}_', part)
                part = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', lambda m: f'_{escape_markdown_v2(m.group(1))}_', part)
                # Handle strikethrough
                part = re.sub(r'~~(.+?)~~', lambda m: f'~{escape_markdown_v2(m.group(1))}~', part)
                # Escape remaining special chars
                part = re.sub(r'(?<!\\)([.!>\-=|{}#\+])', r'\\\1', part)
                escaped_parts.append(part)
        
        processed = ''.join(escaped_parts)
        result_lines.append(processed)
    
    # Handle unclosed code block
    if in_code_block and code_block_content:
        code_content = '\n'.join(code_block_content)
        result_lines.append(f'```\n{code_content}\n```')
    
    return '\n'.join(result_lines)


def markdown_to_html(text: str) -> str:
    """Convert markdown to Telegram HTML format (fallback)."""
    # Escape HTML entities first
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Handle code blocks
    text = re.sub(r'```(\w*)\n(.*?)```', r'<pre>\2</pre>', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Handle headers (convert to bold)
    text = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    
    # Handle formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    return text


class TelegramHandler(PlatformHandler):
    """Telegram bot handler (Assistant Mode only for OSS)."""
    
    name = "telegram"
    
    def __init__(self, config: TelegramConfig):
        super().__init__()
        self.config = config
        self._app: Optional[Application] = None
        self._bot: Optional[Bot] = None
        self._bot_username: Optional[str] = None
        self._review_callback = None
        self._deepsearch_callback = None
    
    def on_review(self, callback):
        """Register callback for website review."""
        self._review_callback = callback
    
    def on_deepsearch(self, callback):
        """Register callback for deep search."""
        self._deepsearch_callback = callback
    
    async def connect(self) -> None:
        """Connect to Telegram."""
        if not self.config.bot_token:
            raise ValueError("Telegram bot token is required")
        
        self._app = Application.builder().token(self.config.bot_token).build()
        
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        self._app.add_handler(CommandHandler("info", self._cmd_info))
        self._app.add_handler(CommandHandler("clear", self._cmd_clear))
        self._app.add_handler(CommandHandler("imagine", self._cmd_imagine))
        self._app.add_handler(CommandHandler("review", self._cmd_review))
        self._app.add_handler(CommandHandler("deepsearch", self._cmd_deepsearch))
        
        self._app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_message
        ))
        
        await self._app.initialize()
        await self._app.start()
        
        self._bot = self._app.bot
        bot_info = await self._bot.get_me()
        self._bot_username = bot_info.username
        
        logger.info(f"Telegram bot connected as @{self._bot_username}")
        self._is_connected = True
        
        await self._app.updater.start_polling(drop_pending_updates=True)
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            self._is_connected = False
            logger.info("Telegram bot disconnected")
    
    async def send_message(
        self, 
        channel_id: str, 
        content: str, 
        reply_to: Optional[str] = None
    ) -> None:
        """Send a message to a Telegram chat."""
        if not self._bot:
            raise RuntimeError("Bot not connected")
        
        await self._bot.send_message(
            chat_id=int(channel_id),
            text=content,
            reply_to_message_id=int(reply_to) if reply_to else None,
        )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming Telegram messages."""
        if not update.message or not update.message.text:
            return
        
        telegram_message = update.message
        
        if not await self._should_respond(telegram_message):
            return
        
        user_id = str(telegram_message.from_user.id)
        if not self.check_rate_limit(
            user_id,
            self.config.rate_limit_messages,
            self.config.rate_limit_window
        ):
            logger.debug(f"Rate limited user {user_id}")
            return
        
        message = self._normalize_message(telegram_message)
        
        if self._message_callback:
            try:
                if self.config.typing_indicator:
                    await context.bot.send_chat_action(
                        chat_id=telegram_message.chat_id,
                        action="typing"
                    )
                
                response = await self._message_callback(message)
                
                if response:
                    try:
                        html_response = markdown_to_html(response)
                        chunks = self._chunk_message(html_response, 4000)
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await telegram_message.reply_text(chunk, parse_mode=ParseMode.HTML)
                            else:
                                await context.bot.send_message(
                                    chat_id=telegram_message.chat_id,
                                    text=chunk,
                                    parse_mode=ParseMode.HTML
                                )
                    except Exception as html_err:
                        logger.warning(f"HTML parse failed, falling back to plain text: {html_err}")
                        chunks = self._chunk_message(response, 4000)
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await telegram_message.reply_text(chunk)
                            else:
                                await context.bot.send_message(
                                    chat_id=telegram_message.chat_id,
                                    text=chunk
                                )
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _should_respond(self, message) -> bool:
        """Determine if the bot should respond to this message."""
        user_id = str(message.from_user.id)
        chat_id = str(message.chat_id)
        
        if user_id in self.config.blocked_users:
            return False
        
        if self.config.allowed_users and user_id not in self.config.allowed_users:
            return False
        
        is_private = message.chat.type == "private"
        
        if is_private:
            if chat_id in self.config.blocked_chats:
                return False
            return self.config.respond_to_private
        
        if chat_id in self.config.blocked_chats:
            return False
        
        if self.config.allowed_chats and chat_id not in self.config.allowed_chats:
            return False
        
        if not self.config.respond_to_groups:
            return False
        
        if self.config.require_mention_in_groups:
            text = message.text or ""
            if self._bot_username and f"@{self._bot_username}" in text:
                return True
            if message.reply_to_message:
                replied_user = message.reply_to_message.from_user
                if replied_user and replied_user.username == self._bot_username:
                    return True
            return False
        
        return True
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            f"Hello! I'm {self._bot_username}, your AI assistant powered by AiAssist.\n\n"
            "Just send me a message and I'll respond!\n\n"
            "Commands:\n"
            "/help - Show available commands\n"
            "/info - Bot information\n"
            "/clear - Clear conversation history\n"
            "/imagine <prompt> - Generate an image\n"
            "/review <url> - Review a website with GTM insights\n"
            "/deepsearch <url> - Deep multi-page analysis"
        )
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "Available Commands:\n\n"
            "/start - Get started\n"
            "/help - Show this help message\n"
            "/info - Bot information\n"
            "/clear - Clear your conversation history\n"
            "/imagine <prompt> - Generate an image\n"
            "/review <url> - Review a website with GTM insights\n"
            "/deepsearch <url> - Deep multi-page website analysis\n\n"
            "Or just send me any message to chat!"
        )
    
    async def _cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /info command."""
        await update.message.reply_text(
            f"Malachi the AiAS Bot - Telegram\n"
            f"Bot: @{self._bot_username}\n"
            f"Platform: Telegram (Assistant Mode)\n"
            f"Powered by AiAssist API"
        )
    
    async def _cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /clear command."""
        user_id = str(update.message.from_user.id)
        channel_id = str(update.message.chat_id)
        
        if self._clear_callback:
            await self._clear_callback(Platform.TELEGRAM, channel_id, user_id)
            await update.message.reply_text("Conversation history cleared!")
        else:
            await update.message.reply_text("Memory system not available.")
    
    async def _cmd_imagine(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /imagine command for image generation."""
        prompt = " ".join(context.args) if context.args else ""
        
        if not prompt:
            await update.message.reply_text("Please provide a prompt! Usage: /imagine a beautiful sunset")
            return
        
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="upload_photo")
        await update.message.reply_text("Generating image... please wait (this may take up to 30 seconds)")
        
        try:
            import urllib.parse
            import httpx
            from io import BytesIO
            import asyncio
            
            encoded_prompt = urllib.parse.quote(prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
            
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
                        response = await client.get(image_url)
                        if response.status_code == 502:
                            if attempt < 2:
                                await asyncio.sleep(3)
                                continue
                        response.raise_for_status()
                        image_data = BytesIO(response.content)
                        image_data.name = "generated.png"
                        break
                except httpx.HTTPStatusError as e:
                    if attempt < 2 and e.response.status_code in (502, 503, 504):
                        await asyncio.sleep(3)
                        continue
                    raise
            
            await update.message.reply_photo(
                photo=image_data,
                caption=f"Generated: {prompt[:100]}"
            )
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            await update.message.reply_text("Image generation service is currently unavailable. Please try again later.")
    
    async def _cmd_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /review command for website analysis."""
        url = " ".join(context.args) if context.args else ""
        
        if not url:
            await update.message.reply_text("Please provide a URL! Usage: /review https://example.com")
            return
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
        await update.message.reply_text(f"Analyzing {url}... This may take a moment.")
        
        if self._review_callback:
            try:
                response = await self._review_callback(url)
                chunks = self._chunk_message(response, 4000)
                for chunk in chunks:
                    # Try MarkdownV2 first for GFM support
                    try:
                        md_chunk = markdown_to_telegram(chunk)
                        await context.bot.send_message(
                            chat_id=update.message.chat_id,
                            text=md_chunk,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    except Exception as md_err:
                        logger.debug(f"MarkdownV2 failed: {md_err}, trying HTML")
                        try:
                            html_chunk = markdown_to_html(chunk)
                            await context.bot.send_message(
                                chat_id=update.message.chat_id,
                                text=html_chunk,
                                parse_mode=ParseMode.HTML
                            )
                        except Exception:
                            # Last resort: plain text
                            await context.bot.send_message(
                                chat_id=update.message.chat_id,
                                text=chunk
                            )
            except Exception as e:
                logger.error(f"Review command failed: {e}")
                await update.message.reply_text(f"Failed to review: {str(e)[:100]}")
        else:
            await update.message.reply_text("Review feature is not available.")
    
    async def _cmd_deepsearch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /deepsearch command for multi-page website analysis."""
        url = " ".join(context.args) if context.args else ""
        
        if not url:
            await update.message.reply_text("Please provide a URL! Usage: /deepsearch https://example.com")
            return
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
        await update.message.reply_text(f"Deep searching {url}... Analyzing multiple pages, this may take a minute.")
        
        if self._deepsearch_callback:
            try:
                response = await self._deepsearch_callback(url)
                chunks = self._chunk_message(response, 4000)
                for chunk in chunks:
                    # Try MarkdownV2 first for GFM support
                    try:
                        md_chunk = markdown_to_telegram(chunk)
                        await context.bot.send_message(
                            chat_id=update.message.chat_id,
                            text=md_chunk,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    except Exception as md_err:
                        logger.debug(f"MarkdownV2 failed: {md_err}, trying HTML")
                        try:
                            html_chunk = markdown_to_html(chunk)
                            await context.bot.send_message(
                                chat_id=update.message.chat_id,
                                text=html_chunk,
                                parse_mode=ParseMode.HTML
                            )
                        except Exception:
                            # Last resort: plain text
                            await context.bot.send_message(
                                chat_id=update.message.chat_id,
                                text=chunk
                            )
            except Exception as e:
                logger.error(f"Deepsearch command failed: {e}")
                await update.message.reply_text(f"Failed to deep search: {str(e)[:100]}")
        else:
            await update.message.reply_text("Deep search feature is not available.")
    
    def _chunk_message(self, text: str, max_length: int = 4000) -> list:
        """Split a long message into chunks that fit Telegram's limit."""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
            
            split_at = text.rfind('\n', 0, max_length)
            if split_at == -1:
                split_at = text.rfind(' ', 0, max_length)
            if split_at == -1:
                split_at = max_length
            
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        
        return chunks
    
    def _normalize_message(self, telegram_message) -> BotMessage:
        """Convert Telegram message to normalized Message format."""
        is_private = telegram_message.chat.type == "private"
        
        text = telegram_message.text or ""
        is_mention = self._bot_username and f"@{self._bot_username}" in text
        
        if is_mention and self._bot_username:
            text = text.replace(f"@{self._bot_username}", "").strip()
        
        return BotMessage(
            id=str(telegram_message.message_id),
            platform=Platform.TELEGRAM,
            channel_id=str(telegram_message.chat_id),
            author_id=str(telegram_message.from_user.id),
            author_name=telegram_message.from_user.full_name or telegram_message.from_user.username or "Unknown",
            content=text,
            timestamp=telegram_message.date,
            reply_to=str(telegram_message.reply_to_message.message_id) if telegram_message.reply_to_message else None,
            attachments=[],
            is_dm=is_private,
            is_mention=is_mention,
            raw_data=telegram_message,
        )
