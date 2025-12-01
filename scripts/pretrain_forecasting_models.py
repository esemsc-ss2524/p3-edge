#!/usr/bin/env python3
"""
Pre-train Forecasting Models on Synthetic Temporal Data

This script generates realistic temporal consumption data and trains models.
CRITICAL LOGIC: This script separates 'natural consumption' from 'restocking events'.
The models are trained ONLY on the consumption slope, ensuring they predict run-outs
correctly rather than predicting magical restocking.

Key Features:
- Generates data with proper temporal sequences (90 days by default)
- Creates realistic consumption patterns with daily variations
- Implements threshold-based restocking (shopping days + low stock)
- Trains one model per item category
- CRITICAL: Masks restock events during training to prevent model corruption
- Saves trained model checkpoints for later use

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
import argparse

import torch

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.forecasting.state_space_model import ConsumptionForecaster, extract_features
from src.utils import get_logger


# Synthetic item templates for training
TRAINING_ITEMS = [
    {
        "name": "Dairy_Products",
        "category": "Dairy",
        "unit": "gallon",
        "base_qty": 2.0,
        "consumption_per_day": 0.28,
        "perishable": True,
        "household_size": 4,
        "restock_threshold": 0.5
    },
    {
        "name": "Fresh_Produce",
        "category": "Produce",
        "unit": "lb",
        "base_qty": 3.0,
        "consumption_per_day": 0.45,
        "perishable": True,
        "household_size": 4,
        "restock_threshold": 0.5
    },
    {
        "name": "Protein_Sources",
        "category": "Protein",
        "unit": "lb",
        "base_qty": 4.0,
        "consumption_per_day": 0.5,
        "perishable": True,
        "household_size": 4,
        "restock_threshold": 1.0
    },
    {
        "name": "Beverages",
        "category": "Beverages",
        "unit": "oz",
        "base_qty": 64.0,
        "consumption_per_day": 8.0,
        "perishable": True,
        "household_size": 4,
        "restock_threshold": 16.0
    },
    {
        "name": "Grains_Pasta",
        "category": "Grains",
        "unit": "lb",
        "base_qty": 5.0,
        "consumption_per_day": 0.15,
        "perishable": False,
        "household_size": 4,
        "restock_threshold": 1.0
    },
]


class SyntheticTemporalDataGenerator:
    """Generates realistic consumption patterns with threshold-based restocking."""

    def __init__(self, days: int = 90, seed: int = 42):
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

        # Start date is N days in the past
        self.start_date = datetime.now() - timedelta(days=days)

    def generate_consumption_sequence(
        self,
        item_template: Dict
    ) -> List[Tuple[datetime, float]]:
        """
        Generate sequence using Threshold-Based Restocking (more realistic).
        People usually buy when they run low, not just on arbitrary days.

        Args:
            item_template: Item configuration

        Returns:
            List of (timestamp, quantity) tuples
        """
        sequence = []
        current_qty = item_template["base_qty"]
        base_rate = item_template["consumption_per_day"]
        threshold = item_template.get("restock_threshold", 0.5)

        for day in range(self.days):
            current_date = self.start_date + timedelta(days=day)
            day_of_week = current_date.weekday()

            # 1. Daily consumption
            daily_factor = 1.3 if day_of_week >= 5 else 1.0  # Weekend boost
            noise = random.uniform(0.8, 1.2)
            consumption = base_rate * daily_factor * noise

            current_qty = max(0, current_qty - consumption)

            sequence.append((current_date, current_qty))

            # 2. Restock Logic (threshold-based + shopping days)
            shopping_days = [2, 5, 6]  # Wed, Sat, Sun

            is_shopping_day = day_of_week in shopping_days
            is_critical = current_qty < (threshold * 0.2)

            if (current_qty < threshold and is_shopping_day) or is_critical:
                restock_amt = item_template["base_qty"] * random.uniform(0.9, 1.1)
                current_qty = min(current_qty + restock_amt, item_template["base_qty"] * 1.5)

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
    """
    Trains models with RESTOCK MASKING.
    The most important logic is in train_model() where we ignore positive jumps.
    """

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
        n_epochs: int = 30
    ) -> ConsumptionForecaster:
        """
        Train a model on synthetic sequence with RESTOCK MASKING.

        The critical innovation: we detect restocks (upward jumps) and use
        handle_restock() instead of update(), preventing the model from
        learning to predict magical inventory increases.

        Args:
            item_name: Item/category name
            item_template: Item configuration
            sequence: List of (timestamp, quantity) observations
            n_epochs: Number of training epochs

        Returns:
            Trained model
        """
        self.logger.info(f"\nTraining model for: {item_name}")
        self.logger.info(f"  Observations: {len(sequence)}")
        self.logger.info(f"  Epochs: {n_epochs}")

        # Create model
        model = ConsumptionForecaster(
            state_dim=4,
            feature_dim=8,
            process_noise_std=0.1,
            obs_noise_std=0.05,
            learning_rate=0.001,
        )

        # Initialize state from first observations
        initial_obs = [(q, t) for t, q in sequence[:7]]

        # Multi-epoch training loop
        for epoch in range(n_epochs):
            # Reinitialize state at start of each epoch
            state = model.initialize_state(sequence[0][1], initial_obs)

            epoch_loss = 0.0
            steps = 0

            prev_qty = sequence[0][1]

            for i, (timestamp, quantity) in enumerate(sequence):
                features = extract_features(item_template, timestamp)

                # RESTOCK DETECTION
                is_restock = quantity > prev_qty + 0.1

                if is_restock:
                    # Restocking event - reset state, don't learn
                    state = model.handle_restock(state, quantity)
                else:
                    # Consumption event - learn from this
                    state, error = model.update(
                        state,
                        quantity,
                        features,
                        perform_learning=True
                    )
                    epoch_loss += error ** 2
                    steps += 1

                prev_qty = quantity

            # Log progress
            if (epoch + 1) % 10 == 0:
                avg_loss = epoch_loss / max(1, steps)
                self.logger.info(f"  Epoch {epoch+1}: MSE={avg_loss:.4f}")

        # Save final state with model
        model.final_state = state

        self.logger.info(f"  Training complete: {model.training_steps} steps")
        return model

    def save_model(self, item_name: str, model: ConsumptionForecaster, template: Dict):
        """Save trained model to disk."""
        path = self.model_dir / f"pretrained_{item_name}.pt"

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
            }
        }

        torch.save(checkpoint_data, path)
        self.logger.info(f"  Saved to {path}")

    def train_all(self, sequences: Dict[str, List[Tuple[datetime, float]]], n_epochs: int = 30):
        """Train models for all categories."""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("Training Models on Synthetic Data with Restock Masking")
        self.logger.info("=" * 70)

        for template in TRAINING_ITEMS:
            name = template["name"]
            seq = sequences[name]
            model = self.train_model(name, template, seq, n_epochs=n_epochs)
            self.save_model(name, model, template)
            self.trained_models[name] = model

            # Verify forecast
            self.verify_forecast(model, template)

        self.logger.info("\n" + "=" * 70)
        self.logger.info(f"Successfully trained {len(self.trained_models)} models")
        self.logger.info("=" * 70)

    def verify_forecast(self, model: ConsumptionForecaster, template: Dict):
        """
        Verify that the model predicts a RUNOUT (downward trend).
        If the model predicts upward trend, something is wrong.
        """
        current_qty = template["base_qty"]
        state = model.initialize_state(current_qty)

        future_dates = [datetime.now() + timedelta(days=i) for i in range(14)]
        features = torch.stack([extract_features(template, d) for d in future_dates])

        _, quantities, _ = model.predict_trajectory(state, features, n_steps=14)

        start_q = quantities[0].item()
        end_q = quantities[-1].item()

        trend_emoji = "📉 Downward" if end_q < start_q else "📈 Upward (BAD)"
        self.logger.info(
            f"  Verification {template['name']}: {start_q:.2f} -> {end_q:.2f} [{trend_emoji}]"
        )

        if end_q >= start_q:
            self.logger.warning("  WARNING: Model is not predicting consumption correctly!")


def main():
    """Main pre-training script."""
    parser = argparse.ArgumentParser(
        description="Pre-train forecasting models on synthetic temporal data with restock masking"
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
        default=90,
        help="Number of days of synthetic data to generate (default: 90)"
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
    print("  Forecasting Model Pre-Training (Corrected Logic)")
    print("=" * 70)
    print()
    print("This script trains state space models on synthetic temporal data")
    print("with RESTOCK MASKING to prevent model corruption.")
    print()
    print("The models learn ONLY from consumption events, ensuring they")
    print("predict run-outs correctly rather than magical restocking.")
    print()
    print(f"Configuration:")
    print(f"  - Training epochs: {args.epochs}")
    print(f"  - Synthetic data days: {args.days}")
    print(f"  - Output directory: {args.output_dir}")
    print()

    # Generate synthetic data
    print("[1/3] Generating synthetic temporal data...")
    gen = SyntheticTemporalDataGenerator(days=args.days)
    sequences = gen.generate_all_sequences()

    # Train models
    print(f"\n[2/3] Training models ({args.epochs} epochs each)...")
    trainer = ModelPreTrainer(Path(args.output_dir))
    trainer.train_all(sequences, n_epochs=args.epochs)

    print("\n[3/3] Verification complete!")
    print()
    print("=" * 70)
    print("  Pre-training Complete!")
    print("=" * 70)
    print()
    print(f"Trained models saved to: {args.output_dir}")
    print()
    print("Notice the 'Verification' steps showing downward trends.")
    print("The models have now learned to ignore restocking jumps.")
    print()
    print("These models can now be used by ForecastService for immediate")
    print("forecasting. As actual user data accumulates, the models will")
    print("adapt through online learning.")
    print()
    print("Example usage:")
    print(f"  python scripts/pretrain_forecasting_models.py --epochs 50 --days 120")
    print("=" * 70)


if __name__ == "__main__":
    main()
