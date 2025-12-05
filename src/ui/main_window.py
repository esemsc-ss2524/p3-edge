from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QToolBar, QStatusBar, QMessageBox
)

from src.database.db_manager import DatabaseManager
from src.services import InventoryService
from src.services.forecast_service import ForecastService
from src.ui.p3_dashboard import P3Dashboard
from src.ui.inventory_page import InventoryPage
from src.ui.forecast_page import ForecastPage
from src.ui.cart_page import CartPage
from src.ui.orders_page import OrdersPage
from src.ui.settings_page import SettingsPage
from src.utils import get_logger

class MainWindow(QMainWindow):
    def __init__(self, db_manager: Optional[DatabaseManager] = None, 
                 tool_executor=None, cart_service=None, autonomous_agent=None):
        super().__init__()
        self.setWindowTitle("P3-Edge | Autonomous Home")
        self.resize(1280, 800)
        self.setStyleSheet("background-color: #F2F2F7;")

        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.cart_service = cart_service
        self.autonomous_agent = autonomous_agent
        self.inventory_service = InventoryService(db_manager) if db_manager else None
        self.forecast_service = ForecastService(db_manager) if db_manager else None
        self.logger = get_logger("main_window")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._create_navigation_panel()
        self._create_content_area()
        self.show_dashboard()

    def _create_navigation_panel(self):
        self.nav_panel = QWidget()
        self.nav_panel.setFixedWidth(240)
        self.nav_panel.setStyleSheet("""
            QWidget { background-color: #FFFFFF; border-right: 1px solid #E5E5EA; }
            QPushButton {
                text-align: left; padding: 12px 20px; border: none;
                color: #1C1C1E; font-size: 14px; font-weight: 500; border-radius: 8px; margin: 4px 10px;
            }
            QPushButton:hover { background-color: #F2F2F7; }
            QPushButton:checked { background-color: #007AFF; color: white; }
        """)
        
        layout = QVBoxLayout(self.nav_panel)
        
        # Logo Area
        lbl_logo = QLabel("P3-EDGE")
        lbl_logo.setStyleSheet("color: #007AFF; font-size: 22px; font-weight: 900; padding: 25px 20px;")
        layout.addWidget(lbl_logo)
        
        self.nav_btns = []
        
        nav_items = [
            ("Home", self.show_dashboard),
            ("Inventory", self.show_inventory),
            ("Forecasts", self.show_forecasts),
            ("Shopping Cart", self.show_cart),
            ("Order History", self.show_orders),
            ("Settings", self.show_settings)
        ]
        
        for label, callback in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(callback)
            btn.clicked.connect(lambda checked, b=btn: self._update_nav_style(b))
            layout.addWidget(btn)
            self.nav_btns.append(btn)
            
        layout.addStretch()
        self.main_layout.addWidget(self.nav_panel)

    def _update_nav_style(self, active_btn):
        for btn in self.nav_btns:
            btn.setChecked(btn == active_btn)

    def _create_content_area(self):
        self.stack = QStackedWidget()
        
        # Instantiate Pages
        self.pages = {}
        if self.db_manager:
            self.pages["home"] = P3Dashboard(self.db_manager, self.tool_executor, self.autonomous_agent)
            self.pages["inventory"] = InventoryPage(self.inventory_service)
            self.pages["forecasts"] = ForecastPage(self.forecast_service)
            self.pages["cart"] = CartPage(self.db_manager, self.cart_service)
            self.pages["orders"] = OrdersPage(self.db_manager, self.cart_service)
            self.pages["settings"] = SettingsPage(self.db_manager)
            
            self.stack.addWidget(self.pages["home"])
            self.stack.addWidget(self.pages["inventory"])
            self.stack.addWidget(self.pages["forecasts"])
            self.stack.addWidget(self.pages["cart"])
            self.stack.addWidget(self.pages["orders"])
            self.stack.addWidget(self.pages["settings"])
            
        self.main_layout.addWidget(self.stack)

    # Nav Callbacks
    def show_dashboard(self): self.stack.setCurrentWidget(self.pages["home"])
    def show_inventory(self): self.stack.setCurrentWidget(self.pages["inventory"])
    def show_forecasts(self): self.stack.setCurrentWidget(self.pages["forecasts"])
    def show_cart(self): self.stack.setCurrentWidget(self.pages["cart"])
    def show_orders(self): self.stack.setCurrentWidget(self.pages["orders"])
    def show_settings(self): self.stack.setCurrentWidget(self.pages["settings"])