#!/usr/bin/env python3
"""Run database migrations using asyncpg."""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# Add backend to path to import config
sys.path.insert(0, "backend")
from config import get_pg_conn_str

# Load environment variables
load_dotenv("backend/.env")


async def run_migration():
    """Run the auth tables migration."""
    try:
        conn_str = get_pg_conn_str()
    except Exception as e:
        print(f"❌ Failed to get connection string: {e}")
        return False
    if not conn_str:
        print("❌ PG_CONN_STR environment variable not set")
        return False

    migration_file = Path("backend/migrations/001_add_auth_tables.sql")
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    print(f"📂 Reading migration: {migration_file}")
    migration_sql = migration_file.read_text()

    print("🔌 Connecting to database...")
    try:
        conn = await asyncpg.connect(conn_str)
        print("✅ Connected to database")

        print("🔄 Running migration...")
        # Execute the migration
        await conn.execute(migration_sql)
        print("✅ Migration completed successfully!")

        # Verify tables were created
        print("\n📊 Verifying tables...")
        tables = await conn.fetch(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN ('users', 'user_threads', 'thread_migrations')
            ORDER BY tablename
            """
        )

        if tables:
            print(f"✅ Found {len(tables)} auth tables:")
            for table in tables:
                print(f"   - {table['tablename']}")
        else:
            print("⚠️  No auth tables found (they may already exist)")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
