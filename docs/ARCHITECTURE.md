# Architecture

This document describes the system design and technical architecture of Malachi the AiAS Bot.

---

## System Overview

Malachi the AiAS Bot is a modular, event-driven bot framework designed to:

1. **Connect** to messaging platforms (Discord, Telegram)
2. **Process** incoming messages with AI (via AiAssist API)
3. **Maintain** persistent memory and context
4. **Respond** intelligently based on knowledge and directives

```
┌──────────────────────────────────────────────────────────────────┐
│                        Malachi the AiAS Bot System                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐             │
│  │  Discord   │    │  Telegram  │    │  Future    │             │
│  │  Handler   │    │  Handler   │    │  Platforms │             │
│  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘             │
│        │                 │                 │                     │
│        └────────────┬────┴─────────────────┘                     │
│                     │                                            │
│                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Message Router                         │   │
│  │  • Normalizes messages from different platforms          │   │
│  │  • Applies rate limiting and filters                     │   │
│  │  • Routes to appropriate handler                         │   │
│  └────────────────────────────┬─────────────────────────────┘   │
│                               │                                  │
│                               ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Bot Engine Core                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │   Memory     │  │   Context    │  │   Response   │    │   │
│  │  │   Manager    │  │   Builder    │  │   Generator  │    │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │   │
│  └────────────────────────────┬─────────────────────────────┘   │
│                               │                                  │
│        ┌──────────────────────┼──────────────────────┐          │
│        ▼                      ▼                      ▼          │
│  ┌──────────┐          ┌──────────┐          ┌──────────┐       │
│  │  SQLite  │          │ AiAssist │          │  Config  │       │
│  │  Memory  │          │   API    │          │  Store   │       │
│  └──────────┘          └──────────┘          └──────────┘       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Platform Handlers

Each platform has a dedicated handler that:
- Manages connection/authentication
- Listens for incoming events
- Normalizes messages to a common format
- Sends responses back to the platform

```python
# Common message format
class Message:
    id: str
    platform: str        # "discord" | "telegram"
    channel_id: str      # Server/chat ID
    author_id: str       # User ID
    author_name: str     # Display name
    content: str         # Message text
    timestamp: datetime
    reply_to: str | None # If replying to another message
    attachments: list    # Files, images, etc.
```

### 2. Message Router

The router receives normalized messages and:
- Filters spam and rate-limited users
- Checks if the bot should respond (mentions, DMs, keywords)
- Queues messages for processing

```python
# Router decision flow
def should_respond(message: Message) -> bool:
    # Always respond to DMs
    if message.is_dm:
        return True
    
    # Check if bot is mentioned
    if bot_mentioned(message):
        return True
    
    # Check for trigger keywords
    if has_trigger_keyword(message):
        return True
    
    return False
```

### 3. Bot Engine Core

The engine processes messages through three stages:

#### Memory Manager
- Loads conversation history
- Retrieves relevant memories
- Stores new interactions

#### Context Builder
- Assembles the prompt with:
  - System directive (from AiAssist)
  - Relevant knowledge base entries
  - Conversation history
  - User preferences/memory

#### Response Generator
- Sends context to AiAssist API
- Streams or waits for response
- Post-processes response (formatting, safety)

### 4. AiAssist API Client

Handles all communication with AiAssist:

```python
class AiAssistClient:
    async def chat(self, messages: list, model: str = None) -> str:
        """Send chat completion request"""
        
    async def get_knowledge(self) -> list:
        """Fetch knowledge base entries"""
        
    async def get_directives(self) -> list:
        """Fetch AI directives"""
        
    async def search_knowledge(self, query: str) -> list:
        """Search relevant knowledge entries"""
```

---

## Automation Modes

### Assistant Mode

```
User Account ─────────────────────► Platform
                                        │
Bot Account ◄──── Malachi the AiAS Bot ◄────────────┘
     │                                  
     └─────────────────────────────► Platform (Response)
```

- Bot has its own account/identity
- Responds as a separate entity
- Safe and compliant with platform TOS

---

## Database Schema

SQLite database with the following tables:

### `conversations`
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,           -- discord, telegram
    channel_id TEXT NOT NULL,         -- Server/chat ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON                     -- Platform-specific data
);
```

