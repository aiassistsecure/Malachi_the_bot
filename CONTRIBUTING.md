# Contributing to Malachi the AiAS Bot

Thank you for your interest in contributing to Malachi the AiAS Bot! This document provides guidelines and information for contributors.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We expect everyone to:

- Be respectful and considerate
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Accept responsibility for mistakes and learn from them

### Unacceptable Behavior

- Harassment, discrimination, or personal attacks
- Trolling or intentionally inflammatory comments
- Publishing others' private information
- Any conduct that would be inappropriate in a professional setting

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- A code editor (VS Code recommended)
- Discord and/or Telegram accounts for testing

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/aiassistsecure/Malachi_the_bot.git
   cd aias-bot
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/aiassistsecure/Malachi_the_bot.git
   ```

---

## Development Setup

### Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Configure for Development

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your test credentials
```

### Run in Development Mode

```bash
python main.py --debug
```

---

## How to Contribute

### Types of Contributions

We welcome:

- **Bug fixes** - Fix issues and improve stability
- **Features** - Add new functionality
- **Documentation** - Improve docs, add examples
- **Platform integrations** - Add support for new platforms
- **Tests** - Improve test coverage
- **Translations** - Localize documentation

### Finding Issues

- Check [GitHub Issues](https://github.com/aiassistsecure/Malachi_the_bot/issues) for open tasks
- Look for issues labeled `good first issue` if you're new
- Look for `help wanted` for issues needing contributors

### Proposing Features

Before starting work on a major feature:

1. Check existing issues and PRs to avoid duplicates
2. Open a new issue to discuss your proposal
3. Wait for feedback before implementing

---

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 2. Make Your Changes

- Write clean, readable code
- Follow the coding standards (below)
- Add tests for new functionality
- Update documentation as needed

### 3. Commit Your Changes

Write clear, concise commit messages:

```bash
# Good
git commit -m "Add Slack platform integration"
git commit -m "Fix memory leak in conversation handler"

# Bad
git commit -m "fixed stuff"
git commit -m "wip"
```

For larger changes, use conventional commits:

```
type(scope): description

feat(telegram): add image generation command
fix(discord): handle rate limit errors gracefully
docs(readme): add troubleshooting section
```

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Description of what and why
- Link to related issues
- Screenshots/examples if applicable

### 5. Review Process

- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged

---

## Coding Standards

### Python Style

We follow PEP 8 with some modifications:

```python
# Good: Clear, descriptive names
async def send_message_to_channel(channel_id: str, content: str) -> Message:
    """Send a message to a specific channel."""
    pass

# Bad: Unclear abbreviations
async def snd_msg(cid, c):
    pass
```

### Type Hints

Use type hints for all functions:

```python
from typing import Optional, List

async def get_user_memories(
    user_id: str,
    platform: str,
    limit: Optional[int] = None
) -> List[Memory]:
    """Retrieve memories for a user."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_rate_limit(messages: int, window: int) -> float:
    """Calculate the rate limit for a user.
    
    Args:
        messages: Number of messages sent
        window: Time window in seconds
        
    Returns:
        Messages per second rate
        
    Raises:
        ValueError: If window is zero
    """
    if window == 0:
        raise ValueError("Window cannot be zero")
    return messages / window
```

### Async/Await

Use async for all I/O operations:

```python
# Good
async def fetch_knowledge() -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Bad (blocking)
def fetch_knowledge() -> list:
    response = requests.get(url)
    return response.json()
```

### Error Handling

Handle errors gracefully with specific exceptions:

```python
class AiASError(Exception):
    """Base exception for Malachi the AiAS Bot."""
    pass

class PlatformConnectionError(AiASError):
    """Failed to connect to a platform."""
    pass

class APIError(AiASError):
    """AiAssist API error."""
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_memory.py

# Run with verbose output
pytest -v
```

### Writing Tests

Place tests in the `tests/` directory:

```python
# tests/test_memory.py
import pytest
from src.memory import MemoryManager

@pytest.fixture
def memory_manager():
    """Create a test memory manager."""
    return MemoryManager(":memory:")  # In-memory SQLite

async def test_store_memory(memory_manager):
    """Test storing a memory entry."""
    await memory_manager.store(
        user_id="123",
        platform="discord",
        key="name",
        value="Alice"
    )
    
    result = await memory_manager.get("123", "discord", "name")
    assert result == "Alice"

async def test_memory_not_found(memory_manager):
    """Test retrieving non-existent memory."""
    result = await memory_manager.get("999", "discord", "unknown")
    assert result is None
```

### Test Coverage

We aim for >80% test coverage. Check coverage:

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Documentation

### Updating Docs

Documentation lives in the `docs/` folder:

- `ARCHITECTURE.md` - System design
- `PLATFORMS.md` - Platform setup guides
- `CONFIG.md` - Configuration reference

### Documentation Style

- Use clear, simple language
- Include code examples
- Add screenshots where helpful
- Keep information up-to-date

### Building Docs

```bash
# Preview docs locally (if using mkdocs)
mkdocs serve
```

---

## Adding a New Platform

To add support for a new messaging platform:

### 1. Create Handler

Create `src/platforms/yourplatform.py`:

```python
from src.platforms.base import PlatformHandler

class YourPlatformHandler(PlatformHandler):
    """Handler for YourPlatform integration."""
    
    name = "yourplatform"
    
    async def connect(self) -> None:
        """Connect to the platform."""
        pass
    
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        pass
    
    async def send_message(self, channel_id: str, content: str) -> None:
        """Send a message."""
        pass
    
    def on_message(self, callback) -> None:
        """Register message callback."""
        pass
```

### 2. Add Configuration

Update `docs/CONFIG.md` with platform settings.

### 3. Add Setup Guide

Add section to `docs/PLATFORMS.md`.

### 4. Add Tests

Create `tests/test_yourplatform.py`.

### 5. Update README

Add platform to the supported platforms list.

---

## Questions?

- Open a [GitHub Discussion](https://github.com/aiassistsecure/Malachi_the_bot/discussions)
- Join our Discord community (coming soon)
- Email: support@aiassist.net

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Malachi the AiAS Bot! 🎉
