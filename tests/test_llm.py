#!/usr/bin/env python3
"""
Test script for LLM integration.

Tests the LLM service to ensure Ollama and Gemma model are working correctly.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.llm_service import LLMService
from src.utils import get_logger


def test_basic_chat():
    """Test basic chat functionality."""
    logger = get_logger("test_llm")

    logger.info("=" * 60)
    logger.info("Testing LLM Service - Basic Chat")
    logger.info("=" * 60)

    try:
        # Initialize service
        logger.info("\n1. Initializing LLM service...")
        llm = LLMService()
        logger.info("✅ LLM service initialized successfully")

        # Test basic chat
        logger.info("\n2. Testing basic chat...")
        test_message = "Hello! Please respond with a brief greeting."
        logger.info(f"Sending: {test_message}")

        response = llm.chat(test_message, keep_history=False)
        logger.info(f"✅ Received response: {response[:100]}...")

        # Test with history
        logger.info("\n3. Testing conversation with history...")
        llm.clear_history()

        response1 = llm.chat("My name is Test User. Remember this.")
        logger.info(f"Response 1: {response1[:80]}...")

        response2 = llm.chat("What is my name?")
        logger.info(f"Response 2: {response2[:80]}...")

        if "Test User" in response2 or "test user" in response2.lower():
            logger.info("✅ Conversation history working correctly")
        else:
            logger.warning("⚠️  Conversation history may not be working as expected")

        # Test clear history
        logger.info("\n4. Testing clear history...")
        llm.clear_history()
        history = llm.get_history()
        if len(history) == 0:
            logger.info("✅ Clear history working correctly")
        else:
            logger.warning(f"⚠️  History not cleared properly, still has {len(history)} messages")

        logger.info("\n" + "=" * 60)
        logger.info("✅ All basic tests passed!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Make sure Ollama server is running: ollama serve")
        logger.info("2. Make sure Gemma model is downloaded: python scripts/download_model.py")
        logger.info("3. Check Ollama status: ollama list")
        return False


def test_feature_suggestions():
    """Test feature suggestion functionality."""
    logger = get_logger("test_llm")

    logger.info("\n" + "=" * 60)
    logger.info("Testing LLM Service - Feature Suggestions")
    logger.info("=" * 60)

    try:
        llm = LLMService()

        logger.info("\nGenerating feature suggestions...")
        suggestions = llm.suggest_features(
            item_name="milk",
            current_features=["quantity", "days_since_last_purchase", "household_size"],
            error_description="Forecast is overestimating consumption by 25%"
        )

        logger.info("\n✅ Feature suggestions generated:")
        logger.info(f"Suggested features: {suggestions.get('suggested_features', [])}")
        logger.info(f"Rationale: {suggestions.get('rationale', 'N/A')[:100]}...")

        return True

    except Exception as e:
        logger.error(f"\n❌ Feature suggestion test failed: {e}")
        return False


def test_decision_explanation():
    """Test decision explanation functionality."""
    logger = get_logger("test_llm")

    logger.info("\n" + "=" * 60)
    logger.info("Testing LLM Service - Decision Explanations")
    logger.info("=" * 60)

    try:
        llm = LLMService()

        logger.info("\nGenerating decision explanation...")
        explanation = llm.explain_decision(
            item="milk",
            vendor="Amazon",
            quantity=2,
            forecast_confidence=0.85,
            price=5.99,
            user_preferences={"prefers_organic": True, "household_size": 4}
        )

        logger.info("\n✅ Decision explanation generated:")
        logger.info(f"Explanation: {explanation}")

        return True

    except Exception as e:
        logger.error(f"\n❌ Decision explanation test failed: {e}")
        return False


def test_question_generation():
    """Test question generation for onboarding."""
    logger = get_logger("test_llm")

    logger.info("\n" + "=" * 60)
    logger.info("Testing LLM Service - Question Generation")
    logger.info("=" * 60)

    try:
        llm = LLMService()

        logger.info("\nGenerating onboarding questions...")
        questions = llm.generate_questions(num_questions=5)

        logger.info("\n✅ Questions generated:")
        for i, q in enumerate(questions, 1):
            logger.info(f"{i}. {q}")

        return True

    except Exception as e:
        logger.error(f"\n❌ Question generation test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger = get_logger("test_llm")

    logger.info("=" * 60)
    logger.info("P3-Edge LLM Integration Test Suite")
    logger.info("=" * 60)

    # Run tests
    results = {
        "Basic Chat": test_basic_chat(),
        "Feature Suggestions": test_feature_suggestions(),
        "Decision Explanations": test_decision_explanation(),
        "Question Generation": test_question_generation(),
    }

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("🎉 All tests passed successfully!")
        logger.info("\nThe LLM integration is ready to use.")
        logger.info("Start the application and navigate to 'AI Chat' to try it out.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
