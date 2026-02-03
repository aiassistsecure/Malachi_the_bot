"""FastAPI management API for Malachi the AiAS Bot."""

import logging
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine import BotEngine
from .config import Config


logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class MemoryInput(BaseModel):
    """Input for adding a memory entry."""
    user_id: str
    platform: str
    key: str
    value: str


class MessageInput(BaseModel):
    """Input for sending a message."""
    platform: str
    channel_id: str
    content: str


_engine: Optional[BotEngine] = None
_api_key: Optional[str] = None


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """Verify API key if configured."""
    if not _api_key:
        return True
    if api_key and api_key == _api_key:
        return True
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


def create_app(config: Config, engine: BotEngine) -> FastAPI:
    """Create the FastAPI application."""
    
    global _engine, _api_key
    _engine = engine
    _api_key = getattr(config.server, 'api_key', None) or None
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
    
    app = FastAPI(
        title="Malachi the AiAS Bot API",
        description="Management API for Malachi the AiAS Bot",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    allowed_origins = ["http://localhost:5000", "http://127.0.0.1:5000"]
    if config.server.host == "0.0.0.0":
        logger.warning("API bound to 0.0.0.0 - ensure API key is configured for security")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/", dependencies=[Depends(verify_api_key)])
    async def root():
        """API root."""
        return {
            "name": "Malachi the AiAS Bot API",
            "version": "0.1.0",
            "status": "running",
            "auth_required": bool(_api_key),
        }
    
    @app.get("/status", dependencies=[Depends(verify_api_key)])
    async def get_status():
        """Get bot status and connected platforms."""
        status = _engine.get_status()
        return status.to_dict()
    
    @app.get("/platforms", dependencies=[Depends(verify_api_key)])
    async def list_platforms():
        """List platform connections."""
        platforms = []
        for name, handler in _engine.platforms.items():
            platforms.append({
                "name": name,
                "connected": handler.is_connected,
            })
        return {"platforms": platforms}
    
    @app.post("/platforms/{name}/connect", dependencies=[Depends(verify_api_key)])
    async def connect_platform(name: str):
        """Connect a platform."""
        handler = _engine.platforms.get(name)
        if not handler:
            raise HTTPException(status_code=404, detail=f"Platform {name} not configured")
        
        if handler.is_connected:
            return {"status": "already_connected"}
        
        try:
            await handler.connect()
            return {"status": "connected"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/platforms/{name}/disconnect", dependencies=[Depends(verify_api_key)])
    async def disconnect_platform(name: str):
        """Disconnect a platform."""
        handler = _engine.platforms.get(name)
        if not handler:
            raise HTTPException(status_code=404, detail=f"Platform {name} not configured")
        
        if not handler.is_connected:
            return {"status": "already_disconnected"}
        
        try:
            await handler.disconnect()
            return {"status": "disconnected"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/conversations", dependencies=[Depends(verify_api_key)])
    async def list_conversations(limit: int = 100):
        """List recent conversations."""
        conversations = await _engine.memory.get_all_conversations(limit)
        return {
            "conversations": [c.to_dict() for c in conversations]
        }
    
    @app.get("/conversations/{conversation_id}/messages", dependencies=[Depends(verify_api_key)])
    async def get_conversation_messages(conversation_id: str, limit: int = 50):
        """Get messages from a conversation."""
        messages = await _engine.memory.get_conversation_history(conversation_id, limit)
        return {
            "messages": [m.to_dict() for m in messages]
        }
    
    @app.delete("/conversations/{conversation_id}", dependencies=[Depends(verify_api_key)])
    async def clear_conversation(conversation_id: str):
        """Clear all messages from a conversation."""
        await _engine.memory.clear_conversation(conversation_id)
        return {"status": "cleared"}
    
    @app.get("/memory", dependencies=[Depends(verify_api_key)])
    async def list_memory(user_id: Optional[str] = None, platform: Optional[str] = None):
        """List memory entries."""
        if user_id and platform:
            from .models import Platform
            try:
                plat = Platform(platform)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
            
            memories = await _engine.memory.get_memory(user_id, plat)
            return {"memories": [m.to_dict() for m in memories]}
        
        return {"memories": [], "note": "Provide user_id and platform to filter"}
    
    @app.post("/memory", dependencies=[Depends(verify_api_key)])
    async def add_memory(input: MemoryInput):
        """Add a memory entry."""
        from .models import Platform
        try:
            plat = Platform(input.platform)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {input.platform}")
        
        memory = await _engine.memory.set_memory(
            input.user_id,
            plat,
            input.key,
            input.value,
        )
        return memory.to_dict()
    
    @app.post("/message", dependencies=[Depends(verify_api_key)])
    async def send_message(input: MessageInput):
        """Send a message to a platform/channel."""
        success = await _engine.send_message(
            input.platform,
            input.channel_id,
            input.content,
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send message")
        
        return {"status": "sent"}
    
    return app
