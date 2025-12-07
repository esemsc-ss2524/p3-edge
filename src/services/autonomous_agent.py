"""
Autonomous Agent Service

Transforms the passive ProactiveAssistant into an autonomous agent that:
- Runs on a scheduled cycle
- Maintains persistent memory
- Autonomously executes tools to maintain system health
- Logs all decisions and actions
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, QThread

from ..database.db_manager import DatabaseManager
from ..services.llm_factory import create_llm_service
from ..services.llm_service import LLMService
from ..services.memory_service import MemoryService
from ..tools.executor import ToolExecutor
from ..utils import get_logger, get_audit_logger
from ..models import ActionType, Actor


class AgentCycleWorker(QThread):
    """
    Worker thread for running autonomous agent cycles.

    This prevents UI freezing during long-running LLM operations.
    """
    cycle_completed = pyqtSignal(str, dict)  # cycle_id, summary
    action_taken = pyqtSignal(str, str)  # action_type, description
    error_occurred = pyqtSignal(str, str)  # error_message, cycle_id

    def __init__(
        self,
        cycle_id: str,
        llm_service: LLMService,
        memory: MemoryService,
        db_manager: DatabaseManager,
        audit_logger,
        system_prompt: str,
        trigger_reason: str
    ):
        super().__init__()
        self.cycle_id = cycle_id
        self.llm_service = llm_service
        self.memory = memory
        self.db_manager = db_manager
        self.audit_logger = audit_logger
        self.system_prompt = system_prompt
        self.trigger_reason = trigger_reason
        self.logger = get_logger("agent_worker")

    def run(self):
        """Execute the autonomous cycle in background thread."""
        try:
            self.logger.info(f"Worker thread started for cycle {self.cycle_id}")

            # Add initial memory
            self.memory.add_memory(
                content=f"Starting decision cycle. Reason: {self.trigger_reason}",
                memory_type="observation",
                importance=50,
                cycle_id=self.cycle_id,
                outcome="pending"
            )

            # print(" ======== system prompt ========= " + self.system_prompt + "\n")

            # Execute LLM with tools (this is the blocking operation)
            response = self.llm_service.chat_with_tools(
                message="Execute autonomous maintenance cycle based on current state.",
                system_prompt=self.system_prompt,
                max_iterations=50
            )

            # Process results - iterate over tool_results instead of tool_calls
            for tool_result in response.tool_results:
                tool_name = tool_result.tool_name
                outcome = "success" if tool_result.status == "success" else "failure"

                # Find corresponding tool_call for parameters
                tool_call = next((tc for tc in response.tool_calls if tc.tool_name == tool_name), None)
                parameters = tool_call.arguments if tool_call else {}

                # Create memory
                context = {
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "result": str(tool_result.result)[:200] if tool_result.result else None,
                    "error": tool_result.error
                }

                content = f"Executed {tool_name}"
                if tool_result.error:
                    content += f" - Failed: {tool_result.error}"
                else:
                    content += f" - Success"

                importance = 7 if tool_name in ["add_to_cart", "start_model_training"] else 5

                self.memory.add_memory(
                    content=content,
                    memory_type="action",
                    importance=importance,
                    cycle_id=self.cycle_id,
                    context=context,
                    outcome=outcome
                )

                # Emit signal for UI update
                self.action_taken.emit(tool_name, content)

                # Audit log
                self.audit_logger.log_action(
                    action_type=f"autonomous_{tool_name}",
                    actor=Actor.SYSTEM.value,
                    details=context,
                    outcome=outcome
                )

            # Log final response
            self.memory.add_memory(
                content=f"Cycle decision: {response.response}",
                memory_type="reflection",
                importance=6,
                cycle_id=self.cycle_id,
                context={"iterations": response.iterations},
                outcome="success"
            )

            # Check if preference memory needs summarization
            if self.memory.should_summarize_preferences(threshold=90.0):
                self.logger.warning("Preference memory at 90% capacity, triggering summarization")
                try:
                    success = self.memory.summarize_preferences(llm_service=self.llm_service)
                    if success:
                        self.logger.info("Preference summarization completed successfully")
                    else:
                        self.logger.error("Preference summarization failed")
                except Exception as e:
                    self.logger.error(f"Error during preference summarization: {e}")

            # Emit completion signal
            summary = {
                "status": "completed",
                "tool_calls": len(response.tool_calls),
                "iterations": response.iterations,
                "response": response.response
            }
            self.cycle_completed.emit(self.cycle_id, summary)

            self.logger.info(f"Worker thread completed for cycle {self.cycle_id}")

        except Exception as e:
            self.logger.error(f"Error in worker thread: {e}", exc_info=True)
            self.error_occurred.emit(str(e), self.cycle_id)


class AutonomousAgent(QObject):
    """
    Autonomous agent that proactively manages inventory and orders.

    Runs on a scheduled cycle using QTimer for Qt integration.
    Maintains memory of past actions and learns from outcomes.
    """

    # Signals for UI updates
    cycle_started = pyqtSignal(str)  # cycle_id
    cycle_completed = pyqtSignal(str, dict)  # cycle_id, summary
    action_taken = pyqtSignal(str, str)  # action_type, description

    def __init__(
        self,
        db_manager: DatabaseManager,
        tool_executor: ToolExecutor,
        cycle_interval_minutes: int = 60,  # Run every hour by default
        enabled: bool = True
    ):
        """
        Initialize autonomous agent.

        Args:
            db_manager: Database manager instance
            tool_executor: Tool executor for running actions
            cycle_interval_minutes: How often to run the cycle (default: 60 minutes)
            enabled: Whether agent is enabled on startup
        """
        super().__init__()

        self.db_manager = db_manager
        self.tool_executor = tool_executor
        self.cycle_interval_minutes = cycle_interval_minutes
        self.enabled = enabled

        self.logger = get_logger("autonomous_agent")
        self.audit_logger = get_audit_logger(db_manager)

        # Initialize services
        self.memory = MemoryService(db_manager)
        self.llm_service: Optional[LLMService] = None

        # State tracking
        self.current_cycle_id: Optional[str] = None
        self.is_running = False
        self.last_cycle_time: Optional[datetime] = None
        self.worker: Optional[AgentCycleWorker] = None

        # QTimer for periodic execution
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timer_tick)

        # Safety limits per cycle
        self.max_items_per_cycle = 10  # Don't add more than 3 items per cycle
        self.max_spend_per_cycle = 100.0  # Don't spend more than $50 per cycle
        self.cooldown_after_action_minutes = 5  # Wait 30 min after taking action

        self.logger.info(
            f"Autonomous agent initialized (interval: {cycle_interval_minutes}m, enabled: {enabled})"
        )

    def start(self, initial_delay_seconds: int = 60):
        """
        Start the autonomous agent.

        Args:
            initial_delay_seconds: Delay before first cycle (default: 60s for startup, 5s for UI enable)
        """
        if not self.enabled:
            self.logger.info("Autonomous agent is disabled, not starting")
            return

        # Initialize LLM service
        if not self.llm_service:
            self._initialize_llm()

        # Start timer
        interval_ms = self.cycle_interval_minutes * 60 * 1000
        self.timer.start(interval_ms)

        self.logger.info(f"Autonomous agent started (checking every {self.cycle_interval_minutes} minutes)")

        # Run initial cycle after specified delay
        QTimer.singleShot(initial_delay_seconds * 1000, self.run_cycle)
        self.logger.info(f"First cycle will run in {initial_delay_seconds} seconds")

    def stop(self):
        """Stop the autonomous agent."""
        self.timer.stop()
        self.logger.info("Autonomous agent stopped")

    def set_enabled(self, enabled: bool, initial_delay_seconds: int = 5):
        """
        Enable or disable the agent.

        Args:
            enabled: Whether to enable the agent
            initial_delay_seconds: Delay before first cycle when enabling (default: 5s for UI)
        """
        self.enabled = enabled
        if enabled:
            self.start(initial_delay_seconds=initial_delay_seconds)
        else:
            self.stop()

    def _initialize_llm(self):
        """Initialize LLM service for reasoning."""
        try:
            from ..config import get_config_manager
            config = get_config_manager()
            provider = config.get("llm.provider", "ollama")

            self.llm_service = create_llm_service(
                provider=provider,
                tool_executor=self.tool_executor
            )
            self.logger.info(f"LLM service initialized ({provider})")

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
            raise

    def _on_timer_tick(self):
        """Called by QTimer on each interval."""
        self.run_cycle()

    def run_cycle(self):
        """
        Execute one autonomous cycle using a background worker thread.

        This is the main autonomous loop:
        1. Check if should run (cooldown, already running)
        2. Quick heuristic checks (on main thread - fast)
        3. Build context and system prompt (on main thread - fast)
        4. Spawn worker thread for LLM reasoning (prevents UI freeze)
        5. Worker executes tools and saves memories
        """
        if not self.enabled:
            return

        if self.is_running:
            self.logger.warning("Cycle already running, skipping")
            return

        # Check cooldown
        if self.last_cycle_time:
            time_since_last = (datetime.now() - self.last_cycle_time).total_seconds() / 60
            if time_since_last < self.cooldown_after_action_minutes:
                self.logger.debug(f"In cooldown period ({time_since_last:.1f}m / {self.cooldown_after_action_minutes}m)")
                return

        self.is_running = True
        self.current_cycle_id = str(uuid.uuid4())

        self.logger.info(f"Starting autonomous cycle: {self.current_cycle_id}")
        self.cycle_started.emit(self.current_cycle_id)

        try:
            # Step 1: Quick heuristic checks (fast - on main thread)
            should_act, reason = self._should_take_action()

            if not should_act:
                self.logger.info(f"No action needed: {reason}")
                self.memory.add_memory(
                    content=f"Routine check: {reason}",
                    memory_type="observation",
                    importance=1,
                    cycle_id=self.current_cycle_id,
                    outcome="skipped"
                )
                self._complete_cycle({"status": "skipped", "reason": reason})
                return

            # Step 2: Build context (fast - on main thread)
            memory_context = self.memory.get_working_context(recent_limit=10, important_limit=5)

            # Step 3: Get current state (fast - on main thread)
            state_summary = self._get_state_summary()

            # Step 4: Build system prompt (fast - on main thread)
            self.logger.info("Spawning worker thread for LLM reasoning")
            system_prompt = self._build_system_prompt(memory_context, state_summary, reason)

            # Step 5: Create and start worker thread (prevents UI freeze)
            self.worker = AgentCycleWorker(
                cycle_id=self.current_cycle_id,
                llm_service=self.llm_service,
                memory=self.memory,
                db_manager=self.db_manager,
                audit_logger=self.audit_logger,
                system_prompt=system_prompt,
                trigger_reason=reason
            )

            # Connect worker signals
            self.worker.cycle_completed.connect(self._on_worker_completed)
            self.worker.action_taken.connect(self._on_worker_action)
            self.worker.error_occurred.connect(self._on_worker_error)
            self.worker.finished.connect(self._on_worker_finished)

            # Start worker thread
            self.worker.start()
            self.logger.info(f"Worker thread started for cycle {self.current_cycle_id}")

        except Exception as e:
            self.logger.error(f"Error starting cycle: {e}", exc_info=True)
            self.memory.add_memory(
                content=f"Cycle failed to start: {str(e)}",
                memory_type="observation",
                importance=8,
                cycle_id=self.current_cycle_id,
                outcome="failure"
            )
            self._complete_cycle({"status": "error", "error": str(e)})
            self.is_running = False

    def _should_take_action(self) -> tuple[bool, str]:
        """
        Multi-signal heuristic check.
        Aggregates all triggering conditions so LLM can weigh them equally.

        Returns:
            (should_act, combined_reason)
        """
        try:
            reasons = []

            # Check 1: Low stock items
            low_stock_query = """
                SELECT COUNT(*) FROM inventory
                WHERE quantity_current < quantity_min
            """
            result = self.db_manager.execute_query(low_stock_query)
            low_stock_count = result[0][0] if result else 0

            if low_stock_count > 0:
                reasons.append(f"{low_stock_count} item(s) below minimum stock")

            # Check 2: Items expiring soon (next 3 days)
            expiring_query = """
                SELECT COUNT(*) FROM inventory
                WHERE expiry_date IS NOT NULL
                AND expiry_date <= date('now', '+3 days')
                AND expiry_date > date('now')
            """
            result = self.db_manager.execute_query(expiring_query)
            expiring_count = result[0][0] if result else 0

            if expiring_count > 0:
                reasons.append(f"{expiring_count} item(s) expiring within 3 days")

            # Check 3: Forecasts predicting runout soon (next 3 days)
            forecast_query = """
                SELECT COUNT(*) FROM forecasts
                WHERE predicted_runout_date <= date('now', '+3 days')
                AND predicted_runout_date > date('now')
            """
            result = self.db_manager.execute_query(forecast_query)
            forecast_count = result[0][0] if result else 0

            if forecast_count > 0:
                reasons.append(f"{forecast_count} item(s) predicted to run out within 3 days")

            # Check 4: Pending orders need approval
            pending_query = """
                SELECT COUNT(*) FROM orders
                WHERE status = 'PENDING'
            """
            result = self.db_manager.execute_query(pending_query)
            pending_count = result[0][0] if result else 0

            if pending_count > 0:
                reasons.append(f"{pending_count} order(s) pending approval")

            # ✅ Final decision (multi-factor)
            if reasons:
                # Join cleanly for LLM context
                combined_reason = " | ".join(reasons)
                return True, combined_reason

            return False, "All systems healthy"

        except Exception as e:
            self.logger.error(f"Error in heuristic checks: {e}")
            return False, f"Error checking state: {str(e)}"


    def _get_state_summary(self) -> str:
        """Get current system state summary."""
        try:
            summary_parts = []

            # Inventory summary
            inv_query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN quantity_current < quantity_min THEN 1 ELSE 0 END) as low_stock,
                    SUM(CASE WHEN quantity_current >= quantity_max THEN 1 ELSE 0 END) as overstocked
                FROM inventory
            """
            result = self.db_manager.execute_query(inv_query)
            if result:
                row = result[0]
                summary_parts.append(
                    f"Inventory: {row[0]} total items, {row[1]} low stock, {row[2]} overstocked"
                )

            # ✅ Forecast runout summary (next 3 days)
            forecast_summary_query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE 
                        WHEN predicted_runout_date <= date('now', '+3 days')
                        AND predicted_runout_date > date('now')
                        THEN 1 ELSE 0 END
                    ) as runout_soon
                FROM forecasts
            """
            result = self.db_manager.execute_query(forecast_summary_query)
            if result:
                row = result[0]
                summary_parts.append(
                    f"Forecasts: {row[0]} tracked items, {row[1]} predicted to run out within 3 days"
                )

            # Cart summary
            cart_query = """
                SELECT vendor, COUNT(*) as items
                FROM orders
                WHERE status = 'PENDING'
                GROUP BY vendor
            """
            result = self.db_manager.execute_query(cart_query)
            if result:
                carts = [f"{row[1]} items in {row[0]} cart" for row in result]
                summary_parts.append(f"Cart: {', '.join(carts)}")
            else:
                summary_parts.append("Cart: Empty")

            # Budget summary
            budget_query = """
                SELECT SUM(total_cost) FROM orders
                WHERE created_at >= date('now', '-3 days')
                AND status IN ('PENDING', 'APPROVED', 'PLACED')
            """
            result = self.db_manager.execute_query(budget_query)
            weekly_spend = result[0][0] if result and result[0][0] else 0.0
            summary_parts.append(f"Weekly spend: ${weekly_spend:.2f}")

            return "\n".join(summary_parts)

        except Exception as e:
            self.logger.error(f"Error getting state summary: {e}")
            return "Error retrieving state"


    def _build_system_prompt(
        self,
        memory_context: str,
        state_summary: str,
        action_reason: str
    ) -> str:
        """Build the system prompt for LLM reasoning."""
        # Get user preferences
        preference_context = self.memory.get_preference_context(min_confidence=0.5)

        return f"""You are P3, an autonomous home management agent.

