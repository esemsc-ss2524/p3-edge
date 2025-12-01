#!/usr/bin/env python3
"""
Pre-train Forecasting Models on Synthetic Temporal Data

This script generates realistic temporal consumption data spanning 2 months
and trains state space models on this data. The trained models are then
saved and can be used for forecasting on actual user inventory without
needing extensive historical data first.

Key Features:
- Generates data with proper temporal sequences (60 days in the past)
- Creates realistic consumption patterns with daily variations
- Trains one model per item category (can be applied to similar items)
- Saves trained model checkpoints for later use
- Does NOT insert data into the database (pure training data)

The pre-trained models provide a "warm start" for forecasting, allowing
the system to make reasonable predictions from day one. As actual user
data accumulates, the online learning mechanism will adapt the models
to the specific user's patterns.
"""

import sys
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import torch

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.forecasting.state_space_model import ConsumptionForecaster, extract_features
from src.forecasting.online_trainer import OnlineForecastTrainer
from src.utils import get_logger


# Synthetic item templates for training
TRAINING_ITEMS = [
    # Dairy
    {
        "name": "Dairy_Products",
        "category": "Dairy",
        "unit": "gallon",
        "base_qty": 2.0,
        "consumption_per_day": 0.28,
        "perishable": True,
        "shelf_life_days": 7,
        "household_size": 4,
    },
    # Produce
    {
        "name": "Fresh_Produce",
        "category": "Produce",
        "unit": "lb",
        "base_qty": 3.0,
        "consumption_per_day": 0.35,
        "perishable": True,
        "shelf_life_days": 5,
        "household_size": 4,
    },
    # Protein
    {
        "name": "Protein_Sources",
        "category": "Protein",
        "unit": "lb",
        "base_qty": 2.0,
        "consumption_per_day": 0.25,
        "perishable": True,
        "shelf_life_days": 10,
        "household_size": 4,
    },
    # Grains
    {
        "name": "Grains_Pasta",
        "category": "Grains",
        "unit": "lb",
        "base_qty": 3.0,
        "consumption_per_day": 0.20,
        "perishable": False,
        "shelf_life_days": 365,
        "household_size": 4,
    },
    # Beverages
    {
        "name": "Beverages",
        "category": "Beverages",
        "unit": "oz",
        "base_qty": 64.0,
        "consumption_per_day": 9.0,
        "perishable": True,
        "shelf_life_days": 7,
        "household_size": 4,
    },
]


class SyntheticTemporalDataGenerator:
    """Generates synthetic temporal consumption data for model training."""

    def __init__(self, days: int = 60, seed: int = 42):
        """
        Initialize generator.

        Args:
            days: Number of days to simulate
            seed: Random seed for reproducibility
        """
        self.days = days
        self.seed = seed
        self.logger = get_logger("synthetic_training")

        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        # Start date is 60 days in the past
        self.start_date = datetime.now() - timedelta(days=days)

    def generate_consumption_sequence(
        self,
        item_template: Dict
    ) -> List[Tuple[datetime, float]]:
        """
        Generate realistic consumption sequence with temporal variations.

        Args:
            item_template: Item configuration

        Returns:
            List of (timestamp, quantity) tuples
        """
        sequence = []
        current_qty = item_template["base_qty"]

        for day in range(self.days):
            current_date = self.start_date + timedelta(days=day)
            day_of_week = current_date.weekday()

            # Weekly restocking pattern (Saturdays)
            if day_of_week == 5:  # Saturday
                # Restock
                restock_amount = item_template["base_qty"] * random.uniform(1.5, 2.5)
                current_qty += restock_amount

            # Mid-week restock for highly perishable items
            elif day_of_week == 2 and item_template["shelf_life_days"] <= 7:
                if current_qty < item_template["base_qty"] * 0.3:
                    restock_amount = item_template["base_qty"] * 0.5
                    current_qty += restock_amount

            # Daily consumption with variations
            base_consumption = item_template["consumption_per_day"]

            # Weekend effect (30% more on Sat/Sun)
            if day_of_week >= 5:
                base_consumption *= 1.3

            # Random variation (±20%)
            consumption = base_consumption * random.uniform(0.8, 1.2)

            # Apply consumption
            current_qty = max(0, current_qty - consumption)

            # Record observation
            sequence.append((current_date, current_qty))

        return sequence

    def generate_all_sequences(self) -> Dict[str, List[Tuple[datetime, float]]]:
        """Generate sequences for all item categories."""
        self.logger.info(f"Generating {self.days} days of synthetic temporal data...")

        sequences = {}
        for template in TRAINING_ITEMS:
            sequence = self.generate_consumption_sequence(template)
            sequences[template["name"]] = sequence
            self.logger.info(
                f"  Generated {len(sequence)} observations for {template['name']}"
            )

        return sequences


