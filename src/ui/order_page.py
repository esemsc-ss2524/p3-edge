"""
Order history page for viewing and managing orders.

Provides interface for viewing order history, approving pending orders, and tracking order status.
"""

from typing import Optional
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QHeaderView,
)

from ..services.cart_service import CartService
from ..vendors import AmazonClient
from ..database.db_manager import DatabaseManager
from ..utils import get_logger


class OrderPage(QWidget):
    """Order history page."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, cart_service=None, parent=None):
        super().__init__(parent)
        self.logger = get_logger("order_page")
        self.db_manager = db_manager

        # Initialize services
        self.cart_service = cart_service if cart_service else (CartService(db_manager) if db_manager else None)
        self.amazon_client = AmazonClient()

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        header = QLabel("Order History")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(header)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_orders)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Info label
        info_label = QLabel("View and manage your orders. Approve pending orders to place them with vendors.")
        info_label.setStyleSheet("font-size: 14px; color: #7f8c8d; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(6)
        self.orders_table.setHorizontalHeaderLabels([
            "Order ID", "Vendor", "Total", "Status", "Date", "Action"
        ])
        self.orders_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                gridline-color: #ecf0f1;
                background: white;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        self.orders_table.horizontalHeader().setStretchLastSection(False)
        self.orders_table.setColumnWidth(0, 200)
        self.orders_table.setColumnWidth(1, 120)
        self.orders_table.setColumnWidth(2, 100)
        self.orders_table.setColumnWidth(3, 150)
        self.orders_table.setColumnWidth(4, 180)
        self.orders_table.setColumnWidth(5, 150)

        layout.addWidget(self.orders_table, stretch=1)

        # Load orders
        self._refresh_orders()

    def _refresh_orders(self):
        """Refresh orders display."""
        if not self.cart_service:
            self.orders_table.setRowCount(0)
            return

        orders = self.cart_service.get_order_history(limit=50)

        self.orders_table.setRowCount(len(orders))

        for row, order in enumerate(orders):
            # Order ID
            id_item = QTableWidgetItem(order.order_id[:16] + "...")
            id_item.setToolTip(order.order_id)  # Full ID on hover
            self.orders_table.setItem(row, 0, id_item)

            # Vendor
            vendor_item = QTableWidgetItem(order.vendor.title())
            self.orders_table.setItem(row, 1, vendor_item)

            # Total
            total_item = QTableWidgetItem(f"${order.total_cost:.2f}")
            self.orders_table.setItem(row, 2, total_item)

            # Status
            status_text = order.status.replace("_", " ").title()
            status_item = QTableWidgetItem(status_text)

            # Color code status
            if order.status == "pending_approval":
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            elif order.status == "approved":
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif order.status == "placed":
                status_item.setForeground(Qt.GlobalColor.darkBlue)
            elif order.status == "cancelled":
                status_item.setForeground(Qt.GlobalColor.red)

            self.orders_table.setItem(row, 3, status_item)

            # Date
            date_str = order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else "N/A"
            date_item = QTableWidgetItem(date_str)
            self.orders_table.setItem(row, 4, date_item)

            # Action button
            if order.status == "pending_approval":
                approve_btn = QPushButton("Approve & Place")
                approve_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        padding: 5px 10px;
                        border: none;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #229954;
                    }
                """)
                approve_btn.clicked.connect(lambda checked, oid=order.order_id: self._approve_order(oid))
                self.orders_table.setCellWidget(row, 5, approve_btn)
            else:
                status_label = QLabel(status_text)
                status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
                self.orders_table.setCellWidget(row, 5, status_label)

    def _approve_order(self, order_id: str):
        """Approve and place an order."""
        reply = QMessageBox.question(
            self,
            "Approve Order",
            "Approve this order and place it with Amazon?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Approve order
                self.cart_service.approve_order(order_id)

                # Place order
                result = self.cart_service.place_order(
                    order_id,
                    self.amazon_client,
                    shipping_address=None,  # Would be from user preferences
                    payment_method=None  # Would be from user preferences
                )

                QMessageBox.information(
                    self,
                    "Order Placed",
                    f"Order placed successfully!\n\nVendor Order ID: {result.get('order_id', 'N/A')}"
                )

                # Refresh orders
                self._refresh_orders()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to place order:\n{e}")

    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        # Refresh orders when page is shown
        self._refresh_orders()
