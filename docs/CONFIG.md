# Configuration Reference

Complete reference for all Malachi the AiAS Bot configuration options.

---

## Configuration Methods

Malachi the AiAS Bot supports three configuration methods (in order of priority):

1. **Environment Variables** (highest priority)
2. **config.yaml file**
3. **Default values** (lowest priority)

---

## Quick Start

Copy the example config:

```bash
cp config.example.yaml config.yaml
```

Minimal configuration:

```yaml
aiassist:
  api_key: "aai_your_key_here"

platforms:
  discord:
    enabled: true
    bot_token: "your_discord_token"
```

---

## Full Configuration Reference

### AiAssist API

```yaml
aiassist:
  # Required: Your AiAssist API key
  api_key: "aai_xxxxxxxxxxxx"
  # Environment: AIASSIST_API_KEY
  
  # API endpoint (default: https://api.aiassist.net)
  api_url: "https://api.aiassist.net"
  # Environment: AIASSIST_API_URL
  
  # Default model for chat completions
  model: "llama-3.3-70b-versatile"
  # Environment: AIASSIST_MODEL
  # Options: llama-3.3-70b-versatile, gpt-4o, claude-3-opus, etc.
  
  # Temperature for response creativity (0.0 - 2.0)
  temperature: 0.7
  
  # Maximum tokens in response
  max_tokens: 1024
  
  # Enable streaming responses (if supported)
  streaming: false
  
  # Timeout for API requests in seconds
  timeout: 30
  
  # Retry failed requests
  retry_attempts: 3
  retry_delay: 1  # seconds
```

### Discord Platform

```yaml
platforms:
  discord:
    # Enable/disable Discord integration
    enabled: true
    
    # Discord bot token (from Developer Portal)
    bot_token: "your_bot_token"
    # Environment: DISCORD_BOT_TOKEN
    
    # Command prefix for text commands
    command_prefix: "!"
    
    # Response triggers
    respond_to_mentions: true      # Respond when @mentioned
    respond_to_dms: true           # Respond to direct messages
    respond_to_replies: true       # Respond when someone replies to bot
    
    # Channel filtering
    allowed_channels: []           # Empty = all channels
    # Example: ["123456789", "987654321"]
    
    blocked_channels: []           # Channels to ignore
    
    # User filtering
    allowed_users: []              # Empty = all users
    blocked_users: []              # Users to ignore
    admin_users: []                # Users with admin commands
    
    # Behavior
    typing_indicator: true         # Show "typing..." while generating
    delete_trigger_message: false  # Delete the user's message after responding
    
    # Rate limiting
    rate_limit_messages: 10        # Max messages per user
    rate_limit_window: 60          # Time window in seconds
    
    # Presence/status
    status: "online"               # online, idle, dnd, invisible
    activity_type: "playing"       # playing, watching, listening, competing
    activity_name: "with AI"       # Activity text
```

### Telegram Platform

```yaml
platforms:
  telegram:
    # Enable/disable Telegram integration
    enabled: true
    
    # Bot token (from @BotFather)
    bot_token: "123456789:ABCdef..."
    # Environment: TELEGRAM_BOT_TOKEN
    
    # Response triggers
    respond_to_private: true       # Respond to private messages
    respond_to_groups: true        # Respond in group chats
    require_mention_in_groups: true  # Only respond when @mentioned in groups
    
    # Chat filtering
    allowed_chats: []              # Empty = all chats
    blocked_chats: []              # Chats to ignore
    
    # User filtering
    allowed_users: []
    blocked_users: []
    admin_users: []
    
    # Behavior
    read_receipts: true            # Mark messages as read
    typing_indicator: true         # Show typing action
    
    # Rate limiting
    rate_limit_messages: 20
    rate_limit_window: 60
```

### Memory & Storage

```yaml
memory:
  # Enable persistent memory
  enabled: true
  
  # SQLite database path
  database: "data/aias.db"
  
  # Conversation history
  max_history: 100                 # Messages per conversation
  history_ttl: 604800              # TTL in seconds (7 days)
  
  # User memory
  max_memories_per_user: 50
  
  # Knowledge cache
  cache_knowledge: true
  knowledge_ttl: 3600              # Re-sync after 1 hour
  
  # Cleanup
  cleanup_interval: 86400          # Run cleanup daily
  cleanup_older_than: 2592000      # Delete data older than 30 days
```

### Bot Engine

```yaml
server:
  # Management API host
  # Use 127.0.0.1 (localhost) for security, 0.0.0.0 for network access
  host: "127.0.0.1"
  
  # Management API port
  port: 8080
  
  # Enable management API
  api_enabled: true
  
  # API authentication (REQUIRED when host is 0.0.0.0)
  api_key: ""
  # Environment: AIAS_API_KEY
  
  # Logging level
  log_level: "INFO"                # DEBUG, INFO, WARNING, ERROR
  
  # Log file (optional)
  log_file: "logs/aias.log"
  
  # Health check endpoint
  health_check: true
```

