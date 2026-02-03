#!/usr/bin/env python3
"""Malachi the AiAS Bot - AI-powered automation for Discord & Telegram."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import click
import uvicorn

from src.config import load_config
from src.engine import BotEngine
from src.api import create_app


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> None:
    """Configure logging level."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(level)
    logging.getLogger("aias").setLevel(level)


async def run_bot(config_path: str, with_api: bool) -> None:
    """Run the bot engine."""
    config = load_config(config_path)
    setup_logging(config.server.log_level)
    
    if not config.aiassist.api_key:
        logger.error("AiAssist API key is required. Set AIASSIST_API_KEY or configure in config.yaml")
        sys.exit(1)
    
    if not config.discord.enabled and not config.telegram.enabled:
        logger.error("At least one platform must be enabled. Configure Discord or Telegram in config.yaml")
        sys.exit(1)
    
    if config.server.host == "0.0.0.0" and not config.server.api_key:
        logger.error("API key required when binding to 0.0.0.0. Set AIAS_API_KEY or server.api_key in config")
        sys.exit(1)
    
    engine = BotEngine(config)
    
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await engine.start()
        
        if with_api and config.server.api_enabled:
            app = create_app(config, engine)
            
            uvicorn_config = uvicorn.Config(
                app,
                host=config.server.host,
                port=config.server.port,
                log_level=config.server.log_level.lower(),
            )
            server = uvicorn.Server(uvicorn_config)
            
            server_task = asyncio.create_task(server.serve())
            
            logger.info(f"Management API running on http://{config.server.host}:{config.server.port}")
            
            await shutdown_event.wait()
            
            server.should_exit = True
            await server_task
        else:
            logger.info("Bot is running. Press Ctrl+C to stop.")
            await shutdown_event.wait()
        
    finally:
        await engine.stop()


@click.group(invoke_without_command=True)
@click.option("--config", "-c", default="config.yaml", help="Path to config file")
@click.option("--with-api", is_flag=True, help="Start with management API")
@click.option("--validate-config", is_flag=True, help="Validate configuration and exit")
@click.pass_context
def cli(ctx, config: str, with_api: bool, validate_config: bool):
    """Malachi the AiAS Bot - AI-powered automation for Discord & Telegram."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    
    if validate_config:
        try:
            cfg = load_config(config)
            
            checks = []
            
            if cfg.aiassist.api_key:
                checks.append(("AiAssist API key", True))
            else:
                checks.append(("AiAssist API key", False))
            
            if cfg.discord.enabled and cfg.discord.bot_token:
                checks.append(("Discord token", True))
            elif cfg.discord.enabled:
                checks.append(("Discord token", False))
            
            if cfg.telegram.enabled and cfg.telegram.bot_token:
                checks.append(("Telegram token", True))
            elif cfg.telegram.enabled:
                checks.append(("Telegram token", False))
            
            db_path = Path(cfg.memory.database)
            if db_path.parent.exists() or db_path.parent == Path("."):
                checks.append(("Database path", True))
            else:
                checks.append(("Database path", False))
            
            from rich.console import Console
            from rich.table import Table
            
            console = Console()
            table = Table(title="Configuration Validation")
            table.add_column("Check", style="cyan")
            table.add_column("Status", style="green")
            
            all_valid = True
            for name, valid in checks:
                status = "[green]✓ Valid[/green]" if valid else "[red]✗ Missing[/red]"
                if not valid:
                    all_valid = False
                table.add_row(name, status)
            
            console.print(table)
            
            if all_valid:
                console.print("\n[green]✓ Configuration valid![/green]")
            else:
                console.print("\n[red]✗ Configuration has issues[/red]")
                sys.exit(1)
            
        except Exception as e:
            click.echo(f"Configuration error: {e}", err=True)
            sys.exit(1)
        
        return
    
    if ctx.invoked_subcommand is None:
        asyncio.run(run_bot(config, with_api))


@cli.command()
@click.pass_context
def run(ctx):
    """Run the bot without management API."""
    asyncio.run(run_bot(ctx.obj["config_path"], with_api=False))


@cli.command()
@click.pass_context
def serve(ctx):
    """Run the bot with management API."""
    asyncio.run(run_bot(ctx.obj["config_path"], with_api=True))


@cli.command()
def version():
    """Show version information."""
    from src import __version__
    click.echo(f"Malachi the AiAS Bot v{__version__}")


if __name__ == "__main__":
    cli()
