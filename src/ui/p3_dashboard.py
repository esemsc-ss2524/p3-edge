from typing import Optional, List, Dict, Any
from pathlib import Path
import json

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, 
    QFrame, QScrollArea, QMessageBox, QSizePolicy, QGraphicsDropShadowEffect,
    QListWidget, QListWidgetItem, QInputDialog, QProgressBar
)
from PyQt6.QtGui import QMovie, QColor, QFont, QIcon, QPainter, QBrush, QPen

from ..services.llm_service import LLMService
from ..services.llm_factory import create_llm_service
from ..config import get_config_manager
from ..models.tool_models import AgentResponse
from ..database.db_manager import DatabaseManager
from ..utils import get_logger

# --- Modern UI Components ---

class ModernCard(QFrame):
    """A sleek, rounded card container with optional shadow."""
    def __init__(self, parent=None, bg_color="#FFFFFF"):
        super().__init__(parent)
        self.setStyleSheet(f"""
            ModernCard {{
                background-color: {bg_color};
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }}
        """)
        # Subtle shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

class StatPill(QFrame):
    """Futuristic HUD stat pill."""
    def __init__(self, label: str, value: str, icon: str, color: str):
        super().__init__()
        self.setFixedSize(140, 80)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-radius: 16px;
                border-left: 4px solid {color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(2)
        
        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 16px;")
        lbl_title = QLabel(label)
        lbl_title.setStyleSheet("color: #8E8E93; font-size: 11px; font-weight: 600; text-transform: uppercase;")
        top_row.addWidget(icon_lbl)
        top_row.addWidget(lbl_title)
        top_row.addStretch()
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: #1C1C1E; font-size: 24px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
        
        layout.addLayout(top_row)
        layout.addWidget(self.lbl_value)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def update_value(self, value):
        self.lbl_value.setText(str(value))

class ChatMessage(QFrame):
    """Modern Apple-style chat bubble."""
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        msg_label = QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_label.setFont(QFont("Segoe UI", 11))

        if is_user:
            layout.addStretch()
            msg_label.setStyleSheet("""
                QLabel {
                    background-color: #007AFF;
                    color: white;
                    padding: 12px 16px;
                    border-radius: 18px;
                    border-bottom-right-radius: 4px;
                }
            """)
            layout.addWidget(msg_label)
        else:
            msg_label.setStyleSheet("""
                QLabel {
                    background-color: #E5E5EA;
                    color: black;
                    padding: 12px 16px;
                    border-radius: 18px;
                    border-bottom-left-radius: 4px;
                }
            """)
            layout.addWidget(msg_label)
            layout.addStretch()

# --- Workers ---

class ChatWorker(QThread):
    response_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, llm_service, message):
        super().__init__()
        self.llm_service = llm_service
        self.message = message

    def run(self):
        try:
            if self.llm_service.tool_executor:
                response = self.llm_service.chat_with_tools(self.message)
                self.response_ready.emit(response)
            else:
                resp_text = self.llm_service.chat(self.message)
                self.response_ready.emit(AgentResponse(response=resp_text))
        except Exception as e:
            self.error_occurred.emit(str(e))

# --- Main Dashboard ---

