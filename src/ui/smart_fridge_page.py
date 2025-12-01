"""
Smart Fridge Connection Page

UI for connecting and managing Samsung Family Hub smart refrigerator integration.
Shows connection status, device info, and real-time inventory sync.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QTextEdit, QMessageBox, QProgressBar,
    QLineEdit, QSpinBox
)

from src.services.smart_fridge_service import SmartFridgeService, SmartFridgeConnectionError
from src.database.db_manager import DatabaseManager
from src.utils import get_logger


class SmartFridgeConnectionWidget(QWidget):
    """Widget for managing smart fridge connection."""

    connection_changed = pyqtSignal(bool)  # Signal: connected status
    inventory_synced = pyqtSignal(dict)  # Signal: sync stats

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)

        self.db_manager = db_manager
        self.logger = get_logger("smart_fridge_ui")

        # Smart fridge service (will be initialized on connect)
        self.fridge_service: Optional[SmartFridgeService] = None

        # UI components
        self.status_label: Optional[QLabel] = None
        self.device_label: Optional[QLabel] = None
        self.last_sync_label: Optional[QLabel] = None
        self.connect_btn: Optional[QPushButton] = None
        self.sync_btn: Optional[QPushButton] = None
        self.polling_btn: Optional[QPushButton] = None
        self.url_input: Optional[QLineEdit] = None
        self.poll_interval_input: Optional[QSpinBox] = None
        self.log_text: Optional[QTextEdit] = None
        self.status_indicator: Optional[QWidget] = None

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_status)
        self.refresh_timer.setInterval(2000)  # 2 seconds

        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Smart Refrigerator Connection")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Connection Settings
        settings_group = QGroupBox("Connection Settings")
        settings_layout = QFormLayout()

        self.url_input = QLineEdit("http://localhost:5001")
        self.url_input.setPlaceholderText("Smart fridge URL")
        settings_layout.addRow("Fridge URL:", self.url_input)

        self.poll_interval_input = QSpinBox()
        self.poll_interval_input.setMinimum(5)
        self.poll_interval_input.setMaximum(300)
        self.poll_interval_input.setValue(30)
        self.poll_interval_input.setSuffix(" seconds")
        settings_layout.addRow("Poll Interval:", self.poll_interval_input)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Connection Status
        status_group = QGroupBox("Device Status")
        status_layout = QFormLayout()

        # Status indicator
        status_row = QHBoxLayout()
        self.status_indicator = QWidget()
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setStyleSheet("background-color: #dc3545; border-radius: 8px;")  # Red (disconnected)
        status_row.addWidget(self.status_indicator)

        self.status_label = QLabel("Disconnected")
        status_row.addWidget(self.status_label)
        status_row.addStretch()

        status_widget = QWidget()
        status_widget.setLayout(status_row)
        status_layout.addRow("Status:", status_widget)

        self.device_label = QLabel("No device connected")
        status_layout.addRow("Device:", self.device_label)

        self.last_sync_label = QLabel("Never")
        status_layout.addRow("Last Sync:", self.last_sync_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Actions
        actions_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        actions_layout.addWidget(self.connect_btn)

        self.sync_btn = QPushButton("Sync Now")
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        self.sync_btn.setEnabled(False)
        actions_layout.addWidget(self.sync_btn)

        self.polling_btn = QPushButton("Start Auto-Sync")
        self.polling_btn.clicked.connect(self._on_polling_clicked)
        self.polling_btn.setEnabled(False)
        actions_layout.addWidget(self.polling_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Activity Log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_log_btn)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()

    def _log(self, message: str):
        """Add message to activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_connect_clicked(self):
        """Handle connect/disconnect button click."""
        if self.fridge_service and self.fridge_service.connected:
            # Disconnect
            self._disconnect()
        else:
            # Connect
            self._connect()

    def _connect(self):
        """Connect to smart fridge."""
        fridge_url = self.url_input.text().strip()
        poll_interval = self.poll_interval_input.value()

        if not fridge_url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid fridge URL")
            return

        self._log(f"Connecting to {fridge_url}...")

        try:
            # Create service
            self.fridge_service = SmartFridgeService(
                self.db_manager,
                fridge_url=fridge_url,
                poll_interval_seconds=poll_interval,
            )

            # Set up callbacks
            self.fridge_service.on_connection_change = self._on_connection_changed
            self.fridge_service.on_inventory_update = self._on_inventory_updated

            # Attempt connection
            if self.fridge_service.connect():
                self._log("✓ Connected successfully")
                self._update_ui_for_connected()

                # Initial sync
                self._log("Performing initial sync...")
                stats = self.fridge_service.sync_inventory()
                self._log(
                    f"✓ Initial sync complete: {stats['added']} added, "
                    f"{stats['updated']} updated"
                )

                # Emit signal
                self.connection_changed.emit(True)

            else:
                self._log("✗ Connection failed")
                QMessageBox.critical(
                    self,
                    "Connection Failed",
                    f"Could not connect to smart fridge at {fridge_url}\n\n"
                    "Please ensure:\n"
                    "1. The smart fridge simulator is running\n"
                    "2. The URL is correct\n"
                    "3. No firewall is blocking the connection"
                )

        except Exception as e:
            self._log(f"✗ Error: {e}")
            self.logger.error(f"Connection error: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while connecting:\n{str(e)}"
            )

    def _disconnect(self):
        """Disconnect from smart fridge."""
        if not self.fridge_service:
            return

        self._log("Disconnecting...")
        self.fridge_service.disconnect()
        self._log("✓ Disconnected")

        self._update_ui_for_disconnected()
        self.connection_changed.emit(False)

    def _on_sync_clicked(self):
        """Handle manual sync button click."""
        if not self.fridge_service or not self.fridge_service.connected:
            return

        self._log("Starting manual sync...")
        self.sync_btn.setEnabled(False)

        try:
            stats = self.fridge_service.sync_inventory()
            self._log(
                f"✓ Sync complete: {stats['added']} added, {stats['updated']} updated, "
                f"{stats['unchanged']} unchanged"
            )

            # Emit signal
            self.inventory_synced.emit(stats)

            # Update last sync time
            info = self.fridge_service.get_connection_info()
            self._update_last_sync_label(info.get("last_sync"))

        except SmartFridgeConnectionError as e:
            self._log(f"✗ Sync failed: {e}")
            QMessageBox.warning(self, "Sync Failed", str(e))

        finally:
            self.sync_btn.setEnabled(True)

    def _on_polling_clicked(self):
        """Handle start/stop auto-sync button click."""
        if not self.fridge_service:
            return

        if self.fridge_service._polling:
            # Stop polling
            self.fridge_service.stop_polling()
            self._log("✓ Auto-sync stopped")
            self.polling_btn.setText("Start Auto-Sync")
        else:
            # Start polling
            if self.fridge_service.start_polling():
                self._log(
                    f"✓ Auto-sync started (every {self.poll_interval_input.value()}s)"
                )
                self.polling_btn.setText("Stop Auto-Sync")
                self.refresh_timer.start()  # Start UI refresh
            else:
                self._log("✗ Failed to start auto-sync")

    def _on_connection_changed(self, connected: bool):
        """Callback when connection status changes."""
        if connected:
            self._log("✓ Connection established")
            self._update_ui_for_connected()
        else:
            self._log("✗ Connection lost")
            self._update_ui_for_disconnected()

    def _on_inventory_updated(self, item_id: str, item_data: dict):
        """Callback when inventory item is updated."""
        self._log(
            f"↻ Updated: {item_data['name']} → {item_data['quantity']} {item_data['unit']}"
        )

    def _update_ui_for_connected(self):
        """Update UI for connected state."""
        if not self.fridge_service:
            return

        info = self.fridge_service.get_connection_info()

        # Update status
        self.status_label.setText("Connected")
        self.status_indicator.setStyleSheet("background-color: #28a745; border-radius: 8px;")  # Green

        # Update device info
        device_name = info.get("device_name", "Unknown Device")
        device_id = info.get("device_id", "")[:8]  # Show first 8 chars
        self.device_label.setText(f"{device_name} ({device_id}...)")

        # Update last sync
        self._update_last_sync_label(info.get("last_sync"))

        # Enable buttons
        self.connect_btn.setText("Disconnect")
        self.sync_btn.setEnabled(True)
        self.polling_btn.setEnabled(True)

        # Disable settings
        self.url_input.setEnabled(False)
        self.poll_interval_input.setEnabled(False)

    def _update_ui_for_disconnected(self):
        """Update UI for disconnected state."""
        # Update status
        self.status_label.setText("Disconnected")
        self.status_indicator.setStyleSheet("background-color: #dc3545; border-radius: 8px;")  # Red

        # Clear device info
        self.device_label.setText("No device connected")
        self.last_sync_label.setText("Never")

        # Update buttons
        self.connect_btn.setText("Connect")
        self.sync_btn.setEnabled(False)
        self.polling_btn.setEnabled(False)
        self.polling_btn.setText("Start Auto-Sync")

        # Enable settings
        self.url_input.setEnabled(True)
        self.poll_interval_input.setEnabled(True)

        # Stop refresh timer
        self.refresh_timer.stop()

    def _update_last_sync_label(self, last_sync_iso: Optional[str]):
        """Update last sync label."""
        if not last_sync_iso:
            self.last_sync_label.setText("Never")
            return

        try:
            last_sync = datetime.fromisoformat(last_sync_iso)
            time_ago = datetime.now() - last_sync
            seconds = int(time_ago.total_seconds())

            if seconds < 60:
                time_str = f"{seconds} seconds ago"
            elif seconds < 3600:
                minutes = seconds // 60
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = seconds // 3600
                time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"

            self.last_sync_label.setText(time_str)

        except Exception:
            self.last_sync_label.setText(last_sync_iso)

    def _refresh_status(self):
        """Refresh status display (called by timer)."""
        if self.fridge_service and self.fridge_service.connected:
            info = self.fridge_service.get_connection_info()
            self._update_last_sync_label(info.get("last_sync"))

    def closeEvent(self, event):
        """Handle widget close."""
        self.refresh_timer.stop()

        if self.fridge_service and self.fridge_service.connected:
            self.fridge_service.stop_polling()
            # Don't disconnect on close - keep connection alive

        event.accept()


