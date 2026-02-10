
from agno.models.openai import OpenAIChat
from src.config import settings

def get_llm_model() -> OpenAIChat:
    """
    Create a configured OpenAIChat model instance with correct headers.
    
    Handles proxy-specific requirements like x-litellm-api-key headers.
    """
    # Create custom headers for proxies
    headers = {}
    if settings.litellm_api_key:
        headers["x-litellm-api-key"] = settings.litellm_api_key
        
    # Configure the model
    # We pass client_params to inject custom headers into the underlying OpenAI client
    return OpenAIChat(
        id=settings.default_model,
        api_key=settings.litellm_api_key,
        base_url=settings.litellm_url,
        client_params={"default_headers": headers}
    )
