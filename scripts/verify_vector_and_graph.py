#!/usr/bin/env python3
"""
Verify vector embeddings (pgvector) and graph DB (PuppyGraph/Gremlin).
Run from project root or inside container: python scripts/verify_vector_and_graph.py
"""

import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    print("=" * 60)
    print("Vector embeddings (pgvector) & Graph DB (PuppyGraph) check")
    print("=" * 60)

    # --- 1. pgvector extension ---
    print("\n[1] pgvector extension")
    try:
        from src.database.connection import check_pgvector_extension
        ok = check_pgvector_extension()
        if ok:
            print("    OK  pgvector extension is installed")
        else:
            print("    FAIL pgvector extension not installed")
            return 1
    except Exception as e:
        print(f"    FAIL {e}")
        return 1

    # --- 2. memory_documents.embedding column ---
    print("\n[2] memory_documents.embedding column")
    try:
        from sqlalchemy import text
        from src.database.connection import sync_engine
        with sync_engine.connect() as conn:
            r = conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'memory_documents' AND column_name = 'embedding'
                )
            """))
            exists = r.scalar()
        if exists:
            print("    OK  embedding column exists")
        else:
            print("    FAIL embedding column not found")
            return 1
    except Exception as e:
        print(f"    FAIL {e}")
        return 1

    # --- 3. Vector embed + search (Memory MCP path) ---
    print("\n[3] Vector embed + similarity search (Memory MCP)")
    try:
        from src.mcps.memory_mcp import MemoryMCPServer
        from src.identity.context import IdentityContext
        from uuid import UUID
        mcp = MemoryMCPServer()
        ctx = IdentityContext(user_id=UUID("00000000-0000-0000-0000-000000000001"), agent_id=None, delegation_chain=[], permissions=set())
        # Embed a test doc
        out = mcp.embed_document("Verify vector test: embedding and search work.", None, ctx)
        if not out or out.get("error"):
            print(f"    FAIL embed_document: {out}")
            return 1
        print("    OK  embed_document succeeded")
        # Search
        search_out = mcp.search_similar("vector test embedding", 3, None, ctx)
        if not search_out or search_out.get("error"):
            print(f"    FAIL search_similar: {search_out}")
            return 1
        docs = search_out.get("documents") or search_out.get("results") or []
        print(f"    OK  search_similar returned {len(docs)} result(s)")
    except Exception as e:
        print(f"    FAIL {e}")
        import traceback
        traceback.print_exc()
        return 1

    # --- 4. PuppyGraph connection ---
    print("\n[4] PuppyGraph (Gremlin) connection")
    try:
        from src.database.graph import get_graph_client
        client = get_graph_client()
        if client is None:
            print("    WARN PuppyGraph not available (SQL fallback will be used)")
        else:
            # Run a simple query
            result = client.execute_query("g.V().limit(1).count()")
            print(f"    OK  Gremlin query succeeded (result: {result})")
    except Exception as e:
        print(f"    WARN PuppyGraph error (optional): {e}")

    print("\n" + "=" * 60)
    print("Vector embeddings: OK")
    print("Graph DB: OK if [4] succeeded, else optional (SQL fallback)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