### Context Building

```yaml
context:
  # System prompt template
  system_template: |
    You are a helpful AI assistant powered by AiAssist.
    {directives}
    {knowledge}
  
  # Include user memories in context
  include_memories: true
  
  # Include knowledge base (synced from AiAssist)
  include_knowledge: true
  max_knowledge_items: 5
  
  # Include directives (synced from AiAssist)
  include_directives: true
  
  # Semantic search for relevant knowledge
  semantic_search: true
  similarity_threshold: 0.7
```

### Scheduling (Future)

```yaml
scheduler:
  # Enable scheduled tasks
  enabled: false
  
  # Scheduled messages
  messages: []
  # Example:
  # - cron: "0 9 * * *"           # Every day at 9 AM
  #   platform: "discord"
  #   channel: "123456789"
  #   message: "Good morning everyone!"
  
  # Sync schedule
  sync_knowledge_cron: "0 * * * *"   # Every hour
  sync_directives_cron: "0 0 * * *"  # Daily at midnight
```

---

## Environment Variables

All sensitive values can be set via environment variables:

| Variable | Config Path | Description |
|----------|-------------|-------------|
| `AIASSIST_API_KEY` | `aiassist.api_key` | AiAssist API key |
| `AIASSIST_API_URL` | `aiassist.api_url` | AiAssist API endpoint |
| `AIASSIST_MODEL` | `aiassist.model` | Default AI model |
| `DISCORD_BOT_TOKEN` | `platforms.discord.bot_token` | Discord bot token |
| `TELEGRAM_BOT_TOKEN` | `platforms.telegram.bot_token` | Telegram bot token |
| `AIAS_API_KEY` | `server.api_key` | Management API key |
| `LOG_LEVEL` | `server.log_level` | Logging verbosity |

### Using .env File

Create a `.env` file:

```bash
AIASSIST_API_KEY=aai_your_key_here
DISCORD_BOT_TOKEN=your_discord_token
TELEGRAM_BOT_TOKEN=your_telegram_token
```

The bot will automatically load `.env` on startup.

---

## Example Configurations

### Minimal Discord Bot

```yaml
aiassist:
  api_key: "aai_xxxxxxxxxxxx"

platforms:
  discord:
    enabled: true
    bot_token: "your_token"
```

### Minimal Telegram Bot

```yaml
aiassist:
  api_key: "aai_xxxxxxxxxxxx"

platforms:
  telegram:
    enabled: true
    bot_token: "your_token"
```

### Multi-Platform Setup

```yaml
aiassist:
  api_key: "aai_xxxxxxxxxxxx"
  model: "llama-3.3-70b-versatile"

platforms:
  discord:
    enabled: true
    bot_token: "discord_token"
    respond_to_mentions: true
    respond_to_dms: true
    
  telegram:
    enabled: true
    bot_token: "telegram_token"
    respond_to_private: true
    respond_to_groups: true
    require_mention_in_groups: true

memory:
  enabled: true
  max_history: 50

server:
  port: 8080
  log_level: "INFO"
```

### Production Setup

```yaml
aiassist:
  api_key: "${AIASSIST_API_KEY}"  # From environment
  api_url: "https://api.aiassist.net"
  model: "llama-3.3-70b-versatile"
  timeout: 60
  retry_attempts: 5

platforms:
  discord:
    enabled: true
    bot_token: "${DISCORD_BOT_TOKEN}"
    rate_limit_messages: 5
    rate_limit_window: 30
    admin_users: ["your_discord_id"]

memory:
  enabled: true
  database: "/var/lib/aias/aias.db"
  cleanup_interval: 86400

server:
  host: "127.0.0.1"              # Localhost only (secure)
  port: 8080
  api_enabled: true
  api_key: "${AIAS_API_KEY}"     # Require auth
  log_level: "WARNING"
  log_file: "/var/log/aias/aias.log"
```

---

## Security Best Practices

1. **Always use localhost by default** - Set `server.host: "127.0.0.1"`
2. **Require API key for network access** - If you must use `0.0.0.0`, set `api_key`
3. **Use environment variables for secrets** - Never commit tokens to git
4. **Enable rate limiting** - Prevent abuse with `rate_limit_messages`
5. **Use blocked lists** - Block known spam users/chats

---

## Validation

Check your configuration:

```bash
python main.py --validate-config
```

Output:
```
✓ AiAssist API key valid
✓ Discord token valid
✓ Telegram token valid
✓ Database path writable
✓ Configuration valid!
```
