#!/usr/bin/env python3
"""
Database initialization script.

Creates and initializes the P3-Edge database with encryption.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config_manager
from src.database.db_manager import create_database_manager
from src.utils import get_logger


def main() -> None:
    """Initialize the database."""
    logger = get_logger("init_db")

    logger.info("=" * 60)
    logger.info("P3-Edge Database Initialization")
    logger.info("=" * 60)

    # Get configuration
    config = get_config_manager()
    db_path = config.get("database.path", "data/p3edge.db")
    encrypted = config.get("database.encrypted", True)

    # Get or create encryption key
    encryption_key = None
    if encrypted:
        encryption_key = config.get_database_encryption_key()
        if encryption_key is None:
            # Prompt for password to derive key
            import getpass
            import secrets

            password = getpass.getpass("Enter master password for database encryption: ")
            confirm_password = getpass.getpass("Confirm password: ")

            if password != confirm_password:
                logger.error("Passwords do not match!")
                sys.exit(1)

            # Generate salt and derive key
            salt = secrets.token_bytes(32)
            from src.utils.encryption import derive_key_from_password

            encryption_key = derive_key_from_password(password, salt).decode('utf-8')

            # Store salt and encryption key
            config.set_credential("database_salt", salt.hex())
            config.set_credential("database_encryption_key", encryption_key)

            logger.info("Encryption key generated and stored securely")

    # Create database manager
    logger.info(f"Creating database at: {db_path}")
    logger.info(f"Encryption: {'ENABLED' if encrypted else 'DISABLED'}")

    db_manager = create_database_manager(db_path, encryption_key)

    try:
        # Initialize database schema
        db_manager.initialize_database()

        # Verify encryption if enabled
        if encrypted:
            if db_manager.verify_encryption():
                logger.info("✓ Database encryption verified")
            else:
                logger.error("✗ Database encryption verification failed")
                sys.exit(1)

        # Check tables
        tables = [
            "inventory",
            "inventory_history",
            "forecasts",
            "orders",
            "preferences",
            "audit_log",
            "model_metadata",
            "vendor_products",
            "conversations",
            "agent_memory",
            "user_preferences"
        ]

        logger.info("\nVerifying database tables:")
        for table in tables:
            if db_manager.table_exists(table):
                logger.info(f"  ✓ {table}")
            else:
                logger.warning(f"  ✗ {table} - NOT FOUND")

        logger.info("\n" + "=" * 60)
        logger.info("Database initialization complete!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
