#!/usr/bin/env python3
"""
Generate realistic seed data for Granzion Lab

This script generates additional realistic data beyond the SQL seed files:
- More users with varied permissions
- Complex delegation chains
- Realistic customer and financial data
- Memory documents with actual embeddings
- A2A message history
- Audit trail of system activity

Usage:
    python scripts/generate_realistic_data.py [--count COUNT]
"""

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import execute_values

# Sample data for generation
FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry",
    "Iris", "Jack", "Kate", "Liam", "Mia", "Noah", "Olivia", "Peter",
    "Quinn", "Rachel", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xavier",
    "Yara", "Zack"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
]

DEPARTMENTS = ["sales", "engineering", "marketing", "finance", "hr", "operations", "security", "product"]

DOCUMENT_TYPES = ["report", "memo", "policy", "procedure", "analysis", "proposal"]

KNOWLEDGE_TOPICS = [
    "customer service best practices",
    "security incident response procedures",
    "data privacy compliance requirements",
    "API authentication and authorization",
    "database backup and recovery procedures",
    "deployment rollback procedures",
    "incident escalation protocols",
    "access control policies",
    "code review guidelines",
    "performance optimization techniques"
]


def generate_users(count: int) -> List[Dict[str, Any]]:
    """Generate realistic user data with unique keycloak_id per user."""
    users = []
    seen_keycloak: set[str] = set()
    for i in range(count):
        user_id = str(uuid.uuid4())
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        base_kc = f"user-{first.lower()}-{last.lower()}"
        keycloak_id = base_kc
        suffix = 0
        while keycloak_id in seen_keycloak:
            suffix += 1
            keycloak_id = f"{base_kc}-{suffix}"
        seen_keycloak.add(keycloak_id)
        email = f"{base_kc.replace('-', '.')}@company.com" if suffix == 0 else f"{base_kc}.{suffix}@company.com"

        permission_sets = [
            ["read"],
            ["read", "write"],
            ["read", "write", "delete"],
            ["admin", "read", "write", "delete"]
        ]
        permissions = random.choice(permission_sets)

        users.append({
            "id": user_id,
            "type": "user",
            "name": name,
            "email": email,
            "keycloak_id": keycloak_id,
            "permissions": permissions
        })

    return users


def generate_delegations(users: List[Dict[str, Any]], agent_ids: List[str]) -> List[Dict[str, Any]]:
    """Generate realistic delegation chains"""
    delegations = []
    
    # Each user delegates to 1-2 agents
    for user in users:
        num_delegations = random.randint(1, 2)
        selected_agents = random.sample(agent_ids, num_delegations)
        
        for agent_id in selected_agents:
            # Delegate subset of user's permissions
            user_perms = user["permissions"]
            if len(user_perms) > 1:
                num_perms = random.randint(1, len(user_perms))
                delegated_perms = random.sample(user_perms, num_perms)
            else:
                delegated_perms = user_perms
            
            delegations.append({
                "from_identity_id": user["id"],
                "to_identity_id": agent_id,
                "permissions": delegated_perms
            })
    
    return delegations


