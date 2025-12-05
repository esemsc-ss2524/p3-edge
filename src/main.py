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
from src.services.cart_service import CartService
from src.services.autonomous_agent import AutonomousAgent
from src.vendors.amazon_client import AmazonClient
from src.ui import MainWindow
from src.utils import get_audit_logger, get_logger

# Import tool framework
from src.tools import get_registry, ToolExecutor

# Import all tool classes
from src.tools.database_tools import (
    GetInventoryItemsTool,
    SearchInventoryTool,
    GetExpiringItemsTool,
    GetForecastsTool,
    GetOrderHistoryTool,
    GetPendingOrdersTool,
)
from src.tools.forecast_tools import (
    GenerateForecastTool,
    GetLowStockPredictionsTool,
    AnalyzeUsageTrendsTool,
    GetModelPerformanceTool,
    CheckModelHealthTool,
)
from src.tools.training_tools import (
    StartModelTrainingTool,
    GetTrainingStatusTool,
    GetTrainingHistoryTool,
)
from src.tools.vendor_tools import (
    SearchProductsTool,
    # BatchSearchProductsTool,
    GetProductDetailsTool,
    CheckProductAvailabilityTool,
    AddToCartTool,
    ViewCartTool,
    RemoveFromCartTool,
    UpdateCartQuantityTool,
)
from src.tools.utility_tools import (
    CalculateDaysRemainingTool,
    CalculateQuantityNeededTool,
    CheckBudgetTool,
    GetUserPreferencesTool,
    ConvertUnitTool,
)
from src.tools.blocked_tools import (
    PlaceOrderTool,
    ApproveOrderTool,
    DeleteInventoryItemTool,
    ModifyPreferencesTool,
    ClearDatabaseTool,
)


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
        self.cart_service = None
        self.vendor_client = None
        self.tool_executor = None
        self.autonomous_agent = None
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

            # Initialize vendor client and cart service
            self.vendor_client = AmazonClient()
            self.cart_service = CartService(self.db_manager)
            self.logger.info("Vendor client and cart service initialized")

            # Initialize tools for LLM agent
            self.tool_executor = self._initialize_tools()
            self.logger.info(f"Tool system initialized with {self.tool_executor.registry.get_tool_count()} tools")

            # Initialize autonomous agent
            agent_enabled = self.config.get("agent.enabled", True)
            agent_interval = self.config.get("agent.cycle_interval_minutes", 60)
            self.autonomous_agent = AutonomousAgent(
                db_manager=self.db_manager,
                tool_executor=self.tool_executor,
                cycle_interval_minutes=agent_interval,
                enabled=agent_enabled
            )
            self.logger.info(f"Autonomous agent initialized (enabled: {agent_enabled}, interval: {agent_interval}m)")

            # Log startup
            self.audit_logger.log_action(
                action_type=ActionType.SYSTEM_STARTUP.value,
                actor=Actor.SYSTEM.value,
                details={"version": "0.1.0", "phase": "Phase 6: Autonomous Agent"}
            )

            self.logger.info("Application initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _initialize_tools(self) -> ToolExecutor:
        """
        Initialize all tools for the LLM agent.

        Returns:
            ToolExecutor instance with all tools registered
        """
        self.logger.info("Initializing tool system...")

        # Get the global registry
        registry = get_registry()

        # Initialize and register database tools
        self.logger.info("Registering database tools...")
        registry.register(GetInventoryItemsTool(self.db_manager))
        registry.register(SearchInventoryTool(self.db_manager))
        registry.register(GetExpiringItemsTool(self.db_manager))
        registry.register(GetForecastsTool(self.db_manager))
        registry.register(GetOrderHistoryTool(self.db_manager))
        registry.register(GetPendingOrdersTool(self.db_manager))

        # Initialize and register forecasting tools
        self.logger.info("Registering forecasting tools...")
        registry.register(GenerateForecastTool(self.forecast_service))
        registry.register(GetLowStockPredictionsTool(self.forecast_service))
        registry.register(AnalyzeUsageTrendsTool(self.forecast_service))
        registry.register(GetModelPerformanceTool(self.forecast_service))
        registry.register(CheckModelHealthTool(self.forecast_service))

        # Initialize and register training tools
        if self.training_scheduler:
            self.logger.info("Registering training tools...")
            registry.register(StartModelTrainingTool(self.training_scheduler))
            registry.register(GetTrainingStatusTool(self.training_scheduler))
            registry.register(GetTrainingHistoryTool(self.training_scheduler))

        # Initialize and register vendor tools
        self.logger.info("Registering vendor and cart tools...")
        registry.register(SearchProductsTool(self.vendor_client))
        # registry.register(BatchSearchProductsTool(self.vendor_client))
        registry.register(GetProductDetailsTool(self.vendor_client))
        registry.register(CheckProductAvailabilityTool(self.vendor_client))
        registry.register(AddToCartTool(self.cart_service, self.vendor_client))
        registry.register(ViewCartTool(self.cart_service))
        registry.register(RemoveFromCartTool(self.cart_service))
        registry.register(UpdateCartQuantityTool(self.cart_service))

        # Initialize and register utility tools
        self.logger.info("Registering utility tools...")
        registry.register(CalculateDaysRemainingTool(self.db_manager))
        registry.register(CalculateQuantityNeededTool(self.db_manager, self.forecast_service))
        registry.register(CheckBudgetTool(self.db_manager))
        registry.register(GetUserPreferencesTool(self.db_manager))
        registry.register(ConvertUnitTool())

        # Initialize and register blocked tools (for safety)
        self.logger.info("Registering blocked tools (safety guards)...")
        registry.register(PlaceOrderTool())
        registry.register(ApproveOrderTool())
        registry.register(DeleteInventoryItemTool())
        registry.register(ModifyPreferencesTool())
        registry.register(ClearDatabaseTool())

        # Mark registry as initialized
        registry.mark_initialized()

        # Create and return tool executor
        tool_executor = ToolExecutor(self.db_manager)

        # Log summary
        summary = registry.get_summary()
        self.logger.info(f"Tool system ready:")
        self.logger.info(f"  Total tools: {summary['total_tools']}")
        self.logger.info(f"  Available: {summary['available_tools']}")
        self.logger.info(f"  Blocked: {summary['blocked_tools']}")
        self.logger.info(f"  By category: {summary['by_category']}")

        return tool_executor

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

            # Create and show main window with db_manager, tool_executor, cart_service, and autonomous_agent
            self.main_window = MainWindow(
                db_manager=self.db_manager,
                tool_executor=self.tool_executor,
                cart_service=self.cart_service,
                autonomous_agent=self.autonomous_agent
            )
            self.main_window.show()

            self.logger.info("Application running...")

            # Start autonomous agent
            if self.autonomous_agent:
                self.autonomous_agent.start()
                self.logger.info("Autonomous agent started")

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

        # Stop autonomous agent
        if self.autonomous_agent:
            self.autonomous_agent.stop()

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
