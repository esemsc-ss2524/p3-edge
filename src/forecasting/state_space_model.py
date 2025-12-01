"""
State Space Model for Consumption Forecasting

Implements a linear Gaussian state space model with online learning capabilities.
The model tracks consumption patterns and predicts future inventory levels.

State: [quantity, consumption_rate, trend, seasonal_component]
"""

import torch
import torch.nn as nn
from typing import Tuple, Optional, Dict, Any
import numpy as np
from datetime import datetime, timedelta


class ConsumptionForecaster(nn.Module):
    """
    PyTorch-based state space model for predicting item consumption.

    Uses a linear Gaussian state space formulation with:
    - State transition dynamics
    - Kalman filter for online updates
    - Confidence interval estimation
    """

    def __init__(
        self,
        state_dim: int = 4,
        feature_dim: int = 8,
        process_noise_std: float = 0.1,
        obs_noise_std: float = 0.05,
        learning_rate: float = 0.001,
    ):
        """
        Initialize the consumption forecaster.

        Args:
            state_dim: Dimension of the state vector (default: 4)
                - 0: quantity
                - 1: consumption_rate (units/day)
                - 2: trend (acceleration of consumption)
                - 3: seasonal_component
            feature_dim: Dimension of feature vector (external factors)
            process_noise_std: Standard deviation of process noise
            obs_noise_std: Standard deviation of observation noise
            learning_rate: Learning rate for parameter updates
        """
        super().__init__()

        self.state_dim = state_dim
        self.feature_dim = feature_dim

        # State transition matrix (learns temporal dynamics)
        self.transition = nn.Linear(state_dim + feature_dim, state_dim, bias=True)

        # Observation matrix (maps state to quantity)
        self.observation = nn.Linear(state_dim, 1, bias=False)

        # Initialize observation matrix to focus on quantity component
        with torch.no_grad():
            self.observation.weight.fill_(0.0)
            self.observation.weight[0, 0] = 1.0  # Direct quantity mapping

        # Noise parameters (learnable)
        self.process_noise = nn.Parameter(torch.tensor(process_noise_std))
        self.obs_noise = nn.Parameter(torch.tensor(obs_noise_std))

        # State covariance (uncertainty in state estimate)
        self.state_cov = torch.eye(state_dim) * 0.1

        # Optimizer for online learning
        self.optimizer = torch.optim.Adam(self.parameters(), lr=learning_rate)

        # Metadata
        self.training_steps = 0
        self.last_loss = None

    def forward(
        self,
        state: torch.Tensor,
        features: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict next state and observation.

        Args:
            state: Current state vector [state_dim]
            features: External features [feature_dim]

        Returns:
            Tuple of (next_state, predicted_quantity)
        """
        if features is None:
            features = torch.zeros(self.feature_dim)

        # Combine state and features
        state_features = torch.cat([state, features], dim=0)

        # Predict next state (deterministic mean)
        next_state_mean = self.transition(state_features)
        next_state = next_state_mean

        # Predict observation (quantity)
        predicted_quantity = self.observation(next_state)

        return next_state, predicted_quantity

    def predict_trajectory(
        self,
        initial_state: torch.Tensor,
        features_sequence: Optional[torch.Tensor] = None,
        n_steps: int = 7,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Predict future trajectory over multiple time steps.

        Args:
            initial_state: Starting state vector [state_dim]
            features_sequence: Feature sequence [n_steps, feature_dim]
            n_steps: Number of future steps to predict

        Returns:
            Tuple of:
                - states: Predicted states [n_steps, state_dim]
                - quantities: Predicted quantities [n_steps]
                - uncertainties: Standard deviations [n_steps]
        """
        states = []
        quantities = []
        uncertainties = []

        current_state = initial_state.clone()
        current_cov = self.state_cov.clone()

        for step in range(n_steps):
            # Get features for this step
            if features_sequence is not None and step < len(features_sequence):
                features = features_sequence[step]
            else:
                features = torch.zeros(self.feature_dim)

            # Predict next state (mean)
            state_features = torch.cat([current_state, features], dim=0)
            next_state_mean = self.transition(state_features)

            # Physics constraint: quantity should not increase naturally (no magic restocking)
            if next_state_mean[0] > current_state[0]:
                next_state_mean[0] = current_state[0] - max(0.01, current_state[1])

            # Predict quantity
            predicted_quantity = self.observation(next_state_mean)

            # Compute uncertainty (from covariance)
            # Simplified: use trace of covariance as overall uncertainty
            uncertainty = torch.sqrt(torch.trace(current_cov) / self.state_dim)

            # Store predictions
            states.append(next_state_mean)
            quantities.append(predicted_quantity.item())
            uncertainties.append(uncertainty.item())

            # Update state and covariance for next iteration
            current_state = next_state_mean

            # Propagate covariance (simplified linear propagation)
            # In full Kalman filter: P_k+1 = F * P_k * F^T + Q
            current_cov = current_cov + torch.eye(self.state_dim) * self.process_noise**2

        return (
            torch.stack(states),
            torch.tensor(quantities),
            torch.tensor(uncertainties),
        )

    def update(
        self,
        state: torch.Tensor,
        observation: float,
        features: Optional[torch.Tensor] = None,
        perform_learning: bool = True,
    ) -> Tuple[torch.Tensor, float]:
        """
        Update state estimate using Kalman filter and optionally update parameters.

        Args:
            state: Current state estimate [state_dim]
            observation: Observed quantity (ground truth)
            features: External features [feature_dim]
            perform_learning: Whether to update model parameters

        Returns:
            Tuple of (updated_state, prediction_error)
        """
        if features is None:
            features = torch.zeros(self.feature_dim)

        # Prediction step
        state_features = torch.cat([state, features], dim=0)
        predicted_state = self.transition(state_features)
        predicted_quantity = self.observation(predicted_state)

        # Compute prediction error
        prediction_error = observation - predicted_quantity.item()

        # Kalman gain (simplified version)
        # K = P * H^T / (H * P * H^T + R)
        obs_matrix = self.observation.weight.squeeze()  # [state_dim]

        # Innovation covariance
        innovation_cov = (
            torch.dot(obs_matrix, torch.matmul(self.state_cov, obs_matrix))
            + self.obs_noise**2
        )

        # Kalman gain
        kalman_gain = torch.matmul(self.state_cov, obs_matrix) / innovation_cov

        # Update state estimate
        updated_state = predicted_state + kalman_gain * prediction_error

        # Update covariance (Joseph form for numerical stability)
        # P = (I - K*H) * P
        identity = torch.eye(self.state_dim)
        cov_update = identity - torch.outer(kalman_gain, obs_matrix)
        self.state_cov = torch.matmul(cov_update, self.state_cov)

        # Parameter learning (gradient descent on prediction error)
        if perform_learning and prediction_error**2 > 1e-6:
            self.optimizer.zero_grad()

            # Compute loss (mean squared error)
            loss = (predicted_quantity - observation)**2
            loss.backward()

            # Clip gradients for stability
            torch.nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)

            self.optimizer.step()

            self.last_loss = loss.item()
            self.training_steps += 1

        return updated_state.detach(), prediction_error

    def handle_restock(self, state: torch.Tensor, new_quantity: float) -> torch.Tensor:
        """
        Handle restocking event by resetting quantity but keeping consumption dynamics.

        This prevents model corruption when inventory increases (not natural consumption).

        Args:
            state: Current state vector
            new_quantity: New quantity after restocking

        Returns:
            Updated state vector with new quantity
        """
        new_state = state.clone()
        new_state[0] = new_quantity  # Update quantity
        # Keep consumption_rate, trend, and seasonal components
        # Reset covariance to moderate uncertainty
        self.state_cov = torch.eye(self.state_dim) * 0.1
        return new_state

    def initialize_state(
        self,
        current_quantity: float,
        recent_observations: Optional[list] = None,
    ) -> torch.Tensor:
        """
        Initialize state vector from current inventory data.

        Args:
            current_quantity: Current inventory quantity
            recent_observations: Recent quantity observations for rate estimation
                               List of (quantity, timestamp) or (quantity,) tuples

        Returns:
            Initial state vector [state_dim]
        """
        state = torch.zeros(self.state_dim)

        # Set current quantity
        state[0] = current_quantity

        # Estimate consumption rate from recent observations
        if recent_observations and len(recent_observations) >= 2:
            # Sort observations by timestamp if available
            sorted_obs = sorted(recent_observations, key=lambda x: x[1] if len(x) > 1 else 0)
            quantities = [obs[0] for obs in sorted_obs]

            # Calculate only consumption drops (ignore restocks)
            drops = []
            for i in range(len(quantities) - 1):
                diff = quantities[i] - quantities[i + 1]
                if diff > 0:  # Only count decreases (consumption)
                    drops.append(diff)

            # Average consumption rate
            if drops:
                avg_rate = np.mean(drops)
                state[1] = avg_rate
            else:
                # No clear consumption pattern, use default
                state[1] = 0.1 * max(1.0, current_quantity)

            # Estimate trend from drops if enough data
            if len(drops) >= 2:
                trend = drops[-1] - drops[0]
                state[2] = trend / len(drops)
        else:
            # Default: assume moderate consumption rate
            state[1] = 0.1 * max(1.0, current_quantity)

        # Seasonal component (initialized to zero, learned over time)
        state[3] = 0.0

        return state

    def compute_confidence_interval(
        self,
        predictions: torch.Tensor,
        uncertainties: torch.Tensor,
        confidence: float = 0.95,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute confidence intervals for predictions.

        Args:
            predictions: Predicted quantities [n_steps]
            uncertainties: Uncertainty estimates (std) [n_steps]
            confidence: Confidence level (e.g., 0.95 for 95%)

        Returns:
            Tuple of (lower_bound, upper_bound) [n_steps]
        """
        # Z-score for desired confidence level
        from scipy.stats import norm
        z_score = norm.ppf((1 + confidence) / 2)

        lower_bound = predictions - z_score * uncertainties
        upper_bound = predictions + z_score * uncertainties

        # Ensure non-negative quantities
        lower_bound = torch.clamp(lower_bound, min=0.0)

        return lower_bound, upper_bound

    def predict_runout_date(
        self,
        initial_state: torch.Tensor,
        features_sequence: Optional[torch.Tensor] = None,
        threshold: float = 0.0,
        max_days: int = 60,
    ) -> Tuple[Optional[int], float]:
        """
        Predict when inventory will run out (reach threshold).

        Args:
            initial_state: Starting state vector
            features_sequence: Future feature sequence
            threshold: Quantity threshold for "runout" (default: 0.0)
            max_days: Maximum days to predict

        Returns:
            Tuple of (days_until_runout, confidence)
                days_until_runout is None if no runout predicted
        """
        states, quantities, uncertainties = self.predict_trajectory(
            initial_state,
            features_sequence,
            n_steps=max_days,
        )

        # Find first day where quantity drops below threshold
        for day, qty in enumerate(quantities):
            if qty <= threshold:
                # Confidence inversely related to uncertainty
                confidence = 1.0 / (1.0 + uncertainties[day])
                return day + 1, confidence

        # No runout predicted within max_days
        return None, 0.0

    def get_metadata(self) -> Dict[str, Any]:
        """Get model metadata for logging/versioning."""
        return {
            "state_dim": self.state_dim,
            "feature_dim": self.feature_dim,
            "training_steps": self.training_steps,
            "last_loss": self.last_loss,
            "process_noise": self.process_noise.item(),
            "obs_noise": self.obs_noise.item(),
        }

    def save_checkpoint(self, path: str) -> None:
        """Save model checkpoint."""
        torch.save({
            "model_state_dict": self.state_dict(),
            "state_cov": self.state_cov,
            "metadata": self.get_metadata(),
        }, path)

    @classmethod
    def load_checkpoint(cls, path: str) -> "ConsumptionForecaster":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location="cpu")

        # Create model with saved metadata
        metadata = checkpoint["metadata"]
        model = cls(
            state_dim=metadata["state_dim"],
            feature_dim=metadata["feature_dim"],
        )

        # Load state dict
        model.load_state_dict(checkpoint["model_state_dict"])
        model.state_cov = checkpoint["state_cov"]
        model.training_steps = metadata["training_steps"]
        model.last_loss = metadata.get("last_loss")

        return model


def extract_features(
    item_data: Dict[str, Any],
    current_date: Optional[datetime] = None,
) -> torch.Tensor:
    """
    Extract feature vector from item data.

    Args:
        item_data: Dictionary with item information
        current_date: Current date for temporal features

    Returns:
        Feature vector [feature_dim=8]
    """
    features = torch.zeros(8)

    if current_date is None:
        current_date = datetime.now()

    # Feature 0: Day of week (normalized 0-1)
    features[0] = current_date.weekday() / 6.0

    # Feature 1: Day of month (normalized 0-1)
    features[1] = current_date.day / 31.0

    # Feature 2: Month of year (normalized 0-1)
    features[2] = current_date.month / 12.0

    # Feature 3: Is weekend (binary)
    features[3] = 1.0 if current_date.weekday() >= 5 else 0.0

    # Feature 4: Household size (if provided)
    household_size = item_data.get("household_size", 2)
    features[4] = household_size / 10.0  # Normalize assuming max 10

    # Feature 5: Perishable indicator
    features[5] = 1.0 if item_data.get("perishable", False) else 0.0

    # Feature 6: Days until expiry (if perishable)
    features[6] = 0.5  # Default middle value
    if item_data.get("expiry_date"):
        try:
            exp_val = item_data["expiry_date"]
            # Handle both string and date types
            if isinstance(exp_val, str):
                expiry = datetime.fromisoformat(exp_val)
            else:
                # Assume it's a date object, convert to datetime
                from datetime import date
                if isinstance(exp_val, date):
                    expiry = datetime.combine(exp_val, datetime.min.time())
                else:
                    expiry = exp_val

            days_until_expiry = (expiry - current_date).days
            features[6] = max(0.0, min(1.0, days_until_expiry / 30.0))
        except Exception:
            pass

    # Feature 7: Reserved for future use (e.g., holiday indicator)
    features[7] = 0.0

    return features
