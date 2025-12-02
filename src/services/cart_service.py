"""
Shopping cart service for managing vendor carts and orders.

Handles cart creation, item management, order placement, and spend cap enforcement.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..database.db_manager import DatabaseManager
from ..vendors import VendorClient, ShoppingCart, CartItem, VendorProduct, OrderStatus
from ..models import Order
from ..utils import get_logger


class CartService:
    """Service for managing shopping carts and orders."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize cart service.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.logger = get_logger("cart_service")
        self.active_carts: Dict[str, ShoppingCart] = {}  # vendor -> cart

    def get_or_create_cart(self, vendor: str, vendor_client: VendorClient) -> ShoppingCart:
        """
        Get existing cart for vendor or create new one.

        Args:
            vendor: Vendor name
            vendor_client: Vendor client instance

        Returns:
            ShoppingCart
        """
        if vendor not in self.active_carts:
            self.logger.info(f"Creating new cart for {vendor}")
            self.active_carts[vendor] = vendor_client.create_cart()
        else:
            self.logger.info(f"Retrieved existing cart for {vendor}")

        return self.active_carts[vendor]

    def add_to_cart(
        self,
        vendor: str,
        vendor_client: VendorClient,
        product: VendorProduct,
        quantity: float
    ) -> ShoppingCart:
        """
        Add item to cart.

        Args:
            vendor: Vendor name
            vendor_client: Vendor client instance
            product: Product to add
            quantity: Quantity to add

        Returns:
            Updated ShoppingCart
        """
        cart = self.get_or_create_cart(vendor, vendor_client)

        # Create cart item
        cart_item = CartItem(
            product_id=product.product_id,
            name=product.name,
            price=product.price,
            quantity=quantity,
            unit=product.unit,
            vendor=vendor,
            image_url=product.image_url
        )

        cart.add_item(cart_item)
        self.logger.info(f"Added {quantity} x {product.name} to {vendor} cart")

        return cart

    def remove_from_cart(self, vendor: str, product_id: str) -> Optional[ShoppingCart]:
        """
        Remove item from cart.

        Args:
            vendor: Vendor name
            product_id: Product ID to remove

        Returns:
            Updated cart or None if cart doesn't exist
        """
        if vendor not in self.active_carts:
            self.logger.warning(f"No active cart for {vendor}")
            return None

        cart = self.active_carts[vendor]
        if cart.remove_item(product_id):
            self.logger.info(f"Removed product {product_id} from {vendor} cart")
            return cart
        else:
            self.logger.warning(f"Product {product_id} not found in cart")
            return cart

    def update_cart_quantity(
        self,
        vendor: str,
        product_id: str,
        quantity: float
    ) -> Optional[ShoppingCart]:
        """
        Update item quantity in cart.

        Args:
            vendor: Vendor name
            product_id: Product ID
            quantity: New quantity

        Returns:
            Updated cart or None if cart doesn't exist
        """
        if vendor not in self.active_carts:
            self.logger.warning(f"No active cart for {vendor}")
            return None

        cart = self.active_carts[vendor]
        if cart.update_quantity(product_id, quantity):
            self.logger.info(f"Updated {product_id} quantity to {quantity} in {vendor} cart")
            return cart
        else:
            self.logger.warning(f"Product {product_id} not found in cart")
            return cart

    def clear_cart(self, vendor: str) -> bool:
        """
        Clear all items from cart.

        Args:
            vendor: Vendor name

        Returns:
            True if cart was cleared
        """
        if vendor in self.active_carts:
            self.active_carts[vendor].clear()
            self.logger.info(f"Cleared {vendor} cart")
            return True
        return False

    def get_cart(self, vendor: str) -> Optional[ShoppingCart]:
        """
        Get current cart for vendor.

        Args:
            vendor: Vendor name

        Returns:
            ShoppingCart or None
        """
        return self.active_carts.get(vendor)

    def get_all_carts(self) -> List[ShoppingCart]:
        """
        Get all active carts.

        Returns:
            List of active carts
        """
        return list(self.active_carts.values())

    def check_spend_cap(self, cart: ShoppingCart) -> Dict[str, Any]:
        """
        Check if cart total exceeds spend caps.

        Args:
            cart: Shopping cart

        Returns:
            Dictionary with:
                - within_cap: bool
                - weekly_remaining: float
                - monthly_remaining: float
                - message: str
        """
        try:
            # Get user preferences
            prefs = self.db_manager.get_preferences()

            weekly_cap = prefs.get("spend_cap_weekly")
            monthly_cap = prefs.get("spend_cap_monthly")

            # Get current spend (this week and this month)
            # TODO: Query actual spend from order history
            current_weekly_spend = 0.0  # Placeholder
            current_monthly_spend = 0.0  # Placeholder

            cart_total = cart.total

            # Check caps
            weekly_remaining = weekly_cap - current_weekly_spend if weekly_cap else float('inf')
            monthly_remaining = monthly_cap - current_monthly_spend if monthly_cap else float('inf')

            within_cap = True
            messages = []

            if weekly_cap and (cart_total + current_weekly_spend) > weekly_cap:
                within_cap = False
                messages.append(f"Cart total ${cart_total:.2f} would exceed weekly cap of ${weekly_cap:.2f}")

            if monthly_cap and (cart_total + current_monthly_spend) > monthly_cap:
                within_cap = False
                messages.append(f"Cart total ${cart_total:.2f} would exceed monthly cap of ${monthly_cap:.2f}")

            return {
                "within_cap": within_cap,
                "weekly_remaining": max(0, weekly_remaining),
                "monthly_remaining": max(0, monthly_remaining),
                "message": "; ".join(messages) if messages else "Within spend caps"
            }

        except Exception as e:
            self.logger.error(f"Error checking spend cap: {e}")
            # Default to allowing purchase if check fails
            return {
                "within_cap": True,
                "weekly_remaining": float('inf'),
                "monthly_remaining": float('inf'),
                "message": "Could not verify spend caps"
            }

    def create_order(
        self,
        cart: ShoppingCart,
        auto_generated: bool = False,
        user_notes: Optional[str] = None
    ) -> Order:
        """
        Create an order from a cart.

        Args:
            cart: Shopping cart
            auto_generated: Whether order was auto-generated by system
            user_notes: Optional user notes

        Returns:
            Created Order
        """
        order_id = str(uuid.uuid4())

        # Convert cart to order items format
        items = []
        for cart_item in cart.items:
            items.append({
                "item_id": cart_item.product_id,
                "name": cart_item.name,
                "quantity": cart_item.quantity,
                "unit": cart_item.unit,
                "price": cart_item.price
            })

        # Create order
        order = Order(
            order_id=order_id,
            vendor=cart.vendor,
            status=OrderStatus.PENDING_APPROVAL,
            items=items,
            total_cost=cart.total,
            created_at=datetime.now(),
            user_notes=user_notes,
            auto_generated=auto_generated
        )

        # Save to database
        self.db_manager.create_order(order)
        self.logger.info(f"Created order {order_id} for {cart.vendor}, total: ${cart.total:.2f}")

        return order

    def approve_order(self, order_id: str) -> bool:
        """
        Approve an order for placement.

        Args:
            order_id: Order ID

        Returns:
            True if approved successfully
        """
        try:
            order = self.db_manager.get_order(order_id)
            if not order:
                self.logger.error(f"Order {order_id} not found")
                return False

            if order.status != OrderStatus.PENDING_APPROVAL:
                self.logger.warning(f"Order {order_id} status is {order.status}, cannot approve")
                return False

            # Update order status
            order.status = OrderStatus.APPROVED
            order.approved_at = datetime.now()

            self.db_manager.update_order(order)
            self.logger.info(f"Approved order {order_id}")

            return True

        except Exception as e:
            self.logger.error(f"Error approving order {order_id}: {e}")
            return False

    def place_order(
        self,
        order_id: str,
        vendor_client: VendorClient,
        shipping_address: Optional[Dict[str, str]] = None,
        payment_method: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Place an approved order with the vendor.

        Args:
            order_id: Order ID
            vendor_client: Vendor client to use
            shipping_address: Shipping address
            payment_method: Payment method

        Returns:
            Order placement result
        """
        try:
            order = self.db_manager.get_order(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")

            if order.status != OrderStatus.APPROVED:
                raise ValueError(f"Order {order_id} must be approved before placing")

            # Reconstruct cart from order
            cart = ShoppingCart(
                cart_id=f"order-cart-{order_id[:8]}",
                vendor=order.vendor
            )

            for item_data in order.items:
                cart_item = CartItem(
                    product_id=item_data.item_id or str(uuid.uuid4()),
                    name=item_data.name,
                    price=item_data.price,
                    quantity=item_data.quantity,
                    unit=item_data.unit,
                    vendor=order.vendor
                )
                cart.add_item(cart_item)


            # Place order with vendor
            vendor_response = vendor_client.place_order(
                cart=cart,
                shipping_address=shipping_address,
                payment_method=payment_method
            )

            # Update order with vendor details
            order.status = OrderStatus.PLACED
            order.placed_at = datetime.now()

            self.db_manager.update_order(order)

            self.logger.info(f"Placed order {order_id} with {order.vendor}")

            # Clear the cart
            if order.vendor in self.active_carts:
                del self.active_carts[order.vendor]

            return vendor_response

        except Exception as e:
            self.logger.error(f"Error placing order {order_id}: {e}")
            # Update order status to failed
            try:
                order = self.db_manager.get_order(order_id)
                if order:
                    order.status = OrderStatus.FAILED
                    self.db_manager.update_order(order)
            except:
                pass

            raise

    def get_pending_orders(self) -> List[Order]:
        """
        Get all orders pending approval.

        Returns:
            List of pending orders
        """
        try:
            all_orders = self.db_manager.get_all_orders()
            pending = [o for o in all_orders if o.status == OrderStatus.PENDING_APPROVAL]
            return pending
        except Exception as e:
            self.logger.error(f"Error getting pending orders: {e}")
            return []

    def get_order_history(self, limit: int = 50) -> List[Order]:
        """
        Get order history.

        Args:
            limit: Maximum number of orders to return

        Returns:
            List of orders
        """
        try:
            orders = self.db_manager.get_all_orders()
            # Sort by created_at descending
            orders.sort(key=lambda o: o.created_at, reverse=True)
            return orders[:limit]
        except Exception as e:
            self.logger.error(f"Error getting order history: {e}")
            return []
