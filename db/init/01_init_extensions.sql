-- Initialize PostgreSQL extensions for Granzion Lab
-- This script runs automatically when the PostgreSQL container starts

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable additional useful extensions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Trigram matching for text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- GIN indexes for better performance

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Granzion Lab extensions initialized successfully';
    RAISE NOTICE '  - uuid-ossp: UUID generation';
    RAISE NOTICE '  - vector: pgvector for embeddings';
    RAISE NOTICE '  - pg_trgm: Trigram text search';
    RAISE NOTICE '  - btree_gin: GIN indexes';
END $$;
