"""
Proactive Assistant Service

Provides intelligent suggestions and alerts based on inventory state,
forecasts, and user preferences.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..database.db_manager import DatabaseManager
from ..utils import get_logger


@dataclass
class Suggestion:
    """A proactive suggestion."""
    priority: str  # "high", "medium", "low"
    category: str  # "low_stock", "expiring", "forecast", "budget"
    message: str
    actionable: bool  # Whether user can take action
    action_hint: Optional[str] = None  # Suggested action


class ProactiveAssistant:
    """Service for generating proactive suggestions and alerts."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize proactive assistant.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.logger = get_logger("proactive_assistant")

    def get_suggestions(self) -> List[Suggestion]:
        """
        Get all proactive suggestions based on current state.

        Returns:
            List of suggestions ordered by priority
        """
        suggestions = []

        # Check low stock items
        suggestions.extend(self._check_low_stock())

        # Check expiring items
        suggestions.extend(self._check_expiring_items())

        # Check forecasts
        suggestions.extend(self._check_forecasts())

        # Check budget status
        suggestions.extend(self._check_budget())

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))

        return suggestions

    def _check_low_stock(self) -> List[Suggestion]:
        """Check for low stock items."""
        suggestions = []

        try:
            query = """
                SELECT name, quantity_current, quantity_min, unit
                FROM inventory
                WHERE quantity_current <= quantity_min
                ORDER BY (quantity_current / quantity_min) ASC
            """
            rows = self.db_manager.execute_query(query)

            for row in rows:
                name = row['name']
                current = row['quantity_current']
                min_qty = row['quantity_min']
                unit = row['unit']

                if current < min_qty * 0.5:
                    # Critical low stock
                    priority = "high"
                    message = f"⚠️ Critical: {name} is very low ({current} {unit}, minimum {min_qty} {unit})"
                else:
                    priority = "medium"
                    message = f"⚡ Low stock: {name} ({current} {unit}, minimum {min_qty} {unit})"

                suggestions.append(Suggestion(
                    priority=priority,
                    category="low_stock",
                    message=message,
                    actionable=True,
                    action_hint=f"Search for '{name}' and add to cart"
                ))

        except Exception as e:
            self.logger.error(f"Error checking low stock: {e}")

        return suggestions

    def _check_expiring_items(self) -> List[Suggestion]:
        """Check for items expiring soon."""
        suggestions = []

        try:
            cutoff_date = (datetime.now() + timedelta(days=3)).isoformat()

            query = """
                SELECT name, expiry_date, quantity_current, unit
                FROM inventory
                WHERE expiry_date IS NOT NULL
                  AND expiry_date <= ?
                  AND expiry_date > ?
                ORDER BY expiry_date ASC
            """
            rows = self.db_manager.execute_query(
                query,
                (cutoff_date, datetime.now().isoformat())
            )

            for row in rows:
                name = row['name']
                expiry = datetime.fromisoformat(row['expiry_date'])
                days_left = (expiry - datetime.now()).days
                quantity = row['quantity_current']
                unit = row['unit']

                if days_left <= 1:
                    priority = "high"
                    message = f"🔴 Expiring soon: {name} expires in {days_left} day(s) ({quantity} {unit} remaining)"
                else:
                    priority = "medium"
                    message = f"🟡 Expiring: {name} expires in {days_left} days ({quantity} {unit} remaining)"

                suggestions.append(Suggestion(
                    priority=priority,
                    category="expiring",
                    message=message,
                    actionable=True,
                    action_hint=f"Use {name} soon or plan meals around it"
                ))

        except Exception as e:
            self.logger.error(f"Error checking expiring items: {e}")

        return suggestions

    def _check_forecasts(self) -> List[Suggestion]:
        """Check forecasts for upcoming runouts."""
        suggestions = []

        try:
            # Get forecasts for next 7 days
            cutoff_date = (datetime.now() + timedelta(days=7)).date().isoformat()

            query = """
                SELECT i.name, f.predicted_runout_date, f.confidence,
                       f.recommended_order_date, f.recommended_quantity
                FROM forecasts f
                JOIN inventory i ON f.item_id = i.item_id
                WHERE f.predicted_runout_date <= ?
                  AND f.predicted_runout_date > ?
                ORDER BY f.predicted_runout_date ASC
            """
            rows = self.db_manager.execute_query(
                query,
                (cutoff_date, datetime.now().date().isoformat())
            )

            for row in rows:
                name = row['name']
                runout = datetime.fromisoformat(row['predicted_runout_date'])
                days_until_runout = (runout - datetime.now()).days
                confidence = row['confidence']

                if days_until_runout <= 2:
                    priority = "high"
                    message = f"📉 Running out soon: {name} will run out in ~{days_until_runout} days (confidence: {confidence:.0%})"
                else:
                    priority = "medium"
                    message = f"📊 Forecast: {name} predicted to run out in {days_until_runout} days (confidence: {confidence:.0%})"

                suggestions.append(Suggestion(
                    priority=priority,
                    category="forecast",
                    message=message,
                    actionable=True,
                    action_hint=f"Order {name} soon"
                ))

        except Exception as e:
            self.logger.error(f"Error checking forecasts: {e}")

        return suggestions

    def _check_budget(self) -> List[Suggestion]:
        """Check budget status and spending."""
        suggestions = []

        try:
            # Get preferences
            prefs = self.db_manager.get_preferences()
            weekly_cap = prefs.get("spend_cap_weekly")
            monthly_cap = prefs.get("spend_cap_monthly")

            if not weekly_cap and not monthly_cap:
                return suggestions

            # Calculate current spending
            week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).date()
            month_start = datetime.now().replace(day=1).date()

            # Weekly spending
            if weekly_cap:
                week_query = """
                    SELECT SUM(total_cost) as total FROM orders
                    WHERE created_at >= ?
                      AND status IN ('PLACED', 'DELIVERED', 'APPROVED')
                """
                week_result = self.db_manager.execute_query(
                    week_query,
                    (week_start.isoformat(),)
                )
                weekly_spent = week_result[0][0] if week_result and week_result[0][0] else 0.0

                weekly_remaining = weekly_cap - weekly_spent
                weekly_pct = (weekly_spent / weekly_cap * 100) if weekly_cap > 0 else 0

                if weekly_pct >= 90:
                    priority = "high"
                    message = f"💰 Budget Alert: {weekly_pct:.0f}% of weekly budget used (${weekly_spent:.2f} / ${weekly_cap:.2f})"
                elif weekly_pct >= 75:
                    priority = "medium"
                    message = f"💵 Budget: {weekly_pct:.0f}% of weekly budget used (${weekly_remaining:.2f} remaining)"
                elif weekly_pct >= 50:
                    priority = "low"
                    message = f"ℹ️ Budget: ${weekly_remaining:.2f} remaining this week"

                if weekly_pct >= 50:
                    suggestions.append(Suggestion(
                        priority=priority,
                        category="budget",
                        message=message,
                        actionable=True,
                        action_hint="Consider prioritizing essential items" if weekly_pct >= 75 else None
                    ))

            # Monthly spending
            if monthly_cap:
                month_query = """
                    SELECT SUM(total_cost) as total FROM orders
                    WHERE created_at >= ?
                      AND status IN ('PLACED', 'DELIVERED', 'APPROVED')
                """
                month_result = self.db_manager.execute_query(
                    month_query,
                    (month_start.isoformat(),)
                )
                monthly_spent = month_result[0][0] if month_result and month_result[0][0] else 0.0

                monthly_remaining = monthly_cap - monthly_spent
                monthly_pct = (monthly_spent / monthly_cap * 100) if monthly_cap > 0 else 0

                if monthly_pct >= 90:
                    priority = "high"
                    message = f"💰 Budget Alert: {monthly_pct:.0f}% of monthly budget used (${monthly_spent:.2f} / ${monthly_cap:.2f})"
                elif monthly_pct >= 75:
                    priority = "medium"
                    message = f"💵 Budget: {monthly_pct:.0f}% of monthly budget used (${monthly_remaining:.2f} remaining)"

                if monthly_pct >= 75:
                    suggestions.append(Suggestion(
                        priority=priority,
                        category="budget",
                        message=message,
                        actionable=True,
                        action_hint="Monitor spending carefully" if monthly_pct >= 90 else None
                    ))

        except Exception as e:
            self.logger.error(f"Error checking budget: {e}")

        return suggestions

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current state.

        Returns:
            Dictionary with summary statistics
        """
        suggestions = self.get_suggestions()

        high_priority = [s for s in suggestions if s.priority == "high"]
        medium_priority = [s for s in suggestions if s.priority == "medium"]
        low_priority = [s for s in suggestions if s.priority == "low"]

        return {
            "total_suggestions": len(suggestions),
            "high_priority": len(high_priority),
            "medium_priority": len(medium_priority),
            "low_priority": len(low_priority),
            "categories": {
                "low_stock": len([s for s in suggestions if s.category == "low_stock"]),
                "expiring": len([s for s in suggestions if s.category == "expiring"]),
                "forecast": len([s for s in suggestions if s.category == "forecast"]),
                "budget": len([s for s in suggestions if s.category == "budget"]),
            },
            "top_suggestions": [s.message for s in suggestions[:5]]
        }
