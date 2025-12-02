#!/usr/bin/env python3
"""
Model download script.

Downloads Gemma 3 4b model for edge inference using Ollama.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import get_logger

try:
    import ollama
except ImportError:
    print("Error: ollama package not installed. Run: pip install ollama")
    sys.exit(1)


def check_ollama_server() -> bool:
    """Check if Ollama server is running."""
    try:
        ollama.list()
        return True
    except Exception as e:
        return False


def download_gemma_model() -> None:
    """Download Gemma 3 4b model via Ollama."""
    logger = get_logger("download_model")

    # Check if Ollama server is running
    if not check_ollama_server():
        logger.error("Ollama server is not running!")
        logger.info("\nPlease start Ollama server first:")
        logger.info("  1. Install Ollama from https://ollama.com")
        logger.info("  2. Run: ollama serve")
        logger.info("  3. Then run this script again")
        sys.exit(1)

    # logger.info("Ollama server is running. Checking for gemma3n:e2b-it-q4_K_M model...")
    logger.info("Ollama server is running. Checking for llama3.2:3b...")

    # Check if model is already downloaded
    try:
        models = ollama.list()
        model_names = [model['model'] for model in models.get('models', [])]

        # if 'gemma3:4b' in model_names or 'gemma2:latest' in model_names:
        # if 'gemma3n:e2b-it-q4_K_M' in model_names:
        if 'gemma3-tools:4b' in model_names:
            logger.info("Gemma model already downloaded!")
            return
    except Exception as e:
        logger.warning(f"Could not check existing models: {e}")

    # Download the model
    logger.info("Downloading orieg/gemma3-tools:4b model...")
    logger.info("This may take several minutes depending on your internet connection.")
    logger.info("Model size: ~4GB")

    try:
        # Pull the model
        response = ollama.pull('orieg/gemma3-tools:4b')
        logger.info("Model downloaded successfully!")
        logger.info(f"Response: {response}")
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        sys.exit(1)


def main() -> None:
    """Download required models."""
    logger = get_logger("download_model")

    logger.info("=" * 60)
    logger.info("P3-Edge Model Download - Phase 4")
    logger.info("=" * 60)

    logger.info("\nDownloading orieg/gemma3-tools:4b via Ollama...")
    logger.info("This model will be used for:")
    logger.info("  - Conversational interface")
    logger.info("  - Feature engineering suggestions")
    logger.info("  - Decision explanations")
    logger.info("  - Natural language understanding")

    download_gemma_model()

    logger.info("\n" + "=" * 60)
    logger.info("Model download complete!")
    logger.info("=" * 60)

    logger.info("\nYou can now use the LLM service in the application.")
    logger.info("The model supports both text and image inputs (multimodal).")


if __name__ == "__main__":
    main()
