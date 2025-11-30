"""
Logging infrastructure for P3-Edge application.

Provides structured logging with file rotation and audit trail integration.
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from ..config.config_manager import get_config_manager


class P3EdgeLogger:
    """
    Custom logger for P3-Edge application.

    Provides both file and console logging with proper formatting.
    """

    def __init__(
        self,
        name: str = "p3edge",
        log_dir: str = "logs",
        log_file: str = "p3edge.log"
    ) -> None:
        """
        Initialize logger.

        Args:
            name: Logger name
            log_dir: Directory for log files
            log_file: Log file name
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / log_file

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Get configuration
        config = get_config_manager()
        self.log_level = config.get("logging.level", "INFO")
        self.max_file_size_mb = config.get("logging.max_file_size_mb", 10)
        self.backup_count = config.get("logging.backup_count", 5)

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, self.log_level))

        # Remove existing handlers
        self.logger.handlers.clear()

        # Create formatters
        self.file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        self.console_formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # Set up handlers
        self._setup_file_handler()
        self._setup_console_handler()

    def _setup_file_handler(self) -> None:
        """Set up rotating file handler."""
        max_bytes = self.max_file_size_mb * 1024 * 1024

        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # File gets all logs
        file_handler.setFormatter(self.file_formatter)

        self.logger.addHandler(file_handler)

    def _setup_console_handler(self) -> None:
        """Set up console handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))
        console_handler.setFormatter(self.console_formatter)

        self.logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)

    def get_logger(self) -> logging.Logger:
        """
        Get underlying logger instance.

        Returns:
            logging.Logger instance
        """
        return self.logger


class AuditLogger:
    """
    Audit logger that writes to database audit log.

    Integrates with the AuditLog model for transparency.
    """

    def __init__(self, db_manager=None) -> None:
        """
        Initialize audit logger.

        Args:
            db_manager: Database manager instance (optional)
        """
        self.db_manager = db_manager
        self.file_logger = get_logger("audit")

    def log_action(
        self,
        action_type: str,
        actor: str,
        details: Optional[dict] = None,
        outcome: str = "success",
        item_id: Optional[str] = None,
        order_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log an action to the audit trail.

        Args:
            action_type: Type of action
            actor: Who performed the action
            details: Additional details
            outcome: Action outcome (success, failure, pending)
            item_id: Related inventory item ID
            order_id: Related order ID
            error_message: Error message if failed
        """
        import uuid
        import json

        # Create log entry
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": actor,
            "details": json.dumps(details or {}),
            "outcome": outcome,
            "item_id": item_id,
            "order_id": order_id,
            "error_message": error_message
        }

        # Log to file
        self.file_logger.info(
            f"AUDIT: {action_type} by {actor} - {outcome}",
            extra={"audit": log_entry}
        )

        # Log to database if available
        if self.db_manager:
            try:
                query = """
                    INSERT INTO audit_log
                    (log_id, timestamp, action_type, actor, details, outcome, item_id, order_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.db_manager.execute_update(
                    query,
                    (
                        log_entry["log_id"],
                        log_entry["timestamp"],
                        log_entry["action_type"],
                        log_entry["actor"],
                        log_entry["details"],
                        log_entry["outcome"],
                        log_entry["item_id"],
                        log_entry["order_id"]
                    )
                )
            except Exception as e:
                self.file_logger.error(f"Failed to write audit log to database: {e}")

    def get_recent_logs(self, limit: int = 100) -> list:
        """
        Get recent audit logs from database.

        Args:
            limit: Maximum number of logs to retrieve

        Returns:
            List of audit log entries
        """
        if not self.db_manager:
            return []

        query = """
            SELECT * FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = self.db_manager.execute_query(query, (limit,))
        return [dict(row) for row in rows]

    def get_logs_by_actor(self, actor: str, limit: int = 100) -> list:
        """
        Get audit logs for specific actor.

        Args:
            actor: Actor name
            limit: Maximum number of logs

        Returns:
            List of audit log entries
        """
        if not self.db_manager:
            return []

        query = """
            SELECT * FROM audit_log
            WHERE actor = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = self.db_manager.execute_query(query, (actor, limit))
        return [dict(row) for row in rows]

    def get_logs_by_action_type(self, action_type: str, limit: int = 100) -> list:
        """
        Get audit logs for specific action type.

        Args:
            action_type: Action type
            limit: Maximum number of logs

        Returns:
            List of audit log entries
        """
        if not self.db_manager:
            return []

        query = """
            SELECT * FROM audit_log
            WHERE action_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = self.db_manager.execute_query(query, (action_type, limit))
        return [dict(row) for row in rows]


# Global logger instance
_logger: Optional[P3EdgeLogger] = None
_audit_logger: Optional[AuditLogger] = None


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get application logger.

    Args:
        name: Optional logger name (defaults to p3edge)

    Returns:
        Logger instance
    """
    global _logger
    if _logger is None:
        _logger = P3EdgeLogger(name or "p3edge")
    return _logger.get_logger()


def get_audit_logger(db_manager=None) -> AuditLogger:
    """
    Get audit logger instance.

    Args:
        db_manager: Database manager instance

    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(db_manager)
    elif db_manager is not None:
        _audit_logger.db_manager = db_manager
    return _audit_logger


def reset_loggers() -> None:
    """Reset global logger instances (mainly for testing)."""
    global _logger, _audit_logger
    _logger = None
    _audit_logger = None