class ModelPreTrainer:
    """Pre-trains forecasting models on synthetic data."""

    def __init__(self, model_dir: Path):
        """
        Initialize pre-trainer.

        Args:
            model_dir: Directory to save trained models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.logger = get_logger("model_pretrainer")
        self.trained_models: Dict[str, ConsumptionForecaster] = {}

    def train_model(
        self,
        item_name: str,
        item_template: Dict,
        sequence: List[Tuple[datetime, float]],
        n_epochs: int = 20
    ) -> ConsumptionForecaster:
        """
        Train a model on synthetic sequence using multiple epochs.

        Args:
            item_name: Item/category name
            item_template: Item configuration
            sequence: List of (timestamp, quantity) observations
            n_epochs: Number of training epochs (default 20)

        Returns:
            Trained model
        """
        self.logger.info(f"\nTraining model for: {item_name}")
        self.logger.info(f"  Observations: {len(sequence)}")
        self.logger.info(f"  Epochs: {n_epochs}")

        # Create model with lower learning rate for stability
        model = ConsumptionForecaster(
            state_dim=4,
            feature_dim=8,
            process_noise_std=0.1,
            obs_noise_std=0.05,
            learning_rate=0.01,  # Higher learning rate for faster training
        )

        # Initialize state from first observations
        initial_obs = [(qty, ts) for ts, qty in sequence[:10]]

        # Multi-epoch training loop
        best_loss = float('inf')
        epoch_losses = []

        for epoch in range(n_epochs):
            # Reinitialize state at start of each epoch
            state = model.initialize_state(sequence[0][1], initial_obs)

            epoch_loss = 0.0
            for timestamp, quantity in sequence:
                # Extract features for this timestamp
                features = extract_features(item_template, timestamp)

                # Update model (online learning with gradient descent)
                state, error = model.update(
                    state,
                    quantity,
                    features,
                    perform_learning=True
                )

                epoch_loss += error ** 2

            # Average loss for this epoch
            avg_epoch_loss = epoch_loss / len(sequence)
            epoch_losses.append(avg_epoch_loss)

            # Track best model
            if avg_epoch_loss < best_loss:
                best_loss = avg_epoch_loss

            # Log progress every 5 epochs
            if (epoch + 1) % 5 == 0 or epoch == 0:
                self.logger.info(
                    f"    Epoch {epoch + 1}/{n_epochs}: MSE={avg_epoch_loss:.4f}, "
                    f"RMSE={np.sqrt(avg_epoch_loss):.4f}"
                )

        # Final evaluation with trained model
        state = model.initialize_state(sequence[0][1], initial_obs)
        final_losses = []

        for timestamp, quantity in sequence:
            features = extract_features(item_template, timestamp)
            state, error = model.update(state, quantity, features, perform_learning=False)
            final_losses.append(error ** 2)

        final_mse = np.mean(final_losses)
        final_rmse = np.sqrt(final_mse)

        self.logger.info(f"  Training complete:")
        self.logger.info(f"    Final MSE: {final_mse:.4f}")
        self.logger.info(f"    Final RMSE: {final_rmse:.4f}")
        self.logger.info(f"    Best Epoch MSE: {best_loss:.4f}")
        self.logger.info(f"    Training steps: {model.training_steps}")

        # Save final state with model
        model.final_state = state

        return model

    def train_all_models(
        self,
        sequences: Dict[str, List[Tuple[datetime, float]]],
        n_epochs: int = 20
    ):
        """
        Train models for all categories.

        Args:
            sequences: Dictionary of category -> sequence of observations
            n_epochs: Number of training epochs per model (default 20)
        """
        self.logger.info("\n" + "=" * 70)
        self.logger.info("Training Models on Synthetic Data")
        self.logger.info("=" * 70)

        for template in TRAINING_ITEMS:
            item_name = template["name"]
            sequence = sequences[item_name]

            # Train model with multiple epochs
            model = self.train_model(item_name, template, sequence, n_epochs=n_epochs)

            # Save model
            self.save_model(item_name, model, template)

            self.trained_models[item_name] = model

        self.logger.info("\n" + "=" * 70)
        self.logger.info(f"Successfully trained {len(self.trained_models)} models")
        self.logger.info("=" * 70)

    def save_model(
        self,
        item_name: str,
        model: ConsumptionForecaster,
        template: Dict
    ):
        """Save trained model to disk."""
        # Save model checkpoint
        model_path = self.model_dir / f"pretrained_{item_name}.pt"

        # Save with additional metadata
        checkpoint_data = {
            "model_state_dict": model.state_dict(),
            "state_cov": model.state_cov,
            "final_state": model.final_state if hasattr(model, 'final_state') else None,
            "metadata": {
                **model.get_metadata(),
                "category": template["category"],
                "unit": template["unit"],
                "base_qty": template["base_qty"],
                "consumption_per_day": template["consumption_per_day"],
                "pretrained": True,
                "training_days": 60,
            }
        }

        torch.save(checkpoint_data, model_path)
        self.logger.info(f"  Saved model to: {model_path}")

    def test_forecast(self, item_name: str, template: Dict):
        """Test forecasting with trained model."""
        if item_name not in self.trained_models:
            return

        model = self.trained_models[item_name]

        # Get final state (or initialize)
        if hasattr(model, 'final_state'):
            state = model.final_state
        else:
            state = torch.zeros(model.state_dim)
            state[0] = template["base_qty"]
            state[1] = template["consumption_per_day"]

        # Generate 14-day forecast
        current_date = datetime.now()
        future_dates = [current_date + timedelta(days=i) for i in range(1, 15)]
        features_sequence = torch.stack([
            extract_features(template, date) for date in future_dates
        ])

        states, quantities, uncertainties = model.predict_trajectory(
            state,
            features_sequence,
            n_steps=14
        )

        # Predict runout
        days_until_runout, confidence = model.predict_runout_date(
            state,
            features_sequence,
            threshold=template["base_qty"] * 0.2,
            max_days=14
        )

        self.logger.info(f"\n  Test Forecast for {item_name}:")
        self.logger.info(f"    Current quantity: {state[0].item():.2f} {template['unit']}")
        self.logger.info(f"    7-day forecast: {quantities[6].item():.2f} {template['unit']}")
        self.logger.info(f"    14-day forecast: {quantities[13].item():.2f} {template['unit']}")
        if days_until_runout:
            self.logger.info(f"    Predicted runout: {days_until_runout} days (confidence: {confidence:.2f})")
        else:
            self.logger.info(f"    No runout predicted in next 14 days")


def main():
    """Main pre-training script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Pre-train forecasting models on synthetic temporal data"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=30,
        help="Number of training epochs per model (default: 30)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Number of days of synthetic data to generate (default: 60)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/pretrained",
        help="Directory to save trained models (default: models/pretrained)"
    )

    args = parser.parse_args()
    logger = get_logger("pretrain_main")

    print("=" * 70)
    print("  Forecasting Model Pre-Training")
    print("=" * 70)
    print()
    print("This script trains state space models on synthetic temporal data.")
    print("The trained models can be used for immediate forecasting without")
    print("requiring extensive historical user data.")
    print()
    print(f"Configuration:")
    print(f"  - Training epochs: {args.epochs}")
    print(f"  - Synthetic data days: {args.days}")
    print(f"  - Output directory: {args.output_dir}")
    print()

    # Generate synthetic data
    print("[1/3] Generating synthetic temporal data...")
    generator = SyntheticTemporalDataGenerator(days=args.days)
    sequences = generator.generate_all_sequences()

    # Train models
    print(f"\n[2/3] Training models ({args.epochs} epochs each)...")
    model_dir = Path(args.output_dir)
    trainer = ModelPreTrainer(model_dir)
    trainer.train_all_models(sequences, n_epochs=args.epochs)

    # Test forecasts
    print("\n[3/3] Testing forecasts...")
    for template in TRAINING_ITEMS:
        trainer.test_forecast(template["name"], template)

    print("\n" + "=" * 70)
    print("  Pre-training Complete!")
    print("=" * 70)
    print()
    print(f"Trained models saved to: {model_dir}")
    print()
    print("These models can now be used by ForecastService for immediate")
    print("forecasting. As actual user data accumulates, the models will")
    print("adapt through online learning.")
    print()
    print("To use pre-trained models:")
    print("  1. They will be automatically loaded if available")
    print("  2. Or manually trigger training via UI")
    print("  3. Models will improve with actual user data over time")
    print()
    print("Example usage:")
    print(f"  python scripts/pretrain_forecasting_models.py --epochs 50 --days 90")
    print("=" * 70)


if __name__ == "__main__":
    main()
