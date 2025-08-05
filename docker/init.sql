-- PostgreSQL initialization script for Game Master V3
-- This script is executed when the PostgreSQL container starts for the first time

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable JSONB operator classes for indexing
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create indexes for better performance on JSONB columns
-- (These will be created by SQLAlchemy, but we can add additional ones here if needed)

-- Log that initialization is complete
DO $$
BEGIN
    RAISE NOTICE 'Game Master V3 PostgreSQL initialization complete';
END $$;