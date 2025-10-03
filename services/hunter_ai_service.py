# services/hunter_ai_service.py

from .ai_service import get_ai_service
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Define Hunter's specific safety policy
HUNTER_AGENT_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# Hunter's CORE persona
HUNTER_CORE_PERSONA = """You are Hunter 🐾, a witty and sharp crypto expert. 
Your analysis is insightful but never hype-driven. You explain complex topics simply, 
inject personality with emojis, and always end with your signature: — Hunter 🐾"""


class HunterAIService:
    def __init__(self):
        self.ai_service = get_ai_service()
    
    @property
    def provider(self):
        """Expose the underlying AI provider for logging purposes."""
        return self.ai_service.provider

    def generate_headline_comment(self, headline: str) -> str:
        """Generates Hunter's one-sentence take on a headline."""
        prompt = f"Crypto news: {headline}\n\nWrite ONE witty sentence. End with: — Hunter 🐾"
        
        try:
            content = self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=200,
                system_instruction="You are Hunter, a sharp crypto analyst dog. Be brief and clever.",
                safety_settings=HUNTER_AGENT_SAFETY_SETTINGS
            )
            return content.strip()
        except Exception as e:
            raise Exception(f"Error generating comment: {e}")

    def generate_analysis(self, prompt: str, max_tokens: int = 2000, system_instruction: str = None) -> str:
        """
        Generates long-form analytical content with Hunter's voice.
        Used for articles, detailed analysis, and explanations.
        
        Args:
            prompt: The content request or topic to analyze
            max_tokens: Maximum length of generated content
            system_instruction: Optional task-specific rules (Hunter persona is always included)
        """
        # Combine Hunter's core persona with any task-specific instructions
        full_system_instruction = HUNTER_CORE_PERSONA
        if system_instruction:
            full_system_instruction += f"\n\n{system_instruction}"
        
        try:
            content = self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                system_instruction=full_system_instruction,
                safety_settings=HUNTER_AGENT_SAFETY_SETTINGS
            )
            return content.strip()
        except Exception as e:
            raise Exception(f"Error generating Hunter analysis: {e}")

    def generate_content(self, input_text: str, task_rules: str, max_tokens: int) -> str:
        """
        Legacy method for backwards compatibility.
        Consider using generate_analysis() for new code.
        """
        system_instruction = f"{HUNTER_CORE_PERSONA}\n\n{task_rules}"
        prompt = f"Based on the following input, please generate the content:\n\"{input_text}\""
        
        try:
            content = self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                system_instruction=system_instruction,
                safety_settings=HUNTER_AGENT_SAFETY_SETTINGS
            )
            return content.strip()
        except Exception as e:
            raise Exception(f"Error generating Hunter content: {e}")

    def generate_thread(self, prompt: str, parts: int = 3, max_tokens: int = 1500, 
                       system_instruction: str = None, delimiter: str = "---") -> list:
        """
        Generates a multi-part Twitter thread with Hunter's persona.
        
        Args:
            prompt: The topic or content request
            parts: Number of tweets in the thread
            max_tokens: Maximum total tokens for the thread
            system_instruction: Optional task-specific rules
            delimiter: Separator between tweets (default: "---")
        """
        # Combine Hunter's core persona with any task-specific instructions
        full_system_instruction = HUNTER_CORE_PERSONA
        if system_instruction:
            full_system_instruction += f"\n\n{system_instruction}"
        
        try:
            thread = self.ai_service.generate_thread(
                prompt=prompt,
                parts=parts,
                max_tokens=max_tokens,
                system_instruction=full_system_instruction,
                safety_settings=HUNTER_AGENT_SAFETY_SETTINGS,
                delimiter=delimiter
            )
            return thread
        except Exception as e:
            raise Exception(f"Error generating Hunter thread: {e}")


# Singleton instance
_hunter_ai_service = None

def get_hunter_ai_service():
    """Provides access to the singleton Hunter AI service."""
    global _hunter_ai_service
    if _hunter_ai_service is None:
        _hunter_ai_service = HunterAIService()
    return _hunter_ai_service