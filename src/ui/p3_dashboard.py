from typing import Optional, List

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
    QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont

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

    def __init__(self, db_manager: DatabaseManager, tool_executor=None, autonomous_agent=None, cart_service=None, parent=None):
        super().__init__(parent)
        self.logger = get_logger("p3_dashboard")
        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.autonomous_agent = autonomous_agent
        self.cart_service = cart_service
        self.llm_service: Optional[LLMService] = None
        self.chat_worker: Optional[ChatWorker] = None

        # UI State
        self.stat_widgets = {}
        self.last_message_date = None  # Track last message date for separators

        self._setup_ui()
        self._initialize_llm()
        self._update_stats()
        self._load_chat_history()  # Load previous messages

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
        """Set up the modern 2-pane UI with specific ratios."""
        self.setStyleSheet("background-color: #F5F7FA;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================================
        # LEFT PANEL: P3 Activity - 50% Width
        # ==========================================================
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #FFFFFF; border-right: 1px solid #E5E5E5;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        # 1. Header with Status
        header_layout = QHBoxLayout()

        p3_title = QLabel("P3 Activity")
        p3_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(p3_title)

        header_layout.addStretch()

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #27ae60; font-size: 12px;")
        status_text = QLabel("ACTIVE")
        status_text.setStyleSheet("color: #95a5a6; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        header_layout.addWidget(self.status_dot)
        header_layout.addWidget(status_text)

        left_layout.addLayout(header_layout)

        # 2. Activity Log
        self.activity_scroll = QScrollArea()
        self.activity_scroll.setWidgetResizable(True)
        self.activity_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.activity_scroll.setStyleSheet("""
            QScrollArea {
                background: #F8F9FA;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
            }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #cbd5e0; border-radius: 4px; }
        """)

        self.activity_container = QWidget()
        self.activity_container.setStyleSheet("background: #F8F9FA;")
        self.activity_layout = QVBoxLayout(self.activity_container)
        self.activity_layout.setContentsMargins(15, 15, 15, 15)
        self.activity_layout.setSpacing(10)
        self.activity_layout.addStretch()

        self.activity_scroll.setWidget(self.activity_container)
        left_layout.addWidget(self.activity_scroll, stretch=1)

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

    # --- Activity Log Methods ---

    def _add_activity(self, message: str, activity_type: str = "info"):
        """Add activity message to P3 activity log."""
        from datetime import datetime

        # Remove spacer
        if self.activity_layout.count() > 0:
            item = self.activity_layout.itemAt(self.activity_layout.count() - 1)
            if item.spacerItem():
                self.activity_layout.removeItem(item)

        # Create activity widget
        activity_widget = QFrame()
        activity_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-left: 3px solid #3498db;
                border-radius: 3px;
                padding: 8px;
            }
        """)

        activity_layout = QVBoxLayout(activity_widget)
        activity_layout.setContentsMargins(8, 8, 8, 8)
        activity_layout.setSpacing(4)

        # Time label
        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
        activity_layout.addWidget(time_label)

        # Message label
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #2c3e50; font-size: 13px;")
        activity_layout.addWidget(msg_label)

        self.activity_layout.addWidget(activity_widget)

        # Add spacer back
        self.activity_layout.addStretch()

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.activity_scroll.verticalScrollBar().setValue(
            self.activity_scroll.verticalScrollBar().maximum()
        ))

    # --- Chat History Management ---

    def _load_chat_history(self):
        """Load previous chat messages from database."""
        if not self.db_manager:
            return

        try:
            from datetime import datetime, timedelta

            # Load messages from the last 7 days
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()

            query = """
                SELECT role, message, timestamp
                FROM conversations
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """
            results = self.db_manager.execute_query(query, (seven_days_ago,))

            if results:
                # Load messages with date separators
                for role, message, timestamp in results:
                    is_user = (role == 'user')
                    msg_datetime = datetime.fromisoformat(timestamp)
                    self._add_message(message, is_user, msg_datetime, save_to_db=False)

        except Exception as e:
            self.logger.error(f"Failed to load chat history: {e}")

    def _save_message_to_db(self, message: str, is_user: bool, timestamp):
        """Save a message to the database."""
        if not self.db_manager:
            return

        try:
            from datetime import datetime
            import uuid

            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = datetime.now().isoformat()

            # Determine role
            role = 'user' if is_user else 'assistant'

            conn = self.db_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversations (conversation_id, role, message, timestamp)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), role, message, timestamp_str))

            conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save message to database: {e}")

    # --- Chat Logic ---

    def _send_message(self):
        message = self.input_field.toPlainText().strip()
        if not message:
            return

        if not self.llm_service:
            QMessageBox.warning(self, "Not Ready", "P3 is initializing...")
            return

        from datetime import datetime
        self._add_message(message, is_user=True, timestamp=datetime.now())
        self.input_field.clear()

        # UI Feedback
        self.input_field.setEnabled(False)
        self.status_dot.setStyleSheet("color: #f39c12;")  # Orange for thinking

        # Threading
        self.chat_worker = ChatWorker(self.llm_service, message)
        self.chat_worker.response_ready.connect(self._handle_response)
        self.chat_worker.error_occurred.connect(self._handle_error)
        self.chat_worker.finished.connect(self._chat_finished)
        self.chat_worker.start()

    def _handle_response(self, agent_response: AgentResponse):
        from datetime import datetime
        self._add_message(agent_response.response, is_user=False, timestamp=datetime.now())

    def _handle_error(self, error_msg: str):
        from datetime import datetime
        self._add_message(f"⚠️ Error: {error_msg}", is_user=False, timestamp=datetime.now())

    def _chat_finished(self):
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.status_dot.setStyleSheet("color: #27ae60;")  # Green for ready

    def _add_message(self, text: str, is_user: bool, timestamp=None, save_to_db: bool = True):
        from datetime import datetime

        if timestamp is None:
            timestamp = datetime.now()

        # Check if we need to add a date separator
        message_date = timestamp.date() if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp).date()

        if self.last_message_date is None or self.last_message_date != message_date:
            # Different day, add date separator
            self._add_date_separator_for_date(message_date)
            self.last_message_date = message_date

        # Remove spacer
        if self.chat_layout.count() > 0:
            item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
            if item.spacerItem():
                self.chat_layout.removeItem(item)

        msg_widget = ModernChatMessage(text, is_user)
        self.chat_layout.addWidget(msg_widget)

        # Add spacer back
        self.chat_layout.addStretch()

        # Save to database if requested
        if save_to_db:
            self._save_message_to_db(text, is_user, timestamp)

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _add_date_separator_for_date(self, date):
        """Add a date separator for a specific date."""
        from datetime import datetime

        # Remove spacer
        if self.chat_layout.count() > 0:
            item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
            if item.spacerItem():
                self.chat_layout.removeItem(item)

        # Create separator
        separator = QLabel()
        today = datetime.now().date()

        # Determine separator text
        if date == today:
            separator_text = f"Today, {datetime.now().strftime('%B %d')}"
        elif (today - date).days == 1:
            separator_text = f"Yesterday, {date.strftime('%B %d')}"
        else:
            separator_text = date.strftime("%B %d, %Y")

        separator.setText(separator_text)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-size: 11px;
                padding: 8px 15px;
                background-color: #E9E9EB;
                border-radius: 10px;
                margin: 15px 100px;
            }
        """)

        self.chat_layout.addWidget(separator)
        self.chat_layout.addStretch()

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
            # 1. Inventory - Total items
            res = self.db_manager.execute_query("SELECT COUNT(*) FROM inventory")
            val = res[0][0] if res else 0
            self.stat_widgets["inventory"].update_value(str(val))

            # 2. Low Stock - Items at or below minimum quantity
            res = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM inventory WHERE quantity_current <= quantity_min AND quantity_min > 0"
            )
            val = res[0][0] if res else 0
            self.stat_widgets["low_stock"].update_value(str(val))

            # 3. Cart Items - Count items in active shopping carts
            cart_count = 0
            if self.cart_service:
                # Count items across all active carts
                for vendor, cart in self.cart_service.active_carts.items():
                    if cart and cart.items:
                        cart_count += len(cart.items)
            self.stat_widgets["pending"].update_value(str(cart_count))

        except Exception as e:
            self.logger.error(f"Stats update error: {e}")

    # --- Autonomous Agent Signal Handlers ---

    def _on_agent_cycle_started(self, cycle_id: str):
        """Called when P3 starts a maintenance cycle."""
        self.logger.info(f"P3 cycle started: {cycle_id}")
        self._add_activity("🔍 Checking inventory and groceries...")
        self.status_dot.setStyleSheet("color: #f39c12;")  # Orange for active

    def _on_agent_cycle_completed(self, cycle_id: str, summary: dict):
        """Called when P3 completes a cycle."""
        status = summary.get('status', 'unknown')
        self.logger.info(f"P3 cycle completed: {cycle_id} - Status: {status}")

        if status == 'completed':
            response = summary.get('response', '')
            # Use the response from the LLM as it should be in natural language
            if response and response != 'No actions taken':
                self._add_activity(f"✅ {response}")
        elif status == 'skipped':
            # Don't show skipped cycles to reduce clutter
            pass
        elif status == 'error':
            error = summary.get('error', 'Unknown error')
            self._add_activity(f"⚠️ Encountered an issue: {error}")

        self.status_dot.setStyleSheet("color: #27ae60;")  # Green for ready
        self._update_stats()  # Refresh stats after actions

    def _on_agent_action(self, action_type: str, description: str):
        """Called when P3 takes an action."""
        self.logger.info(f"P3 action: {action_type} - {description}")

        # Convert technical descriptions to natural language
        natural_message = self._convert_to_natural_language(action_type, description)
        self._add_activity(natural_message)

    def _convert_to_natural_language(self, action_type: str, description: str) -> str:
        """Convert technical action descriptions to natural language."""
        # Map action types to user-friendly messages
        if "low stock" in description.lower() or "running out" in description.lower():
            return f"🛒 {description}"
        elif "added to cart" in description.lower():
            return f"➕ {description}"
        elif "forecast" in description.lower():
            return f"📊 {description}"
        elif "training" in description.lower() or "model" in description.lower():
            return f"🧠 {description}"
        else:
            return f"ℹ️ {description}"