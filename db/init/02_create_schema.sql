-- Create database schema for Granzion Lab
-- This script creates all tables needed for the lab

-- Identities table (users, agents, services)
CREATE TABLE IF NOT EXISTS identities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(20) NOT NULL CHECK (type IN ('user', 'agent', 'service')),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    keycloak_id VARCHAR(255) UNIQUE,
    permissions TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_identities_type ON identities(type);
CREATE INDEX idx_identities_keycloak_id ON identities(keycloak_id);

-- Delegations table (delegation relationships)
CREATE TABLE IF NOT EXISTS delegations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    to_identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    permissions TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- Intentionally nullable (no expiry by default)
    active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_delegations_from ON delegations(from_identity_id);
CREATE INDEX idx_delegations_to ON delegations(to_identity_id);
CREATE INDEX idx_delegations_active ON delegations(active);

-- Audit logs table (system activity logging)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_id UUID REFERENCES identities(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW(),
    logged BOOLEAN DEFAULT TRUE  -- Intentionally manipulable for visibility attacks
);

CREATE INDEX idx_audit_logs_identity ON audit_logs(identity_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_logged ON audit_logs(logged);

-- Messages table (agent-to-agent communication)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_agent_id UUID REFERENCES identities(id) ON DELETE SET NULL,
    to_agent_id UUID REFERENCES identities(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) CHECK (message_type IN ('direct', 'broadcast')),
    encrypted BOOLEAN DEFAULT FALSE,  -- Intentionally false by default
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_from ON messages(from_agent_id);
CREATE INDEX idx_messages_to ON messages(to_agent_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX idx_messages_type ON messages(message_type);

-- Memory documents table (RAG and vector storage)
CREATE TABLE IF NOT EXISTS memory_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES identities(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI embedding dimension
    doc_metadata JSONB,
    similarity_boost FLOAT DEFAULT 0.0,  -- Intentional vulnerability for RAG attacks
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_memory_agent ON memory_documents(agent_id);
CREATE INDEX idx_memory_embedding ON memory_documents USING ivfflat (embedding vector_cosine_ops);

-- Application data table (generic data storage for scenarios)
CREATE TABLE IF NOT EXISTS app_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    owner_id UUID REFERENCES identities(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_app_data_table ON app_data(table_name);
CREATE INDEX idx_app_data_owner ON app_data(owner_id);

-- Scenarios execution log
CREATE TABLE IF NOT EXISTS scenario_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id VARCHAR(50) NOT NULL,
    executor_id UUID REFERENCES identities(id) ON DELETE SET NULL,
    status VARCHAR(20) CHECK (status IN ('running', 'success', 'failure', 'error')),
    state_before JSONB,
    state_after JSONB,
    evidence JSONB,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_scenario_executions_scenario ON scenario_executions(scenario_id);
CREATE INDEX idx_scenario_executions_status ON scenario_executions(status);
CREATE INDEX idx_scenario_executions_started ON scenario_executions(started_at DESC);

-- Log successful schema creation
DO $$
BEGIN
    RAISE NOTICE 'Granzion Lab schema created successfully';
    RAISE NOTICE '  - identities: User, agent, and service identities';
    RAISE NOTICE '  - delegations: Delegation relationships';
    RAISE NOTICE '  - audit_logs: System activity logs';
    RAISE NOTICE '  - messages: Agent-to-agent communication';
    RAISE NOTICE '  - memory_documents: RAG and vector storage';
    RAISE NOTICE '  - app_data: Generic application data';
    RAISE NOTICE '  - scenario_executions: Scenario execution tracking';
END $$;

-- Agent Cards table for A2A discovery
CREATE TABLE IF NOT EXISTS agent_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID UNIQUE NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    version VARCHAR(20) DEFAULT '0.3.0',
    capabilities TEXT[] DEFAULT '{}',
    public_key TEXT,
    issuer_id UUID,
    card_metadata JSONB DEFAULT '{}',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_cards_agent ON agent_cards(agent_id);
