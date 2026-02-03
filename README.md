# Malachi the AiAS Bot

**Open-source personal AI automation for Discord & Telegram**

An open-source bot framework that brings AI-powered automation to your favorite messaging platforms. Powered by [AiAssist API](https://aiassist.net) for intelligent, context-aware responses.

---

## Features

- **Multi-Platform** - Discord and Telegram support out of the box
- **AI-Powered** - Uses AiAssist API for intelligent, context-aware responses
- **Persistent Memory** - SQLite-based conversation history and preferences
- **Conversation Memory** - Remembers user preferences and context
- **Self-Hosted** - Runs on your machine, your data stays with you
- **Secure by Default** - Localhost-only binding, API key required for network access
- **Easy Setup** - Python + FastAPI + SQLite, beginner-friendly stack

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Your Messaging Platforms               │
│         Discord  │  Telegram  │  (Future)           │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│               Malachi the AiAS Bot Engine (8080)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Platforms  │  │   Memory    │  │  Scheduler  │  │
│  │  Handlers   │  │   (SQLite)  │  │   (Cron)    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │ API Calls
                         ▼
┌─────────────────────────────────────────────────────┐
│              AiAssist API (aiassist.net)            │
│  • Chat Completions    • Knowledge Base             │
│  • Multi-Model Access  • AI Directives              │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- AiAssist API key ([get one here](https://aiassist.net))
- Discord bot token and/or Telegram bot token

### Installation

```bash
# Clone the repository
git clone https://github.com/aiassistsecure/Malachi_the_bot.git
cd malachi_the_bot

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp config.example.yaml config.yaml
```

### Configuration

Edit `config.yaml`:

```yaml
# AiAssist API Configuration
aiassist:
  api_url: "https://api.aiassist.net"
  api_key: "aai_your_key_here"
  model: "llama-3.3-70b-versatile"

# Platform Configuration
platforms:
  discord:
    enabled: true
    bot_token: "your_discord_bot_token"
    
  telegram:
    enabled: true
    bot_token: "your_telegram_bot_token"

# Memory & Behavior
memory:
  enabled: true
  max_history: 100  # messages per conversation

# Bot Engine
server:
  host: "127.0.0.1"  # localhost only (secure default)
  port: 8080
```

### Run

```bash
# Validate configuration
python main.py --validate-config

# Start the bot
python main.py serve
```

---

## Platform Setup

### Discord

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token to your config
5. Enable required intents:
   - **Message Content Intent** (required)
   - **Server Members Intent** (optional)
6. Invite bot to your server with these permissions:
   - Send Messages
   - Read Message History
   - Use Slash Commands

**Bot Behavior:**
- Responds to all DMs automatically
- In servers, requires @mention to respond (not "chatty")
- Slash commands: `/ask`, `/help`, `/info`, `/clear`, `/imagine`, `/review`, `/deepsearch`

See [PLATFORMS.md](docs/PLATFORMS.md) for detailed instructions.

### Telegram

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token to your config

**Bot Behavior:**
- Responds to all private messages
- In groups, requires @mention to respond
- Commands: `/start`, `/help`, `/info`, `/clear`, `/imagine`, `/review`, `/deepsearch`

See [PLATFORMS.md](docs/PLATFORMS.md) for detailed instructions.

---

## Security

Malachi the AiAS Bot is designed to be secure by default:

| Setting | Default | Description |
|---------|---------|-------------|
| `server.host` | `127.0.0.1` | Binds to localhost only |
| `server.api_key` | None | Required when binding to `0.0.0.0` |

**To expose the management API on a network:**

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  api_key: "your_secure_api_key_here"  # REQUIRED for network binding
```

All API requests must include the `X-API-Key` header when running on `0.0.0.0`.

---

## Management API

The bot exposes a REST API for monitoring and control:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Bot status and connected platforms |
| `/platforms` | GET | List platform connections |
| `/conversations` | GET | View conversation history |
| `/conversations/{id}` | GET | Get specific conversation |
| `/conversations/{id}` | DELETE | Clear conversation history |
| `/memory/user/{id}` | GET | Get user preferences |

---

## Environment Variables

All config values can be overridden with environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `AIASSIST_API_KEY` | Your AiAssist API key | Yes |
| `AIASSIST_API_URL` | API endpoint (default: https://api.aiassist.net) | No |
| `DISCORD_BOT_TOKEN` | Discord bot token | If using Discord |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | If using Telegram |

---

## Project Structure

```
malachi_the_bot/
├── main.py              # Entry point (serve/validate commands)
├── config.yaml          # Configuration (gitignored)
├── config.example.yaml  # Example configuration
├── requirements.txt     # Python dependencies
├── src/
│   ├── config.py        # YAML + env var config loader
│   ├── models.py        # Message/Conversation dataclasses
│   ├── engine.py        # Core bot engine
│   ├── api.py           # Management API (FastAPI)
│   ├── memory.py        # SQLite persistence layer
│   ├── aiassist.py      # AiAssist API client
│   └── platforms/
│       ├── base.py      # Platform handler interface
│       ├── discord.py   # Discord bot handler
│       └── telegram.py  # Telegram bot handler
├── docs/
│   ├── ARCHITECTURE.md  # System design
│   ├── PLATFORMS.md     # Platform setup guides
│   └── CONFIG.md        # Configuration reference
├── CONTRIBUTING.md      # Contribution guidelines
└── LICENSE              # MIT License
```

---

## Comparison with Other Bots

| Feature | Malachi the AiAS Bot | ClawdBot | ChatGPT |
|---------|----------|----------|---------|
| Open Source | ✅ | ✅ | ❌ |
| Self-Hosted | ✅ | ✅ | ❌ |
| Discord | ✅ | ✅ | ❌ |
| Telegram | ✅ | ✅ | ❌ |
| Custom Knowledge | ✅ (AiAssist KB) | ❌ | ❌ |
| Behavior Rules | ✅ (Directives) | ❌ | ❌ |
| Multi-Model | ✅ | ✅ | ❌ |
| Image Generation | ✅ | ❌ | ✅ |

---

## Roadmap

- [x] Core bot engine
- [x] Discord integration
- [x] Telegram integration
- [x] AiAssist API integration
- [x] Persistent memory
- [x] Image generation (/imagine)
- [x] Security hardening
- [ ] Scheduled messages
- [ ] Proactive notifications
- [ ] Web management dashboard
- [ ] Voice message support
- [ ] Slack integration
- [ ] WhatsApp integration

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- **AiAssist Platform:** [https://aiassist.net](https://aiassist.net)
- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/aiassistsecure/Malachi_the_bot/issues)

---

Built with ❤️ by the AiAssist team
