"""
LLM Service using Ollama for conversational AI.

This service provides a clean interface for interacting with Gemma 3 4b model
via Ollama, supporting both text and image inputs (multimodal).
"""

import json
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    import ollama
except ImportError:
    ollama = None

from ..utils import get_logger


class LLMService:
    """Service for LLM inference using Ollama."""

    def __init__(self, model_name: str = "gemma2:4b"):
        """
        Initialize LLM service.

        Args:
            model_name: Name of the Ollama model to use (default: gemma2:4b)
        """
        self.logger = get_logger("llm_service")
        self.model_name = model_name
        self.conversation_history: List[Dict[str, Any]] = []
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if Ollama is available and model is downloaded."""
        if ollama is None:
            self.logger.error("Ollama package not installed. Run: pip install ollama")
            raise ImportError("Ollama package not installed")

        try:
            # Check if Ollama server is running
            ollama.list()
            self.logger.info("Ollama server is running")
        except Exception as e:
            self.logger.error(f"Ollama server not running: {e}")
            self.logger.info("Please start Ollama server: ollama serve")
            raise RuntimeError("Ollama server not available")

        # Check if model is downloaded
        try:
            models = ollama.list()
            model_names = [model['name'] for model in models.get('models', [])]

            if self.model_name not in model_names:
                # Also check without tag
                base_model = self.model_name.split(':')[0]
                if not any(base_model in name for name in model_names):
                    self.logger.error(f"Model {self.model_name} not found")
                    self.logger.info(f"Please download the model: python scripts/download_model.py")
                    raise RuntimeError(f"Model {self.model_name} not available")

            self.logger.info(f"Model {self.model_name} is available")
        except Exception as e:
            self.logger.error(f"Could not verify model availability: {e}")

    def chat(
        self,
        message: str,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        keep_history: bool = True
    ) -> str:
        """
        Send a chat message to the LLM.

        Args:
            message: User message to send
            images: Optional list of image paths (for multimodal input)
            system_prompt: Optional system prompt to set context
            stream: Whether to stream the response (default: False)
            keep_history: Whether to keep message in conversation history (default: True)

        Returns:
            LLM response as string
        """
        try:
            # Build messages for the chat
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })

            # Add conversation history
            if keep_history and self.conversation_history:
                messages.extend(self.conversation_history)

            # Add current message
            current_message = {
                'role': 'user',
                'content': message
            }

            # Add images if provided
            if images:
                # Convert paths to the format Ollama expects
                current_message['images'] = images
                self.logger.info(f"Including {len(images)} image(s) in message")

            messages.append(current_message)

            # Call Ollama API
            self.logger.debug(f"Sending message to {self.model_name}")
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                stream=stream
            )

            # Extract response
            if stream:
                # For streaming, we'd need to handle chunks
                # For now, we're not using streaming
                response_text = ""
                for chunk in response:
                    response_text += chunk['message']['content']
            else:
                response_text = response['message']['content']

            # Update conversation history
            if keep_history:
                self.conversation_history.append(current_message)
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

            self.logger.debug(f"Received response of length {len(response_text)}")
            return response_text

        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            raise

    def chat_stream(
        self,
        message: str,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        keep_history: bool = True
    ):
        """
        Send a chat message and stream the response.

        Args:
            message: User message to send
            images: Optional list of image paths
            system_prompt: Optional system prompt
            keep_history: Whether to keep message in history

        Yields:
            Response chunks as they arrive
        """
        try:
            # Build messages
            messages = []

            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })

            if keep_history and self.conversation_history:
                messages.extend(self.conversation_history)

            current_message = {
                'role': 'user',
                'content': message
            }

            if images:
                current_message['images'] = images

            messages.append(current_message)

            # Stream response
            response_text = ""
            for chunk in ollama.chat(
                model=self.model_name,
                messages=messages,
                stream=True
            ):
                chunk_text = chunk['message']['content']
                response_text += chunk_text
                yield chunk_text

            # Update history
            if keep_history:
                self.conversation_history.append(current_message)
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

        except Exception as e:
            self.logger.error(f"Error in streaming chat: {e}")
            raise

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        self.logger.info("Conversation history cleared")

    def get_history(self) -> List[Dict[str, Any]]:
        """Get current conversation history."""
        return self.conversation_history.copy()

    def set_history(self, history: List[Dict[str, Any]]) -> None:
        """Set conversation history."""
        self.conversation_history = history
        self.logger.info(f"Conversation history set ({len(history)} messages)")

    def generate_questions(self, num_questions: int = 10) -> List[str]:
        """
        Generate setup questions for initial user onboarding.

        Args:
            num_questions: Number of questions to generate (default: 10)

        Returns:
            List of questions
        """
        system_prompt = """You are a helpful grocery shopping assistant. Generate concise questions
        to set up household grocery management. Focus on: household size, dietary restrictions,
        typical consumption patterns, budget constraints, and vendor preferences. Be conversational
        and friendly."""

        message = f"""Generate {num_questions} concise questions to understand a user's grocery shopping
        needs and preferences. Return ONLY a JSON array of strings, nothing else.

        Example format: ["Question 1?", "Question 2?", ...]"""

        try:
            response = self.chat(message, system_prompt=system_prompt, keep_history=False)

            # Try to parse JSON from response
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])

            questions = json.loads(response)
            self.logger.info(f"Generated {len(questions)} questions")
            return questions

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse questions: {e}")
            # Return fallback questions
            return [
                "How many people are in your household?",
                "Do you have any dietary restrictions or preferences?",
                "What is your typical weekly grocery budget?",
                "Which grocery vendors do you prefer (Amazon, Walmart, etc.)?",
                "How often do you typically shop for groceries?",
                "What are your most frequently purchased items?",
                "Do you prefer organic or conventional products?",
                "Do you have any food allergies in your household?",
                "What time of day do you prefer deliveries?",
                "Would you like automatic reordering for essential items?"
            ]

    def suggest_features(
        self,
        item_name: str,
        current_features: List[str],
        error_description: str
    ) -> Dict[str, Any]:
        """
        Suggest new features to improve forecasting accuracy.

        Args:
            item_name: Name of the item
            current_features: List of current features
            error_description: Description of the forecast error

        Returns:
            Dictionary with suggested features and rationale
        """
        system_prompt = """You are an expert in time series forecasting and feature engineering.
        Suggest features that could improve consumption prediction accuracy."""

        message = f"""Item: {item_name}
        Current features: {current_features}
        Error: {error_description}

        Suggest 3 new features that might improve forecast accuracy. Return ONLY a JSON object with:
        {{"suggested_features": ["feature1", "feature2", "feature3"], "rationale": "explanation"}}"""

        try:
            response = self.chat(message, system_prompt=system_prompt, keep_history=False)

            # Parse JSON response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])

            result = json.loads(response)
            self.logger.info(f"Suggested {len(result.get('suggested_features', []))} features")
            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse feature suggestions: {e}")
            return {
                "suggested_features": ["day_of_week", "days_until_payday", "season"],
                "rationale": "These are common time-based features that often improve consumption forecasting."
            }

    def explain_decision(
        self,
        item: str,
        vendor: str,
        quantity: float,
        forecast_confidence: float,
        price: float,
        user_preferences: Dict[str, Any]
    ) -> str:
        """
        Generate an explanation for a shopping decision.

        Args:
            item: Item name
            vendor: Vendor name
            quantity: Recommended quantity
            forecast_confidence: Forecast confidence (0-1)
            price: Price
            user_preferences: User preferences

        Returns:
            Explanation text
        """
        system_prompt = """You are a helpful grocery shopping assistant. Explain decisions
        in a friendly, concise way (2-3 sentences max)."""

        message = f"""Explain why we're recommending:
        - Item: {item}
        - Vendor: {vendor}
        - Quantity: {quantity}
        - Price: ${price:.2f}
        - Forecast confidence: {forecast_confidence:.1%}
        - User preferences: {json.dumps(user_preferences)}

        Provide a brief, friendly explanation."""

        try:
            response = self.chat(message, system_prompt=system_prompt, keep_history=False)
            return response

        except Exception as e:
            self.logger.error(f"Failed to generate explanation: {e}")
            return f"Based on your consumption pattern, we recommend ordering {quantity} {item} from {vendor} at ${price:.2f}."
