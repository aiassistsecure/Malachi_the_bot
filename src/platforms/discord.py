"""Discord platform handler using discord.py."""

import logging
from typing import Optional, Callable, Awaitable
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from .base import PlatformHandler
from ..models import Message as BotMessage, Platform
from ..config import DiscordConfig


logger = logging.getLogger(__name__)


class DiscordHandler(PlatformHandler):
    """Discord bot handler (Assistant Mode only)."""
    
    name = "discord"
    
    def __init__(self, config: DiscordConfig):
        super().__init__()
        self.config = config
        self._bot: Optional[commands.Bot] = None
        self._bot_user_id: Optional[int] = None
        self._imagine_callback: Optional[Callable[[str], Awaitable[Optional[str]]]] = None
        self._review_callback: Optional[Callable[[str], Awaitable[str]]] = None
        self._deepsearch_callback: Optional[Callable[[str], Awaitable[str]]] = None
        self._clear_callback = None
    
    def on_imagine(self, callback: Callable[[str], Awaitable[Optional[str]]]) -> None:
        """Register callback for image generation."""
        self._imagine_callback = callback
    
    def on_review(self, callback: Callable[[str], Awaitable[str]]) -> None:
        """Register callback for website review."""
        self._review_callback = callback
    
    def on_deepsearch(self, callback: Callable[[str], Awaitable[str]]) -> None:
        """Register callback for deep search."""
        self._deepsearch_callback = callback
    
    def on_clear(self, callback) -> None:
        """Register callback for clearing conversation history."""
        self._clear_callback = callback
    
    async def connect(self) -> None:
        """Connect to Discord."""
        if not self.config.bot_token:
            raise ValueError("Discord bot token is required")
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        
        self._bot = commands.Bot(
            command_prefix=self.config.command_prefix,
            intents=intents,
        )
        
        @self._bot.event
        async def on_ready():
            logger.info(f"Discord bot connected as {self._bot.user}")
            self._bot_user_id = self._bot.user.id
            self._is_connected = True
            # Sync slash commands with Discord
            try:
                synced = await self._bot.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")
        
        # Register slash commands
        @self._bot.tree.command(name="ask", description="Ask the AI assistant a question")
        async def ask_command(interaction: discord.Interaction, question: str):
            await interaction.response.defer(thinking=True)
            if self._message_callback:
                try:
                    # Create a fake message for the callback
                    message = BotMessage(
                        id=str(interaction.id),
                        platform=Platform.DISCORD,
                        channel_id=str(interaction.channel_id),
                        author_id=str(interaction.user.id),
                        author_name=interaction.user.display_name,
                        content=question,
                        timestamp=datetime.now(),
                        is_dm=isinstance(interaction.channel, discord.DMChannel),
                        is_mention=True,
                    )
                    response = await self._message_callback(message)
                    if response:
                        chunks = self._chunk_message(response, 1900)
                        await interaction.followup.send(chunks[0])
                        for chunk in chunks[1:]:
                            await interaction.channel.send(chunk)
                except Exception as e:
                    await interaction.followup.send(f"Sorry, an error occurred: {str(e)[:100]}")
            else:
                await interaction.followup.send("Bot is not ready yet.")
        
        @self._bot.tree.command(name="help", description="Show available commands and how to use the bot")
        async def help_command(interaction: discord.Interaction):
            help_text = """**Malachi the AiAS Bot Commands**

**Slash Commands:**
• `/ask <question>` - Ask the AI a question
• `/imagine <prompt>` - Generate an image from text
• `/review <url>` - Review a website/app with GTM insights
• `/deepsearch <url>` - Deep multi-page website analysis
• `/help` - Show this help message
• `/info` - Show bot information
• `/clear` - Clear your conversation history

**Other ways to interact:**
• **@mention** - Mention the bot in any channel
• **DM** - Send a direct message to the bot
• **Reply** - Reply to any bot message to continue the conversation

Powered by AiAssist API + Pollinations.ai"""
            await interaction.response.send_message(help_text)
        
        @self._bot.tree.command(name="info", description="Show bot information")
        async def info_command(interaction: discord.Interaction):
            info_text = f"""**Malachi the AiAS Bot Info**

• **Name:** {self._bot.user.name}
• **Servers:** {len(self._bot.guilds)}
• **Status:** Online
• **AI Backend:** AiAssist API

Visit https://aiassist.net for more info."""
            await interaction.response.send_message(info_text)
        
        @self._bot.tree.command(name="clear", description="Clear your conversation history")
        async def clear_command(interaction: discord.Interaction):
            from ..models import Platform
            if self._clear_callback:
                await self._clear_callback(Platform.DISCORD, str(interaction.channel_id), str(interaction.user.id))
            await interaction.response.send_message("Your conversation history has been cleared.", ephemeral=True)
        
        @self._bot.tree.command(name="imagine", description="Generate an image from a text description")
        async def imagine_command(interaction: discord.Interaction, prompt: str):
            await interaction.response.defer(thinking=True)
            if self._imagine_callback:
                try:
                    image_url = await self._imagine_callback(prompt)
                    if image_url:
                        embed = discord.Embed(
                            title="Generated Image",
                            description=f"**Prompt:** {prompt[:200]}{'...' if len(prompt) > 200 else ''}",
                            color=0x9B59B6
                        )
                        embed.set_image(url=image_url)
                        embed.set_footer(text="Powered by Pollinations.ai")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("Sorry, couldn't generate the image. Try again!")
                except Exception as e:
                    logger.error(f"Imagine command error: {e}")
                    await interaction.followup.send(f"Error generating image: {str(e)[:100]}")
            else:
                await interaction.followup.send("Image generation is not available.")
        
        @self._bot.tree.command(name="review", description="Review a website/app with GTM insights and AI recommendations")
        async def review_command(interaction: discord.Interaction, url: str):
            await interaction.response.defer(thinking=True)
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            if self._review_callback:
                try:
                    await interaction.followup.send(f"Analyzing {url}... This may take a moment.")
                    response = await self._review_callback(url)
                    chunks = self._chunk_message(response, 1900)
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await interaction.followup.send(chunk)
                        else:
                            await interaction.channel.send(chunk)
                except Exception as e:
                    logger.error(f"Review command error: {e}")
                    await interaction.followup.send(f"Error reviewing site: {str(e)[:100]}")
            else:
                await interaction.followup.send("Review feature is not available.")
        
        @self._bot.tree.command(name="deepsearch", description="Deep multi-page website analysis with comprehensive insights")
        async def deepsearch_command(interaction: discord.Interaction, url: str):
            await interaction.response.defer(thinking=True)
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            if self._deepsearch_callback:
                try:
                    await interaction.followup.send(f"Deep searching {url}... Analyzing multiple pages, this may take a minute.")
                    response = await self._deepsearch_callback(url)
                    chunks = self._chunk_message(response, 1900)
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await interaction.followup.send(chunk)
                        else:
                            await interaction.channel.send(chunk)
                except Exception as e:
                    logger.error(f"Deepsearch command error: {e}")
                    await interaction.followup.send(f"Error during deep search: {str(e)[:100]}")
            else:
                await interaction.followup.send("Deep search feature is not available.")
        
        @self._bot.event
        async def on_message(discord_message: discord.Message):
            if discord_message.author.bot:
                return
            
            if not await self._should_respond(discord_message):
                return
            
            if not self.check_rate_limit(
                str(discord_message.author.id),
                self.config.rate_limit_messages,
                self.config.rate_limit_window
            ):
                logger.debug(f"Rate limited user {discord_message.author.id}")
                return
            
            message = self._normalize_message(discord_message)
            
            if self._message_callback:
                try:
                    if self.config.typing_indicator:
                        async with discord_message.channel.typing():
                            response = await self._message_callback(message)
                    else:
                        response = await self._message_callback(message)
                    
                    if response:
                        # Discord has 2000 char limit, chunk if needed
                        chunks = self._chunk_message(response, 1900)
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await discord_message.reply(chunk)
                            else:
                                await discord_message.channel.send(chunk)
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        await self._bot.start(self.config.bot_token)
    
    async def disconnect(self) -> None:
        """Disconnect from Discord."""
        if self._bot:
            await self._bot.close()
            self._is_connected = False
            logger.info("Discord bot disconnected")
    
    async def send_message(
        self, 
        channel_id: str, 
        content: str, 
        reply_to: Optional[str] = None
    ) -> None:
        """Send a message to a Discord channel."""
        if not self._bot:
            raise RuntimeError("Bot not connected")
        
        channel = self._bot.get_channel(int(channel_id))
        if not channel:
            channel = await self._bot.fetch_channel(int(channel_id))
        
        if channel:
            await channel.send(content)
    
    async def _should_respond(self, message: discord.Message) -> bool:
        """Determine if the bot should respond to this message."""
        if str(message.author.id) in self.config.blocked_users:
            return False
        
        if self.config.allowed_users and str(message.author.id) not in self.config.allowed_users:
            return False
        
        is_dm = isinstance(message.channel, discord.DMChannel)
        if is_dm:
            return self.config.respond_to_dms
        
        if self.config.blocked_channels and str(message.channel.id) in self.config.blocked_channels:
            return False
        
        if self.config.allowed_channels and str(message.channel.id) not in self.config.allowed_channels:
            return False
        
        if self._bot_user_id and self._bot.user in message.mentions:
            return self.config.respond_to_mentions
        
        if message.reference and self.config.respond_to_replies:
            try:
                ref_message = await message.channel.fetch_message(message.reference.message_id)
                if ref_message.author.id == self._bot_user_id:
                    return True
            except:
                pass
        
        return False
    
    def _chunk_message(self, text: str, max_length: int = 1900) -> list:
        """Split a long message into chunks that fit Discord's limit."""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
            
            # Try to split at a newline
            split_at = text.rfind('\n', 0, max_length)
            if split_at == -1:
                # No newline, try space
                split_at = text.rfind(' ', 0, max_length)
            if split_at == -1:
                # No space, hard cut
                split_at = max_length
            
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        
        return chunks
    
    def _normalize_message(self, discord_message: discord.Message) -> BotMessage:
        """Convert Discord message to normalized Message format."""
        is_dm = isinstance(discord_message.channel, discord.DMChannel)
        is_mention = self._bot.user in discord_message.mentions if self._bot else False
        
        content = discord_message.content
        if is_mention and self._bot:
            content = content.replace(f"<@{self._bot_user_id}>", "").strip()
            content = content.replace(f"<@!{self._bot_user_id}>", "").strip()
        
        return BotMessage(
            id=str(discord_message.id),
            platform=Platform.DISCORD,
            channel_id=str(discord_message.channel.id),
            author_id=str(discord_message.author.id),
            author_name=discord_message.author.display_name,
            content=content,
            timestamp=discord_message.created_at,
            reply_to=str(discord_message.reference.message_id) if discord_message.reference else None,
            attachments=[a.url for a in discord_message.attachments],
            is_dm=is_dm,
            is_mention=is_mention,
            raw_data=discord_message,
        )
