"""
Receipt upload and processing dialog.

Allows users to upload receipt images and review extracted items.
"""

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.ingestion import ReceiptItem, process_receipt_image
from src.models import InventoryItem
from src.services import InventoryService


class ReceiptUploadDialog(QDialog):
    """Dialog for uploading and processing receipts."""

    def __init__(self, inventory_service: InventoryService, parent=None):
        """
        Initialize receipt upload dialog.

        Args:
            inventory_service: Inventory service instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.inventory_service = inventory_service
        self.extracted_items: List[ReceiptItem] = []
        self.receipt_path: Optional[str] = None

        self.setWindowTitle("Upload Receipt")
        self.setMinimumSize(800, 600)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Upload and Process Receipt")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # File selection
        file_layout = QHBoxLayout()

        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("color: #7f8c8d;")
        file_layout.addWidget(self.file_path_label)

        file_layout.addStretch()

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(browse_btn)

        upload_btn = QPushButton("Process Receipt")
        upload_btn.setStyleSheet("""
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
        upload_btn.clicked.connect(self._on_process)
        file_layout.addWidget(upload_btn)

        layout.addLayout(file_layout)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("margin: 10px 0; font-style: italic;")
        layout.addWidget(self.status_label)

        # Items table
        table_label = QLabel("Extracted Items:")
        table_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        layout.addWidget(table_label)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "Include",
            "Name",
            "Quantity",
            "Unit",
            "Price",
            "Confidence",
        ])
        self.items_table.horizontalHeader().setStretchLastSection(False)
        self.items_table.setColumnWidth(0, 70)
        self.items_table.setColumnWidth(1, 250)
        self.items_table.setColumnWidth(2, 80)
        self.items_table.setColumnWidth(3, 80)
        self.items_table.setColumnWidth(4, 80)
        self.items_table.setColumnWidth(5, 90)

        layout.addWidget(self.items_table)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.add_btn = QPushButton("Add to Inventory")
        self.add_btn.setEnabled(False)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1abc9c;
                color: white;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a085;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.add_btn.clicked.connect(self._on_add_to_inventory)
        button_layout.addWidget(self.add_btn)

        layout.addLayout(button_layout)

    def _on_browse(self) -> None:
        """Handle browse button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Receipt Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)",
        )

        if file_path:
            self.receipt_path = file_path
            self.file_path_label.setText(Path(file_path).name)
            self.status_label.setText("")
            self.extracted_items = []
            self.items_table.setRowCount(0)
            self.add_btn.setEnabled(False)

    def _on_process(self) -> None:
        """Handle process receipt button click."""
        if not self.receipt_path:
            QMessageBox.warning(self, "No File", "Please select a receipt image first.")
            return

        try:
            self.status_label.setText("Processing receipt... This may take a few seconds.")
            self.status_label.setStyleSheet("margin: 10px 0; font-style: italic; color: #f39c12;")

            # Process in UI thread (could be moved to background thread for better UX)
            self.extracted_items = process_receipt_image(self.receipt_path)

            if not self.extracted_items:
                self.status_label.setText("No items found in receipt. Try a clearer image.")
                self.status_label.setStyleSheet("margin: 10px 0; font-style: italic; color: #e74c3c;")
                return

            # Populate table
            self._populate_table()

            self.status_label.setText(
                f"✓ Found {len(self.extracted_items)} items. Review and edit as needed."
            )
            self.status_label.setStyleSheet("margin: 10px 0; font-style: italic; color: #27ae60;")
            self.add_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Failed to process receipt: {str(e)}")
            self.status_label.setText("Processing failed.")
            self.status_label.setStyleSheet("margin: 10px 0; font-style: italic; color: #e74c3c;")

    def _populate_table(self) -> None:
        """Populate table with extracted items."""
        self.items_table.setRowCount(len(self.extracted_items))

        for row, item in enumerate(self.extracted_items):
            # Include checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(item.confidence > 0.6)  # Auto-check high confidence items
            checkbox_widget = QTableWidgetItem()
            checkbox_widget.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_widget.setCheckState(
                Qt.CheckState.Checked if item.confidence > 0.6 else Qt.CheckState.Unchecked
            )
            self.items_table.setItem(row, 0, checkbox_widget)

            # Name (editable)
            name_item = QTableWidgetItem(item.name)
            self.items_table.setItem(row, 1, name_item)

            # Quantity (editable)
            qty_item = QTableWidgetItem(str(item.quantity))
            self.items_table.setItem(row, 2, qty_item)

            # Unit (editable)
            unit_item = QTableWidgetItem(item.unit or "")
            self.items_table.setItem(row, 3, unit_item)

            # Price
            price_item = QTableWidgetItem(f"${item.price:.2f}" if item.price else "")
            price_item.setFlags(price_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, 4, price_item)

            # Confidence
            conf_item = QTableWidgetItem(f"{item.confidence * 100:.0f}%")
            conf_item.setFlags(conf_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Color code by confidence
            if item.confidence >= 0.8:
                conf_item.setBackground(Qt.GlobalColor.green)
            elif item.confidence >= 0.6:
                conf_item.setBackground(Qt.GlobalColor.yellow)
            else:
                conf_item.setBackground(Qt.GlobalColor.red)

            self.items_table.setItem(row, 5, conf_item)

    def _on_add_to_inventory(self) -> None:
        """Handle add to inventory button click."""
        try:
            added_count = 0

            for row in range(self.items_table.rowCount()):
                # Check if item is selected
                if self.items_table.item(row, 0).checkState() != Qt.CheckState.Checked:
                    continue

                # Get item data from table
                name = self.items_table.item(row, 1).text().strip()
                qty_text = self.items_table.item(row, 2).text().strip()
                unit = self.items_table.item(row, 3).text().strip() or None

                if not name:
                    continue

                try:
                    qty = float(qty_text)
                except ValueError:
                    qty = 1.0

                # Create inventory item
                inventory_item = InventoryItem(
                    name=name,
                    quantity_current=qty,
                    unit=unit,
                    category=None,  # Could be inferred or categorized
                    location="Unknown",  # User can edit later
                )

                # Add to database
                self.inventory_service.create_item(inventory_item)
                added_count += 1

            if added_count > 0:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Added {added_count} items to inventory!",
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "No Items",
                    "No items were selected to add.",
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to add items: {str(e)}",
            )
