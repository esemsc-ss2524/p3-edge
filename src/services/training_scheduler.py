"""
Training Scheduler Service

Schedules automatic model training at 2 AM daily to minimize disruption
during peak usage hours. Uses APScheduler for reliable scheduling.
"""

from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.services.forecast_service import ForecastService
from src.models import ActionType, Actor
from src.utils import get_logger, get_audit_logger


class TrainingScheduler:
    """
    Manages scheduled automatic training of forecasting models.

    Runs training at 2 AM daily when system usage is typically lowest.
    """

    def __init__(
        self,
        forecast_service: ForecastService,
        db_manager,
        training_hour: int = 2,
        training_minute: int = 0,
    ):
        """
        Initialize the training scheduler.

        Args:
            forecast_service: Forecast service for model training
            db_manager: Database manager for audit logging
            training_hour: Hour to run training (0-23, default 2 AM)
            training_minute: Minute to run training (0-59, default 0)
        """
        self.forecast_service = forecast_service
        self.db_manager = db_manager
        self.training_hour = training_hour
        self.training_minute = training_minute

        self.logger = get_logger("training_scheduler")
        self.audit_logger = get_audit_logger(db_manager)

        # Create scheduler
        self.scheduler = BackgroundScheduler(
            timezone="UTC",
            daemon=True,  # Daemon thread won't prevent app shutdown
        )

        self.running = False

    def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            self.logger.warning("Scheduler already running")
            return

        try:
            # Add daily training job
            self.scheduler.add_job(
                func=self._run_scheduled_training,
                trigger=CronTrigger(
                    hour=self.training_hour,
                    minute=self.training_minute,
                ),
                id="daily_model_training",
                name="Daily Model Training",
                replace_existing=True,
            )

            # Start scheduler
            self.scheduler.start()
            self.running = True

            self.logger.info(
                f"Training scheduler started. Models will train daily at "
                f"{self.training_hour:02d}:{self.training_minute:02d}"
            )

            # Log to audit
            self.audit_logger.log_action(
                action_type=ActionType.SYSTEM_STARTUP.value,
                actor=Actor.SYSTEM.value,
                details={
                    "component": "training_scheduler",
                    "schedule": f"{self.training_hour:02d}:{self.training_minute:02d}",
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            return

        try:
            self.scheduler.shutdown(wait=True)
            self.running = False

            self.logger.info("Training scheduler stopped")

            # Log to audit
            self.audit_logger.log_action(
                action_type=ActionType.SYSTEM_SHUTDOWN.value,
                actor=Actor.SYSTEM.value,
                details={"component": "training_scheduler"},
            )

        except Exception as e:
            self.logger.error(f"Failed to stop scheduler: {e}")

    def _run_scheduled_training(self) -> None:
        """
        Run scheduled model training.

        This is called automatically by the scheduler at the configured time.
        """
        self.logger.info("Starting scheduled model training...")

        start_time = datetime.now()

        try:
            # Train all models
            results = self.forecast_service.train_all_models(force_retrain=False)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.logger.info(
                f"Scheduled training complete in {duration:.1f}s: "
                f"{results['trained']} trained, {results['skipped']} skipped, "
                f"{results['failed']} failed"
            )

            # Log to audit
            self.audit_logger.log_action(
                action_type="MODEL_TRAINING",
                actor=Actor.SYSTEM.value,
                details={
                    "trigger": "scheduled",
                    "trained": results["trained"],
                    "skipped": results["skipped"],
                    "failed": results["failed"],
                    "duration_seconds": duration,
                },
            )

        except Exception as e:
            self.logger.error(f"Scheduled training failed: {e}")

            # Log error to audit
            self.audit_logger.log_action(
                action_type="MODEL_TRAINING",
                actor=Actor.SYSTEM.value,
                details={
                    "trigger": "scheduled",
                    "error": str(e),
                    "status": "failed",
                },
            )

    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get the next scheduled run time.

        Returns:
            Next run time or None if scheduler not running
        """
        if not self.running:
            return None

        job = self.scheduler.get_job("daily_model_training")
        if job:
            return job.next_run_time

        return None

    def trigger_manual_training(self) -> None:
        """
        Trigger immediate training outside of schedule.

        This can be used for manual training requests.
        """
        self.logger.info("Manual training triggered")

        try:
            results = self.forecast_service.train_all_models(force_retrain=True)

            self.logger.info(
                f"Manual training complete: {results['trained']} trained, "
                f"{results['skipped']} skipped, {results['failed']} failed"
            )

            # Log to audit
            self.audit_logger.log_action(
                action_type="MODEL_TRAINING",
                actor=Actor.USER.value,
                details={
                    "trigger": "manual",
                    "trained": results["trained"],
                    "skipped": results["skipped"],
                    "failed": results["failed"],
                },
            )

            return results

        except Exception as e:
            self.logger.error(f"Manual training failed: {e}")
            raise
