# Database Migrations

This directory contains SQL migration files for the multi-agent chat application.

## Prerequisites

Ensure you have:
1. PostgreSQL installed and running
2. `PG_CONN_STR` environment variable set in your `.env` file
3. `psql` command-line tool available

## Running Migrations

### Method 1: Using psql directly

```bash
# From project root
psql $PG_CONN_STR < backend/migrations/001_add_auth_tables.sql
```

### Method 2: Using environment variable from .env

```bash
# Load environment variables
export $(grep -v '^#' .env | xargs)

# Run migration
psql $PG_CONN_STR < backend/migrations/001_add_auth_tables.sql
```

### Method 3: Inline connection string

```bash
psql "postgresql://user:password@localhost:5432/multi_agent_panel" < backend/migrations/001_add_auth_tables.sql
```

## Available Migrations

### 001_add_auth_tables.sql
**Purpose:** Add authentication and user management support

**Creates:**
- `users` - User accounts with Google OAuth data
- `user_threads` - Thread ownership mapping
- `thread_migrations` - Tracks localStorage → DB migrations

**Modifies:**
- Adds `user_id` column to existing tables:
  - `debate_state`
  - `argument_units`
  - `stance_history`
  - `responsiveness_scores`
  - `token_usage`

**Safety:**
- Uses `IF NOT EXISTS` - safe to run multiple times
- All `user_id` columns are nullable - existing data unaffected
- Includes verification output

## Verifying Migration Success

After running the migration, verify with:

```bash
psql $PG_CONN_STR -c "\dt"  # List all tables
psql $PG_CONN_STR -c "\d users"  # Describe users table
psql $PG_CONN_STR -c "SELECT COUNT(*) FROM users;"  # Count users
```

Expected output includes:
```
✓ users table created
✓ user_threads table created
✓ thread_migrations table created
```

## Rolling Back

To rollback the migration (destructive - removes user data):

```sql
-- WARNING: This will delete all user data!
DROP TABLE IF EXISTS thread_migrations CASCADE;
DROP TABLE IF EXISTS user_threads CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Remove user_id columns from existing tables
ALTER TABLE debate_state DROP COLUMN IF EXISTS user_id;
ALTER TABLE argument_units DROP COLUMN IF EXISTS user_id;
ALTER TABLE stance_history DROP COLUMN IF EXISTS user_id;
ALTER TABLE responsiveness_scores DROP COLUMN IF EXISTS user_id;
ALTER TABLE token_usage DROP COLUMN IF EXISTS user_id;
```

## Troubleshooting

**Error: `psql: command not found`**
- Install PostgreSQL client: `sudo apt-get install postgresql-client` (Ubuntu/Debian)

**Error: `FATAL: database "..." does not exist`**
- Create the database first: `createdb multi_agent_panel`

**Error: `permission denied`**
- Ensure your database user has CREATE TABLE privileges

**Error: `relation "..." already exists`**
- Migration is idempotent - this is safe, migration will skip existing tables
