"""
Property-based tests for LLM routing and LiteLLM integration.

These tests validate that all LLM requests are properly routed through
LiteLLM proxy and that no direct API calls bypass the unified interface.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch, MagicMock, call
from uuid import uuid4
from typing import List, Dict, Any

from src.llm.client import LLMClient, get_llm_client, reset_llm_client, chat, achat
from src.identity.context import IdentityContext


# Hypothesis strategies for generating test data

@st.composite
def message_list_strategy(draw):
    """Generate a list of chat messages."""
    num_messages = draw(st.integers(min_value=1, max_value=10))
    messages = []
    
    for _ in range(num_messages):
        role = draw(st.sampled_from(["user", "assistant", "system"]))
        content = draw(st.text(min_size=1, max_size=500))
        messages.append({"role": role, "content": content})
    
    return messages


@st.composite
def model_name_strategy(draw):
    """Generate model names."""
    return draw(st.sampled_from([
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "claude-3-sonnet",
        "claude-3-opus",
        "claude-3-haiku",
    ]))


@st.composite
def identity_context_strategy(draw):
    """Generate identity contexts."""
    user_id = uuid4()
    agent_id = draw(st.one_of(st.none(), st.just(uuid4())))
    
    delegation_chain = [user_id]
    if agent_id:
        delegation_chain.append(agent_id)
    
    permissions = draw(st.sets(
        st.sampled_from(["read", "write", "execute", "delegate", "admin"]),
        min_size=1,
        max_size=5
    ))
    
    return IdentityContext(
        user_id=user_id,
        agent_id=agent_id,
        delegation_chain=delegation_chain,
        permissions=permissions,
        keycloak_token="mock_token",
        trust_level=100
    )


# Property 5: LiteLLM routing universality
# For any LLM request made by any agent, the request should be routed through
# LiteLLM, and no direct LLM API calls should bypass the proxy.
# Validates: Requirements 4.4, 4.7

@pytest.mark.property
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    messages=message_list_strategy(),
    model=model_name_strategy(),
    identity_context=st.one_of(st.none(), identity_context_strategy()),
    temperature=st.floats(min_value=0.0, max_value=2.0),
    max_tokens=st.one_of(st.none(), st.integers(min_value=1, max_value=4000))
)
def test_property_5_litellm_routing_universality(
    messages: List[Dict[str, str]],
    model: str,
    identity_context: IdentityContext,
    temperature: float,
    max_tokens: int
):
    """
    **Property 5: LiteLLM routing universality**
    **Validates: Requirements 4.4, 4.7**
    
    For any LLM request made by any agent, the request MUST be routed through
    LiteLLM proxy. No direct LLM API calls should bypass the proxy.
    
    This property ensures:
    1. All completion requests use LiteLLM's completion function
    2. All requests include the configured LiteLLM base URL
    3. All requests include the configured API key
    4. No direct OpenAI/Anthropic/etc. API calls are made
    """
    # Reset client to ensure clean state
    reset_llm_client()
    
    # Mock the litellm.completion function to track calls
    with patch('src.llm.client.completion') as mock_completion:
        # Configure mock to return a valid response
        mock_completion.return_value = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        # Create client and make request
        client = get_llm_client()
        
        try:
            response = client.completion(
                messages=messages,
                model=model,
                identity_context=identity_context,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            # PROPERTY ASSERTION 1: litellm.completion was called
            assert mock_completion.called, \
                "LLM request did not route through LiteLLM proxy"
            
            # PROPERTY ASSERTION 2: Called exactly once
            assert mock_completion.call_count == 1, \
                f"Expected 1 call to LiteLLM, got {mock_completion.call_count}"
            
            # Get the call arguments
            call_args = mock_completion.call_args
            
            # PROPERTY ASSERTION 3: Request includes correct base URL
            assert 'api_base' in call_args.kwargs, \
                "LiteLLM request missing api_base parameter"
            assert call_args.kwargs['api_base'] is not None, \
                "LiteLLM api_base is None"
            
            # PROPERTY ASSERTION 4: Request includes API key
            assert 'api_key' in call_args.kwargs, \
                "LiteLLM request missing api_key parameter"
            assert call_args.kwargs['api_key'] is not None, \
                "LiteLLM api_key is None"
            
            # PROPERTY ASSERTION 5: Request includes the model
            assert call_args.kwargs['model'] == model, \
                f"Model mismatch: expected {model}, got {call_args.kwargs['model']}"
            
            # PROPERTY ASSERTION 6: Request includes messages
            assert call_args.kwargs['messages'] == messages, \
                "Messages not passed correctly to LiteLLM"
            
            # PROPERTY ASSERTION 7: Request includes temperature
            assert call_args.kwargs['temperature'] == temperature, \
                f"Temperature mismatch: expected {temperature}, got {call_args.kwargs['temperature']}"
            
            # PROPERTY ASSERTION 8: Response is returned correctly
            assert response is not None, \
                "LiteLLM client returned None"
            assert 'choices' in response, \
                "LiteLLM response missing choices"
            
        except Exception as e:
            # If an exception occurs, ensure it's not due to bypassing LiteLLM
            pytest.fail(f"LLM request failed: {e}")


@pytest.mark.property
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    messages=message_list_strategy(),
    model=model_name_strategy(),
    identity_context=st.one_of(st.none(), identity_context_strategy())
)
@pytest.mark.asyncio
async def test_property_5_async_litellm_routing_universality(
    messages: List[Dict[str, str]],
    model: str,
    identity_context: IdentityContext
):
    """
    **Property 5 (Async variant): LiteLLM routing universality**
    **Validates: Requirements 4.4, 4.7**
    
    For any async LLM request, the request MUST be routed through LiteLLM proxy.
    """
    reset_llm_client()
    
    # Mock the litellm.acompletion function
    with patch('src.llm.client.acompletion') as mock_acompletion:
        # Configure mock to return a valid response
        mock_acompletion.return_value = {
            "id": "chatcmpl-test-async",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test async response"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        client = get_llm_client()
        
        try:
            response = await client.acompletion(
                messages=messages,
                model=model,
                identity_context=identity_context,
                stream=False
            )
            
            # PROPERTY ASSERTION 1: acompletion was called
            assert mock_acompletion.called, \
                "Async LLM request did not route through LiteLLM proxy"
            
            # PROPERTY ASSERTION 2: Called exactly once
            assert mock_acompletion.call_count == 1, \
                f"Expected 1 async call to LiteLLM, got {mock_acompletion.call_count}"
            
            # Get the call arguments
            call_args = mock_acompletion.call_args
            
            # PROPERTY ASSERTION 3: Request includes correct base URL
            assert 'api_base' in call_args.kwargs, \
                "Async LiteLLM request missing api_base parameter"
            
            # PROPERTY ASSERTION 4: Request includes API key
            assert 'api_key' in call_args.kwargs, \
                "Async LiteLLM request missing api_key parameter"
            
            # PROPERTY ASSERTION 5: Response is valid
            assert response is not None, \
                "Async LiteLLM client returned None"
            assert 'choices' in response, \
                "Async LiteLLM response missing choices"
            
        except Exception as e:
            pytest.fail(f"Async LLM request failed: {e}")


@pytest.mark.property
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    messages=message_list_strategy(),
    model=model_name_strategy()
)
def test_property_5_streaming_litellm_routing(
    messages: List[Dict[str, str]],
    model: str
):
    """
    **Property 5 (Streaming variant): LiteLLM routing universality**
    **Validates: Requirements 4.4, 4.7**
    
    For any streaming LLM request, the request MUST be routed through LiteLLM proxy.
    """
    reset_llm_client()
    
    # Mock the litellm.completion function for streaming
    with patch('src.llm.client.completion') as mock_completion:
        # Configure mock to return a generator of chunks
        def mock_stream():
            yield {
                "id": "chatcmpl-test-stream",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": "Test "},
                    "finish_reason": None
                }]
            }
            yield {
                "id": "chatcmpl-test-stream",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": "stream"},
                    "finish_reason": None
                }]
            }
            yield {
                "id": "chatcmpl-test-stream",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
        
        mock_completion.return_value = mock_stream()
        
        client = get_llm_client()
        
        try:
            # Consume the stream
            chunks = list(client.stream_completion(
                messages=messages,
                model=model,
                stream=True
            ))
            
            # PROPERTY ASSERTION 1: completion was called with stream=True
            assert mock_completion.called, \
                "Streaming LLM request did not route through LiteLLM proxy"
            
            # PROPERTY ASSERTION 2: Stream parameter was set
            call_args = mock_completion.call_args
            assert call_args.kwargs.get('stream') is True, \
                "Streaming request did not set stream=True"
            
            # PROPERTY ASSERTION 3: Request includes base URL
            assert 'api_base' in call_args.kwargs, \
                "Streaming LiteLLM request missing api_base parameter"
            
            # PROPERTY ASSERTION 4: Chunks were received
            assert len(chunks) > 0, \
                "No chunks received from streaming request"
            
        except Exception as e:
            pytest.fail(f"Streaming LLM request failed: {e}")


@pytest.mark.property
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    messages=message_list_strategy(),
    model=model_name_strategy()
)
def test_property_5_convenience_functions_route_through_litellm(
    messages: List[Dict[str, str]],
    model: str
):
    """
    **Property 5 (Convenience functions): LiteLLM routing universality**
    **Validates: Requirements 4.4, 4.7**
    
    Convenience functions (chat, achat) MUST also route through LiteLLM proxy.
    """
    reset_llm_client()
    
    # Mock the litellm.completion function
    with patch('src.llm.client.completion') as mock_completion:
        mock_completion.return_value = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        try:
            # Use convenience function
            response = chat(messages=messages, model=model)
            
            # PROPERTY ASSERTION 1: Routed through LiteLLM
            assert mock_completion.called, \
                "Convenience function 'chat' did not route through LiteLLM proxy"
            
            # PROPERTY ASSERTION 2: Response is a string
            assert isinstance(response, str), \
                f"Expected string response, got {type(response)}"
            
            # PROPERTY ASSERTION 3: Response content matches
            assert response == "Test response", \
                "Convenience function did not extract content correctly"
            
        except Exception as e:
            pytest.fail(f"Convenience function 'chat' failed: {e}")


# Additional test: Verify no direct API calls bypass LiteLLM

@pytest.mark.property
def test_property_5_no_direct_api_calls():
    """
    **Property 5 (Negative test): No direct API calls**
    **Validates: Requirements 4.4, 4.7**
    
    Verify that the LLM client does not make direct calls to OpenAI, Anthropic,
    or other LLM providers, bypassing LiteLLM.
    """
    reset_llm_client()
    
    # Patch potential direct API call libraries
    with patch('openai.ChatCompletion.create') as mock_openai, \
         patch('anthropic.Anthropic.messages.create') as mock_anthropic, \
         patch('src.llm.client.completion') as mock_litellm:
        
        mock_litellm.return_value = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 1,
                "total_tokens": 6
            }
        }
        
        client = get_llm_client()
        
        # Make a request
        client.completion(
            messages=[{"role": "user", "content": "test"}],
            model="gpt-3.5-turbo"
        )
        
        # PROPERTY ASSERTION 1: No direct OpenAI calls
        assert not mock_openai.called, \
            "Direct OpenAI API call detected - bypassing LiteLLM!"
        
        # PROPERTY ASSERTION 2: No direct Anthropic calls
        assert not mock_anthropic.called, \
            "Direct Anthropic API call detected - bypassing LiteLLM!"
        
        # PROPERTY ASSERTION 3: LiteLLM was used
        assert mock_litellm.called, \
            "LiteLLM was not called - request may have bypassed proxy!"
