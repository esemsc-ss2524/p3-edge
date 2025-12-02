"""
Shopping cart page for product search, cart management, and order approval.

Provides interface for searching products, adding to cart, reviewing, and placing orders.
"""

from typing import Optional, List
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QMessageBox,
    QTabWidget,
    QGroupBox,
    QScrollArea,
    QFrame,
    QHeaderView,
    QInputDialog
)

from ..vendors import AmazonClient, VendorProduct, ShoppingCart
from ..services.cart_service import CartService
from ..database.db_manager import DatabaseManager
from ..utils import get_logger


class ProductSearchWorker(QThread):
    """Worker thread for product search."""

    search_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, vendor_client, query: str):
        super().__init__()
        self.vendor_client = vendor_client
        self.query = query

    def run(self):
        """Run product search."""
        try:
            result = self.vendor_client.search_products(self.query, max_results=20)
            self.search_complete.emit(result.products)
        except Exception as e:
            self.error_occurred.emit(str(e))


class CartPage(QWidget):
    """Shopping cart page."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self.logger = get_logger("cart_page")
        self.db_manager = db_manager

        # Initialize services
        self.cart_service = CartService(db_manager) if db_manager else None
        self.amazon_client = AmazonClient()

        # Current search results
        self.search_results: List[VendorProduct] = []
        self.search_worker: Optional[ProductSearchWorker] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Shopping Cart")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(header)

        # Tabs for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #3498db;
            }
        """)

        # Product Search Tab
        search_tab = self._create_search_tab()
        self.tabs.addTab(search_tab, "🔍 Search Products")

        # Cart Tab
        cart_tab = self._create_cart_tab()
        self.tabs.addTab(cart_tab, "🛒 My Cart")

        # Orders Tab
        orders_tab = self._create_orders_tab()
        self.tabs.addTab(orders_tab, "📦 Orders")

        layout.addWidget(self.tabs)

    def _create_search_tab(self) -> QWidget:
        """Create product search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)

        # Search bar
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for products (e.g., 'milk', 'bread', 'eggs')...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.search_input.returnPressed.connect(self._search_products)
        search_layout.addWidget(self.search_input, stretch=1)

        self.search_btn = QPushButton("Search")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 25px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.search_btn.clicked.connect(self._search_products)
        search_layout.addWidget(self.search_btn)

        layout.addLayout(search_layout)

        # Status label
        self.search_status = QLabel("")
        self.search_status.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 5px;")
        layout.addWidget(self.search_status)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Product", "Brand", "Price", "Rating", "Prime", "Stock", "Action"
        ])
        self.results_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                gridline-color: #ecf0f1;
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
        self.results_table.horizontalHeader().setStretchLastSection(False)
        self.results_table.setColumnWidth(0, 250)
        self.results_table.setColumnWidth(1, 120)
        self.results_table.setColumnWidth(2, 80)
        self.results_table.setColumnWidth(3, 80)
        self.results_table.setColumnWidth(4, 60)
        self.results_table.setColumnWidth(5, 80)
        self.results_table.setColumnWidth(6, 120)
        self.results_table.verticalHeader().setDefaultSectionSize(42)   # rows tall enough
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)


        layout.addWidget(self.results_table, stretch=1)

        return widget

    def _create_cart_tab(self) -> QWidget:
        """Create shopping cart tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)

        # Cart info
        info_label = QLabel("Your shopping cart items")
        info_label.setStyleSheet("font-size: 14px; color: #7f8c8d; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Cart table
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels([
            "Product", "Price", "Quantity", "Subtotal", "Vendor", "Action"
        ])
        self.cart_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                gridline-color: #ecf0f1;
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
        self.cart_table.horizontalHeader().setStretchLastSection(False)
        self.cart_table.setColumnWidth(0, 250)
        self.cart_table.setColumnWidth(1, 100)
        self.cart_table.setColumnWidth(2, 100)
        self.cart_table.setColumnWidth(3, 100)
        self.cart_table.setColumnWidth(4, 100)
        self.cart_table.setColumnWidth(5, 120)

        layout.addWidget(self.cart_table, stretch=1)

        # Cart summary
        summary_layout = QHBoxLayout()
        summary_layout.addStretch()

        # Total label
        self.cart_total_label = QLabel("Total: $0.00")
        self.cart_total_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #27ae60;
                padding: 10px;
                background-color: #d5f4e6;
                border-radius: 5px;
            }
        """)
        summary_layout.addWidget(self.cart_total_label)

        layout.addLayout(summary_layout)

        # Action buttons
        action_layout = QHBoxLayout()

        self.clear_cart_btn = QPushButton("Clear Cart")
        self.clear_cart_btn.setStyleSheet("""
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
        self.clear_cart_btn.clicked.connect(self._clear_cart)
        action_layout.addWidget(self.clear_cart_btn)

        action_layout.addStretch()

        self.checkout_btn = QPushButton("Proceed to Checkout")
        self.checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 25px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.checkout_btn.clicked.connect(self._checkout)
        action_layout.addWidget(self.checkout_btn)

        layout.addLayout(action_layout)

        return widget

    def _create_orders_tab(self) -> QWidget:
        """Create orders tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)

        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_orders)
        refresh_layout.addWidget(refresh_btn)

        layout.addLayout(refresh_layout)

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
        self.orders_table.setColumnWidth(0, 150)
        self.orders_table.setColumnWidth(1, 100)
        self.orders_table.setColumnWidth(2, 100)
        self.orders_table.setColumnWidth(3, 150)
        self.orders_table.setColumnWidth(4, 150)
        self.orders_table.setColumnWidth(5, 120)

        layout.addWidget(self.orders_table, stretch=1)

        # Load orders
        self._refresh_orders()

        return widget

    def _search_products(self):
        """Search for products."""
        query = self.search_input.text().strip()

        if not query:
            QMessageBox.warning(self, "Search", "Please enter a search term")
            return

        self.search_btn.setEnabled(False)
        self.search_status.setText("🔍 Searching...")

        # Start search in background
        self.search_worker = ProductSearchWorker(self.amazon_client, query)
        self.search_worker.search_complete.connect(self._on_search_complete)
        self.search_worker.error_occurred.connect(self._on_search_error)
        self.search_worker.start()

    def _on_search_complete(self, products: List[VendorProduct]):
        """Handle search completion."""
        self.search_results = products
        self.search_btn.setEnabled(True)
        self.search_status.setText(f"✅ Found {len(products)} products")

        # Update table
        self.results_table.setRowCount(len(products))

        for row, product in enumerate(products):
            # Product name
            name_item = QTableWidgetItem(product.name)
            self.results_table.setItem(row, 0, name_item)

            # Brand
            brand_item = QTableWidgetItem(product.brand or "")
            self.results_table.setItem(row, 1, brand_item)

            # Price
            price_item = QTableWidgetItem(f"${product.price:.2f}")
            self.results_table.setItem(row, 2, price_item)

            # Rating
            rating_text = f"⭐ {product.rating:.1f}" if product.rating else "N/A"
            rating_item = QTableWidgetItem(rating_text)
            self.results_table.setItem(row, 3, rating_item)

            # Prime
            prime_item = QTableWidgetItem("✓" if product.prime_eligible else "")
            self.results_table.setItem(row, 4, prime_item)

            # Stock
            stock_item = QTableWidgetItem("In Stock" if product.in_stock else "Out")
            stock_item.setForeground(Qt.GlobalColor.darkGreen if product.in_stock else Qt.GlobalColor.red)
            self.results_table.setItem(row, 5, stock_item)

            # Add to cart button
            add_btn = QPushButton("Add to Cart")
            add_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 5px 10px;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            add_btn.clicked.connect(lambda checked, p=product: self._add_to_cart(p))
            self.results_table.setCellWidget(row, 6, add_btn)

    def _on_search_error(self, error: str):
        """Handle search error."""
        self.search_btn.setEnabled(True)
        self.search_status.setText(f"❌ Error: {error}")
        QMessageBox.critical(self, "Search Error", f"Failed to search products:\n{error}")

    def _add_to_cart(self, product: VendorProduct):
        """Add product to cart."""
        if not self.cart_service:
            QMessageBox.warning(self, "Cart", "Cart service not available")
            return

        # Ask for quantity
        quantity, ok = QInputDialog.getDouble(
            self,
            "Add to Cart",
            f"Enter quantity for {product.name}:",
            1.0, 0.1, 100.0, 1
        )

        if ok and quantity > 0:
            try:
                self.cart_service.add_to_cart(
                    vendor="amazon",
                    vendor_client=self.amazon_client,
                    product=product,
                    quantity=quantity
                )

                QMessageBox.information(
                    self,
                    "Success",
                    f"Added {quantity} x {product.name} to cart"
                )

                # Refresh cart display
                self._refresh_cart()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add to cart:\n{e}")

    def _refresh_cart(self):
        """Refresh cart display."""
        if not self.cart_service:
            return

        cart = self.cart_service.get_cart("amazon")

        if not cart or not cart.items:
            self.cart_table.setRowCount(0)
            self.cart_total_label.setText("Total: $0.00")
            self.checkout_btn.setEnabled(False)
            return

        # Update table
        self.cart_table.setRowCount(len(cart.items))

        for row, item in enumerate(cart.items):
            # Product name
            name_item = QTableWidgetItem(item.name)
            self.cart_table.setItem(row, 0, name_item)

            # Price
            price_item = QTableWidgetItem(f"${item.price:.2f}")
            self.cart_table.setItem(row, 1, price_item)

            # Quantity
            qty_item = QTableWidgetItem(f"{item.quantity}")
            self.cart_table.setItem(row, 2, qty_item)

            # Subtotal
            subtotal_item = QTableWidgetItem(f"${item.subtotal:.2f}")
            self.cart_table.setItem(row, 3, subtotal_item)

            # Vendor
            vendor_item = QTableWidgetItem(item.vendor.title())
            self.cart_table.setItem(row, 4, vendor_item)

            # Remove button
            remove_btn = QPushButton("Remove")
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    padding: 5px 10px;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            remove_btn.clicked.connect(lambda checked, pid=item.product_id: self._remove_from_cart(pid))
            self.cart_table.setCellWidget(row, 5, remove_btn)

        # Update total
        self.cart_total_label.setText(f"Total: ${cart.total:.2f}")
        self.checkout_btn.setEnabled(True)

    def _remove_from_cart(self, product_id: str):
        """Remove item from cart."""
        if not self.cart_service:
            return

        reply = QMessageBox.question(
            self,
            "Remove Item",
            "Remove this item from cart?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.cart_service.remove_from_cart("amazon", product_id)
            self._refresh_cart()

    def _clear_cart(self):
        """Clear entire cart."""
        if not self.cart_service:
            return

        reply = QMessageBox.question(
            self,
            "Clear Cart",
            "Are you sure you want to clear your cart?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.cart_service.clear_cart("amazon")
            self._refresh_cart()
            QMessageBox.information(self, "Cart", "Cart cleared")

    def _checkout(self):
        """Proceed to checkout."""
        if not self.cart_service:
            return

        cart = self.cart_service.get_cart("amazon")

        if not cart or not cart.items:
            QMessageBox.warning(self, "Checkout", "Cart is empty")
            return

        # Check spend caps
        spend_check = self.cart_service.check_spend_cap(cart)

        if not spend_check["within_cap"]:
            reply = QMessageBox.warning(
                self,
                "Spend Cap Warning",
                f"{spend_check['message']}\n\nDo you want to proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # Create order
        try:
            order = self.cart_service.create_order(cart, auto_generated=False)

            QMessageBox.information(
                self,
                "Order Created",
                f"Order created successfully!\n\nOrder ID: {order.order_id}\nTotal: ${order.total_cost:.2f}\n\nOrder is pending approval."
            )

            # Clear cart and refresh
            self.cart_service.clear_cart("amazon")
            self._refresh_cart()
            self._refresh_orders()

            # Switch to orders tab
            self.tabs.setCurrentIndex(2)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create order:\n{e}")

    def _refresh_orders(self):
        """Refresh orders display."""
        if not self.cart_service:
            return

        orders = self.cart_service.get_order_history(limit=50)

        self.orders_table.setRowCount(len(orders))

        for row, order in enumerate(orders):
            # Order ID
            id_item = QTableWidgetItem(order.order_id[:16] + "...")
            self.orders_table.setItem(row, 0, id_item)

            # Vendor
            vendor_item = QTableWidgetItem(order.vendor.title())
            self.orders_table.setItem(row, 1, vendor_item)

            # Total
            total_item = QTableWidgetItem(f"${order.total_cost:.2f}")
            self.orders_table.setItem(row, 2, total_item)

            # Status
            status_item = QTableWidgetItem(order.status.replace("_", " ").title())
            self.orders_table.setItem(row, 3, status_item)

            # Date
            date_str = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "N/A"
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
                status_label = QLabel(order.status.replace("_", " ").title())
                status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        # Refresh cart when page is shown
        self._refresh_cart()
        self._refresh_orders()
