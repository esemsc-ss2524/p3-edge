"""
LLM Service using Google Gemini via LangChain.

This service provides access to Google's Gemini models through LangChain,
supporting function calling and multimodal inputs.
"""

import json
import time
import uuid
from typing import Optional, List, Dict, Any

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
    from langchain_core.tools import StructuredTool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..utils import get_logger
from ..models.tool_models import (
    ToolCall,
    ToolResult,
    AgentResponse,
    ToolDefinition,
    ToolResultStatus,
)
from ..tools.executor import ToolExecutor
from .base_llm_service import BaseLLMService


class GeminiLLMService(BaseLLMService):
    """Service for LLM inference using Google Gemini via LangChain."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        api_key: Optional[str] = None,
        tool_executor: Optional[ToolExecutor] = None,
        temperature: float = 0.7,
    ):
        """
        Initialize Gemini LLM service.

        Args:
            model_name: Name of the Gemini model to use
            api_key: Google API key (if None, uses GOOGLE_API_KEY env var)
            tool_executor: Optional ToolExecutor for function calling
            temperature: Sampling temperature (0.0 to 1.0)
        """
        super().__init__(tool_executor)
        self.logger = get_logger("gemini_llm_service")
        self._model_name = model_name
        self._api_key = api_key
        self._temperature = temperature
        self._check_availability()
        self._initialize_model()

    def _check_availability(self) -> None:
        """Check if LangChain and Gemini are available."""
        if not LANGCHAIN_AVAILABLE:
            self.logger.error("LangChain Google GenAI package not installed")
            raise ImportError(
                "LangChain Google GenAI not installed. "
                "Run: pip install langchain-google-genai"
            )

        if not self._api_key:
            import os
            self._api_key = os.getenv("GOOGLE_API_KEY")
            if not self._api_key:
                self.logger.error("Google API key not provided")
                raise ValueError(
                    "Google API key required. Set GOOGLE_API_KEY environment "
                    "variable or pass api_key parameter"
                )

        self.logger.info("Gemini API credentials configured")

    def _initialize_model(self) -> None:
        """Initialize the Gemini model."""
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=self._api_key,
                temperature=self._temperature,
                convert_system_message_to_human=True,
            )
            self.logger.info(f"Gemini model {self._model_name} initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini model: {e}")
            raise

    def chat(
        self,
        message: str,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        keep_history: bool = True,
    ) -> str:
        """
        Send a chat message to Gemini.

        Args:
            message: User message to send
            images: Optional list of image paths (not fully supported yet)
            system_prompt: Optional system prompt to set context
            stream: Whether to stream the response (not implemented)
            keep_history: Whether to keep message in conversation history

        Returns:
            LLM response as string
        """
        try:
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            # Add conversation history
            if keep_history and self.conversation_history:
                for msg in self.conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))

            # Add current message
            messages.append(HumanMessage(content=message))

            # Call Gemini
            self.logger.debug(f"Sending message to {self._model_name}")
            response = self.llm.invoke(messages)

            response_text = response.content

            # Update conversation history
            if keep_history:
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append(
                    {"role": "assistant", "content": response_text}
                )

            self.logger.debug(f"Received response of length {len(response_text)}")
            return response_text

        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            raise

    def chat_with_tools(
        self,
        message: str,
        tool_definitions: Optional[List[ToolDefinition]] = None,
        max_iterations: int = 5,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> AgentResponse:
        """
        Chat with tool calling support using Gemini's native function calling.

        Args:
            message: User message
            tool_definitions: List of available tools (if None, uses all from executor)
            max_iterations: Maximum number of tool calling iterations
            images: Optional images for multimodal input (not fully supported)
            system_prompt: Optional system prompt

        Returns:
            AgentResponse with final response, tool calls, and results
        """
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

        # Convert tools to LangChain format
        langchain_tools = self._convert_tools_to_langchain(tool_definitions)

        # Bind tools to model
        llm_with_tools = self.llm.bind_tools(langchain_tools)

        # Build system prompt
        agent_system_prompt = self._build_agent_system_prompt(
            tool_definitions, system_prompt
        )

        # Initialize messages
        messages = []
        if agent_system_prompt:
            messages.append(SystemMessage(content=agent_system_prompt))

        # Add conversation history
        if self.conversation_history:
            for msg in self.conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # Add current message
        messages.append(HumanMessage(content=message))

        # Track tool calls and results
        all_tool_calls: List[ToolCall] = []
        all_tool_results: List[ToolResult] = []

        # Iterative tool calling loop
        for iteration in range(max_iterations):
            self.logger.info(f"Agent iteration {iteration + 1}/{max_iterations}")

            try:
                # Call Gemini with tools
                response = llm_with_tools.invoke(messages)

                # Check if there are tool calls
                tool_calls = getattr(response, "tool_calls", [])

                if not tool_calls:
                    # No more tool calls, this is the final response
                    self.logger.info("No tool calls, returning final response")

                    # Update conversation history
                    self.conversation_history.append({"role": "user", "content": message})
                    self.conversation_history.append(
                        {"role": "assistant", "content": response.content}
                    )

                    return AgentResponse(
                        response=response.content,
                        tool_calls=all_tool_calls,
                        tool_results=all_tool_results,
                        iterations=iteration + 1,
                        total_time_ms=(time.time() - start_time) * 1000,
                    )

                # Process tool calls
                self.logger.info(f"Processing {len(tool_calls)} tool calls")

                # Add assistant message with tool calls
                messages.append(response)

                for tool_call_data in tool_calls:
                    tool_name = tool_call_data["name"]
                    arguments = tool_call_data["args"]
                    tool_call_id = tool_call_data.get("id", str(uuid.uuid4()))

                    self.logger.info(f"Executing tool: {tool_name}")

                    # Create ToolCall object
                    tool_call = ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        call_id=tool_call_id,
                    )

                    # Execute tool
                    tool_result = self.tool_executor.execute(tool_call)

                    all_tool_calls.append(tool_call)
                    all_tool_results.append(tool_result)

                    # Add tool result to messages
                    tool_message = ToolMessage(
                        content=tool_result.to_llm_format(),
                        tool_call_id=tool_call_id,
                    )
                    messages.append(tool_message)

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

    def _convert_tools_to_langchain(
        self, tool_definitions: List[ToolDefinition]
    ) -> List[Dict[str, Any]]:
        """
        Convert tool definitions to LangChain tool format.

        Args:
            tool_definitions: List of ToolDefinition objects

        Returns:
            List of LangChain tool dictionaries
        """
        langchain_tools = []

        for tool_def in tool_definitions:
            # Skip blocked tools
            if tool_def.blocked:
                continue

            # Build parameter schema for LangChain
            properties = {}
            required = []

            for param in tool_def.parameters:
                properties[param.name] = {
                    "type": param.type.value,
                    "description": param.description,
                }

                if param.enum:
                    properties[param.name]["enum"] = param.enum

                if param.required:
                    required.append(param.name)

            # Create tool dictionary in LangChain format
            tool_dict = {
                "name": tool_def.name,
                "description": tool_def.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }

            langchain_tools.append(tool_dict)

        return langchain_tools

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
8. When a user asks to search for a product, use Search tool first to get the product IDs if they are required.

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
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
                if response.startswith("json"):
                    response = response[4:].strip()

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
                "Would you like automatic reordering for essential items?",
            ]

    def parse_receipt_text(self, ocr_text: str) -> Dict[str, Any]:
        """
        Parse OCR text from a receipt and extract structured item information.

        Args:
            ocr_text: Raw text extracted from receipt via OCR

        Returns:
            Dictionary with store, date, total, and items list
        """
        system_prompt = """You are an expert at parsing grocery receipt text. You will receive
        OCR-extracted text from a receipt that may contain errors, formatting issues, and noise.

        Your task is to extract grocery items with their details in a structured JSON format.
        Be intelligent about handling OCR errors, common abbreviations, and receipt formatting.

        IMPORTANT: You must ALWAYS respond with ONLY valid JSON, no other text.
        Do not include markdown code blocks or any explanation."""

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
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
                if response.startswith("json"):
                    response = response[4:].strip()

            # Parse JSON
            parsed_data = json.loads(response)

            self.logger.info(f"Successfully parsed receipt: {len(parsed_data.get('items', []))} items extracted")
            return parsed_data

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:200]}")
            return {
                "store": None,
                "date": None,
                "total": None,
                "items": []
            }

        except Exception as e:
            self.logger.error(f"Failed to parse receipt text: {e}")
            return {
                "store": None,
                "date": None,
                "total": None,
                "items": []
            }

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
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
                if response.startswith("json"):
                    response = response[4:].strip()

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

    # Required properties from BaseLLMService
    @property
    def provider_name(self) -> str:
        """Get the name of the LLM provider."""
        return "Google Gemini"

    @property
    def model_name(self) -> str:
        """Get the name of the model being used."""
        return self._model_name

    @property
    def supports_images(self) -> bool:
        """Check if the model supports image inputs."""
        # Gemini models support multimodal inputs
        return "vision" in self._model_name.lower() or "flash" in self._model_name.lower()

    @property
    def supports_tools(self) -> bool:
        """Check if the model supports function calling."""
        return True
