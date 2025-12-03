"""
Integrated dashboard with P3 character and chat interface.

The main page showing system status, stats, and interaction with P3.
"""

from typing import Optional, List
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QScrollArea,
    QMessageBox,
)
from PyQt6.QtGui import QMovie, QTextCursor

from ..services.llm_service import LLMService
from ..services.llm_factory import create_llm_service
from ..config import get_config_manager
from ..models.tool_models import AgentResponse
from ..database.db_manager import DatabaseManager
from ..utils import get_logger
import json
import os


class ChatWorker(QThread):
    """Worker thread for LLM chat with P3."""

    response_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, llm_service: LLMService, message: str, system_prompt: Optional[str] = None):
        super().__init__()
        self.llm_service = llm_service
        self.message = message
        self.system_prompt = system_prompt

    def run(self):
        """Run chat operation."""
        try:
            if self.llm_service.tool_executor:
                agent_response = self.llm_service.chat_with_tools(
                    message=self.message,
                    system_prompt=self.system_prompt
                )
                self.response_ready.emit(agent_response)
            else:
                response = self.llm_service.chat(
                    message=self.message,
                    system_prompt=self.system_prompt
                )
                agent_response = AgentResponse(
                    response=response,
                    tool_calls=[],
                    tool_results=[],
                    iterations=1
                )
                self.response_ready.emit(agent_response)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatMessage(QFrame):
    """Widget for displaying a single chat message."""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self._setup_ui()

    def _setup_ui(self):
        """Set up message widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        message_label = QLabel(self.text)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        if self.is_user:
            # User message (right-aligned, blue)
            layout.addStretch()
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #3498db;
                    color: white;
                    padding: 12px 16px;
                    border-radius: 18px;
                    font-size: 14px;
                    max-width: 600px;
                }
            """)
            layout.addWidget(message_label)
        else:
            # P3 message (left-aligned, gray)
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    padding: 12px 16px;
                    border-radius: 18px;
                    font-size: 14px;
                    max-width: 600px;
                }
            """)
            layout.addWidget(message_label)
            layout.addStretch()


class P3Dashboard(QWidget):
    """Main dashboard with P3 character and integrated chat."""

    def __init__(self, db_manager: DatabaseManager, tool_executor=None, parent=None):
        super().__init__(parent)
        self.logger = get_logger("p3_dashboard")
        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.llm_service: Optional[LLMService] = None
        self.chat_worker: Optional[ChatWorker] = None

        self._setup_ui()
        self._initialize_llm()
        self._update_stats()

        # Update stats periodically
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(30000)  # Every 30 seconds

    def _setup_ui(self):
        """Set up the dashboard UI."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Left side: Character and Stats
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, stretch=1)

        # Right side: Chat Interface
        right_panel = self._create_chat_panel()
        main_layout.addWidget(right_panel, stretch=2)

    def _create_left_panel(self):
        """Create left panel with character and stats."""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setSpacing(20)

        # Welcome Section
        welcome_label = QLabel("P3-Edge")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)

        subtitle = QLabel("Your Autonomous Grocery Assistant")
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7f8c8d;
                padding: 0px 10px 20px 10px;
            }
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Character Animation
        character_frame = QFrame()
        character_frame.setStyleSheet("""
            QFrame {
                background-color: #ecf0f1;
                border-radius: 10px;
                min-height: 200px;
                max-height: 200px;
            }
        """)
        char_layout = QVBoxLayout(character_frame)

        self.character_label = QLabel()
        self.character_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character_label.setScaledContents(False)

        # Try to load idle animation
        idle_gif_path = Path("assets/p3_idle.gif")
        if idle_gif_path.exists():
            self.idle_movie = QMovie(str(idle_gif_path))
            self.character_label.setMovie(self.idle_movie)
            self.idle_movie.start()
        else:
            # Placeholder if GIF not found
            self.character_label.setText("🤖")
            self.character_label.setStyleSheet("""
                QLabel {
                    font-size: 80px;
                }
            """)

        char_layout.addWidget(self.character_label)
        layout.addWidget(character_frame)

        # System Status
        self.status_label = QLabel("● Online")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #27ae60;
                padding: 10px;
                background-color: #d5f4e6;
                border-radius: 8px;
                font-weight: bold;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Stats Cards
        stats_title = QLabel("System Overview")
        stats_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px 0px;
            }
        """)
        layout.addWidget(stats_title)

        # Create stat cards
        self.stat_cards = {}
        stat_configs = [
            ("inventory", "Inventory Items", "0", "#3498db"),
            ("low_stock", "Low Stock", "0", "#e74c3c"),
            ("pending", "Pending Orders", "0", "#f39c12"),
        ]

        for key, title, value, color in stat_configs:
            card = self._create_stat_card(title, value, color)
            self.stat_cards[key] = card
            layout.addWidget(card)

        layout.addStretch()
        return panel

    def _create_stat_card(self, title: str, value: str, color: str):
        """Create a stat card."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        value_label = QLabel(value)
        value_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)

        # Store reference to value label for updates
        card.value_label = value_label

        return card

    def _create_chat_panel(self):
        """Create chat panel for P3 interaction."""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        # Chat Header
        header = QLabel("Chat with P3")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(header)

        # Chat Status
        self.chat_status = QLabel("Ready")
        self.chat_status.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #95a5a6;
                padding: 5px;
            }
        """)
        layout.addWidget(self.chat_status)

        # Chat History Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 10px;
            }
        """)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, stretch=1)

        # Input Area
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setSpacing(10)

        # Text Input
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message to P3...")
        self.input_field.setMaximumHeight(80)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                color: #2c3e50;
            }
            QTextEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        input_layout.addWidget(self.input_field)

        # Buttons Row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Clear History Button
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #4e555b;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_history)
        buttons_layout.addWidget(self.clear_btn)

        buttons_layout.addStretch()

        # Send Button
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 30px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.send_btn.clicked.connect(self._send_message)
        buttons_layout.addWidget(self.send_btn)

        input_layout.addLayout(buttons_layout)
        layout.addWidget(input_container)

        return panel

    def _initialize_llm(self):
        """Initialize LLM service for P3."""
        try:
            config = get_config_manager()
            provider = config.get("llm.provider", "ollama")

            factory_args = {
                "provider": provider,
                "tool_executor": self.tool_executor
            }

            if provider == "ollama":
                model_name = config.get("llm.ollama.model", "gemma3n:e2b-it-q4_K_M")
                factory_args["model_name"] = model_name
            elif provider == "gemini":
                model_name = config.get("llm.gemini.model", "gemini-2.0-flash-exp")
                temperature = config.get("llm.gemini.temperature", 0.7)
                api_key_env = config.get("llm.gemini.api_key_env", "GOOGLE_API_KEY")
                api_key = os.environ.get(api_key_env)

                if not api_key:
                    raise ValueError(f"API key not found in environment variable '{api_key_env}'")

                factory_args["model_name"] = model_name
                factory_args["api_key"] = api_key
                factory_args["temperature"] = temperature

            self.logger.info(f"Initializing P3 with provider: {provider}")
            self.llm_service = create_llm_service(**factory_args)

            if self.tool_executor:
                tool_count = len(self.tool_executor.get_available_tools())
                self.chat_status.setText(f"Ready • {tool_count} capabilities available")
            else:
                self.chat_status.setText("Ready")

        except Exception as e:
            self.logger.error(f"Failed to initialize P3: {e}")
            self.chat_status.setText(f"Error: {str(e)}")
            self.send_btn.setEnabled(False)

    def _send_message(self):
        """Send message to P3."""
        message = self.input_field.toPlainText().strip()
        if not message:
            return

        if not self.llm_service:
            QMessageBox.warning(self, "Not Ready", "P3 is not initialized yet")
            return

        # Add user message
        self._add_message(message, is_user=True)
        self.input_field.clear()

        # Disable input while processing
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.chat_status.setText("P3 is thinking...")

        # Play waving animation if available
        self._play_wave_animation()

        # Start chat worker
        self.chat_worker = ChatWorker(self.llm_service, message)
        self.chat_worker.response_ready.connect(self._handle_response)
        self.chat_worker.error_occurred.connect(self._handle_error)
        self.chat_worker.finished.connect(self._chat_finished)
        self.chat_worker.start()

    def _handle_response(self, agent_response: AgentResponse):
        """Handle response from P3."""
        self._add_message(agent_response.response, is_user=False)

        # Log tool usage if any
        if agent_response.tool_calls:
            self.logger.info(f"P3 used {len(agent_response.tool_calls)} tool(s)")

    def _handle_error(self, error_msg: str):
        """Handle error from chat."""
        self._add_message(f"Sorry, I encountered an error: {error_msg}", is_user=False)
        self.logger.error(f"Chat error: {error_msg}")

    def _chat_finished(self):
        """Re-enable input after chat completes."""
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.chat_status.setText("Ready")
        self.input_field.setFocus()

        # Return to idle animation
        self._play_idle_animation()

    def _add_message(self, text: str, is_user: bool):
        """Add message to chat history."""
        # Remove stretch from end
        item_count = self.chat_layout.count()
        if item_count > 0:
            stretch_item = self.chat_layout.itemAt(item_count - 1)
            if stretch_item.spacerItem():
                self.chat_layout.removeItem(stretch_item)

        # Add message
        message_widget = ChatMessage(text, is_user)
        self.chat_layout.addWidget(message_widget)

        # Add stretch back
        self.chat_layout.addStretch()

        # Scroll to bottom
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _clear_history(self):
        """Clear chat history."""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear the chat history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Clear all messages except stretch
            while self.chat_layout.count() > 1:
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Clear LLM conversation history if available
            if self.llm_service:
                self.llm_service.clear_history()

            self.logger.info("Chat history cleared")

    def _play_wave_animation(self):
        """Play waving animation."""
        wave_gif_path = Path("assets/p3_wave.gif")
        if wave_gif_path.exists() and hasattr(self, 'character_label'):
            wave_movie = QMovie(str(wave_gif_path))
            self.character_label.setMovie(wave_movie)
            wave_movie.start()

            # Return to idle after 2 seconds
            QTimer.singleShot(2000, self._play_idle_animation)

    def _play_idle_animation(self):
        """Play idle animation."""
        idle_gif_path = Path("assets/p3_idle.gif")
        if idle_gif_path.exists() and hasattr(self, 'character_label'):
            if not hasattr(self, 'idle_movie'):
                self.idle_movie = QMovie(str(idle_gif_path))
            self.character_label.setMovie(self.idle_movie)
            self.idle_movie.start()

    def _update_stats(self):
        """Update statistics cards."""
        if not self.db_manager:
            return

        try:
            # Inventory count
            inv_query = "SELECT COUNT(*) FROM inventory"
            inv_result = self.db_manager.execute_query(inv_query)
            inventory_count = inv_result[0][0] if inv_result else 0
            self.stat_cards["inventory"].value_label.setText(str(inventory_count))

            # Low stock count
            low_query = "SELECT COUNT(*) FROM inventory WHERE quantity_current <= quantity_min"
            low_result = self.db_manager.execute_query(low_query)
            low_count = low_result[0][0] if low_result else 0
            self.stat_cards["low_stock"].value_label.setText(str(low_count))

            # Pending orders count
            pending_query = "SELECT COUNT(*) FROM orders WHERE status = 'PENDING'"
            pending_result = self.db_manager.execute_query(pending_query)
            pending_count = pending_result[0][0] if pending_result else 0
            self.stat_cards["pending"].value_label.setText(str(pending_count))

        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")
