"""DevNetwork platform handler for Malachi."""

import asyncio
import json
import logging
from typing import Callable, Optional, Awaitable
from datetime import datetime
import aiohttp

from .base import PlatformHandler
from ..models import Message as BotMessage, Platform
from ..config import DevNetworkConfig


logger = logging.getLogger(__name__)


class DevNetworkHandler(PlatformHandler):
    """Handler for DevNetwork platform using Bot API."""
    
    name = "devnetwork"
    
    def __init__(self, config: DevNetworkConfig):
        super().__init__()
        self.config = config
        self._api_url = config.api_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._bot_info: Optional[dict] = None
        self._imagine_callback: Optional[Callable[[str], Awaitable[Optional[str]]]] = None
        self._review_callback: Optional[Callable[[str], Awaitable[str]]] = None
        self._deepsearch_callback: Optional[Callable[[str], Awaitable[str]]] = None
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_lock = asyncio.Lock()
    
    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.bot_token}"}
    
    def on_imagine(self, callback: Callable[[str], Awaitable[Optional[str]]]) -> None:
        """Register imagine handler."""
        self._imagine_callback = callback
    
    def on_review(self, callback: Callable[[str], Awaitable[str]]) -> None:
        """Register review handler."""
        self._review_callback = callback
    
    def on_deepsearch(self, callback: Callable[[str], Awaitable[str]]) -> None:
        """Register deepsearch handler."""
        self._deepsearch_callback = callback
    
    async def connect(self) -> None:
        """Connect to DevNetwork via WebSocket."""
        async with self._reconnect_lock:
            if self._listen_task and not self._listen_task.done():
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass
                self._listen_task = None
            
            if self._ws and not self._ws.closed:
                await self._ws.close()
            
            if not self._session or self._session.closed:
                self._session = aiohttp.ClientSession()
            
            try:
                async with self._session.get(
                    f"{self._api_url}/api/bots/me",
                    headers=self._headers
                ) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        if "<html" in error.lower() or "<!doctype" in error.lower():
                            raise Exception(f"DevNetwork unavailable (HTTP {resp.status})")
                        raise Exception(f"Auth failed (HTTP {resp.status}): {error[:200]}")
                    self._bot_info = await resp.json()
                    logger.info(f"Authenticated as @{self._bot_info['displayName']}")
            except aiohttp.ClientError as e:
                raise Exception(f"DevNetwork unreachable: {type(e).__name__}")
            
            ws_url = self._api_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = f"{ws_url}/ws/bot"
            
            try:
                self._ws = await self._session.ws_connect(ws_url)
                logger.info(f"WebSocket connected to {ws_url}")
                
                await self._ws.send_json({
                    "type": "auth",
                    "token": self.config.bot_token
                })
                
                auth_response = await self._ws.receive_json()
                if auth_response.get("type") != "auth_success":
                    raise Exception(f"WebSocket auth failed: {auth_response}")
                
                logger.info("WebSocket authenticated successfully")
                self._is_connected = True
                self._running = True
                
                approved_groups = self._bot_info.get("bot_data", {}).get("approved_groups", [])
                for gid in approved_groups:
                    try:
                        await self._ws.send_json({"action": "subscribe_group", "group_id": gid})
                        sub_resp = await asyncio.wait_for(self._ws.receive_json(), timeout=5)
                        if sub_resp.get("type") == "subscribed":
                            logger.info(f"Subscribed to group {gid}")
                        else:
                            logger.warning(f"Failed to subscribe to group {gid}: {sub_resp}")
                    except Exception as e:
                        logger.warning(f"Error subscribing to group {gid}: {e}")
                
                self._listen_task = asyncio.create_task(self._listen_loop())
                
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                raise
    
    async def _listen_loop(self) -> None:
        """Listen for incoming WebSocket messages."""
        while self._running and self._ws and not self._ws.closed:
            try:
                msg = await self._ws.receive()
                logger.debug(f"[WS] Raw message received: type={msg.type}")
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    logger.info(f"[WS] Parsed message: {data}")
                    await self._handle_ws_message(data)
                    
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                    logger.warning("WebSocket closed, will reconnect...")
                    break
                    
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._ws.exception()}")
                    break
                    
            except asyncio.CancelledError:
                logger.info("Listen loop cancelled")
                return
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                break
        
        if self._running:
            asyncio.create_task(self._reconnect())
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect to WebSocket with exponential backoff."""
        if not self._running:
            return
        
        if self._reconnect_lock.locked():
            return
        
        self._is_connected = False
        delay = 5
        max_delay = 120
        attempt = 0
        
        while self._running:
            attempt += 1
            logger.info(f"Reconnect attempt {attempt} in {delay}s...")
            await asyncio.sleep(delay)
            
            if not self._running:
                return
            
            try:
                await self.connect()
                logger.info(f"Reconnected successfully after {attempt} attempt(s)")
                return
            except Exception as e:
                logger.warning(f"Reconnect attempt {attempt} failed: {e}")
                delay = min(delay * 2, max_delay)
    
    async def _handle_ws_message(self, data: dict) -> None:
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")
        logger.info(f"[WS] Received message type: {msg_type}, data: {data}")
        
        if msg_type == "dm":
            await self._handle_dm(data)
        elif msg_type == "group_message":
            await self._handle_group_message(data)
        elif msg_type == "feed_post":
            pass
        elif msg_type == "ping":
            await self._ws.send_json({"action": "pong"})
    
    async def _handle_dm(self, data: dict) -> None:
        """Handle incoming DM."""
        logger.info(f"[DM] Handling DM: config.respond_to_dms={self.config.respond_to_dms}")
        if not self.config.respond_to_dms:
            logger.info("[DM] respond_to_dms is False, skipping")
            return
        
        sender_id = data.get("sender_id")
        content = data.get("content", "")
        logger.info(f"[DM] From {sender_id}: {content[:50]}")
        
        if sender_id == self._bot_info["id"]:
            logger.info("[DM] Ignoring own message")
            return
        
        if not self.check_rate_limit(
            sender_id,
            self.config.rate_limit_messages,
            self.config.rate_limit_window
        ):
            logger.info("[DM] Rate limited, skipping")
            return
        
        if content.startswith("/"):
            logger.info(f"[DM] Processing command: {content}")
            parts = content.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            if command == "/imagine" and args and self._imagine_callback:
                image_url = await self._imagine_callback(args)
                if image_url:
                    await self.send_dm(sender_id, f"**{args}**", image_url=image_url)
                else:
                    await self.send_dm(sender_id, "Failed to generate image. Please try again.")
                return
            response = await self._handle_command(content, sender_id, is_dm=True)
            if response:
                logger.info(f"[DM] Sending command response: {response[:50]}...")
                await self.send_dm(sender_id, response)
            return
        
        logger.info(f"[DM] message_callback registered: {self._message_callback is not None}")
        if self._message_callback:
            message = BotMessage(
                id=data.get("id", ""),
                platform=Platform.DEVNETWORK,
                channel_id=f"dm:{sender_id}",
                author_id=sender_id,
                author_name=data.get("sender_name", "User"),
                content=content,
                is_dm=True,
            )
            
            try:
                logger.info("[DM] Calling message callback...")
                response = await self._message_callback(message)
                logger.info(f"[DM] Callback response: {response[:100] if response else 'None'}...")
                if response:
                    await self.send_dm(sender_id, response)
            except Exception as e:
                logger.error(f"[DM] Error in message callback: {e}")
        else:
            logger.warning("[DM] No message callback registered!")
    
    async def _handle_group_message(self, data: dict) -> None:
        """Handle incoming group message."""
        if not self.config.respond_to_groups:
            return
        
        sender_id = data.get("sender_id")
        content = data.get("content", "")
        group_id = data.get("group_id")
        
        if sender_id == self._bot_info["id"]:
            return
        
        bot_username = self._bot_info.get("username", "").lower()
        bot_display = self._bot_info.get("displayName", "").lower()
        content_lower = content.lower()
        is_mention = bool(bot_username) and f"@{bot_username}" in content_lower
        
        if self.config.require_mention_in_groups and not is_mention:
            return
        
        if not self.check_rate_limit(
            sender_id,
            self.config.rate_limit_messages,
            self.config.rate_limit_window
        ):
            return
        
        content_clean = content.replace(f"@{bot_username}", "").replace(f"@{bot_display}", "").strip()
        
        if content_clean.startswith("/"):
            response = await self._handle_command(content_clean, sender_id, group_id=group_id)
            if response:
                await self.send_group_message(group_id, response)
            return
        
        if self._message_callback:
            message = BotMessage(
                id=data.get("id", ""),
                platform=Platform.DEVNETWORK,
                channel_id=group_id,
                author_id=sender_id,
                author_name=data.get("sender_name", "User"),
                content=content_clean,
                is_dm=False,
                is_mention=is_mention,
            )
            
            response = await self._message_callback(message)
            if response:
                success = await self.send_group_message(group_id, response)
                if not success:
                    await self.apply_to_group(group_id)
                    logger.info(f"Auto-applied to group {group_id} after 403")
    
    async def _handle_command(
        self,
        content: str,
        user_id: str,
        is_dm: bool = False,
        group_id: Optional[str] = None
    ) -> Optional[str]:
        """Handle slash commands."""
        parts = content.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "/help":
            return self._get_help_text()
        
        elif command == "/info":
            return self._get_info_text()
        
        elif command == "/clear":
            if self._clear_callback:
                channel_id = f"dm:{user_id}" if is_dm else group_id
                await self._clear_callback(Platform.DEVNETWORK, channel_id, user_id)
            return "Conversation history cleared."
        
        elif command == "/imagine" and args:
            if self._imagine_callback:
                image_url = await self._imagine_callback(args)
                if image_url:
                    return f"**Generated Image**\n\n{args}\n\n![Image]({image_url})"
                return "Failed to generate image. Please try again."
            return "Image generation not available."
        
        elif command == "/review" and args:
            if self._review_callback:
                return await self._review_callback(args)
            return "Website review not available."
        
        elif command == "/deepsearch" and args:
            if self._deepsearch_callback:
                return await self._deepsearch_callback(args)
            return "Deep search not available."
        
        elif command == "/groups":
            operator_id = self._bot_info.get("operator_id") or self._bot_info.get("bot_data", {}).get("operator_id")
            logger.info(f"[CMD] /groups: user_id={user_id}, operator_id={operator_id}")
            if user_id != operator_id:
                return "Only my operator can manage group access. Ask them to use `/groups` and `/knock` commands."
            return await self._handle_groups_command(args)
        
        elif command == "/knock" and args:
            operator_id = self._bot_info.get("operator_id") or self._bot_info.get("bot_data", {}).get("operator_id")
            if user_id != operator_id:
                return "Only my operator can manage group access. Ask them to use `/groups` and `/knock` commands."
            return await self._handle_knock_command(args)
        
        return None
    
    async def _handle_groups_command(self, query: str) -> str:
        """Handle /groups command - discover groups to join."""
        try:
            params = {"limit": 25}
            if query:
                params["q"] = query
            
            async with self._session.get(
                f"{self._api_url}/api/bots/discover",
                headers=self._headers,
                params=params
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"[GROUPS] /api/bots/discover returned {resp.status}: {text}")
                    return "Failed to fetch groups. Make sure you have the `group_message` capability."
                
                groups = await resp.json()
                
                if not groups:
                    if query:
                        return f"No groups found matching '{query}'."
                    return "No groups available."
                
                lines = ["**Available Groups**\n"]
                for g in groups:
                    status_icon = {"approved": "✅", "pending": "⏳", "available": "🚪"}.get(g["status"], "")
                    members = g.get("member_count", 0)
                    lines.append(f"{status_icon} **{g['name']}** (`{g['slug']}`) - {members} members")
                    if g.get("description"):
                        lines.append(f"   _{g['description']}_")
                
                lines.append("\n---")
                lines.append("Use `/knock <group-slug>` to apply for access")
                lines.append("✅ = approved, ⏳ = pending, 🚪 = available")
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error(f"Error in /groups: {e}")
            return "Failed to fetch groups."
    
    async def _handle_knock_command(self, group_query: str) -> str:
        """Handle /knock command - apply to join a group."""
        try:
            async with self._session.get(
                f"{self._api_url}/api/bots/discover",
                headers=self._headers,
                params={"q": group_query, "limit": 5}
            ) as resp:
                if resp.status != 200:
                    return "Failed to search groups."
                
                groups = await resp.json()
                
                if not groups:
                    return f"No groups found matching '{group_query}'."
                
                target = None
                for g in groups:
                    if g["slug"].lower() == group_query.lower() or g["name"].lower() == group_query.lower():
                        target = g
                        break
                
                if not target:
                    target = groups[0]
                
                if target["status"] == "approved":
                    return f"✅ Already approved for **{target['name']}**! You can send messages there."
                
                if target["status"] == "pending":
                    return f"⏳ Application for **{target['name']}** is already pending. The group owner will review it soon."
                
                success = await self.apply_to_group(target["id"])
                if success:
                    return f"🚪 **Knock knock!** Applied to join **{target['name']}** (`{target['slug']}`)\n\nThe group owner will review your application. You'll be notified when approved!"
                else:
                    return f"Failed to apply to **{target['name']}**. Please try again."
                
        except Exception as e:
            logger.error(f"Error in /knock: {e}")
            return "Failed to apply to group."
    
    def _get_help_text(self) -> str:
        """Get help text."""
        bot_name = self._bot_info.get("displayName", "Malachi")
        return f"""**{bot_name} Commands**

