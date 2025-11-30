"""
Item matching utilities for inventory deduplication.

Provides fuzzy matching to detect duplicate items.
"""

from typing import List, Optional, Tuple

from fuzzywuzzy import fuzz

from src.models import InventoryItem


class ItemMatcher:
    """Matches new items against existing inventory to prevent duplicates."""

    def __init__(self, similarity_threshold: int = 85):
        """
        Initialize item matcher.

        Args:
            similarity_threshold: Minimum similarity score (0-100) to consider a match
        """
        self.similarity_threshold = similarity_threshold

    def find_match(
        self, new_item_name: str, existing_items: List[InventoryItem]
    ) -> Optional[Tuple[InventoryItem, int]]:
        """
        Find best matching item from existing inventory.

        Args:
            new_item_name: Name of new item to match
            existing_items: List of existing inventory items

        Returns:
            Tuple of (matched_item, similarity_score) or None if no good match
        """
        if not existing_items:
            return None

        best_match = None
        best_score = 0

        # Normalize the new item name
        normalized_new = self._normalize_name(new_item_name)

        for item in existing_items:
            # Normalize existing item name
            normalized_existing = self._normalize_name(item.name)

            # Calculate similarity scores using different methods
            ratio_score = fuzz.ratio(normalized_new, normalized_existing)
            partial_score = fuzz.partial_ratio(normalized_new, normalized_existing)
            token_sort_score = fuzz.token_sort_ratio(normalized_new, normalized_existing)

            # Use the best score from different methods
            score = max(ratio_score, partial_score, token_sort_score)

            # Exact match bonus
            if normalized_new == normalized_existing:
                score = 100

            if score > best_score:
                best_score = score
                best_match = item

        # Return match only if above threshold
        if best_score >= self.similarity_threshold:
            return (best_match, best_score)

        return None

    def _normalize_name(self, name: str) -> str:
        """
        Normalize item name for better matching.

        Args:
            name: Item name

        Returns:
            Normalized name
        """
        # Convert to lowercase
        normalized = name.lower()

        # Remove common words that don't help matching
        noise_words = ["organic", "fresh", "brand", "select", "choice", "value"]
        for word in noise_words:
            normalized = normalized.replace(word, "")

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Remove trailing unit indicators
        unit_suffixes = [
            "gallon",
            "gal",
            "dozen",
            "doz",
            "lb",
            "lbs",
            "oz",
            "ounce",
            "kg",
            "g",
        ]
        for suffix in unit_suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        return normalized.strip()

    def suggest_merge(
        self, new_item_name: str, existing_items: List[InventoryItem]
    ) -> Optional[str]:
        """
        Suggest a merge message for user.

        Args:
            new_item_name: New item name
            existing_items: Existing items

        Returns:
            Suggestion message or None
        """
        match = self.find_match(new_item_name, existing_items)
        if match:
            item, score = match
            return f"'{new_item_name}' matches existing '{item.name}' ({score}% similar)"
        return None
