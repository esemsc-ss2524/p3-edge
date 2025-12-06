"""
Settings page for application configuration.

Provides interface for managing Smart Fridge connection, budget settings, and other preferences.
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QDialogButtonBox,
    QProgressBar,
    QCheckBox,
    QSpinBox,
)

from src.database.db_manager import DatabaseManager
from src.ui.smart_fridge_page import SmartFridgeConnectionWidget
from src.services.memory_service import MemoryService
from src.config import get_config_manager
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
                value = prefs["spend_cap_weekly"]
                if value and value != 'null':
                    try:
                        self.budget_amount.setValue(float(value))
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid weekly budget value: {value}")
            elif period == "Monthly" and "spend_cap_monthly" in prefs:
                value = prefs["spend_cap_monthly"]
                if value and value != 'null':
                    try:
                        self.budget_amount.setValue(float(value))
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid monthly budget value: {value}")

            # Load alert threshold
            if "budget_alert_threshold" in prefs:
                value = prefs["budget_alert_threshold"]
                if value and value != 'null':
                    try:
                        self.alert_threshold.setValue(float(value))
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid alert threshold value: {value}")

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
            # Determine which preference key to use based on period
            period = self.budget_period.currentText()
            budget_value = self.budget_amount.value()

            if period == "Weekly":
                budget_key = "spend_cap_weekly"
            elif period == "Monthly":
                budget_key = "spend_cap_monthly"
            else:
                # For Bi-weekly and Quarterly, we'll store as monthly equivalent
                if period == "Bi-weekly":
                    # Store as monthly (bi-weekly * ~2.17)
                    budget_key = "spend_cap_monthly"
                    budget_value = budget_value * 2.17
                elif period == "Quarterly":
                    # Store as monthly (quarterly / 3)
                    budget_key = "spend_cap_monthly"
                    budget_value = budget_value / 3

            # FIX: Use 'with' statement to handle the context manager correctly
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Save budget preference
                cursor.execute(
                    """
                    INSERT INTO preferences (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (budget_key, str(budget_value))
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
                
                # Note: conn.commit() is handled automatically by the 
                # context manager in your DatabaseManager implementation, 
                # but explicit commit here is harmless if you want to be sure.

            QMessageBox.information(
                self,
                "Settings Saved",
                f"Budget settings have been saved successfully.\n\n"
                f"{period} budget: ${self.budget_amount.value():.2f}"
            )

            self._update_spending_display()

        except Exception as e:
            self.logger.error(f"Failed to save budget settings: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
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


class EditPreferenceDialog(QDialog):
    """Dialog for adding or editing a user preference."""

    def __init__(self, preference=None, parent=None):
        super().__init__(parent)
        self.preference = preference
        self.setWindowTitle("Edit Preference" if preference else "Add Preference")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "dietary",
            "allergy",
            "product_preference",
            "brand_preference",
            "general"
        ])
        form_layout.addRow("Category:", self.category_combo)

        # Preference Key
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g., milk_type")
        form_layout.addRow("Preference Key:", self.key_input)

        # Preference Value
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("e.g., oat milk")
        form_layout.addRow("Preference Value:", self.value_input)

        # Confidence
        self.confidence_input = QDoubleSpinBox()
        self.confidence_input.setMinimum(0.0)
        self.confidence_input.setMaximum(1.0)
        self.confidence_input.setSingleStep(0.1)
        self.confidence_input.setValue(0.5)
        self.confidence_input.setDecimals(2)
        form_layout.addRow("Confidence:", self.confidence_input)

        layout.addLayout(form_layout)

        # Load existing values if editing
        if self.preference:
            self.category_combo.setCurrentText(self.preference['category'])
            self.key_input.setText(self.preference['preference_key'])
            self.value_input.setText(self.preference['preference_value'])
            self.confidence_input.setValue(self.preference['confidence'])

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self):
        """Get the entered values."""
        return {
            'category': self.category_combo.currentText(),
            'preference_key': self.key_input.text().strip(),
            'preference_value': self.value_input.text().strip(),
            'confidence': self.confidence_input.value()
        }


class MemorySettingsWidget(QWidget):
    """Widget for managing long-term memory (user preferences)."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.memory_service = MemoryService(db_manager) if db_manager else None
        self.logger = get_logger("memory_settings")

        self._setup_ui()
        self._load_preferences()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Title
        title = QLabel("Long-Term Memory Management")
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
            "These are the user preferences learned by the autonomous agent. "
            "The agent uses this long-term memory to make personalized decisions."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        layout.addWidget(desc)

        # Memory Usage Stats
        stats_group = QGroupBox("Memory Usage")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        stats_layout = QFormLayout()

        self.word_count_label = QLabel("0 words")
        self.word_count_label.setStyleSheet("font-size: 14px; color: #3498db;")
        stats_layout.addRow("Current Usage:", self.word_count_label)

        self.usage_progress = QProgressBar()
        self.usage_progress.setMaximum(100)
        self.usage_progress.setValue(0)
        self.usage_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        stats_layout.addRow("Capacity:", self.usage_progress)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Preferences Table
        prefs_group = QGroupBox("User Preferences")
        prefs_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        prefs_layout = QVBoxLayout()

        self.preferences_table = QTableWidget()
        self.preferences_table.setColumnCount(5)
        self.preferences_table.setHorizontalHeaderLabels([
            "Category", "Key", "Value", "Confidence", "Mentions"
        ])
        self.preferences_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.preferences_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.preferences_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.preferences_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                gridline-color: #ecf0f1;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        prefs_layout.addWidget(self.preferences_table)

        prefs_group.setLayout(prefs_layout)
        layout.addWidget(prefs_group)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        add_btn = QPushButton("Add Preference")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        add_btn.clicked.connect(self._add_preference)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.setStyleSheet("""
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
        edit_btn.clicked.connect(self._edit_preference)
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("""
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
        delete_btn.clicked.connect(self._delete_preference)
        button_layout.addWidget(delete_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        refresh_btn.clicked.connect(self._load_preferences)
        button_layout.addWidget(refresh_btn)

        layout.addLayout(button_layout)

    def _load_preferences(self):
        """Load preferences from database and update UI."""
        if not self.memory_service:
            return

        try:
            # Get all preferences
            preferences = self.memory_service.get_preferences(min_confidence=0.0)

            # Update memory usage stats
            word_count = self.memory_service.count_preference_words()
            usage_pct = self.memory_service.get_preference_usage_percentage()

            self.word_count_label.setText(
                f"{word_count} / {self.memory_service.max_preference_words} words"
            )
            self.usage_progress.setValue(int(usage_pct))

            # Update progress bar color based on usage
            if usage_pct >= 90:
                self.usage_progress.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #bdc3c7;
                        border-radius: 5px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #e74c3c;
                    }
                """)
            elif usage_pct >= 70:
                self.usage_progress.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #bdc3c7;
                        border-radius: 5px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #f39c12;
                    }
                """)
            else:
                self.usage_progress.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #bdc3c7;
                        border-radius: 5px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #3498db;
                    }
                """)

            # Update table
            self.preferences_table.setRowCount(len(preferences))

            for row, pref in enumerate(preferences):
                # Category
                cat_item = QTableWidgetItem(pref['category'])
                self.preferences_table.setItem(row, 0, cat_item)

                # Key
                key_item = QTableWidgetItem(pref['preference_key'])
                self.preferences_table.setItem(row, 1, key_item)

                # Value
                value_item = QTableWidgetItem(str(pref['preference_value']))
                self.preferences_table.setItem(row, 2, value_item)

                # Confidence
                confidence_item = QTableWidgetItem(f"{pref['confidence']:.0%}")
                self.preferences_table.setItem(row, 3, confidence_item)

                # Mentions
                mention_item = QTableWidgetItem(str(pref['mention_count']))
                self.preferences_table.setItem(row, 4, mention_item)

                # Store preference ID in first column
                cat_item.setData(Qt.ItemDataRole.UserRole, pref['preference_id'])

            self.logger.info(f"Loaded {len(preferences)} preferences")

        except Exception as e:
            self.logger.error(f"Failed to load preferences: {e}")
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Failed to load preferences:\n{str(e)}"
            )

    def _add_preference(self):
        """Add a new preference."""
        if not self.memory_service:
            QMessageBox.warning(self, "Not Available", "Memory service not available")
            return

        dialog = EditPreferenceDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()

            if not values['preference_key'] or not values['preference_value']:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Please provide both key and value"
                )
                return

            try:
                self.memory_service.learn_preference(
                    category=values['category'],
                    preference_key=values['preference_key'],
                    preference_value=values['preference_value'],
                    source='manual'
                )

                # Update confidence if different from default
                if values['confidence'] != 0.5:
                    # Get the just-created preference
                    prefs = self.memory_service.get_preferences(min_confidence=0.0)
                    for pref in prefs:
                        if (pref['preference_key'] == values['preference_key'] and
                            pref['preference_value'] == values['preference_value']):
                            self.memory_service.update_preference(
                                pref['preference_id'],
                                confidence=values['confidence']
                            )
                            break

                QMessageBox.information(
                    self,
                    "Success",
                    "Preference added successfully"
                )
                self._load_preferences()

            except Exception as e:
                self.logger.error(f"Failed to add preference: {e}")
                QMessageBox.critical(
                    self,
                    "Add Failed",
                    f"Failed to add preference:\n{str(e)}"
                )

    def _edit_preference(self):
        """Edit selected preference."""
        if not self.memory_service:
            return

        selected = self.preferences_table.selectedItems()
        if not selected:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a preference to edit"
            )
            return

        row = selected[0].row()
        pref_id = self.preferences_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        # Get full preference data
        all_prefs = self.memory_service.get_preferences(min_confidence=0.0)
        preference = next((p for p in all_prefs if p['preference_id'] == pref_id), None)

        if not preference:
            QMessageBox.warning(self, "Error", "Preference not found")
            return

        dialog = EditPreferenceDialog(preference=preference, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()

            if not values['preference_key'] or not values['preference_value']:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Please provide both key and value"
                )
                return

            try:
                self.memory_service.update_preference(
                    pref_id,
                    preference_key=values['preference_key'],
                    preference_value=values['preference_value'],
                    category=values['category'],
                    confidence=values['confidence']
                )

                QMessageBox.information(
                    self,
                    "Success",
                    "Preference updated successfully"
                )
                self._load_preferences()

            except Exception as e:
                self.logger.error(f"Failed to update preference: {e}")
                QMessageBox.critical(
                    self,
                    "Update Failed",
                    f"Failed to update preference:\n{str(e)}"
                )

    def _delete_preference(self):
        """Delete selected preference."""
        if not self.memory_service:
            return

        selected = self.preferences_table.selectedItems()
        if not selected:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a preference to delete"
            )
            return

        row = selected[0].row()
        pref_id = self.preferences_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        pref_key = self.preferences_table.item(row, 1).text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{pref_key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.memory_service.delete_preference(pref_id)
                QMessageBox.information(
                    self,
                    "Success",
                    "Preference deleted successfully"
                )
                self._load_preferences()

            except Exception as e:
                self.logger.error(f"Failed to delete preference: {e}")
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    f"Failed to delete preference:\n{str(e)}"
                )


class AutonomousSettingsWidget(QWidget):
    """Widget for managing autonomous agent settings."""

    def __init__(self, autonomous_agent=None, parent=None):
        super().__init__(parent)
        self.autonomous_agent = autonomous_agent
        self.config = get_config_manager()
        self.logger = get_logger("autonomous_settings")

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Title
        title = QLabel("Autonomous Agent Configuration")
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
            "The autonomous agent runs on a scheduled cycle to proactively manage "
            "inventory and shopping. Configure when and how often it runs."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        layout.addWidget(desc)

        # Agent Settings Group
        agent_group = QGroupBox("Agent Configuration")
        agent_group.setStyleSheet("""
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
        agent_layout = QFormLayout()
        agent_layout.setSpacing(15)

        # Enable/Disable Checkbox
        self.enabled_checkbox = QCheckBox("Enable Autonomous Agent")
        self.enabled_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        agent_layout.addRow("Status:", self.enabled_checkbox)

        # Cycle Interval Spinbox
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(1440)  # Max 24 hours
        self.interval_spinbox.setValue(60)
        self.interval_spinbox.setSuffix(" minutes")
        self.interval_spinbox.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
            }
            QSpinBox:focus {
                border: 2px solid #3498db;
            }
        """)
        agent_layout.addRow("Cycle Interval:", self.interval_spinbox)

        # Info label
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #7f8c8d; font-size: 12px; font-style: italic;")
        agent_layout.addRow("", self.info_label)

        agent_group.setLayout(agent_layout)
        layout.addWidget(agent_group)

        # Status Group
        status_group = QGroupBox("Current Status")
        status_group.setStyleSheet("""
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
        status_layout = QFormLayout()
        status_layout.setSpacing(10)

        self.status_label = QLabel("Disabled")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c;")
        status_layout.addRow("Agent Status:", self.status_label)

        self.last_cycle_label = QLabel("Never")
        self.last_cycle_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        status_layout.addRow("Last Cycle:", self.last_cycle_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

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
        """Load autonomous agent settings from config."""
        try:
            # Load settings from config
            enabled = self.config.get("agent.enabled", True)
            interval = self.config.get("agent.cycle_interval_minutes", 60)

            # Update UI
            self.enabled_checkbox.setChecked(enabled)
            self.interval_spinbox.setValue(interval)

            # Update status display
            self._update_status_display()
            self._update_info_label()

        except Exception as e:
            self.logger.error(f"Failed to load autonomous settings: {e}")

    def _save_settings(self):
        """Save autonomous agent settings to config file."""
        try:
            enabled = self.enabled_checkbox.isChecked()
            interval = self.interval_spinbox.value()

            # Save to config
            self.config.set("agent.enabled", enabled, save=False)
            self.config.set("agent.cycle_interval_minutes", interval, save=True)

            # Apply settings to autonomous agent
            if self.autonomous_agent:
                # Update interval
                self.autonomous_agent.cycle_interval_minutes = interval

                # Update timer if already running
                if self.autonomous_agent.timer.isActive():
                    interval_ms = interval * 60 * 1000
                    self.autonomous_agent.timer.setInterval(interval_ms)

                # Handle enable/disable
                if enabled and not self.autonomous_agent.enabled:
                    # Enabling - start agent after 5 seconds
                    self.autonomous_agent.set_enabled(True)
                    self.logger.info("Autonomous agent enabled")
                elif not enabled and self.autonomous_agent.enabled:
                    # Disabling - stop agent (will finish current cycle if running)
                    self.autonomous_agent.set_enabled(False)
                    self.logger.info("Autonomous agent disabled")

            self._update_status_display()

            QMessageBox.information(
                self,
                "Settings Saved",
                f"Autonomous agent settings have been saved successfully.\n\n"
                f"Enabled: {'Yes' if enabled else 'No'}\n"
                f"Cycle Interval: {interval} minutes"
            )

        except Exception as e:
            self.logger.error(f"Failed to save autonomous settings: {e}")
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save settings:\n{str(e)}"
            )

    def _on_enabled_changed(self, state):
        """Handle enable/disable checkbox state change."""
        self._update_info_label()

    def _update_info_label(self):
        """Update the info label based on current settings."""
        enabled = self.enabled_checkbox.isChecked()
        interval = self.interval_spinbox.value()

        if enabled:
            self.info_label.setText(
                f"Agent will run every {interval} minutes. "
                f"On startup, it will start after a 1 minute delay. "
                f"When enabled here, it will start after 5 seconds."
            )
        else:
            self.info_label.setText(
                "Agent is disabled and will not run automatically. "
                "You can still run cycles manually from the Activity Feed."
            )

    def _update_status_display(self):
        """Update the status display."""
        if self.autonomous_agent:
            if self.autonomous_agent.enabled:
                self.status_label.setText("Enabled & Running")
                self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #27ae60;")
            else:
                self.status_label.setText("Disabled")
                self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c;")

            # Update last cycle time
            if self.autonomous_agent.last_cycle_time:
                from datetime import datetime
                time_diff = datetime.now() - self.autonomous_agent.last_cycle_time
                if time_diff.total_seconds() < 60:
                    self.last_cycle_label.setText("Just now")
                elif time_diff.total_seconds() < 3600:
                    minutes = int(time_diff.total_seconds() / 60)
                    self.last_cycle_label.setText(f"{minutes} minute{'s' if minutes != 1 else ''} ago")
                else:
                    hours = int(time_diff.total_seconds() / 3600)
                    self.last_cycle_label.setText(f"{hours} hour{'s' if hours != 1 else ''} ago")
            else:
                self.last_cycle_label.setText("Never")
        else:
            self.status_label.setText("Not Available")
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #95a5a6;")


class SettingsPage(QWidget):
    """Main settings page with tabs for different settings categories."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, autonomous_agent=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.autonomous_agent = autonomous_agent
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

        # Autonomous Agent Tab
        autonomous_widget = AutonomousSettingsWidget(self.autonomous_agent)
        self.tabs.addTab(autonomous_widget, "Autonomous")

        # Budget Settings Tab
        budget_widget = BudgetSettingsWidget(self.db_manager)
        self.tabs.addTab(budget_widget, "Budget")

        # Memory Settings Tab
        if self.db_manager:
            memory_widget = MemorySettingsWidget(self.db_manager)
            self.tabs.addTab(memory_widget, "Memory")
        else:
            placeholder = QLabel("Memory settings unavailable\n\nDatabase not initialized.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #95a5a6; font-size: 14px;")
            self.tabs.addTab(placeholder, "Memory")

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