class SmartFridgePage(QWidget):
    """Full page for smart fridge management."""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)

        self.db_manager = db_manager
        self.logger = get_logger("smart_fridge_page")

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Connection widget
        self.connection_widget = SmartFridgeConnectionWidget(self.db_manager)
        layout.addWidget(self.connection_widget)

        # Info section
        info_group = QGroupBox("About Smart Refrigerator Integration")
        info_layout = QVBoxLayout()

        info_text = QLabel(
            "This feature connects to a Samsung Family Hub smart refrigerator "
            "to automatically track your inventory.\n\n"
            "Features:\n"
            "• Real-time inventory tracking using AI Vision Inside\n"
            "• Automatic sync when items are added or removed\n"
            "• Temperature and door sensor monitoring\n"
            "• Integration with forecasting and shopping lists\n\n"
            "Note: For testing, you can run the smart fridge simulator included "
            "with this application."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        simulator_btn = QPushButton("How to Run Simulator")
        simulator_btn.clicked.connect(self._show_simulator_help)
        info_layout.addWidget(simulator_btn)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

    def _show_simulator_help(self):
        """Show help dialog for running simulator."""
        help_text = """
<h3>Running the Smart Fridge Simulator</h3>

<p>To test the smart refrigerator integration, run the simulator:</p>

<pre>
cd /home/user/p3-edge
python src/ingestion/samsung_fridge_simulator.py
</pre>

<p>The simulator will start a REST API server on port 5001.</p>

<p><b>API Endpoints:</b></p>
<ul>
<li>Device Status: http://localhost:5001/api/devices/{device_id}/status</li>
<li>Inventory: http://localhost:5001/api/inventory</li>
<li>Health Check: http://localhost:5001/api/health</li>
</ul>

<p><b>Simulating Actions:</b></p>
<p>You can simulate adding/removing items using the API or by making HTTP requests.</p>
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Smart Fridge Simulator Help")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(help_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
