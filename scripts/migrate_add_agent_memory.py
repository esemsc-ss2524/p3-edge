#!/usr/bin/env python3
"""
Database migration script to add agent_memory table.

This script adds the agent_memory table to existing P3-Edge databases
without affecting existing data.
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config_manager
from src.database.db_manager import create_database_manager
from src.utils import get_logger


def migrate_database():
    """Add agent_memory table to existing database."""
    logger = get_logger("migration")

    try:
        # Get database configuration
        config = get_config_manager()
        db_path = config.get("database.path", "data/p3edge.db")
        encryption_key = config.get_database_encryption_key()

        logger.info(f"Migrating database: {db_path}")

        # Check if database exists
        if not Path(db_path).exists():
            logger.error(f"Database not found: {db_path}")
            logger.error("Please run 'python scripts/init_db.py' first")
            return False

        # Connect to database
        db_manager = create_database_manager(db_path, encryption_key)

        # Check if agent_memory table already exists
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='agent_memory'
        """
        result = db_manager.execute_query(check_query)

        if result:
            logger.info("agent_memory table already exists, skipping migration")
            db_manager.close()
            return True

        # Create agent_memory table
        logger.info("Creating agent_memory table...")

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS agent_memory (
            memory_id TEXT PRIMARY KEY,
            cycle_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 1,
            context TEXT,
            outcome TEXT,
            consolidated INTEGER DEFAULT 0,
            embedding BLOB
        )
        """
        db_manager.execute_update(create_table_sql)

        # Create indexes
        logger.info("Creating indexes...")

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_agent_memory_timestamp ON agent_memory(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_agent_memory_cycle ON agent_memory(cycle_id)",
            "CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_agent_memory_importance ON agent_memory(importance)"
        ]

        for index_sql in indexes:
            db_manager.execute_update(index_sql)

        logger.info("Migration completed successfully")

        # Close database
        db_manager.close()

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    logger = get_logger("migration")

    logger.info("=" * 60)
    logger.info("P3-Edge Database Migration")
    logger.info("Adding agent_memory table for autonomous agent")
    logger.info("=" * 60)

    success = migrate_database()

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("=" * 60)
        return 0
    else:
        logger.error("\n" + "=" * 60)
        logger.error("Migration failed!")
        logger.error("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
