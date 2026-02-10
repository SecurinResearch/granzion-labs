import asyncio
from uuid import UUID
from src.mcps.data_mcp import DataMCPServer
from src.mcps.memory_mcp import MemoryMCPServer
from src.mcps.identity_mcp import IdentityMCPServer
from src.mcps.comms_mcp import CommsMCPServer
from src.identity.context import IdentityContext

async def test_guest_restrictions():
    guest_id = UUID("00000000-0000-0000-0000-000000000999")
    context = IdentityContext(
        user_id=guest_id,
        agent_id=None,
        delegation_chain=[guest_id],
        permissions={"read:core"},
        trust_level=10
    )
    
    print(f"Testing with Guest ID: {guest_id}")
    
    # 1. Test Data MCP
    data_mcp = DataMCPServer()
    print("\n--- Data MCP ---")
    res = data_mcp.read_data(table="app_data", identity_context=context)
    print(f"read_data: {res.get('error') or 'SUCCESS'}")
    
    res = data_mcp.execute_sql(query="SELECT 1", identity_context=context)
    print(f"execute_sql: {res.get('error') or 'SUCCESS'}")
    
    # 2. Test Memory MCP
    memory_mcp = MemoryMCPServer()
    print("\n--- Memory MCP ---")
    res = memory_mcp.search_similar(query="test", identity_context=context)
    print(f"search_similar: {res.get('error') or 'SUCCESS'}")
    
    res = memory_mcp.get_context(agent_id="00000000-0000-0000-0000-000000000101", identity_context=context)
    print(f"get_context: {res.get('error') or 'SUCCESS'}")
    
    # 3. Test Identity MCP
    identity_mcp = IdentityMCPServer()
    print("\n--- Identity MCP ---")
    res = identity_mcp.list_delegations(identity_context=context)
    print(f"list_delegations: {res.get('error') or 'SUCCESS'}")
    
    res = identity_mcp.explore_graph(query="g.V().limit(1)", identity_context=context)
    print(f"explore_graph: {res.get('error') or 'SUCCESS'}")

    # 4. Test Comms MCP
    comms_mcp = CommsMCPServer()
    print("\n--- Comms MCP ---")
    res = await comms_mcp.send_message(to_agent_id="00000000-0000-0000-0000-000000000101", message="hello", identity_context=context)
    print(f"send_message: {res.get('error') or 'SUCCESS'}")

    res = comms_mcp.receive_message(agent_id="00000000-0000-0000-0000-000000000101", identity_context=context)
    print(f"receive_message: {res.get('error') or 'SUCCESS'}")

if __name__ == "__main__":
    asyncio.run(test_guest_restrictions())
