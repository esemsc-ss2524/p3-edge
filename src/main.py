#!/usr/bin/env python3
"""
Main entry point for P3-Edge application.

Autonomous grocery shopping assistant with edge AI.
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication

from src.config import get_config_manager
from src.database.db_manager import create_database_manager
from src.models import ActionType, Actor, create_audit_log
from src.services.forecast_service import ForecastService
from src.services.training_scheduler import TrainingScheduler
from src.ui import MainWindow
from src.utils import get_audit_logger, get_logger


class P3EdgeApplication:
    """Main application controller."""

    def __init__(self) -> None:
        """Initialize the application."""
        self.logger = get_logger("p3edge")
        self.config = get_config_manager()
        self.db_manager = None
        self.audit_logger = None
        self.forecast_service = None
        self.training_scheduler = None
        self.main_window = None

    def initialize(self) -> bool:
        """
        Initialize application components.

        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("P3-Edge - Autonomous Grocery Assistant")
            self.logger.info("Version 0.1.0 (Phase 1: Foundation)")
            self.logger.info("=" * 60)

            # Initialize database
            db_path = self.config.get("database.path", "data/p3edge.db")
            encryption_key = self.config.get_database_encryption_key()

            self.logger.info(f"Connecting to database: {db_path}")

            # Check if database exists
            db_exists = Path(db_path).exists()

            self.db_manager = create_database_manager(db_path, encryption_key)

            if not db_exists:
                self.logger.warning("Database not found. Please run 'python scripts/init_db.py' first.")
                return False

            # Initialize audit logger
            self.audit_logger = get_audit_logger(self.db_manager)

            # Initialize forecast service
            self.forecast_service = ForecastService(self.db_manager)

            # Initialize and start training scheduler
            enable_scheduler = self.config.get("forecasting.auto_training", True)
            if enable_scheduler:
                self.training_scheduler = TrainingScheduler(
                    forecast_service=self.forecast_service,
                    db_manager=self.db_manager,
                    training_hour=2,  # 2 AM
                    training_minute=0,
                )
                self.training_scheduler.start()
                self.logger.info("Training scheduler enabled")
            else:
                self.logger.info("Training scheduler disabled by configuration")

            # Log startup
            self.audit_logger.log_action(
                action_type=ActionType.SYSTEM_STARTUP.value,
                actor=Actor.SYSTEM.value,
                details={"version": "0.1.0", "phase": "Phase 1: Foundation"}
            )

            self.logger.info("Application initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code
        """
        try:
            # Create Qt application
            app = QApplication(sys.argv)
            app.setApplicationName("P3-Edge")
            app.setOrganizationName("P3-Edge")

            # Create and show main window with db_manager
            self.main_window = MainWindow(db_manager=self.db_manager)
            self.main_window.show()

            self.logger.info("Application running...")

            # Run event loop
            exit_code = app.exec()

            # Log shutdown
            if self.audit_logger:
                self.audit_logger.log_action(
                    action_type=ActionType.SYSTEM_SHUTDOWN.value,
                    actor=Actor.SYSTEM.value,
                    details={"exit_code": exit_code}
                )

            self.logger.info(f"Application exited with code {exit_code}")
            return exit_code

        except Exception as e:
            self.logger.error(f"Application error: {e}")
            import traceback
            traceback.print_exc()
            return 1

    def shutdown(self) -> None:
        """Clean shutdown of the application."""
        self.logger.info("Shutting down application...")

        # Stop training scheduler
        if self.training_scheduler:
            self.training_scheduler.stop()

        # Save all forecast models
        if self.forecast_service:
            try:
                self.forecast_service.save_all_models()
            except Exception as e:
                self.logger.error(f"Failed to save models on shutdown: {e}")

        # Close database
        if self.db_manager:
            self.db_manager.close()

        self.logger.info("Application shutdown complete")


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code
    """
    app = P3EdgeApplication()

    if not app.initialize():
        print("\n" + "=" * 60)
        print("ERROR: Application initialization failed")
        print("=" * 60)
        print("\nPlease run the database initialization script:")
        print("  python scripts/init_db.py")
        print("\nThen try running the application again:")
        print("  python src/main.py")
        print("=" * 60)
        return 1

    try:
        exit_code = app.run()
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal")
        exit_code = 0
    finally:
        app.shutdown()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
