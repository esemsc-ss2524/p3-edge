"""
Online Learning Trainer for Consumption Forecasting

Implements continuous model updates with new observations using:
- Incremental parameter updates
- Exponential weighted moving average for stability
- Periodic full retraining with historical data
"""

import torch
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.forecasting.state_space_model import ConsumptionForecaster, extract_features
from src.models.inventory import InventoryItem
from src.utils.logger import get_logger


class OnlineForecastTrainer:
    """
    Manages online learning for consumption forecasting models.

    Each item gets its own model instance that is continuously updated
    as new inventory observations arrive.

    Supports loading pre-trained models from models/pretrained/ for warm-start
    forecasting when no user history is available.
    """

    def __init__(
        self,
        model_dir: Path,
        ewma_alpha: float = 0.3,
        retrain_interval_days: int = 7,
        pretrained_dir: Optional[Path] = None,
    ):
        """
        Initialize the online trainer.

        Args:
            model_dir: Directory to store model checkpoints
            ewma_alpha: Exponential weighted moving average coefficient (0-1)
            retrain_interval_days: Days between full retraining
            pretrained_dir: Directory with pre-trained models (defaults to models/pretrained)
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.ewma_alpha = ewma_alpha
        self.retrain_interval_days = retrain_interval_days

        # Pre-trained models directory
        if pretrained_dir is None:
            pretrained_dir = Path("models/pretrained")
        self.pretrained_dir = Path(pretrained_dir)

        # Model registry: item_id -> (model, state, last_trained, performance)
        self.models: Dict[str, Dict[str, Any]] = {}

        self.logger = get_logger("online_trainer")

        # Log pre-trained models availability
        if self.pretrained_dir.exists():
            pretrained_count = len(list(self.pretrained_dir.glob("pretrained_*.pt")))
            if pretrained_count > 0:
                self.logger.info(
                    f"Found {pretrained_count} pre-trained models in {self.pretrained_dir}"
                )

    def _load_pretrained_model(self, category: str) -> Optional[ConsumptionForecaster]:
        """
        Load a pre-trained model for a category.

        Uses flexible matching to find the best pre-trained model.

        Args:
            category: Item category (Dairy, Produce, Protein, etc.)

        Returns:
            Pre-trained model or None if not found
        """
        if not self.pretrained_dir.exists():
            return None

        # Flexible matching - find all candidates
        candidates = list(self.pretrained_dir.glob(f"*_{category}*.pt"))
        if not candidates:
            # Fallback to broad search if exact category missing
            candidates = list(self.pretrained_dir.glob("pretrained_*.pt"))

        if not candidates:
            return None

        # Prefer exact match
        best_path = candidates[0]
        for path in candidates:
            if category.lower() in path.name.lower():
                best_path = path
                break

        try:
            checkpoint = torch.load(best_path, map_location="cpu")

            # Create model and load state
            model = ConsumptionForecaster(
                state_dim=4,
                feature_dim=8,
                process_noise_std=0.1,
                obs_noise_std=0.05,
                learning_rate=0.001,
            )
            model.load_state_dict(checkpoint["model_state_dict"])
            model.state_cov = checkpoint["state_cov"]

            self.logger.info(
                f"Loaded pre-trained model for category '{category}' from {best_path.name}"
            )
            return model

        except Exception as e:
            self.logger.error(f"Failed to load pre-trained model from {best_path}: {e}")
            return None

    def get_or_create_model(
        self,
        item_id: str,
        item_data: Dict[str, Any],
    ) -> Tuple[ConsumptionForecaster, torch.Tensor]:
        """
        Get existing model for item or create a new one.

        If no model exists, tries to load a pre-trained model for the category
        before creating a new one from scratch.

        Args:
            item_id: Unique item identifier
            item_data: Item metadata for feature extraction

        Returns:
            Tuple of (model, current_state)
        """
        if item_id in self.models:
            return self.models[item_id]["model"], self.models[item_id]["state"]

        # Try to load pre-trained model for this category
        category = item_data.get("category", "")
        model = None
        used_pretrained = False

        if category and self.pretrained_dir.exists():
            model = self._load_pretrained_model(category)
            if model:
                used_pretrained = True

        # Create new model if no pre-trained model found
        if model is None:
            model = ConsumptionForecaster(
                state_dim=4,
                feature_dim=8,
                process_noise_std=0.1,
                obs_noise_std=0.05,
                learning_rate=0.001,
            )

        # Initialize state
        current_quantity = item_data.get("quantity_current", 0.0)
        recent_observations = item_data.get("recent_observations", [])
        state = model.initialize_state(current_quantity, recent_observations)

        # Register model
        self.models[item_id] = {
            "model": model,
            "state": state,
            "last_trained": datetime.now(),
            "last_retrained": datetime.now(),
            "observations": [],
            "errors": [],
            "pretrained": used_pretrained,
            "prev_qty": current_quantity,  # Track previous quantity for restock detection
        }

        if used_pretrained:
            self.logger.info(
                f"Created model for item {item_id} using pre-trained {category} model"
            )
        else:
            self.logger.info(f"Created new model for item {item_id}")

        return model, state

    def update_model(
        self,
        item_id: str,
        observation: float,
        item_data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """
        Update model with a new observation (online learning).

        Detects if this is a consumption event (learn) or restock event (reset).
        This is CRITICAL to prevent model corruption.

        Args:
            item_id: Unique item identifier
            observation: Observed quantity
            item_data: Item metadata for feature extraction
            timestamp: Observation timestamp

        Returns:
            Dictionary with prediction error and updated metrics
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Get or create model
        model, state = self.get_or_create_model(item_id, item_data)

        # Get previous quantity for restock detection
        prev_qty = self.models[item_id].get("prev_qty", state[0].item())

        # RESTOCK DETECTION LOGIC
        # Inventory increasing = restocking event (not natural consumption)
        is_restock = observation > (prev_qty + 0.05)  # Small buffer for noise

        # Extract features
        features = extract_features(item_data, timestamp)

        if is_restock:
            # Restocking event - don't learn, just reset state
            self.logger.info(
                f"Restock detected for {item_id} ({prev_qty:.2f} -> {observation:.2f}). "
                f"Resetting state without learning."
            )
            updated_state = model.handle_restock(state, observation)
            prediction_error = 0.0
        else:
            # Normal consumption - perform learning
            updated_state, prediction_error = model.update(
                state,
                observation,
                features,
                perform_learning=True,
            )

        # Update registry
        self.models[item_id]["state"] = updated_state
        self.models[item_id]["prev_qty"] = observation  # Track for next comparison
        self.models[item_id]["last_trained"] = timestamp
        self.models[item_id]["observations"].append((observation, timestamp))

        # Only track errors for consumption events (not restocks)
        if not is_restock:
            self.models[item_id]["errors"].append(prediction_error)

        # Compute EWMA of error for tracking
        errors = self.models[item_id]["errors"]
        if len(errors) > 1:
            ewma_error = self._compute_ewma(errors)
            mae = sum(abs(e) for e in errors) / len(errors)
        else:
            ewma_error = abs(prediction_error)
            mae = abs(prediction_error)

        # Check if full retraining is needed
        days_since_retrain = (timestamp - self.models[item_id]["last_retrained"]).days
        if days_since_retrain >= self.retrain_interval_days:
            self.logger.info(f"Triggering full retraining for item {item_id}")
            self._retrain_from_scratch(item_id, item_data)

        self.logger.debug(
            f"Updated model for {item_id}: error={prediction_error:.3f}, "
            f"EWMA error={ewma_error:.3f}, MAE={mae:.3f}"
        )

        return {
            "prediction_error": prediction_error,
            "ewma_error": ewma_error,
            "mae": mae,
            "training_steps": model.training_steps,
        }

    def _compute_ewma(self, values: List[float]) -> float:
        """Compute exponential weighted moving average."""
        if not values:
            return 0.0

        ewma = values[0]
        for value in values[1:]:
            ewma = self.ewma_alpha * value + (1 - self.ewma_alpha) * ewma

        return ewma

    def _retrain_from_scratch(
        self,
        item_id: str,
        item_data: Dict[str, Any],
    ) -> None:
        """
        Retrain model from scratch using full observation history.

        This helps correct drift and incorporate long-term patterns.
        """
        if item_id not in self.models:
            return

        model_info = self.models[item_id]
        observations = model_info["observations"]

        if len(observations) < 5:
            self.logger.info(f"Insufficient data for retraining {item_id}")
            return

        # Create fresh model
        new_model = ConsumptionForecaster(
            state_dim=4,
            feature_dim=8,
            process_noise_std=0.1,
            obs_noise_std=0.05,
            learning_rate=0.001,
        )

        # Initialize state from earliest observations
        initial_quantity = observations[0][0]
        recent_obs = observations[:min(10, len(observations))]
        state = new_model.initialize_state(initial_quantity, recent_obs)

        # Train on full history
        total_loss = 0.0
        for obs_value, obs_time in observations:
            features = extract_features(item_data, obs_time)
            state, error = new_model.update(state, obs_value, features, perform_learning=True)
            total_loss += error**2

        avg_loss = total_loss / len(observations)

        # Replace old model with retrained version
        self.models[item_id]["model"] = new_model
        self.models[item_id]["state"] = state
        self.models[item_id]["last_retrained"] = datetime.now()

        self.logger.info(
            f"Retrained model for {item_id} on {len(observations)} observations. "
            f"Avg loss: {avg_loss:.4f}"
        )

    def generate_forecast(
        self,
        item_id: str,
        item_data: Dict[str, Any],
        n_days: int = 14,
        confidence: float = 0.95,
    ) -> Dict[str, Any]:
        """
        Generate forecast for an item.

        Args:
            item_id: Unique item identifier
            item_data: Item metadata
            n_days: Number of days to forecast
            confidence: Confidence level for intervals

        Returns:
            Dictionary with forecast results
        """
        model, state = self.get_or_create_model(item_id, item_data)

        # Ensure state matches current database quantity
        # (handles case where DB was updated but model state wasn't)
        current_qty = float(item_data.get("quantity_current", 0.0))
        if abs(state[0].item() - current_qty) > 0.1:
            self.logger.debug(
                f"State quantity mismatch for {item_id}: "
                f"state={state[0].item():.2f}, db={current_qty:.2f}. Resetting."
            )
            state = model.handle_restock(state, current_qty)
            self.models[item_id]["state"] = state
            self.models[item_id]["prev_qty"] = current_qty

        # Generate feature sequence for future dates
        current_date = datetime.now()
        future_dates = [current_date + timedelta(days=i) for i in range(1, n_days + 1)]
        features_sequence = torch.stack([
            extract_features(item_data, date) for date in future_dates
        ])

        # Predict trajectory
        states, quantities, uncertainties = model.predict_trajectory(
            state,
            features_sequence,
            n_steps=n_days,
        )

        # Compute confidence intervals
        lower_bound, upper_bound = model.compute_confidence_interval(
            quantities,
            uncertainties,
            confidence,
        )

        # Predict runout date
        threshold = item_data.get("quantity_min", 0.0)
        days_until_runout, runout_confidence = model.predict_runout_date(
            state,
            features_sequence,
            threshold=threshold,
            max_days=n_days,
        )

        # Prepare forecast result
        forecast = {
            "item_id": item_id,
            "forecast_date": current_date.isoformat(),
            "n_days": n_days,
            "current_quantity": state[0].item(),
            "consumption_rate": state[1].item(),
            "predictions": {
                "dates": [date.isoformat() for date in future_dates],
                "quantities": quantities.tolist(),
                "lower_bound": lower_bound.tolist(),
                "upper_bound": upper_bound.tolist(),
                "uncertainties": uncertainties.tolist(),
            },
            "runout_prediction": {
                "days_until_runout": days_until_runout,
                "predicted_date": (
                    (current_date + timedelta(days=days_until_runout)).isoformat()
                    if days_until_runout is not None else None
                ),
                "confidence": runout_confidence,
                "threshold": threshold,
            },
            "model_metadata": model.get_metadata(),
        }

        # Add performance metrics if available
        if item_id in self.models and self.models[item_id]["errors"]:
            errors = self.models[item_id]["errors"]
            forecast["performance"] = {
                "mae": sum(abs(e) for e in errors) / len(errors),
                "rmse": (sum(e**2 for e in errors) / len(errors))**0.5,
                "n_observations": len(self.models[item_id]["observations"]),
            }

        return forecast

    def save_all_models(self) -> None:
        """Save all models to disk."""
        for item_id, model_info in self.models.items():
            model_path = self.model_dir / f"{item_id}.pt"
            model_info["model"].save_checkpoint(str(model_path))

            # Save metadata separately
            metadata_path = self.model_dir / f"{item_id}_meta.json"
            metadata = {
                "last_trained": model_info["last_trained"].isoformat(),
                "last_retrained": model_info["last_retrained"].isoformat(),
                "n_observations": len(model_info["observations"]),
                "recent_errors": model_info["errors"][-10:],  # Last 10 errors
            }

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        self.logger.info(f"Saved {len(self.models)} models to {self.model_dir}")

    def load_model(self, item_id: str) -> bool:
        """
        Load a model from disk.

        Returns:
            True if model was loaded successfully
        """
        model_path = self.model_dir / f"{item_id}.pt"
        metadata_path = self.model_dir / f"{item_id}_meta.json"

        if not model_path.exists():
            return False

        try:
            # Load model
            model = ConsumptionForecaster.load_checkpoint(str(model_path))

            # Load metadata
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)

            # Initialize state (will be updated with next observation)
            state = torch.zeros(model.state_dim)

            # Register model
            self.models[item_id] = {
                "model": model,
                "state": state,
                "last_trained": datetime.fromisoformat(metadata.get(
                    "last_trained",
                    datetime.now().isoformat()
                )),
                "last_retrained": datetime.fromisoformat(metadata.get(
                    "last_retrained",
                    datetime.now().isoformat()
                )),
                "observations": [],
                "errors": metadata.get("recent_errors", []),
                "prev_qty": state[0].item(),  # Initialize previous quantity
            }

            self.logger.info(f"Loaded model for item {item_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load model for {item_id}: {e}")
            return False

    def load_all_models(self) -> int:
        """
        Load all models from disk.

        Returns:
            Number of models loaded
        """
        count = 0
        for model_file in self.model_dir.glob("*.pt"):
            item_id = model_file.stem
            if self.load_model(item_id):
                count += 1

        self.logger.info(f"Loaded {count} models from {self.model_dir}")
        return count

    def get_model_performance(self, item_id: str) -> Optional[Dict[str, float]]:
        """Get performance metrics for a model."""
        if item_id not in self.models:
            return None

        errors = self.models[item_id]["errors"]
        if not errors:
            return None

        return {
            "mae": sum(abs(e) for e in errors) / len(errors),
            "rmse": (sum(e**2 for e in errors) / len(errors))**0.5,
            "ewma_error": self._compute_ewma(errors),
            "n_observations": len(self.models[item_id]["observations"]),
        }

    def train_all_models(
        self,
        items_data: List[Dict[str, Any]],
        force_retrain: bool = False,
    ) -> Dict[str, Any]:
        """
        Train or retrain models for all items with sufficient history.

        This method can be triggered manually by the user or run on a schedule.

        Args:
            items_data: List of item data dictionaries with item_id and metadata
            force_retrain: If True, retrain even if recent training exists

        Returns:
            Dictionary with training summary
        """
        self.logger.info(f"Starting training for {len(items_data)} items...")

        results = {
            "trained": 0,
            "skipped": 0,
            "failed": 0,
            "items": [],
        }

        for item_data in items_data:
            item_id = item_data.get("item_id")
            if not item_id:
                continue

            try:
                # Check if model already exists
                if item_id in self.models and not force_retrain:
                    # Check if recent training exists
                    last_retrained = self.models[item_id]["last_retrained"]
                    days_since = (datetime.now() - last_retrained).days

                    if days_since < self.retrain_interval_days:
                        results["skipped"] += 1
                        continue

                # Get or create model (will use pre-trained if available)
                model, state = self.get_or_create_model(item_id, item_data)

                # If model has observations, retrain from scratch
                if item_id in self.models and len(self.models[item_id]["observations"]) >= 5:
                    self._retrain_from_scratch(item_id, item_data)

                results["trained"] += 1
                results["items"].append({
                    "item_id": item_id,
                    "name": item_data.get("name", "Unknown"),
                    "category": item_data.get("category", "Unknown"),
                    "pretrained": self.models[item_id].get("pretrained", False),
                })

            except Exception as e:
                self.logger.error(f"Failed to train model for {item_id}: {e}")
                results["failed"] += 1

        self.logger.info(
            f"Training complete: {results['trained']} trained, "
            f"{results['skipped']} skipped, {results['failed']} failed"
        )

        return results
