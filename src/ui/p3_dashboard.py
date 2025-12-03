from typing import Optional, List
from pathlib import Path
import os

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
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
    QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QMovie, QColor, QFont, QIcon

# --- Import your existing services ---
from ..services.llm_service import LLMService
from ..services.llm_factory import create_llm_service
from ..config import get_config_manager
from ..models.tool_models import AgentResponse
from ..database.db_manager import DatabaseManager
from ..utils import get_logger


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


class ModernChatMessage(QFrame):
    """A modern, bubble-style chat message widget."""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5) # Side margins for the whole row

        # The Bubble
        message_label = QLabel(self.text)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        
        # Font settings
        font = QFont("Segoe UI", 11)  # Modern clean font
        message_label.setFont(font)

        if self.is_user:
            layout.addStretch()
            # User: Blue bubble, white text, sharp bottom-right corner
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #007AFF;
                    color: white;
                    padding: 12px 18px;
                    border-radius: 18px;
                    border-bottom-right-radius: 4px;
                    min-height: 20px;
                }
            """)
            layout.addWidget(message_label)
        else:
            # P3: Light gray bubble, dark text, sharp bottom-left corner
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #E9E9EB;
                    color: #000000;
                    padding: 12px 18px;
                    border-radius: 18px;
                    border-bottom-left-radius: 4px;
                    min-height: 20px;
                }
            """)
            layout.addWidget(message_label)
            layout.addStretch()


