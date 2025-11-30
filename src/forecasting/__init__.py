"""
Forecasting Engine - State Space Models for Consumption Prediction

This module implements the forecasting engine using PyTorch-based state space models
with online learning capabilities.
"""

from src.forecasting.state_space_model import ConsumptionForecaster
from src.forecasting.online_trainer import OnlineForecastTrainer

__all__ = ["ConsumptionForecaster", "OnlineForecastTrainer"]