### `messages`
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,               -- user, assistant, system
    author_id TEXT,
    author_name TEXT,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

### `memory`
```sql
CREATE TABLE memory (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,            -- Platform user ID
    platform TEXT NOT NULL,
    key TEXT NOT NULL,                -- Memory key (name, preference, etc.)
    value TEXT NOT NULL,              -- Memory value
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, platform, key)
);
```

### `knowledge_cache`
```sql
CREATE TABLE knowledge_cache (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    embedding BLOB,                   -- For local semantic search
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `directives_cache`
```sql
CREATE TABLE directives_cache (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Flow

### Message Processing

```
1. Platform receives message
   │
2. Handler normalizes to Message format
   │
3. Router checks if should respond
   │
4. Memory Manager loads context
   │  ├─ Conversation history (last N messages)
   │  ├─ User memories (preferences, name)
   │  └─ Relevant knowledge (semantic search)
   │
5. Context Builder creates prompt
   │  ├─ System: Active directives
   │  ├─ Context: Knowledge base entries
   │  ├─ History: Previous messages
   │  └─ User: Current message
   │
6. AiAssist API generates response
   │
7. Response sent back to platform
   │
8. Memory Manager stores interaction
```

### Knowledge Sync

```
1. Trigger sync (manual or scheduled)
   │
2. Fetch from AiAssist API
   │  ├─ GET /v1/contexts (knowledge)
   │  └─ GET /v1/directives
   │
3. Update local SQLite cache
   │
4. Optionally generate embeddings for search
```

---

## Security Model

### API Key Protection

- Never log or expose API keys
- Store in environment variables or encrypted config
- Validate key on startup

### Platform Token Security

- Discord/Telegram tokens stored securely
- Support for encrypted config files
- API key required when exposing management API to network

### Rate Limiting

- Per-user rate limits to prevent abuse
- Global rate limit to protect API quota
- Configurable limits per platform

### Message Filtering

- Optional content moderation before processing
- Block list for users/channels
- Keyword filtering

---

## Configuration Hierarchy

```
1. Environment Variables (highest priority)
   ↓
2. config.yaml
   ↓
3. Default values (lowest priority)
```

Example resolution:
```yaml
# config.yaml
aiassist:
  api_key: "aai_config_key"

# Environment: AIASSIST_API_KEY=aai_env_key

# Result: aai_env_key (env takes priority)
```

---

## Extensibility

### Adding a New Platform

1. Create handler in `src/platforms/`
2. Implement the `PlatformHandler` interface:

```python
class PlatformHandler(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to platform"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully disconnect"""
    
    @abstractmethod
    async def send_message(self, channel_id: str, content: str) -> None:
        """Send a message to a channel"""
    
    @abstractmethod
    def on_message(self, callback: Callable) -> None:
        """Register message handler"""
```

3. Register in `engine.py`
4. Add configuration section

### Adding Custom Commands

```python
# src/commands/example.py
from src.engine import command

@command(name="ping", description="Check if bot is alive")
async def ping_command(ctx):
    await ctx.reply("Pong! 🏓")
```

---

## Performance Considerations

### Memory Management

- Limit conversation history to last N messages
- Periodic cleanup of old conversations
- Lazy loading of knowledge base

### Caching

- Cache AiAssist knowledge locally
- Cache user preferences in memory
- Invalidate on sync

### Concurrency

- Async/await throughout
- Connection pooling for SQLite
- Parallel platform handlers

---

## Monitoring & Logging

### Log Levels

- `DEBUG`: Detailed message processing
- `INFO`: Connection status, syncs
- `WARNING`: Rate limits, retries
- `ERROR`: API failures, connection issues

### Metrics (Future)

- Messages processed per hour
- API calls and latency
- Memory usage
- Error rates

---

## Deployment Options

### Local Development

```bash
python main.py
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

### Systemd Service

```ini
[Unit]
Description=Malachi the AiAS Bot
After=network.target

[Service]
Type=simple
User=aias
WorkingDirectory=/opt/aias-bot
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Cloud Platforms

- Replit (recommended for beginners)
- Railway
- Fly.io
- Any VPS with Python 3.11+
