"""
Main window for P3-Edge application.

Provides the primary user interface with navigation and main content area.
"""

from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QToolBar,
    QStatusBar,
    QMessageBox,
)

from src.database.db_manager import DatabaseManager
from src.services import InventoryService
from src.services.forecast_service import ForecastService
from src.ui.p3_dashboard import P3Dashboard
from src.ui.inventory_page import InventoryPage
from src.ui.forecast_page import ForecastPage
from src.ui.smart_fridge_page import SmartFridgePage
from src.ui.cart_page import CartPage
from src.utils import get_logger


class MainWindow(QMainWindow):
    """Main application window with navigation."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        tool_executor: Optional = None,
        cart_service: Optional = None
    ) -> None:
        """
        Initialize the main window.

        Args:
            db_manager: Database manager instance (optional for Phase 1 compatibility)
            tool_executor: Tool executor for LLM agent (optional)
            cart_service: Cart service instance (optional, shared with tools)
        """
        super().__init__()
        self.setWindowTitle("P3-Edge - Autonomous Grocery Assistant")
        self.setMinimumSize(1024, 768)

        # Store dependencies
        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.cart_service = cart_service
        self.inventory_service = InventoryService(db_manager) if db_manager else None
        self.forecast_service = ForecastService(db_manager) if db_manager else None
        self.logger = get_logger("main_window")

        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create UI components
        self._create_navigation_panel()
        self._create_content_area()
        self._create_toolbar()
        self._create_status_bar()
        self._create_menu_bar()

        # Show dashboard by default
        self.show_dashboard()

    def _create_navigation_panel(self) -> None:
        """Create the left navigation panel."""
        self.nav_panel = QWidget()
        self.nav_panel.setMaximumWidth(250)
        self.nav_panel.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                text-align: left;
                padding: 15px 20px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
            QPushButton:pressed {
                background-color: #1abc9c;
            }
        """)

        nav_layout = QVBoxLayout(self.nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        # App title
        title_label = QLabel("P3-Edge")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                background-color: #1abc9c;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(title_label)

        # Navigation buttons
        self.nav_buttons = {}

        nav_items = [
            ("🤖 P3 Home", self.show_dashboard),
            ("📦 Inventory", self.show_inventory),
            ("📊 Forecasts", self.show_forecasts),
            ("🛒 Shopping Cart", self.show_shopping_cart),
            ("📜 Orders", self.show_order_history),
            ("🌡️ Smart Fridge", self.show_smart_fridge),
            ("⚙️ Settings", self.show_settings),
        ]

        for label, callback in nav_items:
            btn = QPushButton(f"  {label}")
            btn.clicked.connect(callback)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_buttons[label] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch()

        # Add navigation panel to main layout
        self.main_layout.addWidget(self.nav_panel)

    def _create_content_area(self) -> None:
        """Create the main content area with stacked pages."""
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #ecf0f1;
            }
        """)

        # Create pages
        self.pages = {
            "dashboard": P3Dashboard(self.db_manager, tool_executor=self.tool_executor) if self.db_manager else self._create_placeholder_page("Dashboard"),
            "inventory": InventoryPage(self.inventory_service) if self.inventory_service else self._create_placeholder_page("Inventory Management"),
            "forecasts": ForecastPage(self.forecast_service) if self.forecast_service else self._create_placeholder_page("Forecast View"),
            "shopping_cart": CartPage(self.db_manager, cart_service=self.cart_service) if self.db_manager else self._create_placeholder_page("Shopping Cart"),
            "order_history": self._create_placeholder_page("Order History"),
            "smart_fridge": SmartFridgePage(self.db_manager) if self.db_manager else self._create_placeholder_page("Smart Refrigerator"),
            "settings": self._create_placeholder_page("Settings"),
        }

        for page in self.pages.values():
            self.content_stack.addWidget(page)

        # Connect smart fridge signals
        if "smart_fridge" in self.pages and hasattr(self.pages["smart_fridge"], "connection_widget"):
            smart_fridge_page = self.pages["smart_fridge"]
            if hasattr(smart_fridge_page, "connection_widget"):
                smart_fridge_page.connection_widget.connection_changed.connect(
                    self._on_smart_fridge_connection_changed
                )

        self.main_layout.addWidget(self.content_stack)

    def _create_dashboard_page(self) -> QWidget:
        """Create the dashboard page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Welcome message
        welcome = QLabel("Welcome to P3-Edge")
        welcome.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(welcome)

        # Subtitle
        subtitle = QLabel("Your autonomous grocery shopping assistant")
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        # Stats cards container
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        # Create stat cards (store for updates)
        self.stat_cards = {}

        stat_card_configs = [
            ("total_items", "Inventory Items", "0", "#3498db"),
            ("low_stock", "Low Stock Items", "0", "#e74c3c"),
            ("pending_orders", "Pending Orders", "0", "#f39c12"),
            ("savings", "This Month's Savings", "$0.00", "#27ae60"),
        ]

        for key, title, value, color in stat_card_configs:
            card = self._create_stat_card(title, value, color)
            self.stat_cards[key] = card
            stats_layout.addWidget(card)

        layout.addLayout(stats_layout)
        layout.addStretch()

        # System status
        status_label = QLabel("System Status: Ready")
        status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #27ae60;
                padding: 10px;
                background-color: #d5f4e6;
                border-radius: 5px;
            }
        """)
        layout.addWidget(status_label)

        return page

    def _create_stat_card(self, title: str, value: str, color: str) -> QWidget:
        """Create a statistics card widget."""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border-left: 5px solid {color};
                border-radius: 5px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                font-weight: bold;
            }
        """)
        layout.addWidget(title_label)

        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                color: {color};
                font-weight: bold;
            }}
        """)
        layout.addWidget(value_label)

        return card

    def _create_placeholder_page(self, page_name: str) -> QWidget:
        """Create a placeholder page for future implementation."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(f"{page_name}\n\nComing Soon...")
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #95a5a6;
            }
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        return page

    def _create_toolbar(self) -> None:
        """Create the application toolbar."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Add toolbar actions
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        self.toolbar.addAction(refresh_action)

        self.toolbar.addSeparator()

        sync_action = QAction("Sync Data", self)
        sync_action.triggered.connect(self.sync_data)
        self.toolbar.addAction(sync_action)

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Add smart fridge connection indicator
        self.fridge_status_label = QLabel("🔴 Smart Fridge: Disconnected")
        self.fridge_status_label.setStyleSheet("""
            QLabel {
                padding: 2px 10px;
                color: #7f8c8d;
                font-size: 11px;
            }
        """)
        self.status_bar.addPermanentWidget(self.fridge_status_label)

    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    # Navigation methods
    def show_dashboard(self) -> None:
        """Show the dashboard page."""
        self.content_stack.setCurrentWidget(self.pages["dashboard"])
        self.status_bar.showMessage("Dashboard")
        self._update_dashboard_stats()

    def _update_dashboard_stats(self) -> None:
        """Update dashboard statistics."""
        if not self.inventory_service:
            return

        try:
            stats = self.inventory_service.get_stats()

            # Update stat cards
            if "total_items" in self.stat_cards:
                self._update_stat_card_value(
                    self.stat_cards["total_items"],
                    str(stats.get("total_items", 0))
                )

            if "low_stock" in self.stat_cards:
                self._update_stat_card_value(
                    self.stat_cards["low_stock"],
                    str(stats.get("low_stock_items", 0))
                )

        except Exception as e:
            self.logger.error(f"Failed to update dashboard stats: {e}")

    def _update_stat_card_value(self, card_widget, new_value: str) -> None:
        """Update the value label in a stat card."""
        # Find the value label (second child in the layout)
        layout = card_widget.layout()
        if layout and layout.count() >= 2:
            value_label = layout.itemAt(1).widget()
            if value_label:
                value_label.setText(new_value)

    def show_inventory(self) -> None:
        """Show the inventory page."""
        self.content_stack.setCurrentWidget(self.pages["inventory"])
        self.status_bar.showMessage("Inventory Management")

    def show_forecasts(self) -> None:
        """Show the forecasts page."""
        self.content_stack.setCurrentWidget(self.pages["forecasts"])
        self.status_bar.showMessage("Forecasts")

    def show_chat(self) -> None:
        """Show the AI chat page."""
        self.content_stack.setCurrentWidget(self.pages["chat"])
        self.status_bar.showMessage("AI Chat")

    def show_shopping_cart(self) -> None:
        """Show the shopping cart page."""
        self.content_stack.setCurrentWidget(self.pages["shopping_cart"])
        self.status_bar.showMessage("Shopping Cart")

    def show_order_history(self) -> None:
        """Show the order history page."""
        self.content_stack.setCurrentWidget(self.pages["order_history"])
        self.status_bar.showMessage("Order History")

    def show_smart_fridge(self) -> None:
        """Show the smart fridge page."""
        self.content_stack.setCurrentWidget(self.pages["smart_fridge"])
        self.status_bar.showMessage("Smart Refrigerator")

    def show_settings(self) -> None:
        """Show the settings page."""
        self.content_stack.setCurrentWidget(self.pages["settings"])
        self.status_bar.showMessage("Settings")

    # Action methods
    def refresh_data(self) -> None:
        """Refresh data from all sources."""
        self.status_bar.showMessage("Refreshing data...", 2000)
        # TODO: Implement data refresh logic

    def sync_data(self) -> None:
        """Sync data with external sources."""
        self.status_bar.showMessage("Syncing data...", 2000)
        # TODO: Implement sync logic

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About P3-Edge",
            "<h2>P3-Edge</h2>"
            "<p>Autonomous Grocery Shopping Assistant</p>"
            "<p>Version 0.1.0</p>"
            "<p>Privacy-first edge computing solution for household management.</p>"
        )

    def _on_smart_fridge_connection_changed(self, connected: bool) -> None:
        """Handle smart fridge connection status change."""
        if connected:
            self.fridge_status_label.setText("🟢 Smart Fridge: Connected")
            self.fridge_status_label.setStyleSheet("""
                QLabel {
                    padding: 2px 10px;
                    color: #27ae60;
                    font-size: 11px;
                }
            """)
        else:
            self.fridge_status_label.setText("🔴 Smart Fridge: Disconnected")
            self.fridge_status_label.setStyleSheet("""
                QLabel {
                    padding: 2px 10px;
                    color: #7f8c8d;
                    font-size: 11px;
                }
            """)