class StatPill(QFrame):
    """A small, capsule-shaped widget for stats (HUD style)."""
    
    def __init__(self, icon: str, label: str, initial_value: str, color_hex: str):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #E5E5E5;
                border-radius: 20px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)

        # Icon/Label
        lbl_title = QLabel(f"{icon}  {label}")
        lbl_title.setStyleSheet("color: #666; font-weight: 600; border: none;")
        
        # Value
        self.lbl_value = QLabel(initial_value)
        self.lbl_value.setStyleSheet(f"color: {color_hex}; font-weight: bold; font-size: 14px; border: none;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_value)
        
        # Add subtle shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def update_value(self, value):
        self.lbl_value.setText(str(value))


class AutoResizingTextEdit(QTextEdit):
    """
    A QTextEdit that auto-resizes its height to fit content 
    up to a maximum height, then enables scrolling.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)  # Initial single-line height
        self.min_height = 50
        self.max_height = 100    # Approx 3-4 lines depending on font
        
        # Style needed for the resize calculation to work correctly
        self.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #E5E5E5;
                border-radius: 20px;
                padding: 10px 15px;
                font-size: 14px;
                color: #2c3e50;
            }
            QTextEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        
        # Connect text changed signal to resize handler
        self.textChanged.connect(self.adjust_height)

    def adjust_height(self):
        # Calculate the height of the document
        doc_height = self.document().size().height()
        # Add padding compensation (approx 20px for top/bottom padding)
        target_height = doc_height + 25 
        
        if target_height > self.max_height:
            self.setFixedHeight(self.max_height)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            # Snap to min_height if empty, otherwise grow
            new_h = max(int(target_height), self.min_height)
            self.setFixedHeight(new_h)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


class P3Dashboard(QWidget):
    """
    Overhauled Autonomous Agent Interface.
    Focus: Character presence and natural conversation.
    """

    def __init__(self, db_manager: DatabaseManager, tool_executor=None, parent=None):
        super().__init__(parent)
        self.logger = get_logger("p3_dashboard")
        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.llm_service: Optional[LLMService] = None
        self.chat_worker: Optional[ChatWorker] = None

        # UI State
        self.stat_widgets = {}

        self._setup_ui()
        self._initialize_llm()
        self._update_stats()

        # Update stats periodically
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(30000) 

    def _setup_ui(self):
        """Set up the modern 2-pane UI with specific ratios."""
        self.setStyleSheet("background-color: #F5F7FA;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================================
        # LEFT PANEL: The Character (P3) - 50% Width
        # ==========================================================
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #FFFFFF; border-right: 1px solid #E5E5E5;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 40, 20, 40)
        
        # 1. Status Indicator
        status_container = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #27ae60; font-size: 12px;")
        status_text = QLabel("SYSTEM ONLINE")
        status_text.setStyleSheet("color: #95a5a6; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        status_container.addWidget(self.status_dot)
        status_container.addWidget(status_text)
        status_container.addStretch()
        left_layout.addLayout(status_container)

        # 2. Character Stage
        self.character_label = QLabel()
        self.character_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.character_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.character_label.mousePressEvent = lambda event: self._on_character_clicked()
        left_layout.addWidget(self.character_label, stretch=10)

        # 3. HUD Stats
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        stats_config = [
            ("inventory", "📦", "Items", "#3498db"),
            ("low_stock", "⚠️", "Low", "#e74c3c"),
            ("pending", "🛒", "Cart", "#f39c12")
        ]
        stats_layout.addStretch()
        for key, icon, label, color in stats_config:
            pill = StatPill(icon, label, "-", color)
            self.stat_widgets[key] = pill
            stats_layout.addWidget(pill)
        stats_layout.addStretch()
        left_layout.addLayout(stats_layout)
        
        # Add Left Panel with Stretch 1 (50% relative to total 2)
        main_layout.addWidget(left_panel, stretch=1) 

        # ==========================================================
        # RIGHT PANEL: The Chat - 50% Width
        # ==========================================================
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #F5F7FA;")
        
        # We use a VBox to split History (90%) and Input (10%)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # --- 1. Chat History Section (approx 90%) ---
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #cbd5e0; border-radius: 4px; }
        """)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addStretch()
        
        self.chat_scroll.setWidget(self.chat_container)
        
        # Add scroll area with high stretch factor (e.g., 9 or 90)
        right_layout.addWidget(self.chat_scroll, stretch=90)

        # --- 2. Input Section (approx 10% - or minimal required space) ---
        input_container = QWidget()
        input_container.setStyleSheet("background-color: #F5F7FA;") # Match background
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(20, 10, 20, 20)
        input_layout.setAlignment(Qt.AlignmentFlag.AlignBottom) # Anchor to bottom

        # Use our new AutoResizingTextEdit
        self.input_field = AutoResizingTextEdit()
        self.input_field.setPlaceholderText("Ask P3 about groceries, recipes...")

        # Send Button
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(45, 45) # Slightly smaller to match default input height
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 22px;
                font-size: 18px;
                font-weight: bold;
                padding-bottom: 3px; 
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; transform: scale(0.95); }
        """)
        self.send_btn.clicked.connect(self._send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        # Add input container with lower stretch factor (e.g., 10)
        # However, for input fields, it's often better to use stretch=0 
        # so it only takes what it needs, and the chat history takes "the rest".
        # But to strictly follow your request of "10% input section":
        right_layout.addWidget(input_container, stretch=10)
        
        # Add Right Panel with Stretch 1 (50% relative to total 2)
        main_layout.addWidget(right_panel, stretch=1)

        # Initialize Default Animation
        self._play_idle_animation()

    # --- Animation Handling ---
    
    def _play_idle_animation(self):
        """Play idle animation."""
        self._play_animation("assets/p3_idle.webp")

    def _play_wave_animation(self):
        """Play waving animation."""
        self._play_animation("assets/p3_wave.webp")
        # Return to idle after approx duration of wave (e.g., 3 seconds)
        QTimer.singleShot(3000, self._play_idle_animation)

    def _play_thinking_animation(self):
        """Play thinking animation."""
        self._play_animation("assets/p3_thinking.webp")

    def _play_animation(self, path_str: str):
        """
        Generic method to load and play animation on the character label
        with enforced height consistency.
        """
        file_path = Path(path_str)
        if not file_path.exists():
            self.logger.warning(f"Animation file not found: {path_str}")
            if self.character_label.movie() is None:
                self.character_label.setText("🤖")
            return

        # 1. Check if we are already playing this file to avoid flickering
        current_movie = self.character_label.movie()
        if current_movie and current_movie.fileName() == str(file_path):
            if current_movie.state() != QMovie.MovieState.Running:
                current_movie.start()
            return

        # 2. Create the new movie
        movie = QMovie(str(file_path))
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        
        if movie.isValid():
            # --- SCALING LOGIC START ---
            # We enforce a specific height, e.g., 400px (or roughly 60% of screen height)
            # You can tweak this number based on your screen size
            target_height = 500 
            
            # Jump to frame 0 to get the actual size of the video/gif
            movie.jumpToFrame(0)
            orig_size = movie.currentImage().size()
            
            if orig_size.isValid():
                aspect_ratio = orig_size.width() / orig_size.height()
                new_width = int(target_height * aspect_ratio)
                movie.setScaledSize(QSize(new_width, target_height))
            # --- SCALING LOGIC END ---

            self.character_label.setMovie(movie)
            movie.start()
        else:
            self.logger.error(f"Invalid movie file: {path_str}")

    def _on_character_clicked(self):
        self._play_wave_animation()
        self._add_message("Hi there! I'm P3, ready to help.", is_user=False)

    # --- Chat Logic ---

    def _send_message(self):
        message = self.input_field.toPlainText().strip()
        if not message:
            return

        if not self.llm_service:
            QMessageBox.warning(self, "Not Ready", "P3 is initializing...")
            return

        self._add_message(message, is_user=True)
        self.input_field.clear()
        
        # UI Feedback
        self.input_field.setEnabled(False)
        self.status_dot.setStyleSheet("color: #f39c12;") # Orange for thinking
        self._play_thinking_animation()

        # Threading
        self.chat_worker = ChatWorker(self.llm_service, message)
        self.chat_worker.response_ready.connect(self._handle_response)
        self.chat_worker.error_occurred.connect(self._handle_error)
        self.chat_worker.finished.connect(self._chat_finished)
        self.chat_worker.start()

    def _handle_response(self, agent_response: AgentResponse):
        self._add_message(agent_response.response, is_user=False)

    def _handle_error(self, error_msg: str):
        self._add_message(f"⚠️ System Error: {error_msg}", is_user=False)

    def _chat_finished(self):
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.status_dot.setStyleSheet("color: #27ae60;") # Green for ready
        self._play_idle_animation()

    def _add_message(self, text: str, is_user: bool):
        # Remove spacer
        if self.chat_layout.count() > 0:
            item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
            if item.spacerItem():
                self.chat_layout.removeItem(item)

        msg_widget = ModernChatMessage(text, is_user)
        self.chat_layout.addWidget(msg_widget)
        
        # Add spacer back
        self.chat_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    # --- Backend & Initialization ---

    def _initialize_llm(self):
        try:
            config = get_config_manager()
            # ... (Keep your existing initialization logic exactly as is) ...
            provider = config.get("llm.provider", "ollama")
            
            # Simplified for brevity in this snippet, ensure you copy your logic back
            factory_args = {"provider": provider, "tool_executor": self.tool_executor}
            if provider == "ollama":
                factory_args["model_name"] = config.get("llm.ollama.model", "gemma:2b")
            elif provider == "gemini":
                 # Ensure you load API keys safely
                 pass 

            self.llm_service = create_llm_service(**factory_args)
            self.logger.info("P3 Initialized")
            
        except Exception as e:
            self.logger.error(f"Init Error: {e}")
            self._add_message(f"System Initialization Failed: {e}", is_user=False)

    def _update_stats(self):
        if not self.db_manager:
            return
        
        # Use a background thread for DB calls in production to prevent UI freeze
        try:
            # 1. Inventory
            res = self.db_manager.execute_query("SELECT COUNT(*) FROM inventory")
            val = res[0][0] if res else 0
            self.stat_widgets["inventory"].update_value(str(val))

            # 2. Low Stock
            res = self.db_manager.execute_query("SELECT COUNT(*) FROM inventory WHERE quantity_current <= quantity_min")
            val = res[0][0] if res else 0
            self.stat_widgets["low_stock"].update_value(str(val))

            # 3. Pending
            res = self.db_manager.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'PENDING'")
            val = res[0][0] if res else 0
            self.stat_widgets["pending"].update_value(str(val))
            
        except Exception as e:
            self.logger.error(f"Stats update error: {e}")