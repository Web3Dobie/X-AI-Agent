"""
AI Service Layer for Hunter Agent
Fully refactored for dynamic safety settings and a clean, consistent interface.
"""

import logging
import fcntl
import json
import os
import time
from collections import deque
from typing import List, Dict, Any, Optional
from enum import Enum

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIProvider(Enum):
    AZURE = "azure"
    GEMINI = "gemini"

class FileBasedRateLimiter:
    """Process-safe rate limiter using file system"""
    def __init__(self, requests_per_minute: int = 50):
        self.rpm = requests_per_minute
        self.lock_file = "/tmp/gemini_rate_limit.lock"
        self.requests_file = "/tmp/gemini_requests.json"
        self.logger = logging.getLogger("FileBasedRateLimiter")
        
    def wait_if_needed(self):
        import fcntl
        import json
        
        now = time.time()
        
        with open(self.lock_file, 'w') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                # Load recent requests
                if os.path.exists(self.requests_file):
                    with open(self.requests_file, 'r') as f:
                        requests = json.load(f)
                else:
                    requests = []
                
                # Clean old requests
                requests = [r for r in requests if r > now - 60]
                
                # Check rate limit
                if len(requests) >= self.rpm:
                    sleep_time = 60 - (now - requests[0])
                    self.logger.info(f"Rate limit: sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                
                # Add current request
                requests.append(now)
                
                # Save back
                with open(self.requests_file, 'w') as f:
                    json.dump(requests, f)
                    
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

class AIService:
    """Unified AI service supporting Azure OpenAI and Google Gemini"""

    def __init__(self):
        self.logger = logging.getLogger("AIService")
        provider_str = os.getenv('AI_PROVIDER', 'gemini').lower()
        try:
            self.provider = AIProvider(provider_str)
        except ValueError:
            self.logger.warning(f"Invalid AI_PROVIDER '{provider_str}', defaulting to Gemini")
            self.provider = AIProvider.GEMINI

        self.azure_client = None
        self.rate_limiter = None

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
            # --- START OF CHANGE 1 ---
            # self.rate_limiter = FileBasedRateLimiter() # <-- Comment this line out
            self.rate_limiter = None # <-- Add this line to ensure the attribute exists
            # --- END OF CHANGE 1 ---
            self.logger.info("Gemini client initialized (Rate Limiter DISABLED for testing)")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    # ==================== PUBLIC INTERFACE (REFACTORED) ====================

    def generate_text(self, prompt: str, max_tokens: int = 2048, system_instruction: str = None, safety_settings: dict = None) -> str:
        """Generates a single block of text."""
        if self.provider == AIProvider.GEMINI:
            return self._generate_gemini_content(prompt, max_tokens, system_instruction, safety_settings)
        else:
            return self._generate_azure_text(prompt, max_tokens, system_instruction)

    def generate_thread(self, prompt: str, parts: int, max_tokens: int, system_instruction: str = None, safety_settings: dict = None, delimiter: str = "---") -> List[str]:
        """Generates a multi-part thread."""
        if self.provider == AIProvider.GEMINI:
            # For Gemini, we ask for a single block of text with delimiters
            full_prompt = f"{prompt}\n\nPlease generate exactly {parts} parts separated by '{delimiter}'."
            raw_text = self._generate_gemini_content(full_prompt, max_tokens, system_instruction, safety_settings)
            thread_parts = raw_text.split(delimiter)
            return [part.strip() for part in thread_parts]
        else:
            return self._generate_azure_thread(prompt, parts, max_tokens, system_instruction, delimiter)

    # ==================== GEMINI IMPLEMENTATION (UNIFIED) ====================

    def _generate_gemini_content(self, prompt: str, max_tokens: int, system_instruction: Optional[str], safety_settings: Optional[Dict]) -> str:
        """
        Unified worker method for all Gemini text generation.
        """
        # --- START OF CHANGE 2 ---
        # self.rate_limiter.wait_if_needed() # <-- Comment this line out
        # --- END OF CHANGE 2 ---
        try:
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro-latest')
            model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=max_tokens,
                top_p=1.0,
            )

            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
                request_options={"timeout": 45}
            )

            if not response.parts:
                finish_reason = "UNKNOWN"
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason.name
                raise ValueError(f"Gemini returned no content. Finish Reason: {finish_reason}")
                
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Gemini content generation failed: {e}")
            raise

    # ==================== AZURE IMPLEMENTATIONS (UNCHANGED LOGIC) ====================

    def _generate_azure_text(self, prompt: str, max_tokens: int, system_instruction: Optional[str]) -> str:
        """Generate long-form text using Azure OpenAI"""
        # (This logic remains the same, but now uses direct parameters)
        system_content = system_instruction or "You are a helpful AI assistant."
        try:
            response = self.azure_client.chat.completions.create(
                model=os.getenv('AZURE_DEPLOYMENT_ID'),
                messages=[{"role": "system", "content": system_content}, {"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Azure text generation failed: {e}")
            raise

    def _generate_azure_thread(self, prompt: str, parts: int, max_tokens: int, system_instruction: Optional[str], delimiter: str) -> List[str]:
        """Generate thread using Azure OpenAI"""
        # (This logic remains the same, but now uses direct parameters)
        system_content = system_instruction or f"Generate {parts} paragraphs separated by '{delimiter}'."
        try:
            response = self.azure_client.chat.completions.create(
                model=os.getenv('AZURE_DEPLOYMENT_ID'),
                messages=[{"role": "system", "content": system_content}, {"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content.strip()
            return [p.strip() for p in content.split(delimiter)]
        except Exception as e:
            self.logger.error(f"Azure thread generation failed: {e}")
            raise

# ==================== SINGLETON INSTANCE ====================

_ai_service_instance = None
def get_ai_service() -> AIService:
    """Get or create singleton AIService instance"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance