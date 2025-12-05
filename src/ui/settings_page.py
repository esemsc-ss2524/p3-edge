from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QFormLayout, 
    QLineEdit, QSpinBox, QGroupBox, QPushButton
)
from .smart_fridge_page import SmartFridgeConnectionWidget

class SettingsPage(QWidget):
    """Unified Settings Page."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E5E5EA; background: white; border-radius: 8px; }
            QTabBar::tab { background: #F2F2F7; padding: 10px 20px; border-radius: 4px; margin-right: 4px; }
            QTabBar::tab:selected { background: #007AFF; color: white; }
        """)
        
        # Tab 1: General (Budget)
        self.tabs.addTab(self._create_general_tab(), "General")
        
        # Tab 2: Smart Fridge (Moved here)
        self.fridge_widget = SmartFridgeConnectionWidget(db_manager)
        self.tabs.addTab(self.fridge_widget, "Smart Fridge")
        
        layout.addWidget(self.tabs)

    def _create_general_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Budget
        self.spin_budget = QSpinBox()
        self.spin_budget.setRange(0, 10000)
        self.spin_budget.setPrefix("$")
        
        # Load current
        prefs = self.db_manager.get_preferences()
        curr = prefs.get("spend_cap_weekly", 150)
        self.spin_budget.setValue(int(float(curr)))
        
        btn_save = QPushButton("Save Preferences")
        btn_save.setFixedWidth(150)
        btn_save.setStyleSheet("background-color: #007AFF; color: white; padding: 8px; border-radius: 6px;")
        btn_save.clicked.connect(self._save_general)
        
        layout.addRow("Weekly Grocery Budget:", self.spin_budget)
        layout.addRow("", btn_save)
        
        return widget

    def _save_general(self):
        val = self.spin_budget.value()
        self.db_manager.set_preference("spend_cap_weekly", val)