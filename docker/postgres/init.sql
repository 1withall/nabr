-- Initialize database for Nābr

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable PostGIS for geographic queries (if needed in future)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- Create custom types will be handled by Alembic migrations

-- Set timezone
SET timezone = 'UTC';
