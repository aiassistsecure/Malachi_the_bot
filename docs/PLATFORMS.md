# Platform Setup Guides

Detailed setup instructions for each supported messaging platform.

---

## Table of Contents

- [Discord](#discord)
- [Telegram](#telegram)
- [Future Platforms](#future-platforms)

---

## Discord

Discord uses bot accounts for automation. Self-bots violate Discord's Terms of Service and are not supported.

### Prerequisites

- A Discord account
- A server where you have admin permissions (or create one for testing)

### Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter a name for your bot (e.g., "Malachi the AiAS Bot")
4. Click **"Create"**

### Step 2: Create the Bot

1. In your application, go to the **"Bot"** section in the left sidebar
2. Click **"Add Bot"**
3. Confirm by clicking **"Yes, do it!"**

### Step 3: Configure Bot Settings

1. **Username**: Customize your bot's display name
2. **Icon**: Upload a profile picture for your bot
3. **Public Bot**: Uncheck if you want only you to add it to servers
4. **Privileged Gateway Intents**: Enable these:
   - ✅ **Message Content Intent** (required to read messages)
   - ✅ **Server Members Intent** (optional, for member info)
   - ✅ **Presence Intent** (optional, for status)

### Step 4: Get Your Bot Token

1. In the **"Bot"** section, find the **"Token"** area
2. Click **"Reset Token"** (or "Copy" if already generated)
3. **Save this token securely** - you won't be able to see it again!

> ⚠️ **Never share your bot token!** Anyone with this token can control your bot.

### Step 5: Invite Bot to Your Server

1. Go to the **"OAuth2"** section in the left sidebar
2. Click **"URL Generator"**
3. Select these scopes:
   - ✅ `bot`
   - ✅ `applications.commands` (for slash commands)
4. Select bot permissions:
   - ✅ Send Messages
   - ✅ Read Message History
   - ✅ Use Slash Commands
   - ✅ Embed Links
   - ✅ Attach Files (if needed)
   - ✅ Add Reactions (if needed)
5. Copy the generated URL
6. Open it in your browser
7. Select your server and authorize

### Step 6: Configure Malachi the AiAS Bot

Add your token to `config.yaml`:

```yaml
platforms:
  discord:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN_HERE"
    
    # Optional settings
    command_prefix: "!"           # Prefix for text commands
    respond_to_mentions: true     # Respond when @mentioned
    respond_to_dms: true          # Respond to direct messages
    allowed_channels: []          # Empty = all channels, or list channel IDs
    blocked_users: []             # User IDs to ignore
```

### Step 7: Run and Test

```bash
python main.py serve
```

Your bot should come online in Discord. Try:
- Mentioning the bot: `@Malachi the AiAS Bot hello!`
- Sending a DM to the bot
- Using slash commands: `/ask`, `/help`, `/info`, `/clear`, `/imagine`

### Bot Behavior

- **DMs**: Responds to all direct messages
- **Servers**: Only responds when @mentioned (not "chatty")
- **Slash Commands**: Available in all servers the bot is in

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot is offline | Check token is correct, check logs for errors |
| Bot doesn't respond | Enable Message Content Intent in developer portal |
| "Missing Access" error | Re-invite bot with correct permissions |
| Rate limited | Reduce message frequency, check for loops |
| Slash commands missing | Wait ~1 hour for sync, or kick and re-invite bot |

---

## Telegram

Telegram uses bot accounts created through @BotFather.

### Step 1: Create a Bot with BotFather

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Enter a **display name** (e.g., "My Malachi the AiAS Bot")
   - Enter a **username** (must end in `bot`, e.g., `myaias_bot`)
4. BotFather will give you a token like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
5. Save this token securely

### Step 2: Configure Bot Settings (Optional)

Send these commands to @BotFather to customize:

```
/setdescription - Set bot description
/setabouttext - Set "About" section
/setuserpic - Upload bot profile picture
/setcommands - Define bot commands menu
```

Example commands setup:
```
start - Start the bot
help - Show available commands
info - Bot information
clear - Clear conversation history
imagine - Generate an image
```

### Step 3: Configure Malachi the AiAS Bot

Add your token to `config.yaml`:

```yaml
platforms:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN_HERE"
    
    # Optional settings
    respond_to_groups: true       # Respond in group chats
    respond_to_private: true      # Respond to private messages
    require_mention_in_groups: true  # Only respond when @mentioned in groups
    allowed_chats: []             # Empty = all chats, or list chat IDs
    blocked_users: []             # User IDs to ignore
```

### Step 4: Run and Test

```bash
python main.py serve
```

Test by:
- Sending a private message to your bot
- Adding bot to a group and @mentioning it
- Using commands: `/start`, `/help`, `/info`, `/clear`, `/imagine`

### Bot Behavior

- **Private Chats**: Responds to all messages
- **Groups**: Only responds when @mentioned (not "chatty")
- **Commands**: Available in all chats

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Unauthorized" error | Check bot token is correct |
| Bot doesn't respond in groups | Add bot as admin, or enable group privacy mode in BotFather |
| Long messages cut off | This is handled automatically via message chunking |
| HTML formatting errors | Bot falls back to plain text automatically |

---

## Future Platforms

We're considering support for:

### Slack
- Workspace automation
- Slash commands and app mentions
- Status: Planned

### WhatsApp
- Business API integration
- Requires WhatsApp Business account
- Status: Researching

### Matrix
- Open-source chat protocol
- Self-hosted option
- Status: Considering

### Reddit
- Community management
- Moderation assistance
- Status: Researching

---

## Adding Custom Platforms

Want to add support for a new platform? See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

The platform handler interface is defined in `src/platforms/base.py`:

```python
class PlatformHandler:
    async def start(self) -> None:
        """Connect to the platform."""
        
    async def stop(self) -> None:
        """Disconnect from the platform."""
        
    def set_message_callback(self, callback) -> None:
        """Set the callback for incoming messages."""
```
