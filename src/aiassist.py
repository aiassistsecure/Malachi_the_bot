"""AiAssist API client for chat completions."""

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
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
    
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
                    logger.error(f"AiAssist API error {response.status}: {error_text}")
                    
                    if response.status >= 500:
                        continue
                    
                    raise Exception(f"API error {response.status}: {error_text}")
                    
            except aiohttp.ClientError as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise
        
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
