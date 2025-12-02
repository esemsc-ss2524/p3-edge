"""
Database manager with SQLCipher encryption support.

This module handles all database operations with encryption at rest.
"""

import os
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    SQLCIPHER_AVAILABLE = True
except ImportError:
    SQLCIPHER_AVAILABLE = False
    import sqlite3 as sqlcipher  # Fallback for development

from ..models.order import Order


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
            # Use sqlcipher's Row class for encrypted connections
            conn.row_factory = sqlcipher.Row
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA foreign_keys = ON")
            # Use sqlite3's Row class for unencrypted connections
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

    # Order management methods

    def create_order(self, order: Order) -> None:
        """
        Create a new order in the database.

        Args:
            order: Order object to save
        """
        query = """
            INSERT INTO orders (
                order_id, vendor, status, items, total_cost,
                created_at, approved_at, placed_at, user_notes, auto_generated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # Serialize items to JSON
        items_json = json.dumps([item.dict() for item in order.items])

        params = (
            order.order_id,
            order.vendor.value if hasattr(order.vendor, 'value') else str(order.vendor),
            order.status.value if hasattr(order.status, 'value') else str(order.status),
            items_json,
            order.total_cost,
            order.created_at.isoformat() if order.created_at else None,
            order.approved_at.isoformat() if order.approved_at else None,
            order.placed_at.isoformat() if order.placed_at else None,
            order.user_notes,
            1 if order.auto_generated else 0
        )

        self.execute_update(query, params)

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get an order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order object or None if not found
        """
        query = """
            SELECT order_id, vendor, status, items, total_cost,
                   created_at, approved_at, placed_at, user_notes, auto_generated
            FROM orders
            WHERE order_id = ?
        """

        rows = self.execute_query(query, (order_id,))

        if not rows:
            return None

        return self._row_to_order(rows[0])

    def update_order(self, order: Order) -> None:
        """
        Update an existing order.

        Args:
            order: Order object with updated values
        """
        query = """
            UPDATE orders
            SET vendor = ?, status = ?, items = ?, total_cost = ?,
                approved_at = ?, placed_at = ?, user_notes = ?
            WHERE order_id = ?
        """

        # Serialize items to JSON
        items_json = json.dumps([item.dict() for item in order.items])

        params = (
            order.vendor.value if hasattr(order.vendor, 'value') else str(order.vendor),
            order.status.value if hasattr(order.status, 'value') else str(order.status),
            items_json,
            order.total_cost,
            order.approved_at.isoformat() if order.approved_at else None,
            order.placed_at.isoformat() if order.placed_at else None,
            order.user_notes,
            order.order_id
        )

        self.execute_update(query, params)

    def get_all_orders(self) -> List[Order]:
        """
        Get all orders from the database.

        Returns:
            List of Order objects
        """
        query = """
            SELECT order_id, vendor, status, items, total_cost,
                   created_at, approved_at, placed_at, user_notes, auto_generated
            FROM orders
            ORDER BY created_at DESC
        """

        rows = self.execute_query(query)
        return [self._row_to_order(row) for row in rows]

    def _row_to_order(self, row: sqlite3.Row) -> Order:
        """
        Convert a database row to an Order object.

        Args:
            row: Database row

        Returns:
            Order object
        """
        # Parse items from JSON
        items_data = json.loads(row['items'])

        # Parse dates
        created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
        approved_at = datetime.fromisoformat(row['approved_at']) if row['approved_at'] else None
        placed_at = datetime.fromisoformat(row['placed_at']) if row['placed_at'] else None

        # Create Order object - items will be validated by Pydantic
        order = Order(
            order_id=row['order_id'],
            vendor=row['vendor'],
            status=row['status'],
            items=items_data,  # Pydantic will convert these dicts to OrderItem objects
            total_cost=row['total_cost'],
            created_at=created_at,
            approved_at=approved_at,
            placed_at=placed_at,
            user_notes=row['user_notes'],
            auto_generated=bool(row['auto_generated'])
        )

        return order

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
