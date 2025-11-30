"""
Inventory entry dialog for manual item management.

Allows users to create and edit inventory items.
"""

from datetime import date, datetime
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.models import InventoryItem


class InventoryItemDialog(QDialog):
    """Dialog for creating/editing inventory items."""

    def __init__(self, parent=None, item: Optional[InventoryItem] = None):
        """
        Initialize inventory dialog.

        Args:
            parent: Parent widget
            item: Existing InventoryItem to edit (None for new item)
        """
        super().__init__(parent)
        self.item = item
        self.is_edit = item is not None

        self.setWindowTitle("Edit Item" if self.is_edit else "Add New Item")
        self.setMinimumWidth(500)

        self._setup_ui()
        if self.is_edit:
            self._populate_fields()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Edit Inventory Item" if self.is_edit else "Add New Inventory Item")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Form layout
        form = QFormLayout()
        form.setSpacing(10)

        # Basic Information
        form.addRow(self._create_section_label("Basic Information"))

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Organic Milk")
        form.addRow("Name*:", self.name_input)

        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems([
            "",
            "Dairy",
            "Produce",
            "Meat & Seafood",
            "Bakery",
            "Pantry",
            "Frozen",
            "Beverages",
            "Snacks",
            "Household",
            "Personal Care",
        ])
        form.addRow("Category:", self.category_input)

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("e.g., Organic Valley")
        form.addRow("Brand:", self.brand_input)

        # Quantity Information
        form.addRow(self._create_section_label("Quantity"))

        quantity_layout = QHBoxLayout()
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0, 10000)
        self.quantity_input.setDecimals(2)
        self.quantity_input.setSuffix(" units")
        quantity_layout.addWidget(self.quantity_input)

        self.unit_input = QComboBox()
        self.unit_input.setEditable(True)
        self.unit_input.addItems(["", "count", "oz", "lb", "gallon", "liter", "kg", "g"])
        quantity_layout.addWidget(QLabel("Unit:"))
        quantity_layout.addWidget(self.unit_input)
        form.addRow("Current Quantity*:", quantity_layout)

        self.min_quantity_input = QDoubleSpinBox()
        self.min_quantity_input.setRange(0, 10000)
        self.min_quantity_input.setDecimals(2)
        self.min_quantity_input.setValue(1.0)
        form.addRow("Minimum Quantity:", self.min_quantity_input)

        self.max_quantity_input = QDoubleSpinBox()
        self.max_quantity_input.setRange(0, 10000)
        self.max_quantity_input.setDecimals(2)
        self.max_quantity_input.setValue(10.0)
        form.addRow("Maximum Quantity:", self.max_quantity_input)

        # Storage Information
        form.addRow(self._create_section_label("Storage"))

        self.location_input = QComboBox()
        self.location_input.setEditable(True)
        self.location_input.addItems(["", "Fridge", "Freezer", "Pantry", "Cabinet"])
        form.addRow("Location:", self.location_input)

        self.perishable_input = QCheckBox("This item is perishable")
        form.addRow("", self.perishable_input)

        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(date.today())
        self.expiry_input.setEnabled(False)
        form.addRow("Expiry Date:", self.expiry_input)

        # Connect perishable checkbox to expiry date
        self.perishable_input.stateChanged.connect(self._on_perishable_changed)

        # Advanced
        form.addRow(self._create_section_label("Advanced"))

        self.consumption_rate_input = QDoubleSpinBox()
        self.consumption_rate_input.setRange(0, 100)
        self.consumption_rate_input.setDecimals(3)
        self.consumption_rate_input.setSuffix(" units/day")
        form.addRow("Consumption Rate:", self.consumption_rate_input)

        layout.addLayout(form)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1abc9c;
                color: white;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a085;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_section_label(self, text: str) -> QLabel:
        """Create a styled section label."""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                margin-top: 10px;
                padding-bottom: 5px;
                border-bottom: 2px solid #1abc9c;
            }
        """)
        return label

    def _populate_fields(self) -> None:
        """Populate form fields with existing item data."""
        if not self.item:
            return

        self.name_input.setText(self.item.name)
        if self.item.category:
            self.category_input.setCurrentText(self.item.category)
        if self.item.brand:
            self.brand_input.setText(self.item.brand)

        self.quantity_input.setValue(self.item.quantity_current)
        if self.item.unit:
            self.unit_input.setCurrentText(self.item.unit)

        self.min_quantity_input.setValue(self.item.quantity_min)
        self.max_quantity_input.setValue(self.item.quantity_max)

        if self.item.location:
            self.location_input.setCurrentText(self.item.location)

        self.perishable_input.setChecked(self.item.perishable)
        if self.item.expiry_date:
            self.expiry_input.setDate(self.item.expiry_date)

        if self.item.consumption_rate:
            self.consumption_rate_input.setValue(self.item.consumption_rate)

    def _on_perishable_changed(self, state: int) -> None:
        """Enable/disable expiry date based on perishable checkbox."""
        self.expiry_input.setEnabled(state == Qt.CheckState.Checked.value)

    def _on_save(self) -> None:
        """Validate and save the item."""
        # Validate required fields
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            self.name_input.setFocus()
            return

        if self.quantity_input.value() < 0:
            QMessageBox.warning(self, "Validation Error", "Quantity must be non-negative")
            self.quantity_input.setFocus()
            return

        if self.min_quantity_input.value() > self.max_quantity_input.value():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Minimum quantity cannot be greater than maximum quantity",
            )
            self.min_quantity_input.setFocus()
            return

        # Create item from form data
        try:
            if self.is_edit:
                # Update existing item
                self.item.name = self.name_input.text().strip()
                self.item.category = self.category_input.currentText() or None
                self.item.brand = self.brand_input.text().strip() or None
                self.item.quantity_current = self.quantity_input.value()
                self.item.unit = self.unit_input.currentText() or None
                self.item.quantity_min = self.min_quantity_input.value()
                self.item.quantity_max = self.max_quantity_input.value()
                self.item.location = self.location_input.currentText() or None
                self.item.perishable = self.perishable_input.isChecked()
                self.item.expiry_date = (
                    self.expiry_input.date().toPyDate() if self.perishable_input.isChecked() else None
                )
                self.item.consumption_rate = (
                    self.consumption_rate_input.value()
                    if self.consumption_rate_input.value() > 0
                    else None
                )
                self.item.last_updated = datetime.now()
            else:
                # Create new item
                self.item = InventoryItem(
                    name=self.name_input.text().strip(),
                    category=self.category_input.currentText() or None,
                    brand=self.brand_input.text().strip() or None,
                    quantity_current=self.quantity_input.value(),
                    unit=self.unit_input.currentText() or None,
                    quantity_min=self.min_quantity_input.value(),
                    quantity_max=self.max_quantity_input.value(),
                    location=self.location_input.currentText() or None,
                    perishable=self.perishable_input.isChecked(),
                    expiry_date=self.expiry_input.date().toPyDate()
                    if self.perishable_input.isChecked()
                    else None,
                    consumption_rate=self.consumption_rate_input.value()
                    if self.consumption_rate_input.value() > 0
                    else None,
                )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save item: {str(e)}")

    def get_item(self) -> Optional[InventoryItem]:
        """
        Get the created/edited item.

        Returns:
            InventoryItem or None if dialog was cancelled
        """
        return self.item
