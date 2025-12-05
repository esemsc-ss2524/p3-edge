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

        reset_btn = QPushButton("Reset Period")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        reset_btn.clicked.connect(self._reset_period)
        button_layout.addWidget(reset_btn)

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

    def _load_settings(self):
        """Load budget settings from database."""
        if not self.db_manager:
            return

        try:
            # Load settings from database
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'budget_%'"
            )
            settings = dict(cursor.fetchall())

            if "budget_amount" in settings:
                self.budget_amount.setValue(float(settings["budget_amount"]))
            if "budget_period" in settings:
                self.budget_period.setCurrentText(settings["budget_period"])
            if "budget_alert_threshold" in settings:
                self.alert_threshold.setValue(float(settings["budget_alert_threshold"]))

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

            # Save settings
            settings = {
                "budget_amount": str(self.budget_amount.value()),
                "budget_period": self.budget_period.currentText(),
                "budget_alert_threshold": str(self.alert_threshold.value()),
            }

            for key, value in settings.items():
                cursor.execute(
                    """
                    INSERT INTO settings (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, value)
                )

            conn.commit()

            QMessageBox.information(
                self,
                "Settings Saved",
                "Budget settings have been saved successfully."
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
        """Reset the current spending period."""
        reply = QMessageBox.question(
            self,
            "Reset Period",
            "Are you sure you want to reset the current spending period?\n\n"
            "This will clear the spending tracking for this period.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if not self.db_manager:
                return

            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()

                # Reset spending tracking
                cursor.execute(
                    """
                    DELETE FROM settings WHERE key LIKE 'budget_spent_%'
                    """
                )
                conn.commit()

                QMessageBox.information(
                    self,
                    "Period Reset",
                    "Spending period has been reset."
                )

                self._update_spending_display()

            except Exception as e:
                self.logger.error(f"Failed to reset period: {e}")
                QMessageBox.critical(
                    self,
                    "Reset Failed",
                    f"Failed to reset period:\n{str(e)}"
                )

    def _update_spending_display(self):
        """Update the spending display with current data."""
        if not self.db_manager:
            return

        try:
            # Get current spending (this would typically come from orders)
            # For now, we'll show placeholder values
            budget = self.budget_amount.value()
            spent = 0.0  # Would calculate from orders in the current period
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
        self.tabs.addTab(budget_widget, "💰 Budget")

        # Smart Fridge Tab
        if self.db_manager:
            smart_fridge_widget = SmartFridgeConnectionWidget(self.db_manager)
            self.tabs.addTab(smart_fridge_widget, "🧊 Smart Fridge")
        else:
            placeholder = QLabel("Smart Fridge settings unavailable\n\nDatabase not initialized.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #95a5a6; font-size: 14px;")
            self.tabs.addTab(placeholder, "🧊 Smart Fridge")

        layout.addWidget(self.tabs)
