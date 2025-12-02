"""
Forecast Service - High-level interface for consumption forecasting

Integrates the forecasting engine with the database and provides
forecast generation, storage, and retrieval capabilities.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from src.database.db_manager import DatabaseManager
from src.forecasting.online_trainer import OnlineForecastTrainer
from src.models.inventory import InventoryItem, Forecast
from src.utils.logger import get_logger


class ForecastService:
    """
    Service layer for managing consumption forecasts.

    Handles:
    - Generating forecasts for inventory items
    - Updating models with new observations
    - Storing and retrieving forecast data
    - Tracking forecast accuracy
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        model_dir: Optional[Path] = None,
    ):
        """
        Initialize the forecast service.

        Args:
            db_manager: Database manager instance
            model_dir: Directory for model checkpoints
        """
        self.db_manager = db_manager
        self.logger = get_logger("forecast_service")

        # Set up model directory
        if model_dir is None:
            model_dir = Path.home() / ".p3edge" / "models"
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Initialize online trainer
        self.trainer = OnlineForecastTrainer(
            model_dir=self.model_dir,
            ewma_alpha=0.3,
            retrain_interval_days=7,
        )

        # Load existing models
        n_loaded = self.trainer.load_all_models()
        self.logger.info(f"Initialized forecast service with {n_loaded} models")

    def generate_forecast(
        self,
        item_id: str,
        n_days: int = 14,
        confidence: float = 0.95,
        save_to_db: bool = True,
    ) -> Optional[Forecast]:
        """
        Generate forecast for an item.

        Args:
            item_id: Unique item identifier
            n_days: Number of days to forecast
            confidence: Confidence level for intervals
            save_to_db: Whether to save forecast to database

        Returns:
            Forecast object or None if item not found
        """
        # Get item data from database
        item_data = self._get_item_data(item_id)
        if not item_data:
            self.logger.warning(f"Item {item_id} not found")
            return None

        # Generate forecast using trainer
        forecast_result = self.trainer.generate_forecast(
            item_id,
            item_data,
            n_days=n_days,
            confidence=confidence,
        )

        # Create Forecast model
        forecast = self._create_forecast_model(forecast_result)

        # Save to database if requested
        if save_to_db and forecast:
            self._save_forecast(forecast)

        return forecast

    def generate_forecasts_for_all_items(
        self,
        n_days: int = 14,
        save_to_db: bool = True,
    ) -> List[Forecast]:
        """
        Generate forecasts for all inventory items.

        Args:
            n_days: Number of days to forecast
            save_to_db: Whether to save forecasts to database

        Returns:
            List of Forecast objects
        """
        forecasts = []

        # Get all items
        items = self._get_all_items()
        self.logger.info(f"Generating forecasts for {len(items)} items")

        for item in items:
            forecast = self.generate_forecast(
                item.item_id,
                n_days=n_days,
                save_to_db=save_to_db,
            )
            if forecast:
                forecasts.append(forecast)

        self.logger.info(f"Generated {len(forecasts)} forecasts")
        return forecasts

    def update_with_observation(
        self,
        item_id: str,
        quantity: float,
        source: str = "manual",
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """
        Update model with a new inventory observation.

        Args:
            item_id: Unique item identifier
            quantity: Observed quantity
            source: Source of observation (manual, receipt, smart_fridge)
            timestamp: Observation timestamp

        Returns:
            Dictionary with update metrics
        """
        # Get item data
        item_data = self._get_item_data(item_id)
        if not item_data:
            self.logger.warning(f"Item {item_id} not found")
            return {}

        # Update model
        metrics = self.trainer.update_model(
            item_id,
            quantity,
            item_data,
            timestamp=timestamp,
        )

        self.logger.debug(
            f"Updated model for {item_id}: "
            f"error={metrics.get('prediction_error', 0):.3f}"
        )

        return metrics

    def get_latest_forecast(self, item_id: str) -> Optional[Forecast]:
        """Get the most recent forecast for an item."""
        query = """
            SELECT * FROM forecasts
            WHERE item_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, (item_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_forecast(row)

        return None

    def get_forecasts_for_item(
        self,
        item_id: str,
        limit: int = 10,
    ) -> List[Forecast]:
        """Get recent forecasts for an item."""
        query = """
            SELECT * FROM forecasts
            WHERE item_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """

        forecasts = []
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, (item_id, limit))
            for row in cursor.fetchall():
                forecasts.append(self._row_to_forecast(row))

        return forecasts

    def get_low_stock_predictions(
        self,
        days_ahead: int = 7,
    ) -> List[Forecast]:
        """
        Get forecasts predicting low stock within threshold days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of forecasts with predicted runout within threshold
        """
        # Get latest forecasts for all items
        query = """
            SELECT f.* FROM forecasts f
            INNER JOIN (
                SELECT item_id, MAX(created_at) as max_created
                FROM forecasts
                GROUP BY item_id
            ) latest ON f.item_id = latest.item_id
                AND f.created_at = latest.max_created
        """

        forecasts = []
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query)
            for row in cursor.fetchall():
                forecast = self._row_to_forecast(row)

                # Check if runout predicted within threshold
                if forecast.predicted_runout_date:
                    days_until = (
                        forecast.predicted_runout_date - datetime.now().date()
                    ).days
                    if 0 <= days_until <= days_ahead:
                        forecasts.append(forecast)

        return forecasts

    def get_model_performance(self, item_id: str) -> Optional[Dict[str, float]]:
        """Get performance metrics for an item's forecast model."""
        return self.trainer.get_model_performance(item_id)

    def save_all_models(self) -> None:
        """Save all models to disk."""
        self.trainer.save_all_models()
        self.logger.info("Saved all forecast models")

    def train_all_models(self, force_retrain: bool = False) -> Dict[str, Any]:
        """
        Train or retrain forecasting models for all inventory items.

        This method can be triggered manually by the user or run on a schedule.
        It will use pre-trained models as warm-start when available.

        Args:
            force_retrain: If True, retrain even if recent training exists

        Returns:
            Dictionary with training summary
        """
        self.logger.info("Starting model training for all items...")

        # Get all items data
        items_data = []
        items = self._get_all_items()

        for item in items:
            item_data = self._get_item_data(item.item_id)
            if item_data:
                items_data.append(item_data)

        # Train models
        results = self.trainer.train_all_models(items_data, force_retrain=force_retrain)

        # Save trained models
        self.save_all_models()

        self.logger.info(
            f"Model training complete: {results['trained']} trained, "
            f"{results['skipped']} skipped, {results['failed']} failed"
        )

        return results

    def update_forecast_accuracy(
        self,
        forecast_id: str,
        actual_runout_date: datetime,
    ) -> bool:
        """
        Update forecast with actual runout date for accuracy tracking.

        Args:
            forecast_id: Forecast identifier
            actual_runout_date: Actual date when item ran out

        Returns:
            True if update was successful
        """
        query = """
            UPDATE forecasts
            SET actual_runout_date = ?
            WHERE forecast_id = ?
        """

        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(query, (actual_runout_date.isoformat(), forecast_id))
                conn.commit()

            self.logger.info(
                f"Updated forecast {forecast_id} with actual runout date"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to update forecast accuracy: {e}")
            return False

    def _get_item_data(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item data from database with recent observations."""
        query = """
            SELECT * FROM inventory WHERE item_id = ?
        """

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, (item_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # Convert row to dict
            item_data = dict(row)

            # Get recent observations from history
            history_query = """
                SELECT quantity, timestamp FROM inventory_history
                WHERE item_id = ?
                ORDER BY timestamp DESC
                LIMIT 20
            """
            cursor = conn.execute(history_query, (item_id,))
            observations = [
                (row["quantity"], datetime.fromisoformat(row["timestamp"]))
                for row in cursor.fetchall()
            ]
            item_data["recent_observations"] = observations

            return item_data

    def _get_all_items(self) -> List[InventoryItem]:
        """Get all inventory items."""
        query = "SELECT * FROM inventory"

        items = []
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query)
            for row in cursor.fetchall():
                try:
                    item = InventoryItem(
                        item_id=row["item_id"],
                        name=row["name"],
                        category=row["category"],
                        brand=row["brand"],
                        unit=row["unit"],
                        quantity_current=row["quantity_current"],
                        quantity_min=row["quantity_min"],
                        quantity_max=row["quantity_max"],
                        last_updated=datetime.fromisoformat(row["last_updated"]),
                        location=row["location"],
                        perishable=bool(row["perishable"]),
                        expiry_date=row["expiry_date"],
                        consumption_rate=row["consumption_rate"],
                    )
                    items.append(item)
                except Exception as e:
                    self.logger.warning(f"Failed to parse item: {e}")

        return items

    def _create_forecast_model(
        self,
        forecast_result: Dict[str, Any],
    ) -> Optional[Forecast]:
        """Create Forecast model from trainer result."""
        try:
            runout_info = forecast_result["runout_prediction"]

            return Forecast(
                forecast_id=str(uuid.uuid4()),
                item_id=forecast_result["item_id"],
                predicted_runout_date=(
                    datetime.fromisoformat(runout_info["predicted_date"]).date()
                    if runout_info["predicted_date"] else None
                ),
                confidence=runout_info["confidence"],
                recommended_order_date=(
                    datetime.fromisoformat(runout_info["predicted_date"]).date()
                    - timedelta(days=2)  # Order 2 days before runout
                    if runout_info["predicted_date"] else None
                ),
                recommended_quantity=forecast_result.get(
                    "recommended_quantity",
                    forecast_result["current_quantity"],  # Default to current qty
                ),
                model_version=f"v{forecast_result['model_metadata']['training_steps']}",
                created_at=datetime.fromisoformat(forecast_result["forecast_date"]),
                features_used=["quantity", "consumption_rate", "trend", "seasonal"],
                actual_runout_date=None,
            )

        except Exception as e:
            self.logger.error(f"Failed to create forecast model: {e}")
            return None

    def _save_forecast(self, forecast: Forecast) -> bool:
        """Save forecast to database."""
        import json

        query = """
            INSERT INTO forecasts (
                forecast_id, item_id, predicted_runout_date, confidence,
                recommended_order_date, recommended_quantity, model_version,
                created_at, features_used, actual_runout_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(query, (
                    forecast.forecast_id,
                    forecast.item_id,
                    forecast.predicted_runout_date.isoformat() if forecast.predicted_runout_date else None,
                    forecast.confidence,
                    forecast.recommended_order_date.isoformat() if forecast.recommended_order_date else None,
                    forecast.recommended_quantity,
                    forecast.model_version,
                    forecast.created_at.isoformat(),
                    json.dumps(forecast.features_used),
                    forecast.actual_runout_date.isoformat() if forecast.actual_runout_date else None,
                ))
                conn.commit()

            return True

        except Exception as e:
            self.logger.error(f"Failed to save forecast: {e}")
            return False

    def _row_to_forecast(self, row) -> Forecast:
        """Convert database row to Forecast model."""
        import json

        return Forecast(
            forecast_id=row["forecast_id"],
            item_id=row["item_id"],
            predicted_runout_date=(
                datetime.fromisoformat(row["predicted_runout_date"]).date()
                if row["predicted_runout_date"] else None
            ),
            confidence=row["confidence"],
            recommended_order_date=(
                datetime.fromisoformat(row["recommended_order_date"]).date()
                if row["recommended_order_date"] else None
            ),
            recommended_quantity=row["recommended_quantity"],
            model_version=row["model_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
            features_used=json.loads(row["features_used"]),
            actual_runout_date=(
                datetime.fromisoformat(row["actual_runout_date"]).date()
                if row["actual_runout_date"] else None
            ),
        )
