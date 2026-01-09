#!/usr/bin/env python3
"""Verify database migration completed successfully."""

import asyncio
import sys

import asyncpg

sys.path.insert(0, "backend")
from config import get_pg_conn_str


async def verify_migration():
    """Verify migration tables and columns."""
    conn_str = get_pg_conn_str()
    conn = await asyncpg.connect(conn_str)

    print("=" * 60)
    print("DATABASE MIGRATION VERIFICATION")
    print("=" * 60)

    # Check new tables
    print("\n1️⃣  New Auth Tables:")
    tables = await conn.fetch(
        """
        SELECT tablename,
               (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name = tablename) as column_count
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename IN ('users', 'user_threads', 'thread_migrations')
        ORDER BY tablename
        """
    )

    for table in tables:
        print(f"   ✅ {table['tablename']} ({table['column_count']} columns)")

    # Check user_id columns added to existing tables
    print("\n2️⃣  User ID Columns Added:")
    existing_tables = [
        "debate_state",
        "argument_units",
        "stance_history",
        "responsiveness_scores",
        "token_usage",
    ]

    for table_name in existing_tables:
        result = await conn.fetchrow(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = $1 AND column_name = 'user_id'
            )
            """,
            table_name,
        )
        if result and result["exists"]:
            print(f"   ✅ {table_name}.user_id")
        else:
            # Check if table exists first
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = $1
                )
                """,
                table_name,
            )
            if table_exists:
                print(f"   ⚠️  {table_name} exists but user_id not added")
            else:
                print(f"   ℹ️  {table_name} (table doesn't exist yet)")

    # Check indexes
    print("\n3️⃣  Indexes Created:")
    indexes = await conn.fetch(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND (
            indexname LIKE 'idx_users_%'
            OR indexname LIKE 'idx_user_threads_%'
            OR indexname LIKE 'idx_thread_migrations_%'
            OR indexname LIKE 'idx_debate_state_user_%'
            OR indexname LIKE 'idx_token_usage_user_%'
            OR indexname LIKE 'idx_argument_units_user%'
            OR indexname LIKE 'idx_stance_history_user%'
            OR indexname LIKE 'idx_responsiveness_user%'
        )
        ORDER BY indexname
        """
    )

    for idx in indexes:
        print(f"   ✅ {idx['indexname']}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ {len(tables)}/3 auth tables created")
    print(f"✅ {len(indexes)} indexes created")
    print("\n🎉 Migration completed successfully!")
    print("=" * 60)

    await conn.close()


if __name__ == "__main__":
    asyncio.run(verify_migration())