class P3Dashboard(QWidget):
    def __init__(self, db_manager: DatabaseManager, tool_executor=None, autonomous_agent=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.autonomous_agent = autonomous_agent
        self.logger = get_logger("p3_dashboard")
        
        self.llm_service = None
        self.stat_widgets = {}
        
        # Init
        self._setup_ui()
        self._initialize_llm()
        self._update_stats()
        
        # Connect Autonomous Agent Signals
        if self.autonomous_agent:
            self.autonomous_agent.cycle_started.connect(self._on_auto_started)
            self.autonomous_agent.action_taken.connect(self._on_auto_action)
            self.autonomous_agent.cycle_completed.connect(self._on_auto_completed)

        # Timers
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(5000)  # Update HUD every 5s

    def _setup_ui(self):
        # Global Style
        self.setStyleSheet("background-color: #F2F2F7; font-family: 'Segoe UI';")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # =================================================
        # LEFT COLUMN: P2 Autonomous Log (The "Working" Side)
        # =================================================
        left_col = QVBoxLayout()
        left_col.setSpacing(20)

        # 1. P2 Working Avatar
        self.p2_work_card = ModernCard(bg_color="transparent")
        self.p2_work_card.setFixedHeight(200)
        work_layout = QVBoxLayout(self.p2_work_card)
        
        self.work_anim_label = QLabel()
        self.work_anim_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._play_animation(self.work_anim_label, "assets/p2_working.webp", default_text="⚙️ P2 Working")
        work_layout.addWidget(self.work_anim_label)
        left_col.addWidget(self.p2_work_card)

        # 2. Autonomous Activity Log
        log_card = ModernCard()
        log_layout = QVBoxLayout(log_card)
        log_header = QLabel("AUTONOMOUS ACTIVITY")
        log_header.setStyleSheet("font-size: 12px; font-weight: 700; color: #8E8E93; letter-spacing: 1px;")
        log_layout.addWidget(log_header)

        self.auto_log_list = QListWidget()
        self.auto_log_list.setFrameShape(QFrame.Shape.NoFrame)
        self.auto_log_list.setStyleSheet("""
            QListWidget { background: transparent; }
            QListWidget::item { padding: 8px 0; border-bottom: 1px solid #F2F2F7; }
        """)
        log_layout.addWidget(self.auto_log_list)
        left_col.addWidget(log_card, stretch=1)

        # 3. HUD Stats & Budget (Moved here)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # HUD Pills
        self.stat_widgets["low_stock"] = StatPill("LOW STOCK", "0", "⚠️", "#FF3B30")
        self.stat_widgets["cart"] = StatPill("IN CART", "0", "🛒", "#007AFF")
        
        stats_layout.addWidget(self.stat_widgets["low_stock"])
        stats_layout.addWidget(self.stat_widgets["cart"])
        left_col.addLayout(stats_layout)

        # Budget Control
        budget_card = ModernCard()
        budget_layout = QHBoxLayout(budget_card)
        
        budget_icon = QLabel("💳")
        budget_icon.setStyleSheet("font-size: 20px;")
        
        info_layout = QVBoxLayout()
        lbl_budget_title = QLabel("WEEKLY BUDGET")
        lbl_budget_title.setStyleSheet("font-size: 10px; color: #8E8E93; font-weight: 700;")
        self.lbl_budget_value = QLabel("$0.00")
        self.lbl_budget_value.setStyleSheet("font-size: 18px; font-weight: 700; color: #1C1C1E;")
        info_layout.addWidget(lbl_budget_title)
        info_layout.addWidget(self.lbl_budget_value)
        
        btn_edit_budget = QPushButton("Edit")
        btn_edit_budget.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit_budget.clicked.connect(self._edit_budget)
        btn_edit_budget.setStyleSheet("""
            QPushButton {
                background-color: #E5E5EA; color: #007AFF; font-weight: 600;
                border-radius: 12px; padding: 6px 12px; border: none;
            }
            QPushButton:hover { background-color: #D1D1D6; }
        """)

        budget_layout.addWidget(budget_icon)
        budget_layout.addLayout(info_layout)
        budget_layout.addStretch()
        budget_layout.addWidget(btn_edit_budget)
        
        left_col.addWidget(budget_card)

        # Add Left Column to Main
        main_layout.addLayout(left_col, stretch=40)

        # =================================================
        # RIGHT COLUMN: Chat with P2 (The "Talking" Side)
        # =================================================
        right_col = QVBoxLayout()
        right_col.setSpacing(20)

        # 1. P2 Chat Avatar (Waist Up)
        self.p2_chat_card = ModernCard(bg_color="transparent")
        self.p2_chat_card.setFixedHeight(220)
        chat_anim_layout = QVBoxLayout(self.p2_chat_card)
        
        self.chat_anim_label = QLabel()
        self.chat_anim_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._play_animation(self.chat_anim_label, "assets/p2_idle.webp", default_text="🤖 P2 Ready")
        chat_anim_layout.addWidget(self.chat_anim_label)
        right_col.addWidget(self.p2_chat_card)

        # 2. Chat Area
        self.chat_area = ModernCard()
        chat_layout_inner = QVBoxLayout(self.chat_area)
        
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setStyleSheet("background: transparent;")
        
        self.chat_content = QWidget()
        self.chat_content_layout = QVBoxLayout(self.chat_content)
        self.chat_content_layout.addStretch()
        
        self.chat_scroll.setWidget(self.chat_content)
        chat_layout_inner.addWidget(self.chat_scroll)
        
        # Input Area
        input_container = QWidget()
        input_row = QHBoxLayout(input_container)
        input_row.setContentsMargins(0, 10, 0, 0)
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Ask P2 anything...")
        self.input_field.setFixedHeight(50)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: #F2F2F7; border: none; border-radius: 20px;
                padding: 10px 15px; font-size: 14px;
            }
        """)
        
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(40, 40)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._send_message)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #007AFF; color: white; border-radius: 20px;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0062CC; }
        """)
        
        input_row.addWidget(self.input_field)
        input_row.addWidget(self.btn_send)
        
        chat_layout_inner.addWidget(input_container)
        
        right_col.addWidget(self.chat_area, stretch=1)
        
        # Add Right Column to Main
        main_layout.addLayout(right_col, stretch=60)

    # --- Logic ---

    def _play_animation(self, label: QLabel, path_str: str, default_text=""):
        path = Path(path_str)
        if path.exists():
            movie = QMovie(str(path))
            movie.setCacheMode(QMovie.CacheMode.CacheAll)
            # Scale
            label.setMovie(movie)
            movie.start()
            # Simple scaling to height
            size = QSize(400, 200) # approximate
            movie.setScaledSize(size)
        else:
            label.setText(default_text)
            label.setStyleSheet("font-size: 40px;")

    def _update_stats(self):
        """Update HUD stats with accurate queries."""
        if not self.db_manager: return
        
        try:
            # 1. Low Stock: Actual count based on min threshold
            res = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM inventory WHERE quantity_current <= quantity_min"
            )
            low_count = res[0][0] if res else 0
            self.stat_widgets["low_stock"].update_value(str(low_count))

            # 2. Cart: Count items inside JSON of Pending orders
            # Schema: items is JSON string in 'orders' table
            res = self.db_manager.execute_query(
                "SELECT items FROM orders WHERE status = 'PENDING_APPROVAL'"
            )
            total_cart_items = 0
            for row in res:
                items_json = row['items']
                try:
                    items_list = json.loads(items_json)
                    # Sum quantities of items in this order
                    total_cart_items += len(items_list) # OR sum(i.get('quantity', 1) for i in items_list)
                except:
                    pass
            self.stat_widgets["cart"].update_value(str(total_cart_items))

            # 3. Budget Update
            prefs = self.db_manager.get_preferences()
            weekly = prefs.get("spend_cap_weekly", 0.0)
            self.lbl_budget_value.setText(f"${float(weekly):.2f}")

        except Exception as e:
            self.logger.error(f"Stats update error: {e}")

    def _edit_budget(self):
        """Open dialog to edit weekly budget."""
        current_text = self.lbl_budget_value.text().replace("$", "")
        val, ok = QInputDialog.getDouble(self, "Set Budget", "Weekly Grocery Budget ($):", 
                                       float(current_text), 0, 10000, 2)
        if ok:
            self.db_manager.set_preference("spend_cap_weekly", val)
            self._update_stats()
            # Log specific action
            self._add_chat_message(f"System: Budget updated to ${val:.2f}", is_user=False)

    # --- Chat Logic ---

    def _send_message(self):
        msg = self.input_field.toPlainText().strip()
        if not msg: return
        
        self._add_chat_message(msg, is_user=True)
        self.input_field.clear()
        
        # Change animation
        self._play_animation(self.chat_anim_label, "assets/p2_thinking.webp", "🤔 Thinking...")
        
        self.chat_worker = ChatWorker(self.llm_service, msg)
        self.chat_worker.response_ready.connect(self._on_response)
        self.chat_worker.start()

    def _on_response(self, response: AgentResponse):
        self._add_chat_message(response.response, is_user=False)
        self._play_animation(self.chat_anim_label, "assets/p2_idle.webp", "🤖 P2 Ready")

    def _add_chat_message(self, text, is_user):
        msg_widget = ChatMessage(text, is_user)
        self.chat_content_layout.addWidget(msg_widget)
        # Scroll to bottom
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    # --- Autonomous Log Logic ---

    def _log_auto_event(self, text, color="#1C1C1E"):
        item = QListWidgetItem(text)
        item.setForeground(QBrush(QColor(color)))
        font = QFont("Segoe UI", 10)
        item.setFont(font)
        self.auto_log_list.addItem(item)
        self.auto_log_list.scrollToBottom()

    def _on_auto_started(self, cycle_id):
        self._play_animation(self.work_anim_label, "assets/p2_working_active.webp", "⚡ Working...")
        self._log_auto_event(f"▶ Cycle {cycle_id[:6]} started...", "#007AFF")

    def _on_auto_action(self, action, desc):
        self._log_auto_event(f"⚙ {action}: {desc}", "#34C759")

    def _on_auto_completed(self, cycle_id, summary):
        self._play_animation(self.work_anim_label, "assets/p2_working.webp", "⚙️ P2 Working")
        status = summary.get('status', 'done')
        color = "#8E8E93" if status == 'skipped' else "#34C759"
        self._log_auto_event(f"◼ Cycle finished: {status}", color)

    def _initialize_llm(self):
        # ... (Keep existing initialization logic) ...
        try:
            config = get_config_manager()
            provider = config.get("llm.provider", "ollama")
            factory_args = {"provider": provider, "tool_executor": self.tool_executor}
            if provider == "ollama":
                factory_args["model_name"] = config.get("llm.ollama.model", "gemma:2b")
            elif provider == "gemini":
                 # Load key
                 pass 
            self.llm_service = create_llm_service(**factory_args)
        except Exception as e:
            self.logger.error(f"Init Error: {e}")