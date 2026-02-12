#!/usr/bin/env python3
"""
Debug script for RAG functionality in Granzion Lab.
Verifies embeddings and search capabilities.
"""

import sys
import os
import asyncio
import numpy as np
from sqlalchemy import text
from typing import List

# Ensure src module is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import get_db
from src.mcps.memory_mcp import MemoryMCPServer
from src.identity.context import IdentityContext
from uuid import UUID

async def debug_rag():
    print("=" * 60)
    print("  RAG DEBUGGER")
    print("=" * 60)

    # 1. Check Document Count
    with get_db() as db:
        count = db.execute(text("SELECT COUNT(*) FROM memory_documents")).scalar()
        print(f"\n[1] Total Documents: {count}")
        
        # 2. Check Embedding Validity
        print("\n[2] Checking Embeddings Sample...")
        # Get a sample embedding
        result = db.execute(text("SELECT id, content, embedding FROM memory_documents LIMIT 5")).fetchall()
        
        if not result:
            print("  FAIL: No documents found!")
            return

        valid_count = 0
        placeholder_count = 0
        
        for row in result:
            emb_str = str(row.embedding)
            # Basic check: is it non-zero? Placeholder often looks like [0.1, 0.1, ...] or [0,0...]
            # pgvector returns a string representation or list depending on driver
            # Let's parse it if it's a string
            if isinstance(row.embedding, str):
                emb_list = [float(x) for x in row.embedding.strip('[]').split(',')]
            else:
                emb_list = row.embedding # asyncpg returns list
            
            # Check if it looks synthetic (all values equal)
            if len(set(emb_list[:10])) == 1:
                print(f"  ⚠ Doc {str(row.id)[:8]} has PLACEHOLDER embedding ({emb_list[0]}...)")
                placeholder_count += 1
            else:
                print(f"  ✓ Doc {str(row.id)[:8]} has REAL embedding (dim={len(emb_list)})")
                valid_count += 1
                
        print(f"  Result: {valid_count} real, {placeholder_count} placeholder / {len(result)} sampled")

    # 3. Test Search
    print("\n[3] Testing Similarity Search...")
    query = "access control policy for developers"
    print(f"  Query: '{query}'")
    
    try:
        server = MemoryMCPServer()
        # Mock identity context (Agent ID 101 = Orchestrator)
        ctx = IdentityContext(
            user_id=UUID("00000000-0000-0000-0000-000000000001"), # Alice
            agent_id=UUID("00000000-0000-0000-0000-000000000101"), # Orchestrator
            permissions=["read_memory"]
        )
        
        results = server.search_similar(query, top_k=3, identity_context=ctx)
        
        if "error" in results:
            print(f"  FAIL: Search error: {results['error']}")
        else:
            print(f"  Found {results['results_count']} results:")
            for i, doc in enumerate(results['documents']):
                snippet = doc['content'][:100].replace('\n', ' ')
                print(f"    {i+1}. Score: {doc['score']:.4f} | {snippet}...")
                
            # Check if relevant document was found
            if any("Access Control" in d['content'] for d in results['documents']):
                print("\n  ✓ RELEVANCE CHECK PASS: Found Access Control Policy")
            else:
                print("\n  ⚠ RELEVANCE CHECK WARN: Did not find Access Control Policy in top 3")

    except Exception as e:
        print(f"  FAIL: Search exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_rag())
