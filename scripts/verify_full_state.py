import sys
import os
from sqlalchemy import text, select, func
from uuid import UUID

# Add project root to path
# Assuming this script is run from project root, or adjusting path accordingly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Adjust import specific to environment if needed
try:
    from src.database.connection import get_db
    from src.database.models import Identity, Delegation, AuditLog, MemoryDocument, AppData, AgentCard
    from src.database.graph import get_graph_client
except ImportError:
    # If standard import fails, try relative or direct path insertion
    sys.path.append(os.path.join(project_root, 'src'))
    from src.database.connection import get_db
    from src.database.models import Identity, Delegation, AuditLog, MemoryDocument, AppData, AgentCard
    from src.database.graph import get_graph_client

def verify_relational_data():
    print("\n--- Relational Data Verification (PostgreSQL) ---")
    with get_db() as db:
        # distinct identities
        identity_count = db.execute(select(func.count(Identity.id))).scalar()
        agent_count = db.execute(select(func.count(Identity.id)).filter(Identity.type == 'agent')).scalar()
        user_count = db.execute(select(func.count(Identity.id)).filter(Identity.type == 'user')).scalar()
        service_count = db.execute(select(func.count(Identity.id)).filter(Identity.type == 'service')).scalar()
        
        print(f"Identities: {identity_count} (Agents: {agent_count}, Users: {user_count}, Services: {service_count})")
        
        # delegations
        delegation_count = db.execute(select(func.count(Delegation.id))).scalar()
        print(f"Delegations: {delegation_count}")
        
        # app data
        app_data_count = db.execute(select(func.count(AppData.id))).scalar()
        print(f"App Data Records: {app_data_count}")

        # audit logs
        audit_log_count = db.execute(select(func.count(AuditLog.id))).scalar()
        print(f"Audit Logs: {audit_log_count}")
        
        # agent cards
        agent_card_count = db.execute(select(func.count(AgentCard.id))).scalar()
        print(f"Agent Cards: {agent_card_count}")

def verify_vector_data():
    print("\n--- Vector Data Verification (pgvector) ---")
    with get_db() as db:
        # memory documents
        doc_count = db.execute(select(func.count(MemoryDocument.id))).scalar()
        print(f"Memory Documents: {doc_count}")
        
        # Check embedding dimension (should be 1536)
        try:
            sample_doc = db.execute(select(MemoryDocument).limit(1)).scalar_one_or_none()
            if sample_doc:
                embedding = sample_doc.embedding
                # Check for array existence properly (using len > 0 instead of implicit bool)
                if embedding is not None and len(embedding) > 0:
                    print(f"Sample Embedding Present: Yes (Length: {len(embedding)})")
                else:
                    print(f"Sample Embedding Present: No (Null or Empty)")
            else:
                print("No documents found to verify embedding.")
        except Exception as e:
            print(f"Vector verification warning: {e}")

def verify_graph_data():
    print("\n--- Graph Data Verification (PuppyGraph) ---")
    try:
        graph = get_graph_client()
        if not graph:
            print("PuppyGraph client not available (check configuration).")
            return

        print("Connected to Graph Client. Executing queries...")

        # Vertex count
        try:
            v_result = graph.execute_query("g.V().count()")
            print(f"Raw Vertex Query Result: {v_result}")
            v_count = v_result[0] if v_result else 0
            print(f"Graph Vertices: {v_count}")
        except Exception as e:
            print(f"Error querying vertices: {e}")
        
        # Edge count
        try:
            e_result = graph.execute_query("g.E().count()")
            e_count = e_result[0] if e_result else 0
            print(f"Graph Edges: {e_count}")
        except Exception as e:
            print(f"Error querying edges: {e}")
        
        # Detail on node types
        try:
            agent_res = graph.execute_query("g.V().hasLabel('agent').count()")
            user_res = graph.execute_query("g.V().hasLabel('user').count()")
            
            agents = agent_res[0] if agent_res else 0
            users = user_res[0] if user_res else 0
            print(f"Graph Agents: {agents}, Graph Users: {users}")
        except Exception as e:
            print(f"Error querying node details: {e}")

    except Exception as e:
        print(f"Graph verification failed: {e}")

if __name__ == "__main__":
    print("Starting Lab Full State Verification...")
    try:
        verify_relational_data()
        verify_vector_data()
        verify_graph_data()
        print("\nVerification Complete.")
    except Exception as e:
        print(f"\nCRITICAL ERROR during verification: {e}")
