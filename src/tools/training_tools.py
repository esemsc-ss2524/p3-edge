"""
Training tools for LLM agent.

These tools allow the agent to trigger model training and check training status.
"""

from datetime import datetime
from typing import List, Dict, Any
from .base import BaseTool
from ..models.tool_models import (
    ToolParameter,
    ToolParameterType,
    ToolCategory,
)
from ..services.training_scheduler import TrainingScheduler


class StartModelTrainingTool(BaseTool):
    """Manually trigger model retraining."""

    def __init__(self, training_scheduler: TrainingScheduler):
        self.training_scheduler = training_scheduler

    @property
    def name(self) -> str:
        return "start_model_training"

    @property
    def description(self) -> str:
        return "Trigger manual retraining of forecasting models with latest data"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.TRAINING

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "Training initiation status and timestamp"

    def execute(self) -> Dict[str, Any]:
        """Start training."""
        try:
            # Trigger training
            self.training_scheduler.trigger_training()

            return {
                "success": True,
                "message": "Model training started successfully",
                "timestamp": datetime.now().isoformat(),
                "note": "Training is running in the background. Use get_training_status to check progress.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class GetTrainingStatusTool(BaseTool):
    """Check if training is currently in progress."""

    def __init__(self, training_scheduler: TrainingScheduler):
        self.training_scheduler = training_scheduler

    @property
    def name(self) -> str:
        return "get_training_status"

    @property
    def description(self) -> str:
        return "Check if model training is currently in progress and get last training time"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.TRAINING

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "Training status with last training timestamp and schedule info"

    def execute(self) -> Dict[str, Any]:
        """Get training status."""
        is_training = self.training_scheduler.is_training()
        last_training = self.training_scheduler.last_training_time

        return {
            "is_training": is_training,
            "last_training_time": last_training.isoformat() if last_training else None,
            "scheduled_time": f"{self.training_scheduler.training_hour:02d}:{self.training_scheduler.training_minute:02d} daily",
            "scheduler_running": self.training_scheduler.scheduler.running
            if self.training_scheduler.scheduler
            else False,
        }


class GetTrainingHistoryTool(BaseTool):
    """Get recent training history from audit log."""

    def __init__(self, training_scheduler: TrainingScheduler):
        self.training_scheduler = training_scheduler

    @property
    def name(self) -> str:
        return "get_training_history"

    @property
    def description(self) -> str:
        return "Get history of recent model training runs with outcomes"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.TRAINING

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="limit",
                type=ToolParameterType.INTEGER,
                description="Number of recent training runs to retrieve (default: 10)",
                required=False,
                default=10,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of recent training runs with timestamps and outcomes"

    def execute(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get training history."""
        query = """
            SELECT timestamp, outcome, details
            FROM audit_log
            WHERE action_type = 'SYSTEM_EVENT'
              AND details LIKE '%training%'
            ORDER BY timestamp DESC
            LIMIT ?
        """
        results = self.training_scheduler.forecast_service.db_manager.execute_query(
            query, (limit,)
        )

        history = []
        for row in results:
            history.append(
                {
                    "timestamp": row[0],
                    "outcome": row[1],
                    "details": row[2],
                }
            )

        return history
