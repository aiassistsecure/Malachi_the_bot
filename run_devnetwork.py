#!/usr/bin/env python3
"""Run Malachi on DevNetwork only."""

import asyncio
import logging
import signal
import os
import sys
import argparse
from aiohttp import web

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config
from src.engine import BotEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

engine = None

async def health_handler(request):
    """Health check endpoint."""
    return web.json_response({
        "status": "ok",
        "bot": "malachi",
        "platform": "devnetwork",
        "connected": engine.is_running if engine else False
    })

async def start_health_server(port: int):
    """Start a simple health check HTTP server."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server running on http://0.0.0.0:{port}")
    return runner


async def main():
    global engine
    
    parser = argparse.ArgumentParser(description="Run Malachi on DevNetwork")
    parser.add_argument("--port", type=int, default=None, help="Port for health check server (optional)")
    args = parser.parse_args()
    
    config = load_config("config.yaml")
    
    if not config.aiassist.api_key:
        logger.error("AIASSIST_API_KEY required")
        sys.exit(1)
    
    if not config.devnetwork.enabled:
        logger.error("DevNetwork not enabled in config.yaml")
        sys.exit(1)
    
    if not config.devnetwork.bot_token:
        logger.error("DevNetwork bot_token required")
        sys.exit(1)
    
    config.discord.enabled = False
    config.telegram.enabled = False
    
    engine = BotEngine(config)
    
    shutdown_event = asyncio.Event()
    health_runner = None
    
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.port:
            health_runner = await start_health_server(args.port)
        
        await engine.start()
        logger.info("Malachi running on DevNetwork. Press Ctrl+C to stop.")
        await shutdown_event.wait()
    finally:
        await engine.stop()
        if health_runner:
            await health_runner.cleanup()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())
