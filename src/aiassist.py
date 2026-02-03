"""AiAssist API client for chat completions."""

import asyncio
import logging
from typing import List, Optional, Dict, Any

import aiohttp

from .config import AiAssistConfig


logger = logging.getLogger(__name__)


class AiAssistClient:
    """Client for AiAssist API."""
    
    def __init__(self, config: AiAssistConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def _headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.provider:
            headers["X-AiAssist-Provider"] = self.config.provider
        return headers
    
    async def connect(self) -> None:
        """Initialize HTTP session."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
    
    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a chat completion request to AiAssist API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to config model)
            temperature: Response creativity (defaults to config)
            max_tokens: Max response length (defaults to config)
            
        Returns:
            The assistant's response text
        """
        if not self._session:
            await self.connect()
        
        url = f"{self.config.api_url}/v1/chat/completions"
        
        payload = {
            "model": model or self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with self._session.post(url, json=payload, headers=self._headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    
                    error_text = await response.text()
                    
                    # Handle rate limits with exponential backoff
                    if response.status == 429 or "rate limit" in error_text.lower():
                        wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s...
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{self.config.retry_attempts}")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Retry on server errors
                    if response.status >= 500:
                        logger.warning(f"Server error {response.status}, retrying...")
                        await asyncio.sleep(1)
                        continue
                    
                    logger.error(f"AiAssist API error {response.status}: {error_text}")
                    raise Exception(f"API error {response.status}: {error_text}")
                    
            except aiohttp.ClientError as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception("All retry attempts failed")
    
    async def imagine(self, prompt: str) -> Optional[str]:
        """
        Generate an image using Pollinations.ai (free, no API key needed).
        
        Args:
            prompt: Description of the image to generate
            
        Returns:
            URL of the generated image
        """
        import urllib.parse
        
        # Pollinations.ai generates images via URL - completely free
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        return image_url
    
    async def validate_key(self) -> bool:
        """Validate the API key by making a test request."""
        if not self._session:
            await self.connect()
        
        url = f"{self.config.api_url}/v1/models"
        
        try:
            async with self._session.get(url, headers=self._headers) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def web_extract(
        self,
        url: str,
        extract_links: bool = False,
        max_content_length: int = 15000,
    ) -> Dict[str, Any]:
        """
        Extract content from a webpage using AiAssist's web extract API.
        
        Tries browser extraction first for SPA support, falls back to HTTP if it fails.
        
        Args:
            url: The URL to extract content from
            extract_links: Whether to extract links from the page
            max_content_length: Maximum content length to return
            
        Returns:
            Dict with url, title, content, domain, etc.
        """
        if not self._session:
            await self.connect()
        
        api_url = f"{self.config.api_url}/v1/web/extract"
        timeout = aiohttp.ClientTimeout(total=90)
        
        # Try browser extraction first (for SPAs)
        payload = {
            "url": url,
            "extract_links": extract_links,
            "max_content_length": max_content_length,
            "use_browser": True,
        }
        
        try:
            logger.info(f"Trying browser extraction for {url}...")
            async with self._session.post(api_url, json=payload, headers=self._headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success", False):
                        logger.info(f"Browser extraction succeeded ({data.get('latency_ms')}ms)")
                        return data
                    
                    # Browser extraction failed, try HTTP fallback
                    error_msg = data.get("error_message") or data.get("error_code") or "unknown"
                    logger.warning(f"Browser extraction failed: {error_msg}. Trying HTTP fallback...")
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Browser extraction request failed: {e}. Trying HTTP fallback...")
        
        # Fallback to HTTP extraction
        payload["use_browser"] = False
        
        try:
            logger.info(f"Trying HTTP extraction for {url}...")
            async with self._session.post(api_url, json=payload, headers=self._headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success", False):
                        logger.info(f"HTTP extraction succeeded ({data.get('latency_ms')}ms)")
                        return data
                    
                    error_msg = (
                        data.get("error_message") or 
                        data.get("error") or 
                        data.get("message") or 
                        f"Error code: {data.get('error_code', 'Unknown')}"
                    )
                    logger.error(f"HTTP extraction also failed: {error_msg}")
                    raise Exception(f"Web extract failed: {error_msg}")
                
                error_text = await response.text()
                logger.error(f"Web extract error {response.status}: {error_text}")
                raise Exception(f"Web extract failed ({response.status}): {error_text}")
                
        except aiohttp.ClientError as e:
            logger.error(f"Web extract request failed: {e}")
            raise
