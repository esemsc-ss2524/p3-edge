"""
Vendor search and cart management tools for LLM agent.

These tools enable the agent to search for products, check availability,
and manage shopping carts.
"""

from typing import List, Dict, Any, Optional
from .base import BaseTool
from ..models.tool_models import (
    ToolParameter,
    ToolParameterType,
    ToolCategory,
)
from ..vendors.base import VendorClient
from ..vendors.models import CartItem
from ..services.cart_service import CartService


class SearchProductsTool(BaseTool):
    """Search for products on vendor."""

    def __init__(self, vendor_client: VendorClient):
        self.vendor_client = vendor_client

    @property
    def name(self) -> str:
        return "search_products"

    @property
    def description(self) -> str:
        return "Search for products by keyword on the vendor (Amazon)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.VENDOR

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="Search query (e.g., 'organic milk', 'whole wheat bread')",
                required=True,
            ),
            ToolParameter(
                name="category",
                type=ToolParameterType.STRING,
                description="Product category to filter by (optional)",
                required=False,
            ),
            ToolParameter(
                name="max_results",
                type=ToolParameterType.INTEGER,
                description="Maximum number of results to return (default: 5)",
                required=False,
                default=5,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of products with names, product_ids, prices, ratings, availability, etc. details."

    @property
    def examples(self) -> Optional[List[str]]:
        return [
            "search_products(query='organic milk', max_results=3)",
            "search_products(query='eggs', category='grocery')",
        ]

    def execute(
        self, query: str, category: Optional[str] = None, max_results: int = 5
    ) -> Dict[str, Any]:
        """Execute search."""
        search_result = self.vendor_client.search_products(
            query=query, category=category, max_results=max_results
        )

        products = []
        for product in search_result.products:
            products.append(
                {
                    "product_id": product.product_id,
                    "name": product.name,
                    "brand": product.brand,
                    "price": product.price,
                    "unit": product.unit,
                    "rating": product.rating,
                    "reviews_count": product.reviews_count,
                    "in_stock": product.in_stock,
                    "prime_eligible": product.prime_eligible,
                    "category": product.category,
                }
            )

        return {
            "query": query,
            "vendor": search_result.vendor,
            "total_results": search_result.total_results,
            "products": products,
        }


class BatchSearchProductsTool(BaseTool):
    """Search for multiple products at once on vendor."""

    def __init__(self, vendor_client: VendorClient):
        self.vendor_client = vendor_client

    @property
    def name(self) -> str:
        return "batch_search_products"

    @property
    def description(self) -> str:
        return "Search for multiple products at once by providing a list of item names. More efficient than multiple individual searches."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.VENDOR

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="queries",
                type=ToolParameterType.ARRAY,
                description="List of search queries/item names (e.g., ['milk', 'eggs', 'bread'])",
                required=True,
                items={"type": "string"},  # Specify array contains strings
            ),
            ToolParameter(
                name="category",
                type=ToolParameterType.STRING,
                description="Product category to filter by (optional)",
                required=False,
            ),
            ToolParameter(
                name="max_results",
                type=ToolParameterType.INTEGER,
                description="Maximum number of results per query (default: 3)",
                required=False,
                default=3,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Dictionary mapping each query to its search results, with products containing names, product_ids, prices, ratings, availability, etc."

    @property
    def examples(self) -> Optional[List[str]]:
        return [
            "batch_search_products(queries=['milk', 'eggs', 'bread'], max_results=3)",
            "batch_search_products(queries=['organic milk', 'whole wheat bread', 'greek yogurt'])",
        ]

    def execute(
        self, queries: List[str], category: Optional[str] = None, max_results: int = 3
    ) -> Dict[str, Any]:
        """Execute batch search."""
        batch_result = self.vendor_client.batch_search_products(
            queries=queries, category=category, max_results=max_results
        )

        # Format results as a dictionary mapping query -> products
        results_by_query = {}
        for search_result in batch_result.results:
            products = []
            for product in search_result.products:
                products.append(
                    {
                        "product_id": product.product_id,
                        "name": product.name,
                        "brand": product.brand,
                        "price": product.price,
                        "unit": product.unit,
                        "rating": product.rating,
                        "reviews_count": product.reviews_count,
                        "in_stock": product.in_stock,
                        "prime_eligible": product.prime_eligible,
                        "category": product.category,
                    }
                )

            results_by_query[search_result.query] = {
                "total_results": search_result.total_results,
                "products": products,
            }

        return {
            "vendor": batch_result.vendor,
            "total_queries": batch_result.total_queries,
            "results": results_by_query,
        }


class GetProductDetailsTool(BaseTool):
    """Get detailed information about a specific product."""

    def __init__(self, vendor_client: VendorClient):
        self.vendor_client = vendor_client

    @property
    def name(self) -> str:
        return "get_product_details"

    @property
    def description(self) -> str:
        return "Get detailed information about a specific product by product ID"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.VENDOR

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="product_id",
                type=ToolParameterType.STRING,
                description="Product ID from search results",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Detailed product information including price, availability, and specifications"

    def execute(self, product_id: str) -> Dict[str, Any]:
        """Get product details."""
        product = self.vendor_client.get_product_details(product_id)

        if not product:
            return {"error": f"Product {product_id} not found"}

        return {
            "product_id": product.product_id,
            "name": product.name,
            "brand": product.brand,
            "category": product.category,
            "price": product.price,
            "unit": product.unit,
            "rating": product.rating,
            "reviews_count": product.reviews_count,
            "in_stock": product.in_stock,
            "prime_eligible": product.prime_eligible,
            "description": getattr(product, "description", None),
        }


class CheckProductAvailabilityTool(BaseTool):
    """Check if a product is in stock."""

    def __init__(self, vendor_client: VendorClient):
        self.vendor_client = vendor_client

    @property
    def name(self) -> str:
        return "check_product_availability"

    @property
    def description(self) -> str:
        return "Check if a specific product is currently in stock"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.VENDOR

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="product_id",
                type=ToolParameterType.STRING,
                description="Product ID to check",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Availability status (true/false)"

    def execute(self, product_id: str) -> Dict[str, Any]:
        """Check availability."""
        is_available = self.vendor_client.check_availability(product_id)

        return {"product_id": product_id, "in_stock": is_available}


class AddToCartTool(BaseTool):
    """Add product to shopping cart."""

    def __init__(self, cart_service: CartService, vendor_client: VendorClient):
        self.cart_service = cart_service
        self.vendor_client = vendor_client

    @property
    def name(self) -> str:
        return "add_to_cart"

    @property
    def description(self) -> str:
        return "Add a product to the shopping cart with specified quantity"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CART

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="product_id",
                type=ToolParameterType.STRING,
                description="Product ID from search results",
                required=True,
            ),
            ToolParameter(
                name="quantity",
                type=ToolParameterType.INTEGER,
                description="Quantity to add",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Updated cart information with total items and cost"

    def execute(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """Add to cart."""
        # Get product details
        product = self.vendor_client.get_product_details(product_id)

        if not product:
            return {"error": f"Product {product_id} not found"}

        if not product.in_stock:
            return {"error": f"Product '{product.name}' is currently out of stock"}

        # Add to cart using cart_service API
        try:
            # Get vendor name from product
            vendor = product.vendor

            # Call add_to_cart with correct parameters
            cart = self.cart_service.add_to_cart(
                vendor=vendor,
                vendor_client=self.vendor_client,
                product=product,
                quantity=float(quantity)
            )

            return {
                "success": True,
                "message": f"Added {quantity} {product.unit} of {product.name} to {vendor} cart",
                "cart_total_items": len(cart.items),
                "cart_total_cost": cart.total,
                "added_item": {
                    "name": product.name,
                    "quantity": quantity,
                    "unit": product.unit,
                    "price": product.price,
                    "subtotal": product.price * quantity,
                },
            }
        except Exception as e:
            return {"error": f"Failed to add to cart: {str(e)}"}


class ViewCartTool(BaseTool):
    """View current shopping cart contents."""

    def __init__(self, cart_service: CartService):
        self.cart_service = cart_service

    @property
    def name(self) -> str:
        return "view_cart"

    @property
    def description(self) -> str:
        return "View all active shopping carts with items and total cost"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CART

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="vendor",
                type=ToolParameterType.STRING,
                description="Vendor name to view cart for (optional, if not provided shows all carts)",
                required=False,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Cart contents with items, quantities, prices, and total"

    def execute(self, vendor: Optional[str] = None) -> Dict[str, Any]:
        """View cart."""
        if vendor:
            # Get specific vendor cart
            cart = self.cart_service.get_cart(vendor)
            if not cart:
                return {"message": f"No active cart for vendor: {vendor}"}

            items = []
            for item in cart.items:
                items.append(
                    {
                        "product_id": item.product_id,
                        "name": item.name,
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "price": item.price,
                        "subtotal": item.subtotal,
                    }
                )

            return {
                "cart_id": cart.cart_id,
                "vendor": cart.vendor,
                "items": items,
                "total_items": len(items),
                "total_cost": cart.total,
                "created_at": cart.created_at.isoformat() if cart.created_at else None,
            }
        else:
            # Get all carts
            carts = self.cart_service.get_all_carts()
            if not carts:
                return {"message": "No active carts", "carts": []}

            cart_summaries = []
            for cart in carts:
                cart_summaries.append({
                    "vendor": cart.vendor,
                    "total_items": len(cart.items),
                    "total_cost": cart.total,
                })

            return {
                "message": f"Found {len(carts)} active cart(s)",
                "carts": cart_summaries
            }


class RemoveFromCartTool(BaseTool):
    """Remove item from shopping cart."""

    def __init__(self, cart_service: CartService):
        self.cart_service = cart_service

    @property
    def name(self) -> str:
        return "remove_from_cart"

    @property
    def description(self) -> str:
        return "Remove an item from the shopping cart by product ID"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CART

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="product_id",
                type=ToolParameterType.STRING,
                description="Product ID of item to remove",
                required=True,
            ),
            ToolParameter(
                name="vendor",
                type=ToolParameterType.STRING,
                description="Vendor name (optional, will search all carts if not provided)",
                required=False,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Updated cart information after removal"

    def execute(self, product_id: str, vendor: Optional[str] = None) -> Dict[str, Any]:
        """Remove from cart."""
        try:
            # If vendor not specified, search all carts
            if not vendor:
                all_carts = self.cart_service.get_all_carts()
                found_vendor = None
                for cart in all_carts:
                    for item in cart.items:
                        if item.product_id == product_id:
                            found_vendor = cart.vendor
                            break
                    if found_vendor:
                        break

                if not found_vendor:
                    return {"error": f"Product {product_id} not found in any cart"}

                vendor = found_vendor

            # Get cart to find item name
            cart = self.cart_service.get_cart(vendor)
            if not cart:
                return {"error": f"No active cart for vendor: {vendor}"}

            # Find item name before removing
            item_name = None
            for item in cart.items:
                if item.product_id == product_id:
                    item_name = item.name
                    break

            if not item_name:
                return {"error": f"Product {product_id} not found in {vendor} cart"}

            # Remove item
            updated_cart = self.cart_service.remove_from_cart(vendor, product_id)

            if updated_cart:
                return {
                    "success": True,
                    "message": f"Removed {item_name} from {vendor} cart",
                    "cart_total_items": len(updated_cart.items),
                    "cart_total_cost": updated_cart.total,
                }
            else:
                return {"error": f"Failed to remove item from cart"}

        except Exception as e:
            return {"error": f"Failed to remove from cart: {str(e)}"}


class UpdateCartQuantityTool(BaseTool):
    """Update quantity of item in cart."""

    def __init__(self, cart_service: CartService):
        self.cart_service = cart_service

    @property
    def name(self) -> str:
        return "update_cart_quantity"

    @property
    def description(self) -> str:
        return "Update the quantity of an item already in the cart"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CART

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="product_id",
                type=ToolParameterType.STRING,
                description="Product ID of item to update",
                required=True,
            ),
            ToolParameter(
                name="quantity",
                type=ToolParameterType.INTEGER,
                description="New quantity",
                required=True,
            ),
            ToolParameter(
                name="vendor",
                type=ToolParameterType.STRING,
                description="Vendor name (optional, will search all carts if not provided)",
                required=False,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Updated cart information with new quantity"

    def execute(self, product_id: str, quantity: int, vendor: Optional[str] = None) -> Dict[str, Any]:
        """Update quantity."""
        try:
            # If vendor not specified, search all carts
            if not vendor:
                all_carts = self.cart_service.get_all_carts()
                found_vendor = None
                for cart in all_carts:
                    for item in cart.items:
                        if item.product_id == product_id:
                            found_vendor = cart.vendor
                            break
                    if found_vendor:
                        break

                if not found_vendor:
                    return {"error": f"Product {product_id} not found in any cart"}

                vendor = found_vendor

            # Update quantity
            cart = self.cart_service.update_cart_quantity(vendor, product_id, float(quantity))

            if not cart:
                return {"error": f"Failed to update quantity"}

            # Find updated item
            updated_item = None
            for item in cart.items:
                if item.product_id == product_id:
                    updated_item = item
                    break

            if updated_item:
                return {
                    "success": True,
                    "message": f"Updated {updated_item.name} quantity to {quantity} in {vendor} cart",
                    "updated_item": {
                        "name": updated_item.name,
                        "quantity": updated_item.quantity,
                        "subtotal": updated_item.subtotal,
                    },
                    "cart_total_cost": cart.total,
                }
            else:
                return {"error": f"Product not found after update"}

        except Exception as e:
            return {"error": f"Failed to update quantity: {str(e)}"}