**Chat:** Just send me a message and I'll respond!

**Commands:**
- `/help` - Show this help message
- `/info` - Show bot information
- `/clear` - Clear conversation history
- `/imagine <prompt>` - Generate an image
- `/review <url>` - Review a website
- `/deepsearch <url>` - Deep analyze a website

**Door Knocking (Group Access):**
- `/groups` - Discover available groups
- `/groups <search>` - Search for groups
- `/knock <group>` - Apply to join a group

Powered by [AiAssist](https://aiassist.net)"""
    
    def _get_info_text(self) -> str:
        """Get info text."""
        bot_name = self._bot_info.get("displayName", "Malachi")
        return f"""**About {bot_name}**

I'm an AI assistant powered by AiAssist.

**Capabilities:**
- Intelligent conversation
- Image generation
- Website analysis

**Platform:** DevNetwork
**Engine:** Malachi the AiAS Bot

Learn more at [aiassist.net](https://aiassist.net)"""
    
    async def send_message(self, channel_id: str, content: str, reply_to: Optional[str] = None) -> None:
        """Send a message (router for DM vs group)."""
        if channel_id.startswith("dm:"):
            user_id = channel_id[3:]
            await self.send_dm(user_id, content)
        else:
            await self.send_group_message(channel_id, content)
    
    async def send_dm(self, user_id: str, content: str, image_url: str = None) -> None:
        """Send a DM to a user, chunking long messages."""
        max_len = 1900
        if image_url:
            await self._send_dm_chunk(user_id, content[:max_len] if content else "", image_url)
            return
        if len(content) <= max_len:
            await self._send_dm_chunk(user_id, content)
            return
        chunks = []
        lines = content.split("\n")
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > max_len:
                if current:
                    chunks.append(current)
                if len(line) > max_len:
                    for i in range(0, len(line), max_len):
                        chunks.append(line[i:i + max_len])
                    current = ""
                else:
                    current = line
            else:
                current = current + "\n" + line if current else line
        if current:
            chunks.append(current)
        for i, chunk in enumerate(chunks):
            await self._send_dm_chunk(user_id, chunk)
            if i < len(chunks) - 1:
                await asyncio.sleep(0.3)

    async def _send_dm_chunk(self, user_id: str, content: str, image_url: str = None) -> None:
        """Send a single DM chunk."""
        logger.info(f"[SEND_DM] Sending DM to {user_id}: {content[:50]}...")
        try:
            payload = {"content": content}
            if image_url:
                payload["image_url"] = image_url
            async with self._session.post(
                f"{self._api_url}/api/bots/dm/{user_id}",
                headers=self._headers,
                json=payload
            ) as resp:
                if resp.status in (200, 201):
                    logger.info(f"[SEND_DM] Successfully sent DM to {user_id}")
                else:
                    error = await resp.text()
                    logger.error(f"[SEND_DM] Failed to send DM (status {resp.status}): {error[:200]}")
        except aiohttp.ClientError as e:
            logger.error(f"[SEND_DM] Failed to send DM: {e}")
    
    async def send_group_message(self, group_id: str, content: str) -> bool:
        """Send a message to a group. Returns False if not approved."""
        try:
            async with self._session.post(
                f"{self._api_url}/api/bots/groups/{group_id}/messages",
                headers=self._headers,
                json={"content": content}
            ) as resp:
                if resp.status in (200, 201):
                    return True
                elif resp.status == 403:
                    error = await resp.text()
                    logger.warning(f"Not approved for group {group_id}: {error}")
                    return False
                else:
                    error = await resp.text()
                    logger.error(f"Failed to send group message: {error}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Failed to send group message: {e}")
            return False
    
    async def apply_to_group(self, group_id: str) -> bool:
        """Apply to join a group for messaging."""
        try:
            async with self._session.post(
                f"{self._api_url}/api/bots/groups/{group_id}/apply",
                headers=self._headers,
                json={}
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    logger.info(f"Applied to group {group_id}: {data.get('message')}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"Failed to apply to group: {error}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Failed to apply to group: {e}")
            return False
    
    async def get_approved_groups(self) -> list:
        """Get list of approved group IDs."""
        if self._bot_info:
            return self._bot_info.get("bot_data", {}).get("approved_groups", [])
        return []
    
    async def create_post(self, content: str) -> Optional[dict]:
        """Create a post on the global feed."""
        try:
            async with self._session.post(
                f"{self._api_url}/api/bots/posts",
                headers=self._headers,
                json={"content": content}
            ) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                error = await resp.text()
                logger.error(f"Failed to create post: {error}")
                return None
        except aiohttp.ClientError as e:
            logger.error(f"Failed to create post: {e}")
            return None
    
    async def disconnect(self) -> None:
        """Disconnect from DevNetwork."""
        self._running = False
        self._is_connected = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info("Disconnected from DevNetwork")
