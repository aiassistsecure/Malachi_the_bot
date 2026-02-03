"""SQLite memory layer for conversations, messages, and user memories."""

import json
import uuid
import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from .models import (
    Platform, MessageRole, Conversation, ChatMessage, Memory
)


class MemoryManager:
    """SQLite-based persistent memory for Malachi the AiAS Bot."""
    
    def __init__(self, database_path: str = "data/aias.db"):
        self.database_path = database_path
        self._db: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Initialize database connection and create tables."""
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._db = await aiosqlite.connect(self.database_path)
        self._db.row_factory = aiosqlite.Row
        
        await self._create_tables()
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
    
    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                author_id TEXT,
                author_name TEXT,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, key)
            );
            
            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_memory_user ON memory(user_id, platform);
            CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(platform, channel_id);
        """)
        await self._db.commit()
    
    async def get_or_create_conversation(
        self, 
        platform: Platform, 
        channel_id: str
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        cursor = await self._db.execute(
            "SELECT * FROM conversations WHERE platform = ? AND channel_id = ?",
            (platform.value, channel_id)
        )
        row = await cursor.fetchone()
        
        if row:
            return Conversation(
                id=row["id"],
                platform=Platform(row["platform"]),
                channel_id=row["channel_id"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
        
        conversation = Conversation(
            id=str(uuid.uuid4()),
            platform=platform,
            channel_id=channel_id,
        )
        
        await self._db.execute(
            "INSERT INTO conversations (id, platform, channel_id, metadata) VALUES (?, ?, ?, ?)",
            (conversation.id, platform.value, channel_id, json.dumps(conversation.metadata))
        )
        await self._db.commit()
        
        return conversation
    
    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        author_id: Optional[str] = None,
        author_name: Optional[str] = None,
    ) -> ChatMessage:
        """Add a message to a conversation."""
        message = ChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            author_id=author_id,
            author_name=author_name,
        )
        
        await self._db.execute(
            """INSERT INTO messages 
               (id, conversation_id, role, author_id, author_name, content, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message.id, conversation_id, role.value, author_id, author_name, content, message.timestamp.isoformat())
        )
        
        await self._db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), conversation_id)
        )
        
        await self._db.commit()
        return message
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[ChatMessage]:
        """Get recent messages from a conversation."""
        cursor = await self._db.execute(
            """SELECT * FROM messages 
               WHERE conversation_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (conversation_id, limit)
        )
        rows = await cursor.fetchall()
        
        messages = []
        for row in reversed(rows):
            messages.append(ChatMessage(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=MessageRole(row["role"]),
                content=row["content"],
                author_id=row["author_id"],
                author_name=row["author_name"],
                timestamp=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.utcnow(),
            ))
        
        return messages
    
    async def set_memory(
        self,
        user_id: str,
        platform: Platform,
        key: str,
        value: str,
    ) -> Memory:
        """Set or update a user memory entry."""
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        await self._db.execute(
            """INSERT INTO memory (id, user_id, platform, key, value, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, platform, key) 
               DO UPDATE SET value = ?, updated_at = ?""",
            (memory_id, user_id, platform.value, key, value, now, now, value, now)
        )
        await self._db.commit()
        
        return Memory(
            id=memory_id,
            user_id=user_id,
            platform=platform,
            key=key,
            value=value,
        )
    
    async def get_memory(
        self,
        user_id: str,
        platform: Platform,
        key: Optional[str] = None,
    ) -> List[Memory]:
        """Get user memory entries."""
        if key:
            cursor = await self._db.execute(
                "SELECT * FROM memory WHERE user_id = ? AND platform = ? AND key = ?",
                (user_id, platform.value, key)
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM memory WHERE user_id = ? AND platform = ?",
                (user_id, platform.value)
            )
        
        rows = await cursor.fetchall()
        return [
            Memory(
                id=row["id"],
                user_id=row["user_id"],
                platform=Platform(row["platform"]),
                key=row["key"],
                value=row["value"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
            )
            for row in rows
        ]
    
    async def get_all_conversations(self, limit: int = 100) -> List[Conversation]:
        """Get all conversations."""
        cursor = await self._db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        
        return [
            Conversation(
                id=row["id"],
                platform=Platform(row["platform"]),
                channel_id=row["channel_id"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            for row in rows
        ]
    
    async def clear_conversation(self, conversation_id: str) -> None:
        """Clear all messages from a conversation."""
        await self._db.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        await self._db.commit()
