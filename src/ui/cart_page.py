from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QPushButton, QMessageBox, QHeaderView, QInputDialog
)
from ..vendors import AmazonClient
from ..services.cart_service import CartService

class CartPage(QWidget):
    def __init__(self, db_manager, cart_service=None, parent=None):
        super().__init__(parent)
        self.cart_service = cart_service if cart_service else CartService(db_manager)
        self.amazon_client = AmazonClient()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header = QLabel("Shopping Cart")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1C1C1E;")
        layout.addWidget(header)
        
        # Product Search Section could go here or remain separate...
        # For brevity, focusing on the cart view
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Product", "Price", "Qty", "Subtotal", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Footer
        footer = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0.00")
        self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #007AFF;")
        
        btn_checkout = QPushButton("Create Order")
        btn_checkout.setStyleSheet("background-color: #007AFF; color: white; padding: 10px 20px; border-radius: 8px;")
        btn_checkout.clicked.connect(self._create_order)
        
        footer.addStretch()
        footer.addWidget(self.lbl_total)
        footer.addWidget(btn_checkout)
        layout.addLayout(footer)
        
        self._refresh_cart()

    def _refresh_cart(self):
        # Implementation to load active cart items...
        # (Re-use logic from previous CartPage but remove the Tabs widget wrapper)
        cart = self.cart_service.get_cart("amazon")
        if not cart:
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(cart.items))
        for r, item in enumerate(cart.items):
            self.table.setItem(r, 0, QTableWidgetItem(item.name))
            self.table.setItem(r, 1, QTableWidgetItem(f"${item.price:.2f}"))
            self.table.setItem(r, 2, QTableWidgetItem(str(item.quantity)))
            self.table.setItem(r, 3, QTableWidgetItem(f"${item.subtotal:.2f}"))
            # Add delete button logic here...
            
        self.lbl_total.setText(f"Total: ${cart.total:.2f}")

    def _create_order(self):
        # Logic to call cart_service.create_order
        pass