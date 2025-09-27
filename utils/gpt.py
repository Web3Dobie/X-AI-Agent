import logging

# This file is now a simple pass-through to the centralized AIService.
# All new code should use get_ai_service() directly.
from services.ai_service import get_ai_service

logging.warning("The 'gpt.py' module is deprecated and will be removed. Please use 'services.ai_service.get_ai_service()' directly.")

# Maintain the old function names for any legacy code that might still call them.
generate_gpt_text = get_ai_service().generate_text
generate_gpt_thread = get_ai_service().generate_thread
generate_gpt_tweet = get_ai_service().generate_tweet

# """
# GPT utility module for generating tweets, threads, and longer text.
# UPDATED: Now uses AIService with backward-compatible wrappers
# Compatible with OpenAI SDK >=1.0.0 (Azure) and Google Gemini.
# """

# import logging
# import os
# import sys
# from typing import List
# from dotenv import load_dotenv

# # Add services directory to path
# sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'services'))

# from services.ai_service import get_ai_service
# from utils.config import LOG_DIR

# # Load env
# load_dotenv()

# # Configure logging  
# log_file = os.path.join(LOG_DIR, "gpt.log")
# os.makedirs(os.path.dirname(log_file), exist_ok=True)
# logging.basicConfig(
#     filename=log_file,
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
# )

# logger = logging.getLogger(__name__)

# # ==================== BACKWARD COMPATIBLE FUNCTIONS ====================
# # These functions maintain the exact same signatures as before
# # but now use the new AIService under the hood

# def generate_gpt_tweet(prompt: str, temperature: float = 0.9) -> str:
#     """
#     Generate a single tweet using AI service.
#     DEPRECATED: Use AIService.generate_tweet() directly for new code.
#     """
#     try:
#         ai_service = get_ai_service()
#         result = ai_service.generate_tweet(prompt, temperature=temperature)
        
#         # Log which provider was used
#         provider = os.getenv('AI_PROVIDER', 'azure')
#         logger.info(f"Generated tweet using {provider} provider")
        
#         return result
        
#     except Exception as e:
#         logger.error(f"Error in generate_gpt_tweet: {e}")
#         return "⚠️ Could not generate response."


# def generate_gpt_thread(
#     prompt: str, max_parts: int = 5, delimiter: str = "---", max_tokens: int = 1500
# ) -> List[str]:
#     """
#     Generate a multi-part thread for X using AI service.
#     DEPRECATED: Use AIService.generate_thread() directly for new code.
#     """
#     try:
#         ai_service = get_ai_service()
#         result = ai_service.generate_thread(
#             prompt, 
#             parts=max_parts, 
#             delimiter=delimiter, 
#             max_tokens=max_tokens
#         )
        
#         # Log which provider was used
#         provider = os.getenv('AI_PROVIDER', 'azure')
#         logger.info(f"Generated {len(result)}-part thread using {provider} provider")
        
#         return result
        
#     except Exception as e:
#         logger.error(f"Error in generate_gpt_thread: {e}")
#         return []


# def generate_gpt_text(prompt: str, max_tokens: int = 1800) -> str:
#     """
#     Generate longer form text (e.g., Substack article) using AI service.
#     DEPRECATED: Use AIService.generate_text() directly for new code.
#     """
#     try:
#         ai_service = get_ai_service()
#         result = ai_service.generate_text(prompt, max_tokens=max_tokens)
        
#         # Log which provider was used
#         provider = os.getenv('AI_PROVIDER', 'azure')
#         logger.info(f"Generated long-form text ({len(result)} chars) using {provider} provider")
        
#         return result
        
#     except Exception as e:
#         logger.error(f"Error in generate_gpt_text: {e}")
#         return "Unable to produce content at this time. Please try again later."

# # ==================== LEGACY AZURE CLIENT FUNCTIONS ====================
# # Keep these for reference but mark as deprecated

# def _get_azure_openai_client():
#     """
#     DEPRECATED: Direct Azure client access is deprecated.
#     Use AIService instead for provider abstraction.
#     """
#     logger.warning("_get_azure_openai_client() is deprecated. Use AIService instead.")
    
#     from openai import AzureOpenAI
#     from utils.config import (
#         AZURE_OPENAI_API_KEY,
#         AZURE_API_VERSION,
#         AZURE_RESOURCE_NAME,
#     )
    
#     return AzureOpenAI(
#         api_key=AZURE_OPENAI_API_KEY,
#         api_version=AZURE_API_VERSION,
#         azure_endpoint=f"https://{AZURE_RESOURCE_NAME}.cognitiveservices.azure.com/",
#     )

# # ==================== MIGRATION HELPERS ====================

# def get_current_ai_provider() -> str:
#     """Helper function to check which AI provider is currently active"""
#     return os.getenv('AI_PROVIDER', 'azure')

# def is_using_gemini() -> bool:
#     """Helper function to check if Gemini is the active provider"""
#     return get_current_ai_provider().lower() == 'gemini'

# def log_provider_usage(operation: str):
#     """Helper to log which provider was used for an operation"""
#     provider = get_current_ai_provider()
#     logger.info(f"Operation '{operation}' completed using {provider} provider")

# # ==================== HEALTH CHECK ====================

# def test_ai_service_health() -> dict:
#     """
#     Test the AI service to ensure it's working correctly.
#     Returns status information.
#     """
#     try:
#         ai_service = get_ai_service()
#         provider = get_current_ai_provider()
        
#         # Simple test generation
#         test_prompt = "Generate a simple test response."
#         test_result = ai_service.generate_tweet(test_prompt, temperature=0.1)
        
#         return {
#             "status": "healthy",
#             "provider": provider,
#             "test_successful": bool(test_result and len(test_result) > 0),
#             "test_result_length": len(test_result) if test_result else 0
#         }
        
#     except Exception as e:
#         logger.error(f"AI service health check failed: {e}")
#         return {
#             "status": "unhealthy",
#             "provider": get_current_ai_provider(),
#             "error": str(e),
#             "test_successful": False
#         }