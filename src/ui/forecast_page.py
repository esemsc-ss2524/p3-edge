"""
Forecast Page - Visualization and management of consumption forecasts

Displays forecasts with:
- Predicted runout dates
- Confidence intervals
- Visual charts with trajectories
- Low stock alerts
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QDialog, QMessageBox, QComboBox,
    QGroupBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Optional, List
from datetime import datetime, timedelta

from src.services.forecast_service import ForecastService
from src.models.inventory import Forecast
from src.utils.logger import get_logger


class ForecastPage(QWidget):
    """Page for viewing and managing inventory forecasts."""

    forecast_updated = pyqtSignal()

    def __init__(self, forecast_service: Optional[ForecastService] = None):
        super().__init__()
        self.forecast_service = forecast_service
        self.logger = get_logger("forecast_page")

        self.forecasts: List[Forecast] = []

        self._init_ui()
        self.refresh_forecasts()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Consumption Forecasts")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Buttons
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_forecasts)
        header_layout.addWidget(self.refresh_btn)

        self.train_models_btn = QPushButton("Train Models")
        self.train_models_btn.clicked.connect(self._on_train_models)
        self.train_models_btn.setToolTip(
            "Train forecasting models on historical data. "
            "Uses pre-trained models when available."
        )
        header_layout.addWidget(self.train_models_btn)

        self.generate_all_btn = QPushButton("Generate All Forecasts")
        self.generate_all_btn.clicked.connect(self._on_generate_all)
        header_layout.addWidget(self.generate_all_btn)

        layout.addLayout(header_layout)

        # Stats bar
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(self.stats_label)

        # Low stock alerts
        self.alerts_group = QGroupBox("Low Stock Alerts (Next 3 Days)")
        alerts_layout = QVBoxLayout()
        self.alerts_label = QLabel("No alerts")
        alerts_layout.addWidget(self.alerts_label)
        self.alerts_group.setLayout(alerts_layout)
        layout.addWidget(self.alerts_group)

        # Forecast table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Item Name",
            "Current Qty",
            "Consumption Rate",
            "Predicted Runout",
            "Days Until Runout",
            "Confidence",
            "Order Date",
            "Actions"
        ])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 8):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def refresh_forecasts(self):
        """Refresh the forecast table."""
        if not self.forecast_service:
            return

        try:
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
            with self.forecast_service.db_manager.get_connection() as conn:
                cursor = conn.execute(query)
                for row in cursor.fetchall():
                    forecast = self.forecast_service._row_to_forecast(row)
                    forecasts.append(forecast)

            self.forecasts = forecasts
            self._populate_table()
            self._update_stats()
            self._update_alerts()

            self.logger.info(f"Refreshed {len(forecasts)} forecasts")

        except Exception as e:
            self.logger.error(f"Failed to refresh forecasts: {e}")
            QMessageBox.warning(self, "Error", f"Failed to refresh forecasts: {e}")

    def _populate_table(self):
        """Populate the forecast table."""
        self.table.setRowCount(len(self.forecasts))

        for row, forecast in enumerate(self.forecasts):
            # Get item name
            item_name = self._get_item_name(forecast.item_id)

            # Get current quantity
            item_data = self.forecast_service._get_item_data(forecast.item_id)
            current_qty = item_data.get("quantity_current", 0) if item_data else 0

            # Get consumption rate from model state (not in inventory table)
            consumption_rate = None
            if forecast.item_id in self.forecast_service.trainer.models:
                state = self.forecast_service.trainer.models[forecast.item_id]["state"]
                consumption_rate = state[1].item()  # consumption_rate is state[1]

            # Item name
            self.table.setItem(row, 0, QTableWidgetItem(item_name))

            # Current quantity
            qty_item = QTableWidgetItem(f"{current_qty:.1f}")
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, qty_item)

            # Consumption rate
            if consumption_rate is not None:
                rate_item = QTableWidgetItem(f"{consumption_rate:.2f}/day")
            else:
                rate_item = QTableWidgetItem("N/A")
            rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, rate_item)

            # Predicted runout date
            if forecast.predicted_runout_date:
                runout_item = QTableWidgetItem(
                    forecast.predicted_runout_date.strftime("%Y-%m-%d")
                )
                runout_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Color code based on urgency
                days_until = (forecast.predicted_runout_date - datetime.now().date()).days
                if days_until <= 2:
                    runout_item.setBackground(QColor(255, 200, 200))  # Red
                elif days_until <= 3:
                    runout_item.setBackground(QColor(255, 255, 200))  # Yellow
            else:
                runout_item = QTableWidgetItem("N/A")
                runout_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 3, runout_item)

            # Days until runout
            if forecast.predicted_runout_date:
                days_until = (forecast.predicted_runout_date - datetime.now().date()).days
                days_item = QTableWidgetItem(str(days_until))
                days_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                days_item = QTableWidgetItem("N/A")
                days_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 4, days_item)

            # Confidence
            if forecast.confidence is not None:
                confidence_pct = forecast.confidence * 100
                conf_item = QTableWidgetItem(f"{confidence_pct:.1f}%")
                conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Color code confidence
                if confidence_pct >= 75:
                    conf_item.setBackground(QColor(200, 255, 200))  # Green
                elif confidence_pct >= 50:
                    conf_item.setBackground(QColor(255, 255, 200))  # Yellow
                else:
                    conf_item.setBackground(QColor(255, 200, 200))  # Red
            else:
                conf_item = QTableWidgetItem("N/A")
                conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 5, conf_item)

            # Recommended order date
            if forecast.recommended_order_date:
                order_item = QTableWidgetItem(
                    forecast.recommended_order_date.strftime("%Y-%m-%d")
                )
            else:
                order_item = QTableWidgetItem("N/A")
            order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, order_item)

            # Actions button
            view_chart_btn = QPushButton("View Chart")
            view_chart_btn.clicked.connect(
                lambda checked, fid=forecast.item_id: self._on_view_chart(fid)
            )
            self.table.setCellWidget(row, 7, view_chart_btn)

    def _update_stats(self):
        """Update statistics display."""
        if not self.forecasts:
            self.stats_label.setText("No forecasts available")
            return

        total = len(self.forecasts)
        runout_soon = sum(
            1 for f in self.forecasts
            if f.predicted_runout_date and
            (f.predicted_runout_date - datetime.now().date()).days <= 3
        )
        high_confidence = sum(
            1 for f in self.forecasts
            if f.confidence >= 0.8
        )

        self.stats_label.setText(
            f"Total Forecasts: {total} | "
            f"Low Stock (Next 3 Days): {runout_soon} | "
            f"High Confidence (≥75%): {high_confidence}"
        )

    def _update_alerts(self):
        """Update low stock alerts."""
        if not self.forecast_service:
            return

        alerts = self.forecast_service.get_low_stock_predictions(days_ahead=3)

        if not alerts:
            self.alerts_label.setText("No low stock alerts")
            self.alerts_label.setStyleSheet("color: green;")
            return

        # Build alert message
        alert_messages = []
        for forecast in sorted(alerts, key=lambda f: f.predicted_runout_date or datetime.max.date()):
            item_name = self._get_item_name(forecast.item_id)
            days_until = (forecast.predicted_runout_date - datetime.now().date()).days

            # Handle None confidence
            conf_str = f"{forecast.confidence*100:.0f}%" if forecast.confidence is not None else "N/A"

            alert_messages.append(
                f"⚠️ {item_name}: Running out in {days_until} days "
                f"(Confidence: {conf_str})"
            )

        self.alerts_label.setText("\n".join(alert_messages))
        self.alerts_label.setStyleSheet("color: red; font-weight: bold;")

    def _get_item_name(self, item_id: str) -> str:
        """Get item name from database."""
        if not self.forecast_service:
            return "Unknown"

        query = "SELECT name FROM inventory WHERE item_id = ?"
        with self.forecast_service.db_manager.get_connection() as conn:
            cursor = conn.execute(query, (item_id,))
            row = cursor.fetchone()
            return row["name"] if row else "Unknown"

    def _on_train_models(self):
        """Train forecasting models on historical data."""
        if not self.forecast_service:
            return

        reply = QMessageBox.question(
            self,
            "Train Models",
            "Train forecasting models on historical data?\n\n"
            "This will:\n"
            "• Use pre-trained models as starting point when available\n"
            "• Train on your actual usage history\n"
            "• Improve forecast accuracy over time\n\n"
            "This may take a few moments.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Disable button during training
                self.train_models_btn.setEnabled(False)
                self.train_models_btn.setText("Training...")

                # Train models
                results = self.forecast_service.train_all_models(force_retrain=False)

                # Re-enable button
                self.train_models_btn.setEnabled(True)
                self.train_models_btn.setText("Train Models")

                # Show results
                message = (
                    f"Training Complete!\n\n"
                    f"• Trained: {results['trained']} models\n"
                    f"• Skipped: {results['skipped']} (recently trained)\n"
                    f"• Failed: {results['failed']}\n"
                )

                if results["items"]:
                    pretrained_count = sum(
                        1 for item in results["items"] if item.get("pretrained", False)
                    )
                    if pretrained_count > 0:
                        message += f"\n✓ {pretrained_count} models used pre-trained weights"

                QMessageBox.information(self, "Training Complete", message)

            except Exception as e:
                self.logger.error(f"Failed to train models: {e}")
                self.train_models_btn.setEnabled(True)
                self.train_models_btn.setText("Train Models")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to train models: {e}",
                )

    def _on_generate_all(self):
        """Generate forecasts for all items."""
        if not self.forecast_service:
            return

        reply = QMessageBox.question(
            self,
            "Generate Forecasts",
            "Generate forecasts for all inventory items? This may take a few moments.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                forecasts = self.forecast_service.generate_forecasts_for_all_items(
                    n_days=14,
                    save_to_db=True,
                )

                QMessageBox.information(
                    self,
                    "Success",
                    f"Generated {len(forecasts)} forecasts successfully!",
                )

                self.refresh_forecasts()
                self.forecast_updated.emit()

            except Exception as e:
                self.logger.error(f"Failed to generate forecasts: {e}")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to generate forecasts: {e}",
                )

    def _on_view_chart(self, item_id: str):
        """View forecast chart for an item."""
        dialog = ForecastChartDialog(item_id, self.forecast_service, self)
        dialog.exec()


class ForecastChartDialog(QDialog):
    """Dialog to display forecast chart for an item."""

    def __init__(
        self,
        item_id: str,
        forecast_service: ForecastService,
        parent=None,
    ):
        super().__init__(parent)
        self.item_id = item_id
        self.forecast_service = forecast_service
        self.logger = get_logger("forecast_chart")

        self.setWindowTitle("Forecast Chart")
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._generate_chart()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Header
        item_name = self._get_item_name()
        title_label = QLabel(f"Forecast for: {item_name}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Chart display (we'll use a label to show the rendered chart)
        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.chart_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        # Controls
        controls_layout = QHBoxLayout()

        # Days selector
        controls_layout.addWidget(QLabel("Forecast Days:"))
        self.days_combo = QComboBox()
        self.days_combo.addItems(["7", "14", "30", "60"])
        self.days_combo.setCurrentText("14")
        self.days_combo.currentTextChanged.connect(self._generate_chart)
        controls_layout.addWidget(self.days_combo)

        controls_layout.addStretch()

        # Regenerate button
        regen_btn = QPushButton("Regenerate Forecast")
        regen_btn.clicked.connect(self._on_regenerate)
        controls_layout.addWidget(regen_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        controls_layout.addWidget(close_btn)

        layout.addLayout(controls_layout)

    def _get_item_name(self) -> str:
        """Get item name from database."""
        query = "SELECT name FROM inventory WHERE item_id = ?"
        with self.forecast_service.db_manager.get_connection() as conn:
            cursor = conn.execute(query, (self.item_id,))
            row = cursor.fetchone()
            return row["name"] if row else "Unknown Item"

    def _generate_chart(self):
        """Generate and display forecast chart."""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            import io
            from PyQt6.QtGui import QPixmap

            # Get forecast data
            n_days = int(self.days_combo.currentText())
            item_data = self.forecast_service._get_item_data(self.item_id)

            if not item_data:
                self.chart_label.setText("No data available for this item")
                return

            # Generate forecast
            forecast_result = self.forecast_service.trainer.generate_forecast(
                self.item_id,
                item_data,
                n_days=n_days,
                confidence=0.95,
            )

            predictions = forecast_result["predictions"]
            dates_str = predictions["dates"]
            quantities = predictions["quantities"]
            lower_bound = predictions["lower_bound"]
            upper_bound = predictions["upper_bound"]

            # Convert dates
            from datetime import datetime
            dates = [datetime.fromisoformat(d).date() for d in dates_str]
            days = list(range(len(dates)))

            # Create figure
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)

            # Plot forecast
            ax.plot(days, quantities, 'b-', linewidth=2, label='Predicted Quantity')
            ax.fill_between(
                days,
                lower_bound,
                upper_bound,
                alpha=0.3,
                label='95% Confidence Interval'
            )

            # Plot current quantity
            current_qty = forecast_result["current_quantity"]
            ax.axhline(y=current_qty, color='g', linestyle='--', label='Current Quantity')

            # Plot min threshold
            min_qty = item_data.get("quantity_min", 0)
            ax.axhline(y=min_qty, color='r', linestyle='--', label='Min Threshold')

            # Plot runout prediction
            runout_info = forecast_result["runout_prediction"]
            if runout_info["days_until_runout"] is not None:
                runout_day = runout_info["days_until_runout"] - 1
                if runout_day < len(quantities):
                    ax.plot(
                        runout_day,
                        quantities[runout_day],
                        'ro',
                        markersize=10,
                        label=f'Predicted Runout (Day {runout_day+1})'
                    )

            # Formatting
            ax.set_xlabel('Days from Now')
            ax.set_ylabel('Quantity')
            ax.set_title(f'Consumption Forecast: {self._get_item_name()}')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)

            # Set x-axis labels to show dates every few days
            step = max(1, n_days // 7)
            ax.set_xticks(days[::step])
            ax.set_xticklabels([dates[i].strftime('%m/%d') for i in range(0, len(dates), step)])

            fig.tight_layout()

            # Convert to pixmap and display
            canvas = FigureCanvasQTAgg(fig)
            canvas.draw()

            # Get the RGBA buffer from the figure
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100)
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.chart_label.setPixmap(pixmap)

            plt.close(fig)

        except Exception as e:
            self.logger.error(f"Failed to generate chart: {e}")
            self.chart_label.setText(f"Error generating chart: {e}")

    def _on_regenerate(self):
        """Regenerate forecast for this item."""
        try:
            n_days = int(self.days_combo.currentText())
            forecast = self.forecast_service.generate_forecast(
                self.item_id,
                n_days=n_days,
                save_to_db=True,
            )

            if forecast:
                QMessageBox.information(
                    self,
                    "Success",
                    "Forecast regenerated successfully!",
                )
                self._generate_chart()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to generate forecast",
                )

        except Exception as e:
            self.logger.error(f"Failed to regenerate forecast: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to regenerate forecast: {e}",
            )
