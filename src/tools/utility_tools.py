"""
Utility tools for LLM agent.

These tools provide helper functions for calculations, conversions,
and data analysis.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .base import BaseTool
from ..models.tool_models import (
    ToolParameter,
    ToolParameterType,
    ToolCategory,
)
from ..database.db_manager import DatabaseManager
from ..services.forecast_service import ForecastService


class CalculateDaysRemainingTool(BaseTool):
    """Calculate how many days an item will last."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "calculate_days_remaining"

    @property
    def description(self) -> str:
        return "Calculate how many days until an item runs out based on current quantity and consumption rate"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="item_name",
                type=ToolParameterType.STRING,
                description="Name of the item (e.g., 'milk', 'eggs')",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Estimated days remaining and runout date"

    @property
    def examples(self) -> Optional[List[str]]:
        return [
            "calculate_days_remaining(item_name='milk')",
            "calculate_days_remaining(item_name='eggs')",
        ]

    def execute(self, item_name: str) -> Dict[str, Any]:
        """Calculate days remaining."""
        query = """
            SELECT item_id, name, quantity_current, consumption_rate,
                   expiry_date, unit, perishable
            FROM inventory
            WHERE LOWER(name) LIKE LOWER(?)
            LIMIT 1
        """
        results = self.db_manager.execute_query(query, (f"%{item_name}%",))

        if not results:
            return {"error": f"Item '{item_name}' not found in inventory"}

        row = results[0]
        item_id, name, quantity, consumption_rate, expiry_date, unit, perishable = row

        # Calculate based on consumption rate
        if consumption_rate and consumption_rate > 0:
            days_remaining = quantity / consumption_rate
            runout_date = datetime.now() + timedelta(days=days_remaining)
        else:
            days_remaining = None
            runout_date = None

        # Check expiry
        will_expire_first = False
        expiry_note = None
        if expiry_date:
            expiry = datetime.fromisoformat(expiry_date)
            if runout_date and expiry < runout_date:
                will_expire_first = True
                days_remaining = (expiry - datetime.now()).days
                runout_date = expiry
                expiry_note = "Item will expire before running out based on consumption"
            elif runout_date:
                expiry_note = "Item will run out before expiry date"

        return {
            "item_name": name,
            "quantity_current": quantity,
            "unit": unit,
            "consumption_rate": consumption_rate,
            "consumption_rate_unit": f"{unit}/day" if consumption_rate else None,
            "days_remaining": round(days_remaining, 1) if days_remaining else None,
            "estimated_runout_date": runout_date.isoformat() if runout_date else None,
            "will_expire_first": will_expire_first,
            "expiry_date": expiry_date,
            "is_perishable": bool(perishable),
            "note": expiry_note,
        }


