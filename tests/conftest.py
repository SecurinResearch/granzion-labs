"""
Pytest configuration and fixtures for Granzion Lab tests.
"""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_user_alice():
    """Fixture for test user Alice."""
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "type": "user",
        "name": "Alice",
        "email": "[email protected]",
        "permissions": ["read", "write"]
    }


@pytest.fixture
def test_user_bob():
    """Fixture for test user Bob."""
    return {
        "id": "00000000-0000-0000-0000-000000000002",
        "type": "user",
        "name": "Bob",
        "email": "[email protected]",
        "permissions": ["admin", "read", "write", "delete"]
    }


@pytest.fixture
def test_orchestrator_agent():
    """Fixture for Orchestrator Agent."""
    return {
        "id": "00000000-0000-0000-0000-000000000101",
        "type": "agent",
        "name": "Orchestrator Agent",
        "permissions": ["delegate", "coordinate", "read"]
    }


# TODO: Add more fixtures as needed for:
# - Database connections
# - MCP server instances
# - Agent instances
# - Test scenarios
