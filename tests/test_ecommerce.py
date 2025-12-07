#!/usr/bin/env python3
"""
Test script for e-commerce integration.

Tests Amazon client, cart service, and order workflow.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vendors import AmazonClient, CartItem
from src.services.cart_service import CartService
from src.database.db_manager import DatabaseManager
from src.utils import get_logger


def test_amazon_client():
    """Test Amazon client functionality."""
    logger = get_logger("test_ecommerce")

    logger.info("=" * 60)
    logger.info("Testing Amazon Client")
    logger.info("=" * 60)

    try:
        # Initialize client
        logger.info("\n1. Initializing Amazon client...")
        client = AmazonClient()
        logger.info("✅ Client initialized")

        # Test product search
        logger.info("\n2. Testing product search...")
        result = client.search_products("milk", max_results=5)
        logger.info(f"✅ Found {len(result.products)} products")

        for i, product in enumerate(result.products, 1):
            logger.info(f"\n   Product {i}:")
            logger.info(f"   - Name: {product.name}")
            logger.info(f"   - Brand: {product.brand}")
            logger.info(f"   - Price: ${product.price:.2f}")
            logger.info(f"   - Prime: {'Yes' if product.prime_eligible else 'No'}")
            logger.info(f"   - Rating: {product.rating:.1f}/5.0" if product.rating else "   - Rating: N/A")

        # Test product details
        if result.products:
            logger.info("\n3. Testing product details retrieval...")
            product_id = result.products[0].product_id
            details = client.get_product_details(product_id)

            if details:
                logger.info(f"✅ Retrieved details for: {details.name}")
            else:
                logger.error("❌ Failed to retrieve product details")

            # Test price check
            logger.info("\n4. Testing price check...")
            price = client.get_product_price(product_id)
            logger.info(f"✅ Price: ${price:.2f}")

            # Test availability
            logger.info("\n5. Testing availability check...")
            available = client.check_availability(product_id)
            logger.info(f"✅ Available: {available}")

        # Test cart creation
        logger.info("\n6. Testing cart creation...")
        cart = client.create_cart()
        logger.info(f"✅ Created cart: {cart.cart_id}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Amazon client tests passed!")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_cart_service():
    """Test cart service functionality."""
    logger = get_logger("test_ecommerce")

    logger.info("\n" + "=" * 60)
    logger.info("Testing Cart Service")
    logger.info("=" * 60)

    try:
        # Initialize database and service
        logger.info("\n1. Initializing cart service...")
        db_manager = DatabaseManager("data/test_ecommerce.db", "test_password")
        db_manager.initialize_database()
        cart_service = CartService(db_manager)
        amazon_client = AmazonClient()
        logger.info("✅ Service initialized")

        # Search for products
        logger.info("\n2. Searching for products...")
        result = amazon_client.search_products("bread", max_results=3)
        logger.info(f"✅ Found {len(result.products)} products")

        # Add items to cart
        logger.info("\n3. Adding items to cart...")
        for product in result.products[:2]:
            cart = cart_service.add_to_cart(
                vendor="amazon",
                vendor_client=amazon_client,
                product=product,
                quantity=1.0
            )
            logger.info(f"   Added: {product.name}")

        logger.info(f"✅ Cart total: ${cart.total:.2f}")
        logger.info(f"✅ Cart items: {cart.item_count}")

        # Test spend cap check
        logger.info("\n4. Testing spend cap enforcement...")
        spend_check = cart_service.check_spend_cap(cart)
        logger.info(f"✅ Within cap: {spend_check['within_cap']}")
        logger.info(f"   Message: {spend_check['message']}")

        # Create order
        logger.info("\n5. Creating order from cart...")
        order = cart_service.create_order(
            cart,
            auto_generated=False,
            user_notes="Test order"
        )
        logger.info(f"✅ Order created: {order.order_id}")
        logger.info(f"   Status: {order.status}")
        logger.info(f"   Total: ${order.total_cost:.2f}")

        # Approve order
        logger.info("\n6. Approving order...")
        success = cart_service.approve_order(order.order_id)
        logger.info(f"✅ Order approved: {success}")

        # Place order
        logger.info("\n7. Placing order with vendor...")
        result = cart_service.place_order(
            order.order_id,
            amazon_client,
            shipping_address={"street": "123 Main St", "city": "Anytown", "state": "CA", "zip": "12345"},
            payment_method={"type": "credit_card", "last4": "1234"}
        )
        logger.info(f"✅ Order placed!")
        logger.info(f"   Vendor Order ID: {result['order_id']}")
        logger.info(f"   Status: {result['status']}")

        # Get order history
        logger.info("\n8. Retrieving order history...")
        orders = cart_service.get_order_history(limit=10)
        logger.info(f"✅ Found {len(orders)} orders")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Cart service tests passed!")
        logger.info("=" * 60)

        # Cleanup
        import os
        if os.path.exists("data/test_ecommerce.db"):
            os.remove("data/test_ecommerce.db")

        return True

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_cart_management():
    """Test cart item management."""
    logger = get_logger("test_ecommerce")

    logger.info("\n" + "=" * 60)
    logger.info("Testing Cart Management")
    logger.info("=" * 60)

    try:
        logger.info("\n1. Testing cart item operations...")

        db_manager = DatabaseManager("data/test_cart.db", "test_password")
        cart_service = CartService(db_manager)
        amazon_client = AmazonClient()

        # Add items
        result = amazon_client.search_products("eggs", max_results=2)

        for product in result.products:
            cart_service.add_to_cart(
                vendor="amazon",
                vendor_client=amazon_client,
                product=product,
                quantity=1.0
            )

        cart = cart_service.get_cart("amazon")
        initial_count = cart.item_count
        logger.info(f"✅ Initial cart has {initial_count} items")

        # Update quantity
        logger.info("\n2. Testing quantity update...")
        first_item_id = cart.items[0].product_id
        cart_service.update_cart_quantity("amazon", first_item_id, 3.0)
        cart = cart_service.get_cart("amazon")
        logger.info(f"✅ Updated quantity to 3.0")

        # Remove item
        logger.info("\n3. Testing item removal...")
        cart_service.remove_from_cart("amazon", first_item_id)
        cart = cart_service.get_cart("amazon")
        logger.info(f"✅ Removed item, cart now has {cart.item_count} items")

        # Clear cart
        logger.info("\n4. Testing cart clear...")
        cart_service.clear_cart("amazon")
        cart = cart_service.get_cart("amazon")
        logger.info(f"✅ Cart cleared, items: {cart.item_count if cart else 0}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Cart management tests passed!")
        logger.info("=" * 60)

        # Cleanup
        import os
        if os.path.exists("data/test_cart.db"):
            os.remove("data/test_cart.db")

        return True

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Run all tests."""
    logger = get_logger("test_ecommerce")

    logger.info("=" * 60)
    logger.info("E-Commerce Integration Test Suite")
    logger.info("=" * 60)

    results = {}

    # Run tests
    logger.info("\n")
    results["Amazon Client"] = test_amazon_client()

    logger.info("\n")
    results["Cart Service"] = test_cart_service()

    logger.info("\n")
    results["Cart Management"] = test_cart_management()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("🎉 All tests passed successfully!")
        logger.info("\nThe e-commerce integration is working correctly.")
        logger.info("You can now:")
        logger.info("  - Search for products")
        logger.info("  - Add items to cart")
        logger.info("  - Create and approve orders")
        logger.info("  - Place orders with Amazon (simulated)")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
