"""
Forecasting tools for LLM agent.

These tools enable the agent to generate forecasts, analyze consumption
patterns, and predict when items will run out.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseTool
from ..models.tool_models import (
    ToolParameter,
    ToolParameterType,
    ToolCategory,
)
from ..services.forecast_service import ForecastService


class GenerateForecastTool(BaseTool):
    """Generate fresh forecast for an item."""

    def __init__(self, forecast_service: ForecastService):
        self.forecast_service = forecast_service

    @property
    def name(self) -> str:
        return "generate_forecast"

    @property
    def description(self) -> str:
        return "Generate a fresh runout forecast for a specific inventory item"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FORECASTING

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="item_name",
                type=ToolParameterType.STRING,
                description="Name of the item to forecast (e.g., 'milk', 'eggs')",
                required=True,
            ),
            ToolParameter(
                name="days_ahead",
                type=ToolParameterType.INTEGER,
                description="Number of days to forecast ahead (default: 14)",
                required=False,
                default=14,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Forecast with predicted runout date, confidence, and recommended order date"

    def execute(
        self, item_name: str, days_ahead: int = 14
    ) -> Dict[str, Any]:
        """Generate forecast."""
        # Find item ID by name
        query = "SELECT item_id, name FROM inventory WHERE LOWER(name) LIKE LOWER(?) LIMIT 1"
        results = self.forecast_service.db_manager.execute_query(
            query, (f"%{item_name}%",)
        )

        if not results:
            return {"error": f"Item '{item_name}' not found in inventory"}

        item_id, name = results[0]

        # Generate forecast
        forecast = self.forecast_service.generate_forecast(
            item_id=item_id, n_days=days_ahead
        )

        if not forecast:
            return {"error": f"Failed to generate forecast for '{name}'"}

        return {
            "item_name": name,
            "forecast_id": forecast.forecast_id,
            "predicted_runout_date": forecast.predicted_runout_date.isoformat()
            if forecast.predicted_runout_date
            else None,
            "confidence": forecast.confidence,
            "recommended_order_date": forecast.recommended_order_date.isoformat()
            if forecast.recommended_order_date
            else None,
            "recommended_quantity": forecast.recommended_quantity,
            "model_version": forecast.model_version,
            "features_used": forecast.features_used,
        }


class GetLowStockPredictionsTool(BaseTool):
    """Get items predicted to run out soon."""

    def __init__(self, forecast_service: ForecastService):
        self.forecast_service = forecast_service

    @property
    def name(self) -> str:
        return "get_low_stock_predictions"

    @property
    def description(self) -> str:
        return "Get items predicted to run out within specified days, based on forecasts"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FORECASTING

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="days",
                type=ToolParameterType.INTEGER,
                description="Number of days to check ahead (default: 7)",
                required=False,
                default=7,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of items predicted to run out soon with confidence scores"

    def execute(
        self, days: int = 3
    ) -> List[Dict[str, Any]]:
        """Get predictions."""
        predictions = self.forecast_service.get_low_stock_predictions(
            days_ahead=days
        )

        results = []
        for forecast in predictions:
            # Get item name
            query = "SELECT name FROM inventory WHERE item_id = ?"
            name_result = self.forecast_service.db_manager.execute_query(
                query, (forecast.item_id,)
            )
            item_name = name_result[0][0] if name_result else "Unknown"

            results.append(
                {
                    "item_name": item_name,
                    "predicted_runout_date": forecast.predicted_runout_date.isoformat()
                    if forecast.predicted_runout_date
                    else None,
                    "days_until_runout": (
                        forecast.predicted_runout_date - datetime.now().date()
                    ).days
                    if forecast.predicted_runout_date
                    else None,
                    "confidence": forecast.confidence,
                    "recommended_order_date": forecast.recommended_order_date.isoformat()
                    if forecast.recommended_order_date
                    else None,
                    "recommended_quantity": forecast.recommended_quantity,
                }
            )

        return results


class AnalyzeUsageTrendsTool(BaseTool):
    """Analyze historical usage trends for an item."""

    def __init__(self, forecast_service: ForecastService):
        self.forecast_service = forecast_service

    @property
    def name(self) -> str:
        return "analyze_usage_trends"

    @property
    def description(self) -> str:
        return "Analyze historical usage patterns and consumption trends for an item"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FORECASTING

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="item_name",
                type=ToolParameterType.STRING,
                description="Name of the item to analyze",
                required=True,
            ),
            ToolParameter(
                name="days_back",
                type=ToolParameterType.INTEGER,
                description="Number of days of history to analyze (default: 30)",
                required=False,
                default=30,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Usage statistics including average consumption, trends, and patterns"

    def execute(
        self, item_name: str, days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze trends."""
        # Find item
        query = "SELECT item_id, name, consumption_rate FROM inventory WHERE LOWER(name) LIKE LOWER(?) LIMIT 1"
        results = self.forecast_service.db_manager.execute_query(
            query, (f"%{item_name}%",)
        )

        if not results:
            return {"error": f"Item '{item_name}' not found in inventory"}

        item_id, name, consumption_rate = results[0]

        # Get history
        history_query = """
            SELECT timestamp, quantity, source
            FROM inventory_history
            WHERE item_id = ?
              AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """
        history = self.forecast_service.db_manager.execute_query(
            history_query, (item_id, days_back)
        )

        if not history:
            return {
                "item_name": name,
                "error": "No historical data available for analysis",
            }

        # Analyze history
        data_points = len(history)
        quantities = [row[1] for row in history]

        # Calculate statistics
        avg_quantity = sum(quantities) / len(quantities) if quantities else 0
        max_quantity = max(quantities) if quantities else 0
        min_quantity = min(quantities) if quantities else 0

        # Detect trend (simple linear)
        if len(quantities) >= 2:
            # Compare first half to second half
            mid = len(quantities) // 2
            first_half_avg = sum(quantities[:mid]) / mid
            second_half_avg = sum(quantities[mid:]) / (len(quantities) - mid)
            trend = "increasing" if second_half_avg > first_half_avg else "decreasing"
        else:
            trend = "insufficient_data"

        return {
            "item_name": name,
            "days_analyzed": days_back,
            "data_points": data_points,
            "current_consumption_rate": consumption_rate,
            "statistics": {
                "average_quantity": round(avg_quantity, 2),
                "max_quantity": max_quantity,
                "min_quantity": min_quantity,
            },
            "trend": trend,
            "history_available": data_points > 0,
        }


