-- Seed initial data for Granzion Lab
-- Creates test users, agents, and services

-- Insert test users
INSERT INTO identities (id, type, name, email, keycloak_id, permissions) VALUES
    ('00000000-0000-0000-0000-000000000001', 'user', 'Alice', '[email protected]', 'user-alice', ARRAY['read', 'write']),
    ('00000000-0000-0000-0000-000000000002', 'user', 'Bob', '[email protected]', 'user-bob', ARRAY['admin', 'read', 'write', 'delete']),
    ('00000000-0000-0000-0000-000000000003', 'user', 'Charlie', '[email protected]', 'user-charlie', ARRAY['read'])
ON CONFLICT (id) DO NOTHING;

-- Insert agents
INSERT INTO identities (id, type, name, keycloak_id, permissions) VALUES
    ('00000000-0000-0000-0000-000000000101', 'agent', 'Orchestrator Agent', 'sa-orchestrator', ARRAY['delegate', 'coordinate', 'read']),
    ('00000000-0000-0000-0000-000000000102', 'agent', 'Researcher Agent', 'sa-researcher', ARRAY['read', 'embed', 'search']),
    ('00000000-0000-0000-0000-000000000103', 'agent', 'Executor Agent', 'sa-executor', ARRAY['read', 'write', 'execute', 'deploy']),
    ('00000000-0000-0000-0000-000000000104', 'agent', 'Monitor Agent', 'sa-monitor', ARRAY['read', 'monitor'])
ON CONFLICT (id) DO NOTHING;

-- Insert services (MCPs)
INSERT INTO identities (id, type, name, keycloak_id, permissions) VALUES
    ('00000000-0000-0000-0000-000000000201', 'service', 'Identity MCP', 'svc-identity-mcp', ARRAY['identity', 'delegation']),
    ('00000000-0000-0000-0000-000000000202', 'service', 'Memory MCP', 'svc-memory-mcp', ARRAY['memory', 'vector']),
    ('00000000-0000-0000-0000-000000000203', 'service', 'Data MCP', 'svc-data-mcp', ARRAY['data', 'sql']),
    ('00000000-0000-0000-0000-000000000204', 'service', 'Comms MCP', 'svc-comms-mcp', ARRAY['communication', 'messaging']),
    ('00000000-0000-0000-0000-000000000205', 'service', 'Infra MCP', 'svc-infra-mcp', ARRAY['infrastructure', 'deployment'])
ON CONFLICT (id) DO NOTHING;

-- Create some initial delegations for testing
INSERT INTO delegations (from_identity_id, to_identity_id, permissions) VALUES
    -- Alice delegates to Orchestrator
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000101', ARRAY['read', 'write']),
    -- Bob delegates to Orchestrator with admin permissions
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000101', ARRAY['admin', 'read', 'write', 'delete'])
ON CONFLICT DO NOTHING;

-- Log successful seed
DO $$
BEGIN
    RAISE NOTICE 'Granzion Lab seed data inserted successfully';
    RAISE NOTICE '  - 3 test users: Alice, Bob, Charlie';
    RAISE NOTICE '  - 4 agents: Orchestrator, Researcher, Executor, Monitor';
    RAISE NOTICE '  - 5 services: Identity, Memory, Data, Comms, Infra MCPs';
    RAISE NOTICE '  - 2 initial delegations for testing';
END $$;
