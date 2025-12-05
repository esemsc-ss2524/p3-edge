"""
Settings page for application configuration.

Provides interface for managing Smart Fridge connection, budget settings, and other preferences.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QGroupBox,
    QFormLayout,
    QDoubleSpinBox,
    QComboBox,
    QPushButton,
    QMessageBox,
    QLineEdit,
)

from src.database.db_manager import DatabaseManager
from src.ui.smart_fridge_page import SmartFridgeConnectionWidget
from src.utils import get_logger


class BudgetSettingsWidget(QWidget):
    """Widget for managing budget settings."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = get_logger("budget_settings")

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Title
        title = QLabel("Budget Management")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Set your grocery shopping budget to help track spending and get alerts when approaching limits."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        layout.addWidget(desc)

        # Budget Settings Group
        budget_group = QGroupBox("Budget Configuration")
        budget_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        budget_layout = QFormLayout()
        budget_layout.setSpacing(15)

        # Budget Amount
        self.budget_amount = QDoubleSpinBox()
        self.budget_amount.setPrefix("$ ")
        self.budget_amount.setMinimum(0.0)
        self.budget_amount.setMaximum(99999.99)
        self.budget_amount.setValue(500.0)
        self.budget_amount.setDecimals(2)
        self.budget_amount.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #3498db;
            }
        """)
        budget_layout.addRow("Budget Amount:", self.budget_amount)

        # Budget Period
        self.budget_period = QComboBox()
        self.budget_period.addItems(["Weekly", "Monthly", "Bi-weekly", "Quarterly"])
        self.budget_period.setCurrentText("Monthly")
        self.budget_period.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #3498db;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        budget_layout.addRow("Budget Period:", self.budget_period)

        # Connect period change to reload settings
        self.budget_period.currentTextChanged.connect(self._on_period_changed)

        # Alert Threshold
        self.alert_threshold = QDoubleSpinBox()
        self.alert_threshold.setSuffix(" %")
        self.alert_threshold.setMinimum(0.0)
        self.alert_threshold.setMaximum(100.0)
        self.alert_threshold.setValue(80.0)
        self.alert_threshold.setDecimals(0)
        self.alert_threshold.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #3498db;
            }
        """)
        budget_layout.addRow("Alert Threshold:", self.alert_threshold)

        budget_group.setLayout(budget_layout)
        layout.addWidget(budget_group)

        # Current Spending Group
        spending_group = QGroupBox("Current Period Spending")
        spending_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        spending_layout = QFormLayout()
        spending_layout.setSpacing(10)

        self.spent_label = QLabel("$0.00")
        self.spent_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #3498db;")
        spending_layout.addRow("Total Spent:", self.spent_label)

        self.remaining_label = QLabel("$500.00")
        self.remaining_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
        spending_layout.addRow("Remaining:", self.remaining_label)

        self.percentage_label = QLabel("0%")
        self.percentage_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #7f8c8d;")
        spending_layout.addRow("Used:", self.percentage_label)

        spending_group.setLayout(spending_layout)
        layout.addWidget(spending_group)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        view_period_btn = QPushButton("View Period Details")
        view_period_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        view_period_btn.clicked.connect(self._reset_period)
        button_layout.addWidget(view_period_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

    def _on_period_changed(self, period: str):
        """Handle period selection change."""
        self._load_settings()

    def _load_settings(self):
        """Load budget settings from database."""
        if not self.db_manager:
            return

        try:
            # Load preferences from database
            query = "SELECT key, value FROM preferences WHERE key IN ('spend_cap_weekly', 'spend_cap_monthly', 'budget_alert_threshold')"
            results = self.db_manager.execute_query(query)
            prefs = dict(results) if results else {}

            # Load budget based on current period selection
            period = self.budget_period.currentText()
            if period == "Weekly" and "spend_cap_weekly" in prefs:
                self.budget_amount.setValue(float(prefs["spend_cap_weekly"]))
            elif period == "Monthly" and "spend_cap_monthly" in prefs:
                self.budget_amount.setValue(float(prefs["spend_cap_monthly"]))

            # Load alert threshold
            if "budget_alert_threshold" in prefs:
                self.alert_threshold.setValue(float(prefs["budget_alert_threshold"]))

            self._update_spending_display()

        except Exception as e:
            self.logger.error(f"Failed to load budget settings: {e}")

    def _save_settings(self):
        """Save budget settings to database."""
        if not self.db_manager:
            QMessageBox.warning(
                self,
                "Save Failed",
                "Database not available. Settings cannot be saved."
            )
            return

        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()

            # Determine which preference key to use based on period
            period = self.budget_period.currentText()
            if period == "Weekly":
                budget_key = "spend_cap_weekly"
            elif period == "Monthly":
                budget_key = "spend_cap_monthly"
            else:
                # For Bi-weekly and Quarterly, we'll store as monthly equivalent
                budget_value = self.budget_amount.value()
                if period == "Bi-weekly":
                    # Store as monthly (bi-weekly * ~2.17)
                    budget_key = "spend_cap_monthly"
                    budget_value = budget_value * 2.17
                elif period == "Quarterly":
                    # Store as monthly (quarterly / 3)
                    budget_key = "spend_cap_monthly"
                    budget_value = budget_value / 3
                self.budget_amount.setValue(budget_value)

            # Save budget preference
            cursor.execute(
                """
                INSERT INTO preferences (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (budget_key, str(self.budget_amount.value()))
            )

            # Save alert threshold
            cursor.execute(
                """
                INSERT INTO preferences (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("budget_alert_threshold", str(self.alert_threshold.value()))
            )

            conn.commit()

            QMessageBox.information(
                self,
                "Settings Saved",
                f"Budget settings have been saved successfully.\n\n"
                f"{period} budget: ${self.budget_amount.value():.2f}"
            )

            self._update_spending_display()

        except Exception as e:
            self.logger.error(f"Failed to save budget settings: {e}")
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save settings:\n{str(e)}"
            )

    def _reset_period(self):
        """Show information about current spending period."""
        if not self.db_manager:
            return

        try:
            period = self.budget_period.currentText()

            # Calculate current spending based on period
            from datetime import datetime, timedelta

            if period == "Weekly":
                period_start = (datetime.now() - timedelta(days=datetime.now().weekday())).date()
                period_name = "this week"
            else:  # Monthly (and others default to monthly)
                period_start = datetime.now().replace(day=1).date()
                period_name = "this month"

            # Get spending for the period
            query = """
                SELECT SUM(total_cost) FROM orders
                WHERE created_at >= ?
                  AND status IN ('pending_approval', 'approved', 'placed', 'delivered')
            """
            result = self.db_manager.execute_query(query, (period_start.isoformat(),))
            spent = result[0][0] if result and result[0][0] else 0.0

            budget = self.budget_amount.value()
            remaining = budget - spent

            QMessageBox.information(
                self,
                "Current Period Summary",
                f"Period: {period_name.title()}\n"
                f"Budget: ${budget:.2f}\n"
                f"Spent: ${spent:.2f}\n"
                f"Remaining: ${remaining:.2f}\n\n"
                f"Note: Spending is calculated from orders.\n"
                f"Period starts: {period_start}"
            )

        except Exception as e:
            self.logger.error(f"Failed to show period info: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to calculate period info:\n{str(e)}"
            )

    def _update_spending_display(self):
        """Update the spending display with current data."""
        if not self.db_manager:
            return

        try:
            from datetime import datetime, timedelta

            budget = self.budget_amount.value()
            period = self.budget_period.currentText()

            # Calculate period start based on selection
            if period == "Weekly":
                period_start = (datetime.now() - timedelta(days=datetime.now().weekday())).date()
            elif period == "Bi-weekly":
                # Last 14 days
                period_start = (datetime.now() - timedelta(days=14)).date()
            elif period == "Quarterly":
                # Last 90 days
                period_start = (datetime.now() - timedelta(days=90)).date()
            else:  # Monthly
                period_start = datetime.now().replace(day=1).date()

            # Get actual spending from orders (matching CheckBudgetTool logic)
            query = """
                SELECT SUM(total_cost) FROM orders
                WHERE created_at >= ?
                  AND status IN ('pending_approval', 'approved', 'placed', 'delivered')
            """
            result = self.db_manager.execute_query(query, (period_start.isoformat(),))
            spent = result[0][0] if result and result[0][0] else 0.0

            remaining = budget - spent
            percentage = (spent / budget * 100) if budget > 0 else 0

            self.spent_label.setText(f"${spent:.2f}")
            self.remaining_label.setText(f"${remaining:.2f}")
            self.percentage_label.setText(f"{percentage:.1f}%")

            # Update colors based on threshold
            if percentage >= self.alert_threshold.value():
                self.percentage_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
                self.remaining_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
            elif percentage >= 50:
                self.percentage_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f39c12;")
                self.remaining_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f39c12;")
            else:
                self.percentage_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
                self.remaining_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")

        except Exception as e:
            self.logger.error(f"Failed to update spending display: {e}")


class SettingsPage(QWidget):
    """Main settings page with tabs for different settings categories."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = get_logger("settings_page")

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Settings")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(header)

        # Tabs for different settings
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 3px solid #3498db;
            }
            QTabBar::tab:hover {
                background: #d5dbdb;
            }
        """)

        # Budget Settings Tab
        budget_widget = BudgetSettingsWidget(self.db_manager)
        self.tabs.addTab(budget_widget, "Budget")

        # Smart Fridge Tab
        if self.db_manager:
            smart_fridge_widget = SmartFridgeConnectionWidget(self.db_manager)
            self.tabs.addTab(smart_fridge_widget, "Smart Fridge")
        else:
            placeholder = QLabel("Smart Fridge settings unavailable\n\nDatabase not initialized.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #95a5a6; font-size: 14px;")
            self.tabs.addTab(placeholder, "Smart Fridge")

        layout.addWidget(self.tabs)
