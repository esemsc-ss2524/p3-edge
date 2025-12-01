"""
Chat page for conversational interaction with the LLM assistant.

Provides a chat interface where users can interact with the Gemma 3 4b model
through natural language conversations.
"""

from typing import Optional, List
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtGui import QTextCursor

from ..services.llm_service import LLMService
from ..utils import get_logger


class ChatWorker(QThread):
    """Worker thread for LLM chat operations."""

    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        llm_service: LLMService,
        message: str,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None
    ):
        super().__init__()
        self.llm_service = llm_service
        self.message = message
        self.images = images
        self.system_prompt = system_prompt

    def run(self):
        """Run the chat operation in a separate thread."""
        try:
            response = self.llm_service.chat(
                message=self.message,
                images=self.images,
                system_prompt=self.system_prompt
            )
            self.response_ready.emit(response)
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
        """Set up the message widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # Create message bubble
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
                    padding: 10px 15px;
                    border-radius: 10px;
                    font-size: 14px;
                    max-width: 600px;
                }
            """)
            layout.addWidget(message_label)
        else:
            # Assistant message (left-aligned, gray)
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    padding: 10px 15px;
                    border-radius: 10px;
                    font-size: 14px;
                    max-width: 600px;
                }
            """)
            layout.addWidget(message_label)
            layout.addStretch()


class ChatPage(QWidget):
    """Chat page for conversational interaction with the LLM."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger("chat_page")
        self.llm_service: Optional[LLMService] = None
        self.chat_worker: Optional[ChatWorker] = None
        self.attached_images: List[str] = []

        self._setup_ui()
        self._initialize_llm()

    def _setup_ui(self):
        """Set up the chat UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("AI Assistant Chat")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("Have a conversation with your grocery shopping assistant")
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(subtitle)

        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #95a5a6;
                padding: 5px;
            }
        """)
        layout.addWidget(self.status_label)

        # Chat history area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
            }
        """)

        # Widget to contain chat messages
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, stretch=1)

        # Attached images label
        self.images_label = QLabel("")
        self.images_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #3498db;
                padding: 3px;
            }
        """)
        layout.addWidget(self.images_label)

        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        # Attach image button
        self.attach_btn = QPushButton("📎 Attach Image")
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.attach_btn.clicked.connect(self._attach_image)
        input_layout.addWidget(self.attach_btn)

        # Text input
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setMaximumHeight(80)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        input_layout.addWidget(self.input_field, stretch=1)

        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 25px;
                border: none;
                border-radius: 5px;
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
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        # Clear history button
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_history)
        action_layout.addWidget(self.clear_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

    def _initialize_llm(self):
        """Initialize the LLM service."""
        try:
            self.llm_service = LLMService()
            self.status_label.setText("✅ Ready - Gemma 3 4b model loaded")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #27ae60;
                    padding: 5px;
                }
            """)

            # Add welcome message
            self._add_message(
                "Hello! I'm your grocery shopping assistant. I can help you with:\n"
                "• Managing your inventory\n"
                "• Understanding consumption patterns\n"
                "• Making shopping recommendations\n"
                "• Answering questions about your groceries\n\n"
                "How can I help you today?",
                is_user=False
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #e74c3c;
                    padding: 5px;
                }
            """)
            self.send_btn.setEnabled(False)
            self.attach_btn.setEnabled(False)

            # Show error message in chat
            self._add_message(
                "Sorry, I'm currently unavailable. Please make sure:\n"
                "1. Ollama server is running (ollama serve)\n"
                "2. Gemma model is downloaded (python scripts/download_model.py)",
                is_user=False
            )

    def _add_message(self, text: str, is_user: bool = True):
        """Add a message to the chat history."""
        # Remove the stretch from the end
        if self.chat_layout.count() > 0:
            last_item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
            if last_item and last_item.spacerItem():
                self.chat_layout.removeItem(last_item)

        # Add the message
        message = ChatMessage(text, is_user)
        self.chat_layout.addWidget(message)

        # Add stretch back
        self.chat_layout.addStretch()

        # Scroll to bottom
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def _send_message(self):
        """Send a message to the LLM."""
        message = self.input_field.toPlainText().strip()

        if not message:
            return

        if not self.llm_service:
            QMessageBox.warning(
                self,
                "LLM Not Available",
                "The LLM service is not available. Please check the logs."
            )
            return

        # Add user message to chat
        self._add_message(message, is_user=True)

        # Clear input
        self.input_field.clear()

        # Disable input while processing
        self.send_btn.setEnabled(False)
        self.attach_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        self.status_label.setText("🤔 Thinking...")

        # Create system prompt for context
        system_prompt = """You are a helpful grocery shopping assistant for P3-Edge,
        an autonomous grocery management system. You help users with inventory management,
        consumption patterns, shopping recommendations, and general grocery-related questions.
        Be concise, friendly, and helpful."""

        # Start worker thread
        self.chat_worker = ChatWorker(
            self.llm_service,
            message,
            images=self.attached_images if self.attached_images else None,
            system_prompt=system_prompt
        )
        self.chat_worker.response_ready.connect(self._on_response_ready)
        self.chat_worker.error_occurred.connect(self._on_error)
        self.chat_worker.start()

        # Clear attached images after sending
        self.attached_images = []
        self.images_label.setText("")

    def _on_response_ready(self, response: str):
        """Handle LLM response."""
        self._add_message(response, is_user=False)

        # Re-enable input
        self.send_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.status_label.setText("✅ Ready")
        self.input_field.setFocus()

    def _on_error(self, error: str):
        """Handle LLM error."""
        self._add_message(
            f"Sorry, I encountered an error: {error}",
            is_user=False
        )

        # Re-enable input
        self.send_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.status_label.setText("❌ Error occurred")

    def _attach_image(self):
        """Attach an image to the message."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            self.attached_images.append(file_path)
            self.images_label.setText(
                f"📎 {len(self.attached_images)} image(s) attached"
            )
            self.logger.info(f"Attached image: {file_path}")

    def _clear_history(self):
        """Clear chat history."""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear the chat history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Clear UI
            while self.chat_layout.count() > 1:  # Keep the stretch
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Clear LLM history
            if self.llm_service:
                self.llm_service.clear_history()

            # Add welcome message back
            self._add_message(
                "Chat history cleared. How can I help you?",
                is_user=False
            )

            self.logger.info("Chat history cleared")
