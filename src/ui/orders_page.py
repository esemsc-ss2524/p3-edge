from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from ..services.cart_service import CartService
from ..vendors import AmazonClient

class OrdersPage(QWidget):
    """Dedicated page for viewing order history and managing pending orders."""

    def __init__(self, db_manager, cart_service=None, parent=None):
        super().__init__(parent)
        self.cart_service = cart_service if cart_service else CartService(db_manager)
        # For MVP we simulate amazon client
        self.amazon_client = AmazonClient() 
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("Order History & Approvals")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1C1C1E; font-family: 'Segoe UI';")
        layout.addWidget(header)

        # Refresh
        btn_refresh = QPushButton("Refresh List")
        btn_refresh.setFixedWidth(120)
        btn_refresh.clicked.connect(self._refresh_orders)
        layout.addWidget(btn_refresh, alignment=Qt.AlignmentFlag.AlignRight)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Vendor", "Total", "Status", "Date", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                background-color: white;
                selection-background-color: #E5F1FB;
                selection-color: black;
            }
            QHeaderView::section {
                background-color: #F2F2F7;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)
        
        self._refresh_orders()

    def _refresh_orders(self):
        orders = self.cart_service.get_order_history(limit=50)
        self.table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            self.table.setItem(row, 0, QTableWidgetItem(order.order_id[:8]))
            self.table.setItem(row, 1, QTableWidgetItem(order.vendor.title()))
            self.table.setItem(row, 2, QTableWidgetItem(f"${order.total_cost:.2f}"))
            
            status_item = QTableWidgetItem(order.status.replace("_", " ").title())
            if "pending" in order.status.lower():
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            self.table.setItem(row, 3, status_item)
            
            date_str = order.created_at.strftime("%Y-%m-%d") if order.created_at else "-"
            self.table.setItem(row, 4, QTableWidgetItem(date_str))
            
            if order.status == "pending_approval":
                btn_approve = QPushButton("Approve")
                btn_approve.setStyleSheet("background-color: #34C759; color: white; border-radius: 4px;")
                btn_approve.clicked.connect(lambda _, oid=order.order_id: self._approve_order(oid))
                self.table.setCellWidget(row, 5, btn_approve)
            else:
                self.table.setItem(row, 5, QTableWidgetItem("-"))

    def _approve_order(self, order_id):
        reply = QMessageBox.question(self, "Confirm", "Approve this order?")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.cart_service.approve_order(order_id)
                # In MVP, we might simulate placement immediately
                self.cart_service.place_order(order_id, self.amazon_client)
                QMessageBox.information(self, "Success", "Order placed successfully.")
                self._refresh_orders()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))