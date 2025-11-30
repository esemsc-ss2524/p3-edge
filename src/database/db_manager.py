"""
Database manager with SQLCipher encryption support.

This module handles all database operations with encryption at rest.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    SQLCIPHER_AVAILABLE = True
except ImportError:
    SQLCIPHER_AVAILABLE = False
    import sqlite3 as sqlcipher  # Fallback for development


class DatabaseManager:
    """
    Manages encrypted SQLite database with SQLCipher.

    Provides secure storage for all application data with AES-256 encryption.
    """

    def __init__(self, db_path: str, encryption_key: Optional[str] = None) -> None:
        """
        Initialize database manager.

        Args:
            db_path: Path to the database file
            encryption_key: Encryption key for SQLCipher (None uses unencrypted for dev)
        """
        self.db_path = Path(db_path)
        self.encryption_key = encryption_key
        self.is_encrypted = encryption_key is not None and SQLCIPHER_AVAILABLE

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Schema file path
        self.schema_path = Path(__file__).parent / "schema.sql"

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            Database connection object
        """
        if self.is_encrypted:
            conn = sqlcipher.connect(str(self.db_path))
            # Set encryption key
            conn.execute(f"PRAGMA key = '{self.encryption_key}'")
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Set cipher settings for better security
            conn.execute("PRAGMA cipher_page_size = 4096")
            conn.execute("PRAGMA kdf_iter = 256000")
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA foreign_keys = ON")

        # Enable row factory for dict-like access
        conn.row_factory = sqlite3.Row

        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def initialize_database(self) -> None:
        """
        Initialize database with schema from schema.sql.

        Creates all tables if they don't exist.
        """
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        # Read schema
        with open(self.schema_path, 'r') as f:
            schema_sql = f.read()

        # Execute schema
        with self.get_connection() as conn:
            conn.executescript(schema_sql)

        print(f"Database initialized at: {self.db_path}")
        if self.is_encrypted:
            print("Encryption: ENABLED (SQLCipher)")
        else:
            print("Encryption: DISABLED (development mode)")

    def verify_encryption(self) -> bool:
        """
        Verify that the database is properly encrypted.

        Returns:
            True if database is encrypted and accessible with the key
        """
        if not self.is_encrypted:
            return False

        try:
            with self.get_connection() as conn:
                # Try a simple query
                conn.execute("SELECT name FROM sqlite_master LIMIT 1")
            return True
        except Exception:
            return False

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> List[sqlite3.Row]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL SELECT query
            params: Query parameters (optional)

        Returns:
            List of rows as dict-like objects
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.fetchall()

    def execute_update(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.

        Args:
            query: SQL query
            params: Query parameters (optional)

        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.rowcount

    def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> int:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            return cursor.rowcount

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column info dictionaries
        """
        query = f"PRAGMA table_info({table_name})"
        rows = self.execute_query(query)
        return [dict(row) for row in rows]

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table

        Returns:
            True if table exists
        """
        query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """
        rows = self.execute_query(query, (table_name,))
        return len(rows) > 0

    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        rows = self.execute_query(query)
        return rows[0]['count'] if rows else 0

    def vacuum(self) -> None:
        """
        Vacuum the database to reclaim space and optimize.
        """
        with self.get_connection() as conn:
            conn.execute("VACUUM")

    def backup(self, backup_path: str) -> None:
        """
        Create a backup of the database.

        Args:
            backup_path: Path for the backup file
        """
        with self.get_connection() as source:
            backup_conn = sqlcipher.connect(backup_path) if self.is_encrypted else sqlite3.connect(backup_path)
            if self.is_encrypted:
                backup_conn.execute(f"PRAGMA key = '{self.encryption_key}'")

            source.backup(backup_conn)
            backup_conn.close()

        print(f"Database backed up to: {backup_path}")

    def close(self) -> None:
        """
        Close the database manager.

        Note: Connections are managed per-transaction, so this is mainly
        for cleanup and future resource management.
        """
        pass


def create_database_manager(
    db_path: str = "data/p3edge.db",
    encryption_key: Optional[str] = None
) -> DatabaseManager:
    """
    Factory function to create a DatabaseManager instance.

    Args:
        db_path: Path to database file
        encryption_key: Encryption key (None for development mode)

    Returns:
        Configured DatabaseManager instance
    """
    return DatabaseManager(db_path, encryption_key)
