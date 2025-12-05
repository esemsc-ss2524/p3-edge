"""
Memory Service for Autonomous Agent

Manages the agent's persistent memory stream with importance-based pruning
and summarization capabilities.
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..database.db_manager import DatabaseManager
from ..utils import get_logger


@dataclass
class Memory:
    """A single memory entry."""
    memory_id: str
    cycle_id: Optional[str]
    timestamp: datetime
    memory_type: str
    content: str
    importance: int
    context: Optional[Dict[str, Any]]
    outcome: Optional[str]
    consolidated: bool


class MemoryService:
    """Service for managing autonomous agent memory."""

    def __init__(self, db_manager: DatabaseManager, max_entries: int = 1000):
        """
        Initialize memory service.

        Args:
            db_manager: Database manager instance
            max_entries: Maximum number of raw memories before pruning
        """
        self.db_manager = db_manager
        self.max_entries = max_entries
        self.logger = get_logger("memory_service")

    def add_memory(
        self,
        content: str,
        memory_type: str = "observation",
        importance: int = 1,
        cycle_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None
    ) -> str:
        """
        Add a new memory entry.

        Args:
            content: The memory content
            memory_type: Type of memory (observation, action, plan, summary, reflection)
            importance: Importance score 1-10
            cycle_id: ID of the autonomous cycle this belongs to
            context: Additional context as JSON
            outcome: Outcome of the action (success, failure, pending, skipped)

        Returns:
            Memory ID
        """
        memory_id = str(uuid.uuid4())

        try:
            query = """
                INSERT INTO agent_memory
                (memory_id, cycle_id, memory_type, content, importance, context, outcome, consolidated)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """
            self.db_manager.execute_update(
                query,
                (
                    memory_id,
                    cycle_id,
                    memory_type,
                    content,
                    min(max(importance, 1), 10),  # Clamp to 1-10
                    json.dumps(context) if context else None,
                    outcome
                )
            )

            # Check if pruning is needed
            count_query = "SELECT COUNT(*) FROM agent_memory WHERE consolidated = 0"
            result = self.db_manager.execute_query(count_query)
            count = result[0][0] if result else 0

            if count > self.max_entries:
                self.logger.info(f"Memory count ({count}) exceeds max ({self.max_entries}), triggering prune")
                self.prune_memory()

            return memory_id

        except Exception as e:
            self.logger.error(f"Error adding memory: {e}")
            raise

    def get_working_context(
        self,
        recent_limit: int = 10,
        important_limit: int = 5
    ) -> str:
        """
        Get a formatted context string for the LLM.

        Combines recent memories with important historical memories.

        Args:
            recent_limit: Number of recent memories to include
            important_limit: Number of important historical memories to include

        Returns:
            Formatted context string
        """
        try:
            # Get recent memories
            recent_query = """
                SELECT memory_type, content, timestamp, outcome
                FROM agent_memory
                ORDER BY timestamp DESC
                LIMIT ?
            """
            recent = self.db_manager.execute_query(recent_query, (recent_limit,))

            # Get important historical memories (high importance, not recent)
            important_query = """
                SELECT memory_type, content, timestamp, outcome
                FROM agent_memory
                WHERE importance >= 7
                  AND timestamp < datetime('now', '-1 hour')
                ORDER BY importance DESC, timestamp DESC
                LIMIT ?
            """
            important = self.db_manager.execute_query(important_query, (important_limit,))

            # Format context
            context_parts = []

            if important:
                context_parts.append("=== Important Historical Context ===")
                for row in important:
                    memory_type = row['memory_type']
                    content = row['content']
                    timestamp = row['timestamp']
                    outcome = row['outcome'] or 'N/A'
                    context_parts.append(f"[{timestamp}] {memory_type.upper()}: {content} (Outcome: {outcome})")

            if recent:
                context_parts.append("\n=== Recent Activity ===")
                for row in recent:
                    memory_type = row['memory_type']
                    content = row['content']
                    timestamp = row['timestamp']
                    outcome = row['outcome'] or 'N/A'
                    context_parts.append(f"[{timestamp}] {memory_type.upper()}: {content} (Outcome: {outcome})")

            if not context_parts:
                return "No previous memories."

            return "\n".join(context_parts)

        except Exception as e:
            self.logger.error(f"Error getting working context: {e}")
            return "Error retrieving memories."

    def get_cycle_memories(self, cycle_id: str) -> List[Memory]:
        """
        Get all memories for a specific cycle.

        Args:
            cycle_id: The cycle ID

        Returns:
            List of Memory objects
        """
        try:
            query = """
                SELECT memory_id, cycle_id, timestamp, memory_type, content,
                       importance, context, outcome, consolidated
                FROM agent_memory
                WHERE cycle_id = ?
                ORDER BY timestamp ASC
            """
            rows = self.db_manager.execute_query(query, (cycle_id,))

            memories = []
            for row in rows:
                memories.append(Memory(
                    memory_id=row['memory_id'],
                    cycle_id=row['cycle_id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    memory_type=row['memory_type'],
                    content=row['content'],
                    importance=row['importance'],
                    context=json.loads(row['context']) if row['context'] else None,
                    outcome=row['outcome'],
                    consolidated=bool(row['consolidated'])
                ))

            return memories

        except Exception as e:
            self.logger.error(f"Error getting cycle memories: {e}")
            return []

    def get_recent_memories(self, limit: int = 20) -> List[Memory]:
        """
        Get recent memories for UI display.

        Args:
            limit: Maximum number of memories to retrieve

        Returns:
            List of Memory objects
        """
        try:
            query = """
                SELECT memory_id, cycle_id, timestamp, memory_type, content,
                       importance, context, outcome, consolidated
                FROM agent_memory
                ORDER BY timestamp DESC
                LIMIT ?
            """
            rows = self.db_manager.execute_query(query, (limit,))

            memories = []
            for row in rows:
                memories.append(Memory(
                    memory_id=row['memory_id'],
                    cycle_id=row['cycle_id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    memory_type=row['memory_type'],
                    content=row['content'],
                    importance=row['importance'],
                    context=json.loads(row['context']) if row['context'] else None,
                    outcome=row['outcome'],
                    consolidated=bool(row['consolidated'])
                ))

            return memories

        except Exception as e:
            self.logger.error(f"Error getting recent memories: {e}")
            return []

    def prune_memory(self) -> int:
        """
        Prune old, low-importance memories.

        Strategy:
        1. Delete memories older than 30 days with importance < 3
        2. Delete oldest half of memories with importance < 5 if still over limit

        Returns:
            Number of memories deleted
        """
        deleted_count = 0

        try:
            # Step 1: Delete old, unimportant memories
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            delete_query = """
                DELETE FROM agent_memory
                WHERE timestamp < ?
                  AND importance < 3
                  AND consolidated = 0
            """
            result = self.db_manager.execute_update(delete_query, (cutoff_date,))
            deleted_count += result

            # Step 2: Check if still over limit
            count_query = "SELECT COUNT(*) FROM agent_memory WHERE consolidated = 0"
            result = self.db_manager.execute_query(count_query)
            count = result[0][0] if result else 0

            if count > self.max_entries:
                # Delete oldest half of low-importance memories
                to_delete = (count - self.max_entries) + 100  # Extra buffer

                delete_query = """
                    DELETE FROM agent_memory
                    WHERE memory_id IN (
                        SELECT memory_id FROM agent_memory
                        WHERE importance < 5 AND consolidated = 0
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                """
                result = self.db_manager.execute_update(delete_query, (to_delete,))
                deleted_count += result

            self.logger.info(f"Pruned {deleted_count} memories")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error pruning memory: {e}")
            return deleted_count

    def consolidate_old_memories(self, llm_service=None) -> bool:
        """
        Consolidate old memories into summaries using LLM.

        This is a future enhancement - requires LLM service to summarize.

        Args:
            llm_service: Optional LLM service for summarization

        Returns:
            True if consolidation succeeded
        """
        # Future enhancement: Use LLM to summarize old memories
        # For now, just mark old memories as candidates
        try:
            cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
            update_query = """
                UPDATE agent_memory
                SET consolidated = 1
                WHERE timestamp < ?
                  AND importance < 3
                  AND consolidated = 0
            """
            self.db_manager.execute_update(update_query, (cutoff_date,))
            return True

        except Exception as e:
            self.logger.error(f"Error consolidating memories: {e}")
            return False

    def clear_all_memories(self) -> bool:
        """
        Clear all memories (for testing/reset).

        Returns:
            True if successful
        """
        try:
            self.db_manager.execute_update("DELETE FROM agent_memory")
            self.logger.warning("All memories cleared")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing memories: {e}")
            return False

    # --- User Preferences Management ---

    def learn_preference(
        self,
        category: str,
        preference_key: str,
        preference_value: str,
        source: str = "chat",
        learned_from: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Learn or reinforce a user preference.

        If the preference already exists, increases confidence and mention count.
        If new, creates it with initial confidence.

        Args:
            category: 'dietary', 'allergy', 'product_preference', 'brand_preference', 'general'
            preference_key: e.g., 'milk_type', 'peanut_allergy'
            preference_value: e.g., 'oat milk', 'true'
            source: Where this was learned from ('chat', 'autonomous', 'manual')
            learned_from: conversation_id or cycle_id
            metadata: Additional context as JSON

        Returns:
            Preference ID
        """
        try:
            # Check if preference already exists
            check_query = """
                SELECT preference_id, confidence, mention_count
                FROM user_preferences
                WHERE preference_key = ? AND preference_value = ?
            """
            result = self.db_manager.execute_query(
                check_query,
                (preference_key, preference_value)
            )

            if result:
                # Update existing preference
                pref_id = result[0]['preference_id']
                current_confidence = result[0]['confidence']
                current_mentions = result[0]['mention_count']

                # Increase confidence (asymptotic to 1.0)
                new_confidence = min(current_confidence + (1.0 - current_confidence) * 0.3, 0.95)
                new_mentions = current_mentions + 1

                update_query = """
                    UPDATE user_preferences
                    SET confidence = ?,
                        mention_count = ?,
                        last_confirmed = CURRENT_TIMESTAMP,
                        source = ?,
                        learned_from = ?,
                        metadata = ?
                    WHERE preference_id = ?
                """
                self.db_manager.execute_update(
                    update_query,
                    (
                        new_confidence,
                        new_mentions,
                        source,
                        learned_from,
                        json.dumps(metadata) if metadata else None,
                        pref_id
                    )
                )

                self.logger.info(
                    f"Reinforced preference: {preference_key}={preference_value} "
                    f"(confidence: {current_confidence:.2f} -> {new_confidence:.2f}, "
                    f"mentions: {new_mentions})"
                )

                return pref_id

            else:
                # Create new preference
                pref_id = str(uuid.uuid4())

                insert_query = """
                    INSERT INTO user_preferences
                    (preference_id, category, preference_key, preference_value,
                     confidence, source, learned_from, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.db_manager.execute_update(
                    insert_query,
                    (
                        pref_id,
                        category,
                        preference_key,
                        preference_value,
                        0.5,  # Initial confidence
                        source,
                        learned_from,
                        json.dumps(metadata) if metadata else None
                    )
                )

                self.logger.info(f"Learned new preference: {preference_key}={preference_value}")

                return pref_id

        except Exception as e:
            self.logger.error(f"Error learning preference: {e}")
            raise

    def get_preferences(
        self,
        category: Optional[str] = None,
        min_confidence: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Get user preferences, optionally filtered by category.

        Args:
            category: Filter by category (None = all)
            min_confidence: Minimum confidence threshold (default 0.3)

        Returns:
            List of preference dictionaries
        """
        try:
            if category:
                query = """
                    SELECT preference_id, category, preference_key, preference_value,
                           confidence, source, learned_from, first_mentioned,
                           last_confirmed, mention_count, metadata
                    FROM user_preferences
                    WHERE category = ? AND confidence >= ?
                    ORDER BY confidence DESC, mention_count DESC
                """
                results = self.db_manager.execute_query(query, (category, min_confidence))
            else:
                query = """
                    SELECT preference_id, category, preference_key, preference_value,
                           confidence, source, learned_from, first_mentioned,
                           last_confirmed, mention_count, metadata
                    FROM user_preferences
                    WHERE confidence >= ?
                    ORDER BY category, confidence DESC, mention_count DESC
                """
                results = self.db_manager.execute_query(query, (min_confidence,))

            preferences = []
            for row in results:
                preferences.append({
                    'preference_id': row['preference_id'],
                    'category': row['category'],
                    'preference_key': row['preference_key'],
                    'preference_value': row['preference_value'],
                    'confidence': row['confidence'],
                    'source': row['source'],
                    'learned_from': row['learned_from'],
                    'first_mentioned': row['first_mentioned'],
                    'last_confirmed': row['last_confirmed'],
                    'mention_count': row['mention_count'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None
                })

            return preferences

        except Exception as e:
            self.logger.error(f"Error getting preferences: {e}")
            return []

    def get_preference_context(self, min_confidence: float = 0.5) -> str:
        """
        Get a formatted preference context string for LLM prompts.

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            Formatted string with user preferences
        """
        try:
            preferences = self.get_preferences(min_confidence=min_confidence)

            if not preferences:
                return "No strong user preferences learned yet."

            # Group by category
            by_category = {}
            for pref in preferences:
                cat = pref['category']
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(pref)

            # Format output
            lines = ["=== User Preferences (Learned) ==="]

            for category, prefs in sorted(by_category.items()):
                lines.append(f"\n{category.upper()}:")
                for pref in prefs:
                    confidence_pct = int(pref['confidence'] * 100)
                    lines.append(
                        f"  • {pref['preference_key']}: {pref['preference_value']} "
                        f"({confidence_pct}% confident, mentioned {pref['mention_count']}x)"
                    )

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"Error getting preference context: {e}")
            return "Error retrieving user preferences."

    def get_preference_value(
        self,
        preference_key: str,
        min_confidence: float = 0.5
    ) -> Optional[str]:
        """
        Get the value for a specific preference key if confidence is high enough.

        Args:
            preference_key: The preference key to look up
            min_confidence: Minimum confidence required

        Returns:
            Preference value or None if not found/low confidence
        """
        try:
            query = """
                SELECT preference_value, confidence
                FROM user_preferences
                WHERE preference_key = ? AND confidence >= ?
                ORDER BY confidence DESC, mention_count DESC
                LIMIT 1
            """
            result = self.db_manager.execute_query(query, (preference_key, min_confidence))

            if result:
                return result[0]['preference_value']

            return None

        except Exception as e:
            self.logger.error(f"Error getting preference value: {e}")
            return None
