"""
LLM Service using Ollama for conversational AI.

This service provides a clean interface for interacting with Gemma 3 4b model
via Ollama, supporting both text and image inputs (multimodal) and function calling.
"""

import json
import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator

try:
    import ollama
except ImportError:
    ollama = None

from ..utils import get_logger
from ..models.tool_models import (
    ToolCall,
    ToolResult,
    AgentResponse,
    ToolDefinition,
)
from ..tools.executor import ToolExecutor
from .base_llm_service import BaseLLMService


# Pydantic models for receipt parsing validation
class ReceiptItemSchema(BaseModel):
    """Schema for a single receipt item."""

    name: str = Field(..., description="Item name, cleaned and normalized")
    quantity: float = Field(default=1.0, ge=0, description="Quantity of the item")
    unit: Optional[str] = Field(None, description="Unit like 'lb', 'oz', 'kg', 'gallon', etc.")
    price: Optional[float] = Field(None, ge=0, description="Item price")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence score")

    @validator("unit")
    def normalize_unit(cls, v):
        """Normalize unit to lowercase."""
        return v.lower() if v else None

    @validator("name")
    def clean_name(cls, v):
        """Clean and normalize item name."""
        # Remove extra whitespace
        return " ".join(v.split())


class ReceiptParseResult(BaseModel):
    """Schema for complete receipt parsing result."""

    store: Optional[str] = Field(None, description="Store name")
    date: Optional[str] = Field(None, description="Receipt date in YYYY-MM-DD format")
    total: Optional[float] = Field(None, ge=0, description="Total amount")
    items: List[ReceiptItemSchema] = Field(default_factory=list, description="List of items")

    @validator("items")
    def validate_items(cls, v):
        """Ensure at least items list is present."""
        return v if v is not None else []


class OllamaLLMService(BaseLLMService):
    """Service for LLM inference using Ollama."""

    # def __init__(self, model_name: str = "gemma3:4b"):
    def __init__(
        self,
        model_name: str = "gemma3n:e2b-it-q4_K_M",
        tool_executor: Optional[ToolExecutor] = None,
    ):
    # def __init__(self, model_name: str = "llama3.2:3b"):
        """
        Initialize LLM service.

        Args:
            model_name: Name of the Ollama model to use
            tool_executor: Optional ToolExecutor for function calling
        """
        super().__init__(tool_executor)
        self.logger = get_logger("ollama_llm_service")
        self._model_name = model_name
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
            # print(models)
            model_names = [model['model'] for model in models.get('models', [])]

            if self._model_name not in model_names:
                # Also check without tag
                base_model = self._model_name.split(':')[0]
                if not any(base_model in name for name in model_names):
                    self.logger.error(f"Model {self._model_name} not found")
                    self.logger.info(f"Please download the model: python scripts/download_model.py")
                    raise RuntimeError(f"Model {self._model_name} not available")

            self.logger.info(f"Model {self._model_name} is available")
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
            self.logger.debug(f"Sending message to {self._model_name}")
            response = ollama.chat(
                model=self._model_name,
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
                model=self._model_name,
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

    def parse_receipt_text(self, ocr_text: str) -> Dict[str, Any]:
        """
        Parse OCR text from a receipt and extract structured item information.

        Uses the LLM to intelligently extract grocery items, quantities, prices, and units
        from raw OCR text, handling various receipt formats and OCR errors.

        Args:
            ocr_text: Raw text extracted from receipt via OCR

        Returns:
            Dictionary with:
                - items: List of dicts with {name, quantity, unit, price, confidence}
                - store: Store name (if detected)
                - total: Total amount (if detected)
                - date: Receipt date (if detected)

        Example:
            {
                "store": "Walmart",
                "date": "2024-12-02",
                "total": 45.67,
                "items": [
                    {
                        "name": "Organic Milk",
                        "quantity": 1.0,
                        "unit": "gallon",
                        "price": 5.99,
                        "confidence": 0.95
                    },
                    ...
                ]
            }
        """
        system_prompt = """You are an expert at parsing grocery receipt text. You will receive
        OCR-extracted text from a receipt that may contain errors, formatting issues, and noise.

        Your task is to extract grocery items with their details in a structured JSON format.
        Be intelligent about handling OCR errors, common abbreviations, and receipt formatting.

        IMPORTANT: You must ALWAYS respond with ONLY valid JSON, no other text.
        Do not include markdown code blocks or any explanation."""

        # Define the JSON schema
        schema = {
            "store": "string (store name if detected, otherwise null)",
            "date": "string (receipt date in YYYY-MM-DD format if detected, otherwise null)",
            "total": "number (total amount if detected, otherwise null)",
            "items": [
                {
                    "name": "string (item name, cleaned and normalized)",
                    "quantity": "number (quantity, default 1.0 if not specified)",
                    "unit": "string (unit like 'lb', 'oz', 'kg', 'gallon', 'count', or null)",
                    "price": "number (item price, or null if not found)",
                    "confidence": "number (0.0-1.0, your confidence in this extraction)"
                }
            ]
        }

        message = f"""Parse this receipt OCR text and extract the grocery items.

OCR Text:
{ocr_text}

Required JSON schema:
{json.dumps(schema, indent=2)}

Rules:
1. Extract ONLY grocery items (food, beverages, household items)
2. Skip store headers, footers, payment info, totals, subtotals, tax lines
3. Clean up item names (remove extra spaces, fix common OCR errors)
4. Normalize units (lb, oz, kg, g, ct, count, gallon, liter)
5. If quantity is not specified, use 1.0
6. Set confidence based on clarity of the text
7. If price has OCR errors or is unclear, set to null
8. Return ONLY the JSON object, no markdown or explanation

Response (JSON only):"""

        try:
            response = self.chat(message, system_prompt=system_prompt, keep_history=False)

            # Clean up response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                lines = response.split('\n')
                # Remove first and last lines (markdown markers)
                response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
                # Also handle ```json
                if response.startswith("json"):
                    response = response[4:].strip()

            # Parse JSON
            raw_data = json.loads(response)

            # Validate with Pydantic model
            validated_result = ReceiptParseResult(**raw_data)

            # Convert back to dict for backward compatibility
            parsed_data = validated_result.dict()

            self.logger.info(f"Successfully parsed receipt: {len(parsed_data['items'])} items extracted")
            return parsed_data

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:200]}")

            # Fallback: return empty structure
            return {
                "store": None,
                "date": None,
                "total": None,
                "items": []
            }

        except Exception as e:
            # Handle Pydantic validation errors
            if "ValidationError" in str(type(e).__name__):
                self.logger.error(f"Schema validation failed: {e}")
                self.logger.debug(f"Response was: {response[:200]}")

                # Fallback: return empty structure
                return {
                    "store": None,
                    "date": None,
                    "total": None,
                    "items": []
                }

            self.logger.error(f"Failed to parse receipt text: {e}")
            raise

    def chat_with_tools(
        self,
        message: str,
        tool_definitions: Optional[List[ToolDefinition]] = None,
        max_iterations: int = 50,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> AgentResponse:
        """
        Chat with tool calling support using Ollama's native function calling.

        Args:
            message: User message
            tool_definitions: List of available tools (if None, uses all from executor)
            max_iterations: Maximum number of tool calling iterations
            images: Optional images for multimodal input
            system_prompt: Optional system prompt

        Returns:
            AgentResponse with final response, tool calls, and results
        """
        import time

        start_time = time.time()

        if not self.tool_executor:
            self.logger.warning("No tool executor configured, falling back to regular chat")
            response = self.chat(message, images, system_prompt, keep_history=True)
            return AgentResponse(
                response=response,
                tool_calls=[],
                tool_results=[],
                iterations=1,
                total_time_ms=(time.time() - start_time) * 1000,
            )

        # Get tool definitions
        if tool_definitions is None:
            tool_definitions = self.tool_executor.get_tool_definitions()

        # Convert to Ollama format
        ollama_tools = [tool.to_ollama_tool() for tool in tool_definitions]

        # Build system prompt with tool instructions
        agent_system_prompt = self._build_agent_system_prompt(
            tool_definitions, system_prompt
        )

        # Initialize conversation
        messages = []
        if agent_system_prompt:
            messages.append({"role": "system", "content": agent_system_prompt})

        # Add conversation history
        if self.conversation_history:
            messages.extend(self.conversation_history)

        # Add current message
        current_message = {"role": "user", "content": message}
        if images:
            current_message["images"] = images

        messages.append(current_message)

        # Track tool calls and results
        all_tool_calls: List[ToolCall] = []
        all_tool_results: List[ToolResult] = []

        # Iterative tool calling loop
        for iteration in range(max_iterations):
            self.logger.info(f"Agent iteration {iteration + 1}/{max_iterations}")

            try:
                # Call Ollama with tools
                response = ollama.chat(
                    model=self._model_name,
                    messages=messages,
                    tools=ollama_tools if ollama_tools else None,
                )

                assistant_message = response["message"]
                content = assistant_message.get("content", "")

                # Check if there are tool calls
                tool_calls_data = assistant_message.get("tool_calls", [])

                if not tool_calls_data:
                    # No more tool calls, this is the final response
                    self.logger.info("No tool calls, returning final response")

                    # Update conversation history
                    self.conversation_history.append(current_message)
                    self.conversation_history.append(
                        {"role": "assistant", "content": content}
                    )

                    return AgentResponse(
                        response=content,
                        tool_calls=all_tool_calls,
                        tool_results=all_tool_results,
                        iterations=iteration + 1,
                        total_time_ms=(time.time() - start_time) * 1000,
                    )

                # Process tool calls
                self.logger.info(f"Processing {len(tool_calls_data)} tool calls")

                # Add assistant message with tool calls to conversation
                messages.append(assistant_message)

                for tool_call_data in tool_calls_data:
                    function_data = tool_call_data.get("function", {})
                    tool_name = function_data.get("name")
                    arguments = function_data.get("arguments", {})

                    self.logger.info(f"Executing tool: {tool_name}")

                    # Create ToolCall object
                    tool_call = ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        call_id=str(uuid.uuid4()),
                    )

                    # Execute tool
                    tool_result = self.tool_executor.execute(tool_call)

                    all_tool_calls.append(tool_call)
                    all_tool_results.append(tool_result)

                    # Add tool result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "content": tool_result.to_llm_format(),
                        }
                    )

                    self.logger.info(
                        f"Tool {tool_name} executed: {tool_result.status.value}"
                    )

            except Exception as e:
                self.logger.error(f"Error in tool calling loop: {e}", exc_info=True)
                error_response = (
                    f"I encountered an error while processing your request: {str(e)}"
                )

                return AgentResponse(
                    response=error_response,
                    tool_calls=all_tool_calls,
                    tool_results=all_tool_results,
                    iterations=iteration + 1,
                    total_time_ms=(time.time() - start_time) * 1000,
                )

        # Max iterations reached
        self.logger.warning(f"Max iterations ({max_iterations}) reached")
        return AgentResponse(
            response="I apologize, but I couldn't complete the request within the allowed steps. Please try breaking down your request or being more specific.",
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            iterations=max_iterations,
            total_time_ms=(time.time() - start_time) * 1000,
        )

    def _build_agent_system_prompt(
        self,
        tool_definitions: List[ToolDefinition],
        custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Build comprehensive system prompt for agent.

        Args:
            tool_definitions: Available tools
            custom_prompt: Optional custom instructions

        Returns:
            System prompt string
        """
        base_prompt = """You are an intelligent grocery shopping assistant with access to tools for managing household inventory, forecasting consumption, and shopping.

Your capabilities:
- Query inventory to see what's in stock
- Check when items will run out
- Generate forecasts for consumption
- Search for products on Amazon
- Add items to shopping cart
- Analyze usage patterns
- Calculate quantities needed
- Check budget constraints

Important guidelines:
1. NEVER place orders - only humans can approve and place orders
2. Always check inventory before suggesting purchases
3. Consider user preferences and dietary restrictions
4. Use forecasts to make proactive suggestions
5. Be clear about quantities and units
6. Explain your reasoning when making recommendations
7. If a tool fails, try an alternative approach or ask for clarification

TOOL CHAINING INTELLIGENCE:
When handling requests, think about the logical flow of tools:
- For "I need X" → check inventory → (if low) search products → suggest adding to cart
- For "What should I buy?" → check inventory → check forecasts → identify low items → search products
- For cart operations → always check budget constraints before final recommendations
- Chain tools automatically without asking for permission at each step

PROACTIVE SUGGESTIONS:
- When you see low stock items, proactively suggest reordering
- When items are expiring soon, mention it even if not asked
- If consumption patterns suggest running out soon, warn the user
- Compare prices and suggest better alternatives when searching

BUDGET AWARENESS:
- ALWAYS check budget before recommending purchases
- If approaching budget limits, suggest prioritizing essential items
- Warn users when cart total exceeds weekly/monthly caps
- Suggest cheaper alternatives if budget constrained

CONVERSATION MEMORY:
- Remember context from earlier in the conversation
- If user says "also add X" after discussing Y, understand the connection
- Build on previous tool results without re-querying unnecessarily

When answering questions:
- Be concise and helpful
- Use tools to get accurate data rather than guessing
- Provide specific numbers and dates
- Suggest actionable next steps
- Show your reasoning process

Tool usage will be handled automatically by the system."""

        if custom_prompt:
            base_prompt += f"\n\nAdditional context:\n{custom_prompt}"

        return base_prompt

    def set_tool_executor(self, tool_executor: ToolExecutor) -> None:
        """
        Set or update the tool executor.

        Args:
            tool_executor: ToolExecutor instance
        """
        self.tool_executor = tool_executor
        self.logger.info("Tool executor updated")

    # Required properties from BaseLLMService
    @property
    def provider_name(self) -> str:
        """Get the name of the LLM provider."""
        return "Ollama"

    @property
    def model_name(self) -> str:
        """Get the name of the model being used."""
        return self._model_name

    @property
    def supports_images(self) -> bool:
        """Check if the model supports image inputs."""
        # Gemma 3 models support images
        return True

    @property
    def supports_tools(self) -> bool:
        """Check if the model supports function calling."""
        return True