class GetModelPerformanceTool(BaseTool):
    """Get forecasting model performance metrics."""

    def __init__(self, forecast_service: ForecastService):
        self.forecast_service = forecast_service

    @property
    def name(self) -> str:
        return "get_model_performance"

    @property
    def description(self) -> str:
        return "Get performance metrics for the forecasting models"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FORECASTING

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "Model performance metrics including accuracy, MAE, and RMSE"

    def execute(self) -> Dict[str, Any]:
        """Get performance metrics."""
        query = """
            SELECT model_type, version, accuracy, mae, rmse,
                   training_date, training_samples
            FROM model_metadata
            ORDER BY training_date DESC
            LIMIT 10
        """
        results = self.forecast_service.db_manager.execute_query(query)

        models = []
        for row in results:
            model = {
                "model_type": row[0],
                "version": row[1],
                "accuracy": row[2],
                "mae": row[3],
                "rmse": row[4],
                "training_date": row[5],
                "training_samples": row[6],
            }
            models.append(model)

        if not models:
            return {"message": "No model performance data available yet"}

        return {"models": models, "total_models": len(models)}


class CheckModelHealthTool(BaseTool):
    """Check health status of forecasting models."""

    def __init__(self, forecast_service: ForecastService):
        self.forecast_service = forecast_service

    @property
    def name(self) -> str:
        return "check_model_health"

    @property
    def description(self) -> str:
        return "Check if forecasting models need retraining based on age and performance"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FORECASTING

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "Model health status with recommendations for retraining if needed"

    def execute(self) -> Dict[str, Any]:
        """Check model health."""
        try:
            # Get model metadata
            query = """
                SELECT model_id, model_type, version, trained_at,
                       performance_metrics, active
                FROM model_metadata
                WHERE active = 1
                ORDER BY trained_at DESC
                LIMIT 10
            """
            results = self.forecast_service.db_manager.execute_query(query)

            if not results:
                return {
                    "status": "unhealthy",
                    "message": "No active models found",
                    "recommendation": "Train initial models using start_model_training tool"
                }

            import json
            from datetime import datetime, timedelta

            issues = []
            models_info = []

            for row in results:
                model_id = row['model_id']
                model_type = row['model_type']
                version = row['version']
                trained_at = datetime.fromisoformat(row['trained_at'])
                metrics_json = row['performance_metrics']

                # Parse metrics
                try:
                    metrics = json.loads(metrics_json) if metrics_json else {}
                except:
                    metrics = {}

                # Check age
                age_days = (datetime.now() - trained_at).days
                is_stale = age_days > 7

                # Check performance (MAE threshold)
                mae = metrics.get('mae', 0)
                is_inaccurate = mae > 0.5  # High error

                model_info = {
                    "model_type": model_type,
                    "version": version,
                    "age_days": age_days,
                    "trained_at": trained_at.isoformat(),
                    "mae": mae,
                    "is_stale": is_stale,
                    "is_inaccurate": is_inaccurate
                }
                models_info.append(model_info)

                # Collect issues
                if is_stale:
                    issues.append(f"{model_type} model is {age_days} days old (last trained: {trained_at.date()})")
                if is_inaccurate:
                    issues.append(f"{model_type} model has high error (MAE: {mae:.2f})")

            # Overall health status
            if not issues:
                status = "healthy"
                recommendation = "Models are performing well and up-to-date"
            else:
                status = "needs_attention"
                recommendation = "Consider retraining models using start_model_training tool"

            return {
                "status": status,
                "models": models_info,
                "issues": issues,
                "issue_count": len(issues),
                "recommendation": recommendation
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking model health: {str(e)}",
                "recommendation": "Check database and model metadata"
            }