class CalculateQuantityNeededTool(BaseTool):
    """Calculate how much to order based on consumption."""

    def __init__(self, db_manager: DatabaseManager, forecast_service: ForecastService):
        self.db_manager = db_manager
        self.forecast_service = forecast_service

    @property
    def name(self) -> str:
        return "calculate_quantity_needed"

    @property
    def description(self) -> str:
        return "Calculate recommended order quantity based on consumption rate and desired coverage period"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="item_name",
                type=ToolParameterType.STRING,
                description="Name of the item",
                required=True,
            ),
            ToolParameter(
                name="days_coverage",
                type=ToolParameterType.INTEGER,
                description="Number of days of supply needed (default: 14)",
                required=False,
                default=14,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Recommended quantity to order with justification"

    def execute(self, item_name: str, days_coverage: int = 14) -> Dict[str, Any]:
        """Calculate quantity needed."""
        query = """
            SELECT item_id, name, quantity_current, quantity_min, quantity_max,
                   consumption_rate, unit
            FROM inventory
            WHERE LOWER(name) LIKE LOWER(?)
            LIMIT 1
        """
        results = self.db_manager.execute_query(query, (f"%{item_name}%",))

        if not results:
            return {"error": f"Item '{item_name}' not found in inventory"}

        (
            item_id,
            name,
            current_qty,
            min_qty,
            max_qty,
            consumption_rate,
            unit,
        ) = results[0]

        if not consumption_rate or consumption_rate <= 0:
            return {
                "item_name": name,
                "error": "No consumption rate available for calculation",
                "recommendation": f"Consider ordering at least {min_qty} {unit} to maintain minimum stock",
            }

        # Calculate needed quantity
        needed_for_coverage = consumption_rate * days_coverage
        needed_to_reach_max = max_qty - current_qty if max_qty else needed_for_coverage
        recommended = max(0, min(needed_for_coverage, needed_to_reach_max))

        return {
            "item_name": name,
            "current_quantity": current_qty,
            "unit": unit,
            "consumption_rate": consumption_rate,
            "days_coverage_requested": days_coverage,
            "recommended_quantity": round(recommended, 2),
            "total_after_order": round(current_qty + recommended, 2),
            "will_cover_days": round(
                (current_qty + recommended) / consumption_rate, 1
            ),
            "justification": f"Based on {consumption_rate} {unit}/day consumption rate for {days_coverage} days coverage",
        }


class CheckBudgetTool(BaseTool):
    """Check remaining budget."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "check_budget"

    @property
    def description(self) -> str:
        return "Check remaining weekly/monthly grocery budget based on user preferences"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "Budget information with spent amount and remaining amount"

    def execute(self) -> Dict[str, Any]:
        """Check budget."""
        # Get budget preferences
        pref_query = """
            SELECT key, value FROM preferences
            WHERE key IN ('spend_cap_weekly', 'spend_cap_monthly')
        """
        prefs = self.db_manager.execute_query(pref_query)

        budget_weekly = None
        budget_monthly = None

        for key, value in prefs:
            if key == "spend_cap_weekly":
                try:
                    # Handle 'null' string or None values
                    if value and value != 'null':
                        budget_weekly = float(value)
                except (ValueError, TypeError):
                    pass
            elif key == "spend_cap_monthly":
                try:
                    # Handle 'null' string or None values
                    if value and value != 'null':
                        budget_monthly = float(value)
                except (ValueError, TypeError):
                    pass

        # Calculate spending this week
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).date()
        week_query = """
            SELECT SUM(total_cost) FROM orders
            WHERE created_at >= ?
              AND status IN ('PLACED', 'DELIVERED')
        """
        week_result = self.db_manager.execute_query(
            week_query, (week_start.isoformat(),)
        )
        spent_this_week = week_result[0][0] if week_result and week_result[0][0] else 0.0

        # Calculate spending this month
        month_start = datetime.now().replace(day=1).date()
        month_query = """
            SELECT SUM(total_cost) FROM orders
            WHERE created_at >= ?
              AND status IN ('PLACED', 'DELIVERED')
        """
        month_result = self.db_manager.execute_query(
            month_query, (month_start.isoformat(),)
        )
        spent_this_month = month_result[0][0] if month_result and month_result[0][0] else 0.0

        return {
            "weekly": {
                "budget": budget_weekly,
                "spent": round(spent_this_week, 2),
                "remaining": round(budget_weekly - spent_this_week, 2)
                if budget_weekly
                else None,
                "percentage_used": round(
                    (spent_this_week / budget_weekly * 100), 1
                )
                if budget_weekly
                else None,
            },
            "monthly": {
                "budget": budget_monthly,
                "spent": round(spent_this_month, 2),
                "remaining": round(budget_monthly - spent_this_month, 2)
                if budget_monthly
                else None,
                "percentage_used": round(
                    (spent_this_month / budget_monthly * 100), 1
                )
                if budget_monthly
                else None,
            },
        }


class GetUserPreferencesTool(BaseTool):
    """Get user preferences."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "get_user_preferences"

    @property
    def description(self) -> str:
        return "Get user shopping preferences including dietary restrictions, preferred vendors, and budget"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "User preferences dictionary"

    def execute(self) -> Dict[str, Any]:
        """Get preferences."""
        query = "SELECT key, value FROM preferences"
        results = self.db_manager.execute_query(query)

        preferences = {}
        for key, value in results:
            # Try to parse JSON values
            import json

            try:
                preferences[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                preferences[key] = value

        return preferences


class ConvertUnitTool(BaseTool):
    """Convert between units."""

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "convert_unit"

    @property
    def description(self) -> str:
        return "Convert quantity between different units (e.g., gallons to liters, pounds to kg)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="quantity",
                type=ToolParameterType.NUMBER,
                description="Quantity to convert",
                required=True,
            ),
            ToolParameter(
                name="from_unit",
                type=ToolParameterType.STRING,
                description="Source unit (e.g., 'gallon', 'lb', 'oz')",
                required=True,
            ),
            ToolParameter(
                name="to_unit",
                type=ToolParameterType.STRING,
                description="Target unit (e.g., 'liter', 'kg', 'g')",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Converted quantity in target unit"

    def execute(self, quantity: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
        """Convert units."""
        # Simple conversion table
        conversions = {
            # Volume
            ("gallon", "liter"): 3.78541,
            ("liter", "gallon"): 0.264172,
            ("quart", "liter"): 0.946353,
            ("liter", "quart"): 1.05669,
            # Weight
            ("lb", "kg"): 0.453592,
            ("kg", "lb"): 2.20462,
            ("oz", "g"): 28.3495,
            ("g", "oz"): 0.035274,
            # Same unit
            ("gallon", "gallon"): 1.0,
            ("liter", "liter"): 1.0,
            ("lb", "lb"): 1.0,
            ("kg", "kg"): 1.0,
        }

        key = (from_unit.lower(), to_unit.lower())
        if key in conversions:
            converted = quantity * conversions[key]
            return {
                "original_quantity": quantity,
                "original_unit": from_unit,
                "converted_quantity": round(converted, 3),
                "converted_unit": to_unit,
            }
        else:
            return {
                "error": f"Conversion from {from_unit} to {to_unit} not supported",
                "supported_conversions": list(
                    set(f"{k[0]} -> {k[1]}" for k in conversions.keys())
                ),
            }


class LearnUserPreferenceTool(BaseTool):
    """Learn and store user dietary preferences, allergies, and product preferences."""

    def __init__(self, memory_service):
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "learn_user_preference"

    @property
    def description(self) -> str:
        return """Learn and store a user preference discovered during conversation.
        Use this when the user mentions dietary preferences (e.g., 'I prefer oat milk'),
        allergies (e.g., 'I'm allergic to peanuts'), brand preferences, or any other
        shopping-related preference. This helps P3 make better decisions in the future."""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="category",
                type=ToolParameterType.STRING,
                description="Category of preference: 'dietary', 'allergy', 'product_preference', 'brand_preference', or 'general'",
                required=True,
            ),
            ToolParameter(
                name="preference_key",
                type=ToolParameterType.STRING,
                description="Key identifying the preference (e.g., 'milk_type', 'peanut_allergy', 'organic_preference')",
                required=True,
            ),
            ToolParameter(
                name="preference_value",
                type=ToolParameterType.STRING,
                description="Value of the preference (e.g., 'oat milk', 'true', 'preferred')",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Confirmation that preference was learned or reinforced"

    def execute(
        self,
        category: str,
        preference_key: str,
        preference_value: str
    ) -> Dict[str, Any]:
        """Learn a user preference."""
        try:
            # Validate category
            valid_categories = ['dietary', 'allergy', 'product_preference', 'brand_preference', 'general']
            if category not in valid_categories:
                return {
                    "error": f"Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}",
                    "success": False
                }

            # Learn the preference
            pref_id = self.memory_service.learn_preference(
                category=category,
                preference_key=preference_key,
                preference_value=preference_value,
                source="chat",
                learned_from=None  # Can be enhanced to track conversation_id
            )

            # Get updated preference info
            prefs = self.memory_service.get_preferences(min_confidence=0.0)
            pref_info = next((p for p in prefs if p['preference_id'] == pref_id), None)

            if pref_info:
                confidence_pct = int(pref_info['confidence'] * 100)
                return {
                    "success": True,
                    "message": f"Learned: {preference_key} = {preference_value}",
                    "confidence": confidence_pct,
                    "mention_count": pref_info['mention_count'],
                    "first_time": pref_info['mention_count'] == 1
                }
            else:
                return {
                    "success": True,
                    "message": f"Learned: {preference_key} = {preference_value}"
                }

        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }


class GetLearnedPreferencesTool(BaseTool):
    """Retrieve learned user preferences from memory."""

    def __init__(self, memory_service):
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "get_learned_preferences"

    @property
    def description(self) -> str:
        return """Get all learned user preferences including dietary preferences, allergies,
        and product preferences. Use this to check what P3 knows about the user before making
        decisions about products to search for or add to cart."""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="category",
                type=ToolParameterType.STRING,
                description="Optional: filter by category ('dietary', 'allergy', 'product_preference', 'brand_preference', 'general'). Leave empty for all.",
                required=False,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Dictionary of learned user preferences"

    def execute(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get learned preferences."""
        try:
            prefs = self.memory_service.get_preferences(
                category=category,
                min_confidence=0.3
            )

            if not prefs:
                return {
                    "preferences": [],
                    "message": "No user preferences learned yet"
                }

            # Format for easy consumption
            formatted = {}
            for pref in prefs:
                key = pref['preference_key']
                if key not in formatted:
                    formatted[key] = {
                        'value': pref['preference_value'],
                        'category': pref['category'],
                        'confidence_pct': int(pref['confidence'] * 100),
                        'mentions': pref['mention_count']
                    }

            return {
                "preferences": formatted,
                "count": len(formatted),
                "message": f"Found {len(formatted)} learned preference(s)"
            }

        except Exception as e:
            return {
                "error": str(e),
                "preferences": {}
            }
