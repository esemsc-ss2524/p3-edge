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
        layout.setContentsMargins(10, 5, 10, 5)

        # The Bubble
        message_label = QLabel(self.text)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        # Font settings
        font = QFont("Segoe UI", 11)
        message_label.setFont(font)

        if self.is_user:
            layout.addStretch()
            # User: Blue bubble, white text
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #1280C5;
                    color: #FFFEFF;
                    padding: 12px 16px;
                    border-radius: 16px;
                    border-bottom-right-radius: 4px;
                    min-height: 20px;
                }
            """)
            layout.addWidget(message_label)
        else:
            # P3: Light bubble, dark text
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #F3FBFB;
                    color: #3D4145;
                    padding: 12px 16px;
                    border-radius: 16px;
                    border-bottom-left-radius: 4px;
                    min-height: 20px;
                    border: 1px solid #1280C5;
                }
            """)
            layout.addWidget(message_label)
            layout.addStretch()


class AutonomousLogEntry(QFrame):
    """A log entry for autonomous activity."""

    def __init__(self, text: str, activity_type: str = "info", parent=None):
        super().__init__(parent)
        self.text = text
        self.activity_type = activity_type
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.NoFrame)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        # Icon based on type
        icon_map = {
            "info": "ℹ️",
            "action": "⚡",
            "success": "✓",
            "error": "⚠️",
            "cycle": "🔄"
        }
        icon_label = QLabel(icon_map.get(self.activity_type, "•"))
        icon_label.setStyleSheet("font-size: 14px; color: #1280C5;")
        icon_label.setFixedWidth(20)

        # Message
        message_label = QLabel(self.text)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                background-color: rgba(18, 128, 197, 0.08);
                color: #3D4145;
                padding: 10px 14px;
                border-radius: 8px;
                border-left: 3px solid #1280C5;
                font-size: 11px;
            }
        """)

        layout.addWidget(icon_label)
        layout.addWidget(message_label, stretch=1)


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

    def __init__(self, db_manager: DatabaseManager, tool_executor=None, autonomous_agent=None, parent=None):
        super().__init__(parent)
        self.logger = get_logger("p3_dashboard")
        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.autonomous_agent = autonomous_agent
        self.llm_service: Optional[LLMService] = None
        self.chat_worker: Optional[ChatWorker] = None

        # UI State
        self.stat_widgets = {}

        self._setup_ui()
        self._initialize_llm()
        self._update_stats()

        # Connect to autonomous agent signals if available
        if self.autonomous_agent:
            self.autonomous_agent.cycle_started.connect(self._on_agent_cycle_started)
            self.autonomous_agent.cycle_completed.connect(self._on_agent_cycle_completed)
            self.autonomous_agent.action_taken.connect(self._on_agent_action)

        # Update stats periodically
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(30000) 

    def _setup_ui(self):
        """Set up the futuristic two-column UI."""
        # Color palette
        self.COLOR_WHITE = "#FFFEFF"
        self.COLOR_BLUE = "#1280C5"
        self.COLOR_DARK = "#3D4145"
        self.COLOR_LIGHT_BLUE = "#F3FBFB"

        self.setStyleSheet(f"background-color: {self.COLOR_LIGHT_BLUE};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================================
        # TOP: P3 Character Header (full width, small)
        # ==========================================================
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.COLOR_BLUE}, stop:1 #0a5a8a);
                border: none;
            }}
        """)
        header.setFixedHeight(120)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 15, 30, 15)

        # P3 Character (small, centered)
        self.character_label = QLabel()
        self.character_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character_label.setFixedSize(80, 80)
        self.character_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.character_label.mousePressEvent = lambda event: self._on_character_clicked()

        # Status and HUD
        info_layout = QVBoxLayout()

        # Status
        status_layout = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: #2ecc71; font-size: 10px;")
        status_text = QLabel("P3 ONLINE")
        status_text.setStyleSheet(f"color: {self.COLOR_WHITE}; font-size: 11px; font-weight: 600; letter-spacing: 2px;")
        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(status_text)
        status_layout.addStretch()
        info_layout.addLayout(status_layout)

        # HUD Stats + Budget
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        stats_config = [
            ("inventory", "📦", "Items", self.COLOR_WHITE),
            ("low_stock", "⚠️", "Low", "#e74c3c"),
            ("cart", "🛒", "Cart", "#f39c12")
        ]
        for key, icon, label, color in stats_config:
            pill = StatPill(icon, label, "-", color)
            pill.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(255, 255, 255, 0.15);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 15px;
                }}
            """)
            self.stat_widgets[key] = pill
            stats_layout.addWidget(pill)

        # Budget Display
        budget_container = QFrame()
        budget_container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                padding: 5px 12px;
            }}
        """)
        budget_layout = QHBoxLayout(budget_container)
        budget_layout.setContentsMargins(8, 5, 8, 5)
        budget_layout.setSpacing(8)

        budget_icon = QLabel("💰")
        self.budget_label = QLabel("Budget: $-")
        self.budget_label.setStyleSheet(f"color: {self.COLOR_WHITE}; font-weight: 600; font-size: 12px; border: none;")

        self.budget_edit_btn = QPushButton("✎")
        self.budget_edit_btn.setFixedSize(24, 24)
        self.budget_edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.budget_edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.2);
                color: {self.COLOR_WHITE};
                border: none;
                border-radius: 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.3); }}
        """)
        self.budget_edit_btn.clicked.connect(self._edit_budget)

        budget_layout.addWidget(budget_icon)
        budget_layout.addWidget(self.budget_label)
        budget_layout.addWidget(self.budget_edit_btn)

        stats_layout.addWidget(budget_container)
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)

        header_layout.addWidget(self.character_label)
        header_layout.addLayout(info_layout, stretch=1)

        main_layout.addWidget(header)

        # ==========================================================
        # MIDDLE: Two Column Layout
        # ==========================================================
        columns_layout = QHBoxLayout()
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(0)

        # LEFT COLUMN: User Chat with P3
        left_column = self._create_chat_column(
            title="Chat with P3",
            is_user_chat=True
        )

        # RIGHT COLUMN: P3 Autonomous Log
        right_column = self._create_autonomous_log_column(
            title="P3 Activity Log"
        )

        columns_layout.addWidget(left_column, stretch=1)
        columns_layout.addWidget(right_column, stretch=1)

        main_layout.addLayout(columns_layout, stretch=1)

        # Initialize Default Animation
        self._play_idle_animation()
        self._load_budget()

    def _create_chat_column(self, title: str, is_user_chat: bool):
        """Create the user chat column."""
        column = QFrame()
        column.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLOR_WHITE};
                border-right: 2px solid {self.COLOR_BLUE};
            }}
        """)

        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLOR_DARK};
                border: none;
            }}
        """)
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {self.COLOR_WHITE};
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1px;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addWidget(title_bar)

        # Chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setStyleSheet(f"""
            QScrollArea {{ background: {self.COLOR_WHITE}; border: none; }}
            QScrollBar:vertical {{
                width: 8px;
                background: {self.COLOR_LIGHT_BLUE};
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.COLOR_BLUE};
                border-radius: 4px;
            }}
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet(f"background: {self.COLOR_WHITE};")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, stretch=1)

        # Input area
        input_container = QWidget()
        input_container.setStyleSheet(f"background-color: {self.COLOR_LIGHT_BLUE}; border: none;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(20, 15, 20, 15)

        self.input_field = AutoResizingTextEdit()
        self.input_field.setPlaceholderText("Ask P3 anything...")
        self.input_field.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.COLOR_WHITE};
                border: 2px solid {self.COLOR_BLUE};
                border-radius: 20px;
                padding: 12px 18px;
                font-size: 13px;
                color: {self.COLOR_DARK};
            }}
            QTextEdit:focus {{
                border: 2px solid {self.COLOR_BLUE};
            }}
        """)

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(50, 50)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLOR_BLUE};
                color: {self.COLOR_WHITE};
                border-radius: 25px;
                font-size: 20px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #0d6ba3;
            }}
            QPushButton:pressed {{
                background-color: #0a5a8a;
            }}
        """)
        self.send_btn.clicked.connect(self._send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(input_container)

        return column

    def _create_autonomous_log_column(self, title: str):
        """Create the autonomous activity log column."""
        column = QFrame()
        column.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLOR_LIGHT_BLUE};
                border: none;
            }}
        """)

        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLOR_DARK};
                border: none;
            }}
        """)
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {self.COLOR_WHITE};
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1px;
        """)

        self.autonomous_status = QLabel("● Monitoring")
        self.autonomous_status.setStyleSheet(f"""
            color: #2ecc71;
            font-size: 11px;
            font-weight: 500;
        """)

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.autonomous_status)

        layout.addWidget(title_bar)

        # Activity log area
        self.autonomous_scroll = QScrollArea()
        self.autonomous_scroll.setWidgetResizable(True)
        self.autonomous_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.autonomous_scroll.setStyleSheet(f"""
            QScrollArea {{ background: {self.COLOR_LIGHT_BLUE}; border: none; }}
            QScrollBar:vertical {{
                width: 8px;
                background: {self.COLOR_WHITE};
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.COLOR_BLUE};
                border-radius: 4px;
            }}
        """)

        self.autonomous_container = QWidget()
        self.autonomous_container.setStyleSheet(f"background: {self.COLOR_LIGHT_BLUE};")
        self.autonomous_layout = QVBoxLayout(self.autonomous_container)
        self.autonomous_layout.setContentsMargins(20, 20, 20, 20)
        self.autonomous_layout.setSpacing(12)
        self.autonomous_layout.addStretch()

        self.autonomous_scroll.setWidget(self.autonomous_container)
        layout.addWidget(self.autonomous_scroll, stretch=1)

        return column

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
            # We enforce a specific height for the character animation
            # Reduced size to keep dashboard compact
            target_height = 250 
            
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
        """Add message to user chat column."""
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

    def _add_autonomous_log(self, text: str, activity_type: str = "info"):
        """Add entry to autonomous activity log column."""
        # Remove spacer
        if self.autonomous_layout.count() > 0:
            item = self.autonomous_layout.itemAt(self.autonomous_layout.count() - 1)
            if item.spacerItem():
                self.autonomous_layout.removeItem(item)

        log_entry = AutonomousLogEntry(text, activity_type)
        self.autonomous_layout.addWidget(log_entry)

        # Add spacer back
        self.autonomous_layout.addStretch()

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.autonomous_scroll.verticalScrollBar().setValue(
            self.autonomous_scroll.verticalScrollBar().maximum()
        ))

    def _load_budget(self):
        """Load and display budget from preferences."""
        try:
            prefs = self.db_manager.get_preferences()
            weekly_cap = prefs.get("spend_cap_weekly", 0)
            monthly_cap = prefs.get("spend_cap_monthly", 0)

            if monthly_cap:
                self.budget_label.setText(f"Budget: ${monthly_cap}/mo")
            elif weekly_cap:
                self.budget_label.setText(f"Budget: ${weekly_cap}/wk")
            else:
                self.budget_label.setText("Budget: Not Set")
        except Exception as e:
            self.logger.error(f"Error loading budget: {e}")
            self.budget_label.setText("Budget: Error")

    def _edit_budget(self):
        """Open dialog to edit budget."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Set Budget")
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {self.COLOR_WHITE};
            }}
            QLabel {{
                color: {self.COLOR_DARK};
                font-size: 13px;
            }}
            QLineEdit {{
                border: 2px solid {self.COLOR_BLUE};
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                color: {self.COLOR_DARK};
            }}
            QComboBox {{
                border: 2px solid {self.COLOR_BLUE};
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {self.COLOR_BLUE};
                color: {self.COLOR_WHITE};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #0d6ba3;
            }}
        """)

        layout = QVBoxLayout(dialog)

        # Amount input
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Amount: $"))
        amount_input = QLineEdit()
        amount_input.setPlaceholderText("100")
        amount_layout.addWidget(amount_input)
        layout.addLayout(amount_layout)

        # Period selection
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Period:"))
        period_combo = QComboBox()
        period_combo.addItems(["Weekly", "Monthly"])
        period_layout.addWidget(period_combo)
        layout.addLayout(period_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLOR_DARK};
                color: {self.COLOR_WHITE};
            }}
        """)

        def save_budget():
            try:
                amount = float(amount_input.text())
                period = period_combo.currentText().lower()

                prefs = self.db_manager.get_preferences()
                if period == "weekly":
                    prefs["spend_cap_weekly"] = amount
                    prefs["spend_cap_monthly"] = None
                else:
                    prefs["spend_cap_monthly"] = amount
                    prefs["spend_cap_weekly"] = None

                # Save preferences
                for key, value in prefs.items():
                    self.db_manager.set_preference(key, value)

                self._load_budget()
                dialog.accept()
            except ValueError:
                amount_input.setPlaceholderText("Invalid amount")

        save_btn.clicked.connect(save_budget)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec()

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
        """Update HUD stats with correct values."""
        if not self.db_manager:
            return

        try:
            # 1. Inventory
            res = self.db_manager.execute_query("SELECT COUNT(*) FROM inventory")
            val = res[0][0] if res else 0
            self.stat_widgets["inventory"].update_value(str(val))

            # 2. Low Stock (quantity <= min)
            res = self.db_manager.execute_query("SELECT COUNT(*) FROM inventory WHERE quantity_current <= quantity_min")
            val = res[0][0] if res else 0
            self.stat_widgets["low_stock"].update_value(str(val))

            # 3. Cart (count items in pending orders)
            res = self.db_manager.execute_query("""
                SELECT SUM(json_array_length(items))
                FROM orders
                WHERE status = 'PENDING'
            """)
            # json_array_length may not be available, so let's count differently
            # Get all PENDING orders and parse their items JSON
            orders_res = self.db_manager.execute_query("SELECT items FROM orders WHERE status = 'PENDING'")
            total_items = 0
            if orders_res:
                import json
                for row in orders_res:
                    try:
                        items = json.loads(row[0]) if row[0] else []
                        total_items += len(items)
                    except:
                        pass
            self.stat_widgets["cart"].update_value(str(total_items))

        except Exception as e:
            self.logger.error(f"Stats update error: {e}")

    # --- Autonomous Agent Signal Handlers ---

    def _on_agent_cycle_started(self, cycle_id: str):
        """Called when autonomous agent starts a new cycle."""
        self.logger.info(f"P3 cycle started: {cycle_id}")
        self._add_autonomous_log("Starting maintenance cycle...", "cycle")
        self.autonomous_status.setText("● Working")
        self.autonomous_status.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: 500;")

    def _on_agent_cycle_completed(self, cycle_id: str, summary: dict):
        """Called when autonomous agent completes a cycle."""
        status = summary.get('status', 'unknown')
        self.logger.info(f"P3 cycle completed: {cycle_id} - Status: {status}")

        if status == 'completed':
            tool_calls = summary.get('tool_calls', 0)
            response = summary.get('response', 'No actions taken')
            self._add_autonomous_log(
                f"Cycle complete: {tool_calls} action(s) taken. {response}",
                "success"
            )
        elif status == 'skipped':
            reason = summary.get('reason', 'No action needed')
            self.logger.debug(f"P3 cycle skipped: {reason}")
            self._add_autonomous_log(f"System check: {reason}", "info")
        elif status == 'error':
            error = summary.get('error', 'Unknown error')
            self._add_autonomous_log(f"Cycle failed: {error}", "error")

        self.autonomous_status.setText("● Monitoring")
        self.autonomous_status.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: 500;")
        self._update_stats()  # Refresh stats after actions

    def _on_agent_action(self, action_type: str, description: str):
        """Called when autonomous agent takes an action."""
        self.logger.info(f"P3 action: {action_type} - {description}")
        self._add_autonomous_log(description, "action")