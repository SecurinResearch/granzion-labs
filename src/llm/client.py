"""
LiteLLM client wrapper for Granzion Lab.

All LLM requests MUST go through this client to ensure:
1. Unified interface across providers
2. Request logging and tracking
3. Cost monitoring
4. Identity context propagation
"""

from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from uuid import UUID, uuid4

import litellm
from litellm import completion, acompletion
from loguru import logger

from src.config import settings
from src.identity.context import IdentityContext
from src.database.connection import get_db
from src.database.queries import create_audit_log


# Configure LiteLLM
litellm.api_base = settings.litellm_url
litellm.api_key = settings.litellm_api_key
litellm.drop_params = True  # Drop unsupported params instead of erroring
litellm.set_verbose = settings.debug


class LLMClient:
    """
    Client for making LLM requests through LiteLLM proxy.
    
    This client ensures all LLM requests are:
    - Routed through LiteLLM proxy
    - Logged with identity context
    - Tracked for cost and usage
    - Observable for attack detection
    """
    
    def __init__(self):
        """Initialize LLM client."""
        self.base_url = settings.litellm_url
        self.api_key = settings.litellm_api_key
        self._request_count = 0
        self._total_tokens = 0
    
    def completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        identity_context: Optional[IdentityContext] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a completion request to LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (e.g., 'gpt-4', 'claude-3-sonnet')
            identity_context: Optional identity context for logging
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters for the model
            
        Returns:
            Completion response in OpenAI format
        """
        request_id = uuid4()
        start_time = datetime.utcnow()
        
        # Use default model from settings if not specified
        if model is None:
            model = settings.default_model
        
        try:
            # Log request
            logger.info(
                f"LLM Request [{request_id}]: model={model}, "
                f"messages={len(messages)}, stream={stream}"
            )
            
            if identity_context:
                logger.debug(
                    f"  Identity: user={identity_context.user_id}, "
                    f"agent={identity_context.agent_id}"
                )
            
            # Make request through LiteLLM
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                api_base=self.base_url,
                api_key=self.api_key,
                **kwargs
            )
            
            # Update metrics
            self._request_count += 1
            
            if not stream:
                # Log response
                usage = response.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                self._total_tokens += total_tokens
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                logger.info(
                    f"LLM Response [{request_id}]: "
                    f"tokens={total_tokens}, duration={duration:.2f}s"
                )
                
                # Audit log
                self._log_request(
                    request_id=request_id,
                    model=model,
                    messages=messages,
                    response=response,
                    identity_context=identity_context,
                    duration=duration
                )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM Request [{request_id}] failed: {e}")
            
            # Log failure
            self._log_request(
                request_id=request_id,
                model=model,
                messages=messages,
                response=None,
                identity_context=identity_context,
                error=str(e)
            )
            
            raise
    
    async def acompletion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        identity_context: Optional[IdentityContext] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an async completion request to LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            identity_context: Optional identity context for logging
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Returns:
            Completion response in OpenAI format
        """
        request_id = uuid4()
        start_time = datetime.utcnow()
        
        # Use default model from settings if not specified
        if model is None:
            model = settings.default_model
        
        try:
            logger.info(
                f"Async LLM Request [{request_id}]: model={model}, "
                f"messages={len(messages)}"
            )
            
            # Make async request through LiteLLM
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                api_base=self.base_url,
                api_key=self.api_key,
                **kwargs
            )
            
            self._request_count += 1
            
            if not stream:
                usage = response.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                self._total_tokens += total_tokens
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                logger.info(
                    f"Async LLM Response [{request_id}]: "
                    f"tokens={total_tokens}, duration={duration:.2f}s"
                )
                
                self._log_request(
                    request_id=request_id,
                    model=model,
                    messages=messages,
                    response=response,
                    identity_context=identity_context,
                    duration=duration
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Async LLM Request [{request_id}] failed: {e}")
            raise
    
    def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        identity_context: Optional[IdentityContext] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream a completion response from LiteLLM.
        
        Args:
            messages: List of message dicts
            model: Model name
            identity_context: Optional identity context
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters
            
        Yields:
            Streaming chunks in OpenAI format
        """
        request_id = uuid4()
        
        # Use default model from settings if not specified
        if model is None:
            model = settings.default_model
        
        logger.info(f"Streaming LLM Request [{request_id}]: model={model}")
        
        try:
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                api_base=self.base_url,
                api_key=self.api_key,
                **kwargs
            )
            
            for chunk in response:
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming LLM Request [{request_id}] failed: {e}")
            raise
    
    def _log_request(
        self,
        request_id: UUID,
        model: str,
        messages: List[Dict[str, str]],
        response: Optional[Dict[str, Any]],
        identity_context: Optional[IdentityContext],
        duration: Optional[float] = None,
        error: Optional[str] = None
    ):
        """
        Log LLM request to audit log.
        
        Args:
            request_id: Request UUID
            model: Model name
            messages: Request messages
            response: Response data
            identity_context: Identity context
            duration: Request duration in seconds
            error: Error message if failed
        """
        try:
            with get_db() as db:
                details = {
                    "request_id": str(request_id),
                    "model": model,
                    "message_count": len(messages),
                    "duration_seconds": duration,
                }
                
                if response:
                    usage = response.get("usage", {})
                    details.update({
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "finish_reason": response.get("choices", [{}])[0].get("finish_reason"),
                    })
                
                if error:
                    details["error"] = error
                
                if identity_context:
                    details.update({
                        "user_id": str(identity_context.user_id),
                        "agent_id": str(identity_context.agent_id) if identity_context.agent_id else None,
                        "delegation_depth": identity_context.delegation_depth,
                    })
                
                create_audit_log(
                    db,
                    identity_id=identity_context.current_identity_id if identity_context else None,
                    action="llm_request",
                    resource_type="llm",
                    resource_id=request_id,
                    details=details
                )
                
        except Exception as e:
            logger.error(f"Failed to log LLM request: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get client metrics.
        
        Returns:
            Dictionary with request count and token usage
        """
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
        }
    
    def health_check(self) -> bool:
        """
        Check if LiteLLM proxy is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Make a minimal request to check connectivity
            response = completion(
                model=settings.default_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                api_base=self.base_url,
                api_key=self.api_key
            )
            logger.info("LiteLLM health check passed")
            return True
        except Exception as e:
            logger.error(f"LiteLLM health check failed: {e}")
            return False
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        identity_context: Optional[IdentityContext] = None,
        **kwargs
    ) -> str:
        """
        Simple chat completion that returns just the message content.
        
        Args:
            messages: List of message dicts
            model: Model name
            identity_context: Optional identity context
            **kwargs: Additional parameters
            
        Returns:
            Assistant's response content
        """
        response = self.completion(
            messages=messages,
            model=model,
            identity_context=identity_context,
            **kwargs
        )
        return response["choices"][0]["message"]["content"]


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reset_llm_client():
    """Reset the global LLM client (for testing)."""
    global _llm_client
    _llm_client = None


# Convenience functions

def chat(
    messages: List[Dict[str, str]],
    model: str = None,
    identity_context: Optional[IdentityContext] = None,
    **kwargs
) -> str:
    """
    Simple chat completion that returns just the message content.
    
    Args:
        messages: List of message dicts
        model: Model name
        identity_context: Optional identity context
        **kwargs: Additional parameters
        
    Returns:
        Assistant's response content
    """
    client = get_llm_client()
    response = client.completion(
        messages=messages,
        model=model,
        identity_context=identity_context,
        **kwargs
    )
    return response["choices"][0]["message"]["content"]


async def achat(
    messages: List[Dict[str, str]],
    model: str = None,
    identity_context: Optional[IdentityContext] = None,
    **kwargs
) -> str:
    """
    Async simple chat completion.
    
    Args:
        messages: List of message dicts
        model: Model name
        identity_context: Optional identity context
        **kwargs: Additional parameters
        
    Returns:
        Assistant's response content
    """
    client = get_llm_client()
    response = await client.acompletion(
        messages=messages,
        model=model,
        identity_context=identity_context,
        **kwargs
    )
    return response["choices"][0]["message"]["content"]