Your role is to proactively maintain household inventory by:
1. Monitoring stock levels and forecasts
2. Searching for needed items on vendors
3. Adding items to cart for user approval
4. NEVER placing orders (user must approve)

IMPORTANT SAFETY CONSTRAINTS:
- Maximum {self.max_items_per_cycle} items per cycle
- Maximum ${self.max_spend_per_cycle} spending per cycle
- DO NOT add items already in cart
- DO NOT place orders (blocked tool)
- ALWAYS check budget before adding to cart

USER PREFERENCES (LEARNED):
{preference_context}

IMPORTANT: When searching for products, ALWAYS respect user preferences:
- Check learned preferences BEFORE searching (use get_learned_preferences tool)
- Apply dietary preferences (e.g., if user prefers oat milk, search for "oat milk" not just "milk")
- Avoid allergens (e.g., if user has peanut allergy, never add peanut products)
- Prefer user's preferred brands when available

CURRENT STATE:
{state_summary}

TRIGGER REASON:
{action_reason}

MEMORY CONTEXT:
{memory_context}

YOUR TASK:
Analyze the current state and take appropriate actions to maintain system health.
Focus on the highest priority items first.
ALWAYS check user preferences before making product decisions.
Log your reasoning clearly.
Stop when constraints are met or all critical issues addressed.
Act independently without asking user for confirmation.
"""

    def _on_worker_completed(self, cycle_id: str, summary: dict):
        """Called when worker thread completes successfully."""
        self.logger.info(f"Worker completed for cycle {cycle_id}")
        self._complete_cycle(summary)

    def _on_worker_action(self, action_type: str, description: str):
        """Called when worker thread executes an action."""
        # Forward signal to UI
        self.action_taken.emit(action_type, description)

    def _on_worker_error(self, error_msg: str, cycle_id: str):
        """Called when worker thread encounters an error."""
        self.logger.error(f"Worker error for cycle {cycle_id}: {error_msg}")
        self.memory.add_memory(
            content=f"Cycle failed with error: {error_msg}",
            memory_type="observation",
            importance=8,
            cycle_id=cycle_id,
            outcome="failure"
        )
        self._complete_cycle({"status": "error", "error": error_msg})

    def _on_worker_finished(self):
        """Called when worker thread finishes (regardless of success/error)."""
        self.logger.info("Worker thread finished")
        self.is_running = False
        self.last_cycle_time = datetime.now()
        self.worker = None

    def _complete_cycle(self, summary: Dict[str, Any]):
        """Complete the current cycle and emit summary."""
        self.logger.info(f"Cycle {self.current_cycle_id} completed: {summary}")
        self.cycle_completed.emit(self.current_cycle_id, summary)

        # Audit log
        self.audit_logger.log_action(
            action_type=ActionType.AGENT_CYCLE.value if hasattr(ActionType, 'AGENT_CYCLE') else "autonomous_cycle",
            actor=Actor.SYSTEM.value,
            details={"cycle_id": self.current_cycle_id, "summary": summary}
        )

        self.current_cycle_id = None

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "current_cycle_id": self.current_cycle_id,
            "last_cycle_time": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            "cycle_interval_minutes": self.cycle_interval_minutes,
            "next_cycle_minutes": self.cycle_interval_minutes - (
                (datetime.now() - self.last_cycle_time).total_seconds() / 60
                if self.last_cycle_time else 0
            )
        }
