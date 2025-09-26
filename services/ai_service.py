"""
AI Service Layer for HTD Research Agent
Provides unified interface for Azure OpenAI and Google Gemini APIs
with rate limiting, queueing, and fallback capabilities.
"""

import asyncio
import logging
import os
import time
from collections import deque
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import google.generativeai as genai
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIProvider(Enum):
    AZURE = "azure"
    GEMINI = "gemini"

@dataclass
class AIRequest:
    """Represents a queued AI generation request"""
    prompt: str
    request_type: str
    params: Dict[str, Any]
    future: asyncio.Future
    timestamp: float

class GeminiRateLimiter:
    """
    Token bucket rate limiter for Gemini API
    Ensures we stay under 60 requests/minute with smart queuing
    """
    
    def __init__(self, requests_per_minute: int = 50):  # 10 request buffer
        self.rpm = requests_per_minute
        self.requests = deque()  # Timestamp tracking
        self.request_queue = asyncio.Queue()  # Request queue
        self.is_processing = False
        self.logger = logging.getLogger("GeminiRateLimiter")
        
    async def enqueue_request(self, request: AIRequest) -> Any:
        """Add request to queue and wait for processing"""
        await self.request_queue.put(request)
        
        # Start processor if not running
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
            
        # Wait for result
        return await request.future
        
    async def _process_queue(self):
        """Process queued requests with rate limiting"""
        self.is_processing = True
        self.logger.info("🎯 Gemini queue processor started")
        
        try:
            while True:
                # Get next request (wait if queue empty)
                try:
                    request = await asyncio.wait_for(
                        self.request_queue.get(), 
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    # No requests for 5 seconds, stop processor
                    break
                    
                # Apply rate limiting
                await self._acquire_rate_limit()
                
                # Process request
                try:
                    if request.request_type == "thread":
                        result = await self._call_gemini_thread(
                            request.prompt, 
                            request.params
                        )
                    elif request.request_type == "tweet":
                        result = await self._call_gemini_tweet(
                            request.prompt,
                            request.params
                        )
                    elif request.request_type == "text":
                        result = await self._call_gemini_text(
                            request.prompt,
                            request.params
                        )
                    else:
                        raise ValueError(f"Unknown request type: {request.request_type}")
                        
                    request.future.set_result(result)
                    self.logger.info(f"✅ Processed {request.request_type} request")
                    
                except Exception as e:
                    self.logger.error(f"❌ Request failed: {e}")
                    request.future.set_exception(e)
                    
        finally:
            self.is_processing = False
            self.logger.info("⏹️ Gemini queue processor stopped")
            
    async def _acquire_rate_limit(self):
        """Apply rate limiting before making API call"""
        now = time.time()
        
        # Remove requests older than 1 minute
        while self.requests and self.requests[0] < now - 60:
            self.requests.popleft()
            
        # Check if we need to wait
        if len(self.requests) >= self.rpm:
            sleep_time = 60 - (now - self.requests[0])
            self.logger.info(f"⏳ Rate limit: sleeping {sleep_time:.1f}s")
            await asyncio.sleep(sleep_time)
            
        # Record this request
        self.requests.append(now)
        
    async def _call_gemini_thread(self, prompt: str, params: Dict) -> List[str]:
        """Make actual Gemini API call for thread generation"""
        try:
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
            model = genai.GenerativeModel(model_name)
            
            system_prompt = (
                f"You are Hunter, a witty, crypto-savvy Doberman. "
                f"Write exactly {params['parts']} tweet-length blurbs separated by \"{params['delimiter']}\". "
                f"Do NOT number the tweets. End each with '— Hunter 🐾.'"
            )
            
            full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=params['temperature'],
                max_output_tokens=params['max_tokens'],
                top_p=1.0,
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            if not response.text:
                raise ValueError("Gemini returned empty response")
                
            content = response.text.strip()
            parts = content.split(params['delimiter'])
            if len(parts) < params['parts']:
                parts = content.split("\n\n")
            return [p.strip() for p in parts if p.strip()][:params['parts']]
            
        except Exception as e:
            self.logger.error(f"Gemini thread generation failed: {e}")
            raise
        
    async def _call_gemini_tweet(self, prompt: str, params: Dict) -> str:
        """Make actual Gemini API call for tweet generation"""  
        try:
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
            model = genai.GenerativeModel(model_name)
            
            system_prompt = (
                "You are Hunter, a crypto-native Doberman. "
                "Write bold, witty, Web3-savvy tweets. "
                "Sign off with '— Hunter 🐾.' "
                "Keep it under 280 characters."
            )
            
            full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=params['temperature'],
                max_output_tokens=params['max_tokens'],
                top_p=1.0,
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            if not response.text:
                raise ValueError("Gemini returned empty response")
                
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Gemini tweet generation failed: {e}")
            raise
        
    async def _call_gemini_text(self, prompt: str, params: Dict) -> str:
        """Make actual Gemini API call for text generation"""
        try:
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
            model = genai.GenerativeModel(model_name)
            
            system_prompt = (
                "You are Hunter, a crypto-native Doberman. "
                "Write engaging, informative articles on crypto topics. "
                "Maintain your witty, insightful personality throughout."
            )
            
            full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=params['temperature'],
                max_output_tokens=params['max_tokens'],
                top_p=1.0,
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            if not response.text:
                raise ValueError("Gemini returned empty response")
                
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Gemini text generation failed: {e}")
            raise

class AIService:
    """
    Unified AI service supporting Azure OpenAI and Google Gemini
    with automatic provider switching and rate limiting
    """
    
    def __init__(self):
        self.logger = logging.getLogger("AIService")
        
        # Provider selection from environment
        provider_str = os.getenv('AI_PROVIDER', 'azure').lower()
        try:
            self.provider = AIProvider(provider_str)
        except ValueError:
            self.logger.warning(f"Invalid AI_PROVIDER '{provider_str}', defaulting to Azure")
            self.provider = AIProvider.AZURE
            
        # Initialize clients
        self.azure_client = None
        self.gemini_client = None
        self.rate_limiter = None
        
        # Initialize based on provider
        if self.provider == AIProvider.AZURE:
            self._init_azure()
        else:
            self._init_gemini()
            
        self.logger.info(f"🤖 AIService initialized with provider: {self.provider.value}")
        
    def _init_azure(self):
        """Initialize Azure OpenAI client"""
        try:
            self.azure_client = AzureOpenAI(
                api_key=os.getenv('AZURE_OPENAI_API_KEY'),
                api_version=os.getenv('AZURE_API_VERSION', '2024-02-15-preview'),
                azure_endpoint=f"https://{os.getenv('AZURE_RESOURCE_NAME')}.cognitiveservices.azure.com/",
            )
            self.logger.info("✅ Azure OpenAI client initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Azure client: {e}")
            raise
            
    def _init_gemini(self):
        """Initialize Gemini client and rate limiter"""
        try:
            api_key = os.getenv('GEMINI_HUNTER-AGENT_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_HUNTER-AGENT_API_KEY not found in environment")
                
            genai.configure(api_key=api_key)
            
            # Initialize rate limiter for Gemini
            self.rate_limiter = GeminiRateLimiter(requests_per_minute=50)
            
            self.logger.info("✅ Gemini client and rate limiter initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Gemini client: {e}")
            raise
    
    # ==================== PUBLIC INTERFACE ====================
    
    def generate_thread(self, prompt: str, parts: int = 5, delimiter: str = "---", 
                       max_tokens: int = 1500, temperature: float = 0.85) -> List[str]:
        """
        Generate a multi-part thread
        
        Args:
            prompt: The generation prompt
            parts: Number of thread parts to generate
            delimiter: Delimiter to split parts on
            max_tokens: Maximum tokens per generation
            temperature: Generation temperature (0.0-1.0)
            
        Returns:
            List of thread parts as strings
        """
        params = {
            "parts": parts,
            "delimiter": delimiter, 
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if self.provider == AIProvider.GEMINI:
            return asyncio.run(self._generate_gemini_thread(prompt, params))
        else:
            return self._generate_azure_thread(prompt, params)
            
    def generate_tweet(self, prompt: str, temperature: float = 0.9, 
                      max_tokens: int = 280) -> str:
        """
        Generate a single tweet
        
        Args:
            prompt: The generation prompt
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum tokens (Twitter limit is ~280 chars)
            
        Returns:
            Generated tweet as string
        """
        params = {
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if self.provider == AIProvider.GEMINI:
            return asyncio.run(self._generate_gemini_tweet(prompt, params))
        else:
            return self._generate_azure_tweet(prompt, params)
            
    def generate_text(self, prompt: str, max_tokens: int = 1800, 
                     temperature: float = 0.9) -> str:
        """
        Generate longer form text (articles, etc.)
        
        Args:
            prompt: The generation prompt  
            max_tokens: Maximum tokens for generation
            temperature: Generation temperature (0.0-1.0)
            
        Returns:
            Generated text as string
        """
        params = {
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if self.provider == AIProvider.GEMINI:
            return asyncio.run(self._generate_gemini_text(prompt, params))
        else:
            return self._generate_azure_text(prompt, params)
    
    # ==================== AZURE IMPLEMENTATIONS ====================
    
    def _generate_azure_thread(self, prompt: str, params: Dict) -> List[str]:
        """Generate thread using Azure OpenAI"""
        try:
            system_content = (
                f"You are Hunter, a witty, crypto-savvy Doberman. "
                f"Write exactly {params['parts']} tweet-length blurbs separated by \"{params['delimiter']}\". "
                f"Do NOT number the tweets. End each with '— Hunter 🐾.'"
            )
            
            response = self.azure_client.chat.completions.create(
                model=os.getenv('AZURE_DEPLOYMENT_ID'),
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                temperature=params['temperature'],
                max_tokens=params['max_tokens'],
                top_p=1.0,
            )
            
            content = response.choices[0].message.content.strip()
            parts = content.split(params['delimiter'])
            if len(parts) < params['parts']:
                parts = content.split("\n\n")
            return [p.strip() for p in parts if p.strip()][:params['parts']]
            
        except Exception as e:
            self.logger.error(f"Azure thread generation failed: {e}")
            return []
            
    def _generate_azure_tweet(self, prompt: str, params: Dict) -> str:
        """Generate tweet using Azure OpenAI"""
        try:
            response = self.azure_client.chat.completions.create(
                model=os.getenv('AZURE_DEPLOYMENT_ID'),
                messages=[
                    {
                        "role": "system",
                        "content": "You are Hunter, a crypto-native Doberman. Write bold, witty, Web3-savvy tweets. Sign off with '— Hunter 🐾.'"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=params['temperature'],
                max_tokens=params['max_tokens'],
                top_p=1.0,
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Azure tweet generation failed: {e}")
            return "⚠️ Could not generate response."
            
    def _generate_azure_text(self, prompt: str, params: Dict) -> str:
        """Generate long-form text using Azure OpenAI"""
        try:
            response = self.azure_client.chat.completions.create(
                model=os.getenv('AZURE_DEPLOYMENT_ID'),
                messages=[
                    {
                        "role": "system",
                        "content": "You are Hunter, a crypto-native Doberman. Write engaging, informative articles on crypto topics."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=params['temperature'],
                max_tokens=params['max_tokens'],
                top_p=1.0,
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Azure text generation failed: {e}")
            return "Unable to produce content at this time. Please try again later."
    
    # ==================== GEMINI IMPLEMENTATIONS ====================
    
    async def _generate_gemini_thread(self, prompt: str, params: Dict) -> List[str]:
        """Generate thread using Gemini (queued and rate limited)"""
        request = AIRequest(
            prompt=prompt,
            request_type="thread",
            params=params,
            future=asyncio.Future(),
            timestamp=time.time()
        )
        
        return await self.rate_limiter.enqueue_request(request)
        
    async def _generate_gemini_tweet(self, prompt: str, params: Dict) -> str:
        """Generate tweet using Gemini (queued and rate limited)"""
        request = AIRequest(
            prompt=prompt,
            request_type="tweet", 
            params=params,
            future=asyncio.Future(),
            timestamp=time.time()
        )
        
        return await self.rate_limiter.enqueue_request(request)
        
    async def _generate_gemini_text(self, prompt: str, params: Dict) -> str:
        """Generate long-form text using Gemini (queued and rate limited)"""
        request = AIRequest(
            prompt=prompt,
            request_type="text",
            params=params, 
            future=asyncio.Future(),
            timestamp=time.time()
        )
        
        return await self.rate_limiter.enqueue_request(request)

# ==================== SINGLETON INSTANCE ====================

# Global service instance for easy access
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Get or create singleton AIService instance"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance