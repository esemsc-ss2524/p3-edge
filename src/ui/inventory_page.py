"""
Inventory management page with table view and CRUD operations.
"""

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.models import InventoryItem
from src.services import InventoryService
from src.ui.dialogs import InventoryItemDialog, ReceiptUploadDialog


class InventoryPage(QWidget):
    """Inventory management page."""

    def __init__(self, inventory_service: InventoryService, parent=None):
        """
        Initialize inventory page.

        Args:
            inventory_service: Inventory service instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.inventory_service = inventory_service
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Inventory Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        header_layout.addWidget(self.stats_label)

        layout.addLayout(header_layout)

        # Search and Actions
        action_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, category, or brand...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        action_layout.addWidget(self.search_input)

        action_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_table)
        action_layout.addWidget(refresh_btn)

        upload_receipt_btn = QPushButton("📷 Upload Receipt")
        upload_receipt_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        upload_receipt_btn.clicked.connect(self._on_upload_receipt)
        action_layout.addWidget(upload_receipt_btn)

        add_btn = QPushButton("+ Add Item")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1abc9c;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a085;
            }
        """)
        add_btn.clicked.connect(self._on_add_item)
        action_layout.addWidget(add_btn)

        layout.addLayout(action_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "Category",
            "Brand",
            "Quantity",
            "Unit",
            "Min",
            "Max",
            "Location",
            "Actions",
        ])

        # Configure table
        # Let content columns stretch, but fix actions column
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.table.verticalHeader().setDefaultSectionSize(42)   # rows tall enough
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)


        # Fix the Actions column width
        self.table.setColumnWidth(8, 160)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
        """)



        layout.addWidget(self.table)

        self._update_stats()

    def refresh_table(self, items: Optional[List[InventoryItem]] = None) -> None:
        """
        Refresh the table with current inventory.

        Args:
            items: Optional list of items to display (None loads all items)
        """
        if items is None or isinstance(items, bool):
            items = self.inventory_service.get_all_items()

        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            # Name
            self.table.setItem(row, 0, QTableWidgetItem(item.name))

            # Category
            self.table.setItem(row, 1, QTableWidgetItem(item.category or ""))

            # Brand
            self.table.setItem(row, 2, QTableWidgetItem(item.brand or ""))

            # Quantity (highlight low stock)
            qty_item = QTableWidgetItem(f"{item.quantity_current:.2f}")
            if item.is_low_stock():
                qty_item.setBackground(Qt.GlobalColor.yellow)
                qty_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 3, qty_item)

            # Unit
            self.table.setItem(row, 4, QTableWidgetItem(item.unit or ""))

            # Min
            self.table.setItem(row, 5, QTableWidgetItem(f"{item.quantity_min:.2f}"))

            # Max
            self.table.setItem(row, 6, QTableWidgetItem(f"{item.quantity_max:.2f}"))

            # Location
            self.table.setItem(row, 7, QTableWidgetItem(item.location or ""))

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 2, 5, 2)
            actions_layout.setSpacing(5)

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("padding: 4px 8px;")
            edit_btn.clicked.connect(lambda checked, i=item: self._on_edit_item(i))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 8px;
                    background-color: #e74c3c;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            delete_btn.clicked.connect(lambda checked, i=item: self._on_delete_item(i))
            actions_layout.addWidget(delete_btn)

            actions_layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetMinimumSize)
            edit_btn.setMinimumWidth(60)
            delete_btn.setMinimumWidth(70)

            self.table.setCellWidget(row, 8, actions_widget)

        self._update_stats()

    def _update_stats(self) -> None:
        """Update statistics label."""
        stats = self.inventory_service.get_stats()
        self.stats_label.setText(
            f"Total: {stats['total_items']} | "
            f"Low Stock: {stats['low_stock_items']} | "
            f"Expired: {stats['expired_items']}"
        )

    def _on_search(self, text: str) -> None:
        """Handle search text changes."""
        if text.strip():
            items = self.inventory_service.search_items(text.strip())
        else:
            items = self.inventory_service.get_all_items()
        self.refresh_table(items)

    def _on_upload_receipt(self) -> None:
        """Handle upload receipt button click."""
        dialog = ReceiptUploadDialog(self.inventory_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh table to show newly added items
            self.refresh_table()

    def _on_add_item(self) -> None:
        """Handle add item button click."""
        dialog = InventoryItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = dialog.get_item()
            if item:
                try:
                    self.inventory_service.create_item(item)
                    self.refresh_table()
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Item '{item.name}' added successfully!",
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to add item: {str(e)}",
                    )

    def _on_edit_item(self, item: InventoryItem) -> None:
        """Handle edit item button click."""
        dialog = InventoryItemDialog(self, item=item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_item = dialog.get_item()
            if updated_item:
                try:
                    self.inventory_service.update_item(updated_item)
                    self.refresh_table()
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Item '{updated_item.name}' updated successfully!",
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to update item: {str(e)}",
                    )

    def _on_delete_item(self, item: InventoryItem) -> None:
        """Handle delete item button click."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{item.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.inventory_service.delete_item(item.item_id)
                self.refresh_table()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Item '{item.name}' deleted successfully!",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete item: {str(e)}",
                )
