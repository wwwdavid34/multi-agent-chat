-- Migration: Add authentication and user management tables
-- Created: 2026-01-08
-- Purpose: Enable multi-user support with Google OAuth

-- ============================================================================
-- PART 1: Create new user management tables
-- ============================================================================

-- Users table with encrypted API keys
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    picture_url TEXT,

    -- Encrypted API keys storage (AES-256-GCM encrypted JSON)
    encrypted_api_keys TEXT,
    encryption_salt BYTEA,

    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Thread ownership table
CREATE TABLE IF NOT EXISTS user_threads (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, thread_id)
);

CREATE INDEX IF NOT EXISTS idx_user_threads_user ON user_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_user_threads_thread ON user_threads(thread_id);

-- Thread migration tracking (for localStorage → DB migration)
CREATE TABLE IF NOT EXISTS thread_migrations (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id VARCHAR(255) NOT NULL,
    migrated_at TIMESTAMP DEFAULT NOW(),
    source_metadata JSONB  -- Store original localStorage data for audit
);

CREATE INDEX IF NOT EXISTS idx_thread_migrations_user ON thread_migrations(user_id);

-- ============================================================================
-- PART 2: Alter existing tables to add user_id column
-- ============================================================================

-- Add user_id to debate_state (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'debate_state') THEN
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'debate_state' AND column_name = 'user_id') THEN
            ALTER TABLE debate_state ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
            CREATE INDEX idx_debate_state_user_thread ON debate_state(user_id, thread_id);
        END IF;
    END IF;
END $$;

-- Add user_id to argument_units (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'argument_units') THEN
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'argument_units' AND column_name = 'user_id') THEN
            ALTER TABLE argument_units ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
            CREATE INDEX idx_argument_units_user ON argument_units(user_id);
        END IF;
    END IF;
END $$;

-- Add user_id to stance_history (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'stance_history') THEN
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'stance_history' AND column_name = 'user_id') THEN
            ALTER TABLE stance_history ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
            CREATE INDEX idx_stance_history_user ON stance_history(user_id);
        END IF;
    END IF;
END $$;

-- Add user_id to responsiveness_scores (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'responsiveness_scores') THEN
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'responsiveness_scores' AND column_name = 'user_id') THEN
            ALTER TABLE responsiveness_scores ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
            CREATE INDEX idx_responsiveness_user ON responsiveness_scores(user_id);
        END IF;
    END IF;
END $$;

-- Add user_id to token_usage (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'token_usage') THEN
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'token_usage' AND column_name = 'user_id') THEN
            ALTER TABLE token_usage ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
            CREATE INDEX idx_token_usage_user_thread ON token_usage(user_id, thread_id);
        END IF;
    END IF;
END $$;

-- ============================================================================
-- PART 3: Verification queries
-- ============================================================================

-- Verify all tables were created
DO $$
BEGIN
    RAISE NOTICE 'Migration complete. Verifying tables...';

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
        RAISE NOTICE '✓ users table created';
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_threads') THEN
        RAISE NOTICE '✓ user_threads table created';
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'thread_migrations') THEN
        RAISE NOTICE '✓ thread_migrations table created';
    END IF;
END $$;