def generate_data_records(users: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    """Generate realistic data records"""
    records = []
    
    for i in range(count):
        owner = random.choice(users)
        record_type = random.choice(["customer", "financial", "document", "config"])
        
        if record_type == "customer":
            content = {
                "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                "email": f"customer{i}@example.com",
                "phone": f"555-{random.randint(1000, 9999)}",
                "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm'])} St"
            }
            metadata = {"created_by": owner["name"], "sensitivity": "PII"}
        
        elif record_type == "financial":
            content = {
                "account": f"ACC-{random.randint(1000, 9999)}",
                "balance": round(random.uniform(1000, 500000), 2),
                "currency": "USD",
                "type": random.choice(["checking", "savings", "investment"])
            }
            metadata = {"created_by": owner["name"], "sensitivity": "confidential"}
        
        elif record_type == "document":
            content = {
                "title": f"{random.choice(['Q1', 'Q2', 'Q3', 'Q4'])} {random.choice(DOCUMENT_TYPES).title()}",
                "content": f"Document content for {random.choice(DEPARTMENTS)} department",
                "author": owner["name"]
            }
            metadata = {"created_by": owner["name"], "department": random.choice(DEPARTMENTS)}
        
        else:  # config
            content = {
                "service": random.choice(["api", "database", "cache", "queue"]),
                "endpoint": f"https://{random.choice(['api', 'db', 'cache'])}.internal.com",
                "timeout": random.choice([10, 30, 60]),
                "retry": random.choice([3, 5, 10])
            }
            metadata = {"created_by": owner["name"], "environment": random.choice(["dev", "staging", "production"])}
        
        records.append({
            "id": str(uuid.uuid4()),
            "owner_id": owner["id"],
            "table_name": record_type,
            "data": {**content, "_metadata": metadata}
        })

    return records


def generate_memory_documents(agent_ids: List[str], count: int) -> List[Dict[str, Any]]:
    """Generate realistic memory documents with placeholder embeddings"""
    documents = []
    
    for i in range(count):
        owner = random.choice(agent_ids)
        topic = random.choice(KNOWLEDGE_TOPICS)
        
        content = f"{topic.title()}: {' '.join(['Important information about ' + topic] * 3)}"
        
        metadata = {
            "source": random.choice(["manual", "documentation", "training", "policy"]),
            "category": random.choice(["security", "compliance", "technical", "business"]),
            "version": f"2024.{random.randint(1, 12)}"
        }
        
        # Placeholder embedding (1536 dimensions)
        # In production, this would be generated by the embedding model
        embedding = [random.uniform(-1, 1) for _ in range(1536)]
        
        documents.append({
            "id": str(uuid.uuid4()),
            "owner_id": owner,
            "content": content,
            "metadata": json.dumps(metadata),
            "embedding": embedding
        })
    
    return documents


def generate_messages(agent_ids: List[str], count: int) -> List[Dict[str, Any]]:
    """Generate realistic A2A messages"""
    messages = []
    
    message_types = ["task_request", "task_response", "status_update", "alert", "coordination"]
    
    for i in range(count):
        from_agent = random.choice(agent_ids)
        to_agent = random.choice([a for a in agent_ids if a != from_agent]) if random.random() > 0.2 else None
        
        msg_type = random.choice(message_types)
        
        if msg_type == "task_request":
            content = {
                "type": "task_request",
                "task": random.choice(["search_data", "deploy_service", "analyze_logs", "generate_report"]),
                "parameters": {"query": "sample query"}
            }
        elif msg_type == "task_response":
            content = {
                "type": "task_response",
                "status": random.choice(["completed", "failed", "in_progress"]),
                "results": [f"result_{j}" for j in range(random.randint(1, 5))]
            }
        else:
            content = {
                "type": msg_type,
                "message": f"Sample {msg_type} message"
            }
        
        message_type = "broadcast" if to_agent is None else "direct"
        to_agent_id = to_agent if to_agent else None
        messages.append({
            "id": str(uuid.uuid4()),
            "from_agent_id": from_agent,
            "to_agent_id": to_agent_id,
            "content": json.dumps(content),
            "message_type": message_type,
        })

    return messages


def insert_data(conn, users, delegations, data_records, memory_docs, messages):
    """Insert generated data into database"""
    cursor = conn.cursor()
    
    try:
        # Insert users
        print(f"Inserting {len(users)} users...")
        user_values = [
            (u["id"], u["type"], u["name"], u.get("email"), u["keycloak_id"], u["permissions"])
            for u in users
        ]
        execute_values(
            cursor,
            "INSERT INTO identities (id, type, name, email, keycloak_id, permissions) VALUES %s ON CONFLICT (id) DO NOTHING",
            user_values
        )
        
        # Insert delegations
        print(f"Inserting {len(delegations)} delegations...")
        delegation_values = [
            (d["from_identity_id"], d["to_identity_id"], d["permissions"])
            for d in delegations
        ]
        execute_values(
            cursor,
            "INSERT INTO delegations (from_identity_id, to_identity_id, permissions) VALUES %s ON CONFLICT DO NOTHING",
            delegation_values
        )
        
        # Insert app_data (schema table is app_data, not data_records)
        print(f"Inserting {len(data_records)} app_data records...")
        record_values = [
            (r["id"], r["table_name"], json.dumps(r["data"]), r["owner_id"])
            for r in data_records
        ]
        execute_values(
            cursor,
            "INSERT INTO app_data (id, table_name, data, owner_id) VALUES %s ON CONFLICT (id) DO NOTHING",
            record_values
        )
        
        # Insert memory documents (id, agent_id, content, embedding; metadata column name varies by schema)
        print(f"Inserting {len(memory_docs)} memory documents...")
        for doc in memory_docs:
            emb_str = "[" + ",".join(str(x) for x in doc["embedding"]) + "]"
            cursor.execute(
                """
                INSERT INTO memory_documents (id, agent_id, content, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (id) DO NOTHING
                """,
                (doc["id"], doc["owner_id"], doc["content"], emb_str)
            )
        
        # Insert messages (schema: from_agent_id, to_agent_id, content, message_type)
        print(f"Inserting {len(messages)} messages...")
        message_values = [
            (m["id"], m["from_agent_id"], m["to_agent_id"], m["content"], m["message_type"])
            for m in messages
        ]
        execute_values(
            cursor,
            "INSERT INTO messages (id, from_agent_id, to_agent_id, content, message_type) VALUES %s ON CONFLICT (id) DO NOTHING",
            message_values
        )
        
        conn.commit()
        print("\n✅ All data inserted successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error inserting data: {e}")
        raise
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description="Generate realistic seed data for Granzion Lab")
    parser.add_argument("--users", type=int, default=20, help="Number of users to generate")
    parser.add_argument("--records", type=int, default=50, help="Number of data records to generate")
    parser.add_argument("--memory", type=int, default=30, help="Number of memory documents to generate")
    parser.add_argument("--messages", type=int, default=40, help="Number of messages to generate")
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument("--db-port", default="5432", help="Database port")
    parser.add_argument("--db-name", default="granzion", help="Database name")
    parser.add_argument("--db-user", default="granzion", help="Database user")
    parser.add_argument("--db-password", default="granzion_password", help="Database password")
    
    args = parser.parse_args()
    
    # Known agent IDs from seed data
    agent_ids = [
        "00000000-0000-0000-0000-000000000101",  # Orchestrator
        "00000000-0000-0000-0000-000000000102",  # Researcher
        "00000000-0000-0000-0000-000000000103",  # Executor
        "00000000-0000-0000-0000-000000000104",  # Monitor
    ]
    
    print("=" * 60)
    print("Granzion Lab - Realistic Data Generator")
    print("=" * 60)
    print(f"Generating:")
    print(f"  - {args.users} users")
    print(f"  - {args.records} data records")
    print(f"  - {args.memory} memory documents")
    print(f"  - {args.messages} messages")
    print("=" * 60)
    
    # Generate data
    print("\n📊 Generating data...")
    users = generate_users(args.users)
    delegations = generate_delegations(users, agent_ids)
    data_records = generate_data_records(users, args.records)
    memory_docs = generate_memory_documents(agent_ids, args.memory)
    messages = generate_messages(agent_ids, args.messages)
    
    # Connect to database
    print(f"\n🔌 Connecting to database at {args.db_host}:{args.db_port}...")
    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password
    )
    
    # Insert data
    print("\n💾 Inserting data into database...")
    insert_data(conn, users, delegations, data_records, memory_docs, messages)
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Data generation complete!")
    print("=" * 60)
    print(f"Total records created:")
    print(f"  - Users: {len(users)}")
    print(f"  - Delegations: {len(delegations)}")
    print(f"  - Data Records: {len(data_records)}")
    print(f"  - Memory Documents: {len(memory_docs)}")
    print(f"  - Messages: {len(messages)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
