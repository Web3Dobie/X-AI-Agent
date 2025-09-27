"""
AI Service Layer for HTD Research Agent
Clean implementation with synchronous rate limiting
"""

import logging
import os
import time
from collections import deque
from typing import List, Dict, Any
from enum import Enum

import google.generativeai as genai
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIProvider(Enum):
    AZURE = "azure"
    GEMINI = "gemini"

class SimpleRateLimiter:
    """Simple synchronous rate limiter for Gemini API"""
    
    def __init__(self, requests_per_minute: int = 5):
        self.rpm = requests_per_minute
        self.requests = deque()
        self.logger = logging.getLogger("SimpleRateLimiter")
        
    def wait_if_needed(self):
        """Apply rate limiting before making API call"""
        now = time.time()
        
        # Remove requests older than 1 minute
        while self.requests and self.requests[0] < now - 60:
            self.requests.popleft()
            
        # Check if we need to wait
        if len(self.requests) >= self.rpm:
            sleep_time = 60 - (now - self.requests[0])
            self.logger.info(f"Rate limit: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
            
        # Record this request
        self.requests.append(now)

class AIService:
    """Unified AI service supporting Azure OpenAI and Google Gemini"""
    
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
        self.rate_limiter = None
        
        # Initialize based on provider
        if self.provider == AIProvider.AZURE:
            self._init_azure()
        else:
            self._init_gemini()
            
        self.logger.info(f"AIService initialized with provider: {self.provider.value}")
        
    def _init_azure(self):
        """Initialize Azure OpenAI client"""
        try:
            self.azure_client = AzureOpenAI(
                api_key=os.getenv('AZURE_OPENAI_API_KEY'),
                api_version=os.getenv('AZURE_API_VERSION', '2024-02-15-preview'),
                azure_endpoint=f"https://{os.getenv('AZURE_RESOURCE_NAME')}.cognitiveservices.azure.com/",
            )
            self.logger.info("Azure OpenAI client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure client: {e}")
            raise
            
    def _init_gemini(self):
        """Initialize Gemini client and rate limiter"""
        try:
            api_key = os.getenv('GEMINI_HUNTER-AGENT_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_HUNTER-AGENT_API_KEY not found in environment")
                
            genai.configure(api_key=api_key)
            self.rate_limiter = SimpleRateLimiter(requests_per_minute=50)
            
            self.logger.info("Gemini client and rate limiter initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    # ==================== PUBLIC INTERFACE ====================
    
    def generate_thread(self, prompt: str, parts: int = 5, delimiter: str = "---", 
                       max_tokens: int = 1500, temperature: float = 0.85) -> List[str]:
        """Generate a multi-part thread"""
        params = {
            "parts": parts,
            "delimiter": delimiter, 
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if self.provider == AIProvider.GEMINI:
            return self._generate_gemini_thread(prompt, params)
        else:
            return self._generate_azure_thread(prompt, params)
            
    def generate_tweet(self, prompt: str, temperature: float = 0.9, 
                      max_tokens: int = 280) -> str:
        """Generate a single tweet"""
        params = {
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if self.provider == AIProvider.GEMINI:
            return self._generate_gemini_tweet(prompt, params)
        else:
            return self._generate_azure_tweet(prompt, params)
            
    def generate_text(self, prompt: str, max_tokens: int = 1800, 
                     temperature: float = 0.9) -> str:
        """Generate longer form text"""
        params = {
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if self.provider == AIProvider.GEMINI:
            return self._generate_gemini_text(prompt, params)
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
    
    def _generate_gemini_thread(self, prompt: str, params: Dict) -> List[str]:
        """Generate thread using Gemini (rate limited)"""
        self.rate_limiter.wait_if_needed()
        
        try:
            model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
            model = genai.GenerativeModel(model_name)
            
            system_prompt = (
                f"You are Hunter, a witty, crypto-savvy Doberman. "
                f"Write exactly {params['parts']} tweet-length blurbs separated by \"{params['delimiter']}\". "
                f"Do NOT number the tweets. End each with '— Hunter 🐾.'"
            )
            
            full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
            
            generation_config = genai.types.GenerationConfig(
                temperature=params['temperature'],
                max_output_tokens=params['max_tokens'],
                top_p=1.0,
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                }
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
        
    def _generate_gemini_tweet(self, prompt: str, params: Dict) -> str:
        """Generate tweet using Gemini (rate limited)"""
        self.rate_limiter.wait_if_needed()
        
        try:
            model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
            model = genai.GenerativeModel(model_name)
            
            system_prompt = (
                "You are Hunter, a crypto-native Doberman. "
                "Write bold, witty, Web3-savvy tweets. "
                "Sign off with '— Hunter 🐾.' "
                "Keep it under 280 characters."
            )
            
            full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
            
            generation_config = genai.types.GenerationConfig(
                temperature=params['temperature'],
                max_output_tokens=params['max_tokens'],
                top_p=1.0,
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                }
            )
            
            if not response.text:
                raise ValueError("Gemini returned empty response")
                
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Gemini tweet generation failed: {e}")
            raise
        
    def _generate_gemini_text(self, prompt: str, params: Dict) -> str:
        """Generate long-form text using Gemini (rate limited)"""
        self.rate_limiter.wait_if_needed()
        
        try:
            model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
            model = genai.GenerativeModel(model_name)
            
            system_prompt = (
                "You are Hunter, a crypto-native Doberman. "
                "Write engaging, informative articles on crypto topics. "
                "Maintain your witty, insightful personality throughout."
            )
            
            full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
            
            generation_config = genai.types.GenerationConfig(
                temperature=params['temperature'],
                max_output_tokens=params['max_tokens'],
                top_p=1.0,
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                }
            )
            
            if not response.text:
                raise ValueError("Gemini returned empty response")
                
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Gemini text generation failed: {e}")
            raise

# ==================== SINGLETON INSTANCE ====================

_ai_service_instance = None

def get_ai_service() -> AIService:
    """Get or create singleton AIService instance"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance