# LLM Integration Setup Guide

This guide explains how to set up and use the LLM integration (Phase 4) in P3-Edge.

## Overview

Phase 4 introduces conversational AI capabilities using Gemma 3 4b model through Ollama. This enables:
- Natural language conversations with your grocery assistant
- Feature suggestions for forecasting models
- Decision explanations
- Interactive help and guidance

## Prerequisites

1. **Python 3.10+** with all P3-Edge dependencies installed
2. **Ollama server** installed and running
3. **Gemma 2 4b model** downloaded via Ollama

## Installation Steps

### Step 1: Install Ollama

Download and install Ollama from [https://ollama.com](https://ollama.com)

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download installer from [https://ollama.com/download](https://ollama.com/download)

### Step 2: Start Ollama Server

In a terminal window, start the Ollama server:

```bash
ollama serve
```

Leave this terminal open and running.

### Step 3: Install Python Dependencies

If you haven't already, install the Python dependencies:

```bash
pip install -r requirements.txt
```

This will install the `ollama` Python package along with other dependencies.

### Step 4: Download Gemma 3 4b Model

Run the model download script:

```bash
python scripts/download_model.py
```

This will:
- Check if Ollama server is running
- Download the Gemma 2 4b model (approximately 3GB)
- Verify the model is available

**Note:** The download may take several minutes depending on your internet connection.

Alternative manual download:
```bash
ollama pull gemma2:4b
```

### Step 5: Verify Installation

Check that the model is available:

```bash
ollama list
```

You should see `gemma2:4b` in the list.

## Using the AI Chat

### Starting the Application

1. Ensure Ollama server is running (`ollama serve`)
2. Launch P3-Edge:
   ```bash
   python src/main.py
   ```

### Accessing the Chat Interface

1. Click on **"AI Chat"** in the navigation panel
2. The chat interface will load and show a welcome message
3. Type your message in the text box at the bottom
4. Click **"Send"** or press Enter to send

### Features

#### Text Conversations
- Ask questions about your inventory
- Get shopping recommendations
- Request explanations for forecasts
- General grocery-related queries

Example queries:
- "What items are running low?"
- "Should I buy more milk this week?"
- "Why was this item recommended?"
- "How does the forecasting work?"

#### Image Attachments (Multimodal)
While image input is available, it's currently configured for text-only chat. To attach images:
1. Click **"📎 Attach Image"**
2. Select an image file (PNG, JPG, etc.)
3. The image will be sent with your next message

**Use cases for images:**
- Receipt scanning (future feature)
- Product photos for identification
- Fridge interior photos for inventory detection

#### Conversation History
- The chat maintains conversation context
- All messages are kept in memory during the session
- Click **"Clear History"** to start fresh

## Configuration

### Changing the Model

To use a different Gemma model variant:

1. Edit `src/services/llm_service.py`
2. Change the default model in `__init__`:
   ```python
   def __init__(self, model_name: str = "gemma2:4b"):
   ```

Available Gemma models:
- `gemma2:2b` - Smaller, faster (2B parameters)
- `gemma2:4b` - Balanced (4B parameters) **[Default]**
- `gemma2:9b` - Larger, more capable (9B parameters)
- `gemma2:27b` - Largest (27B parameters, requires more RAM)

3. Download the new model:
   ```bash
   ollama pull <model-name>
   ```

### System Prompts

The chat interface uses a system prompt to set context. This can be customized in `src/ui/chat_page.py`:

```python
system_prompt = """You are a helpful grocery shopping assistant for P3-Edge,
an autonomous grocery management system. You help users with inventory management,
consumption patterns, shopping recommendations, and general grocery-related questions.
Be concise, friendly, and helpful."""
```

## Troubleshooting

### "Ollama server not running"

**Solution:** Make sure Ollama is running in a separate terminal:
```bash
ollama serve
```

### "Model not found"

**Solution:** Download the model:
```bash
python scripts/download_model.py
```

Or manually:
```bash
ollama pull gemma2:4b
```

### Slow Response Times

**Possible causes:**
- Large model on CPU (no GPU acceleration)
- Long conversation history

**Solutions:**
- Use a smaller model (e.g., `gemma2:2b`)
- Clear conversation history regularly
- If available, enable GPU acceleration in Ollama

### Chat Interface Not Loading

**Check:**
1. Ollama server is running
2. Model is downloaded (`ollama list`)
3. Check application logs for errors

**Logs location:**
- Application logs: `~/.p3-edge/logs/`
- Look for `llm_service` and `chat_page` entries

### Connection Errors

**Error:** `Connection refused` or `Cannot connect to Ollama`

**Solution:**
- Verify Ollama is running on default port (11434)
- Check firewall settings
- Ensure no other service is using port 11434

### Memory Issues

If Ollama crashes or runs out of memory:

**Solution:**
- Use a smaller model
- Close other applications
- Increase system swap space
- Consider upgrading RAM

**Minimum requirements:**
- 2B model: 4GB RAM
- 4B model: 8GB RAM
- 9B model: 16GB RAM
- 27B model: 32GB RAM

## Performance Optimization

### CPU-Only Optimization

Gemma models run on CPU by default. To optimize:

1. **Use quantized models** (already done by Ollama)
2. **Reduce context window** - Keep conversations focused
3. **Use smaller models** for simple tasks
4. **Batch requests** when possible

### GPU Acceleration

If you have a compatible GPU, Ollama will automatically use it. To verify:

```bash
ollama run gemma2:4b --verbose
```

Look for GPU detection messages.

## LLM-Enhanced Receipt OCR

Phase 4 includes an intelligent receipt parsing system that uses the LLM to extract items from OCR text. This significantly improves accuracy over traditional regex-based parsing.

### How It Works

1. **Tesseract OCR** extracts raw text from receipt images
2. **LLM Service** intelligently parses the OCR text, handling:
   - OCR errors and typos
   - Various receipt formats
   - Item name normalization
   - Quantity and unit extraction
   - Price detection
3. **Pydantic Validation** ensures data quality with strict schema enforcement
4. **Automatic Fallback** to regex parsing if LLM is unavailable

### Features

- **Intelligent Parsing**: Handles OCR errors and abbreviations
- **Structured Output**: Returns JSON with validated schema:
  ```json
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
      }
    ]
  }
  ```
- **Confidence Scores**: Each item has a confidence score (0.0-1.0)
- **Unit Normalization**: Standardizes units (lb, oz, kg, gallon, etc.)
- **Header/Footer Filtering**: Automatically skips non-item text

### Usage

The LLM-enhanced parsing is **enabled by default** when you upload a receipt through the UI.

To use it programmatically:

```python
from src.ingestion.receipt_ocr import ReceiptOCR

# With LLM (default)
ocr = ReceiptOCR(use_llm=True)
items = ocr.process_receipt("path/to/receipt.jpg")

# Without LLM (fallback to regex)
ocr = ReceiptOCR(use_llm=False)
items = ocr.process_receipt("path/to/receipt.jpg")
```

Direct text parsing:

```python
from src.services.llm_service import LLMService

llm = LLMService()
result = llm.parse_receipt_text(ocr_text)

for item in result['items']:
    print(f"{item['name']}: ${item['price']}")
```

### Testing

Test the LLM-enhanced OCR:

```bash
python scripts/test_ocr_llm.py
```

This will test:
- LLM receipt text parsing
- Schema validation
- Comparison with regex parsing

### Performance

**LLM Parsing:**
- More accurate on complex receipts
- Handles OCR errors better
- Extracts more metadata (store, date, total)
- Higher confidence scores
- Slower (~2-5 seconds per receipt)

**Regex Parsing (Fallback):**
- Faster (<1 second per receipt)
- Works offline without Ollama
- Less accurate on messy OCR
- Limited metadata extraction

### Configuration

The OCR pipeline automatically uses LLM if available. To disable:

```python
# In your code
ocr = ReceiptOCR(use_llm=False)
```

Or check if LLM is available:

```python
from src.ingestion.receipt_ocr import LLM_AVAILABLE

if LLM_AVAILABLE:
    print("LLM parsing available")
else:
    print("Using regex fallback")
```

## Advanced Features

### Feature Suggestions

The LLM service can suggest features for forecasting models:

```python
from src.services.llm_service import LLMService

llm = LLMService()
suggestions = llm.suggest_features(
    item_name="milk",
    current_features=["quantity", "days_since_purchase"],
    error_description="Overestimating consumption by 25%"
)
print(suggestions)
```

### Decision Explanations

Generate human-readable explanations for shopping decisions:

```python
explanation = llm.explain_decision(
    item="milk",
    vendor="Amazon",
    quantity=2,
    forecast_confidence=0.85,
    price=5.99,
    user_preferences={"prefers_organic": True}
)
print(explanation)
```

### Setup Question Generation

Generate personalized onboarding questions:

```python
questions = llm.generate_questions(num_questions=10)
for i, q in enumerate(questions, 1):
    print(f"{i}. {q}")
```

## Security and Privacy

### Data Privacy

- **All processing is local** - LLM runs on your machine via Ollama
- **No data sent to cloud** - Conversations stay on your device
- **Conversation history** is stored in memory only (not persisted)

### Best Practices

1. **Don't share sensitive information** in chat unless necessary
2. **Clear history** after discussing personal/financial details
3. **Review logs** periodically if storing conversations
4. **Use secure connection** if accessing UI remotely

## Future Enhancements

Planned improvements for LLM integration:

- [ ] Persistent conversation storage (encrypted)
- [ ] Voice input/output
- [ ] Multi-turn task planning
- [ ] Integration with forecasting service
- [ ] Automated feature engineering
- [ ] Shopping cart building via chat
- [ ] Receipt parsing via vision model

## API Reference

### LLMService Class

```python
from src.services.llm_service import LLMService

# Initialize
llm = LLMService(model_name="gemma2:4b")

# Chat (basic)
response = llm.chat("What items are low in stock?")

# Chat with images
response = llm.chat(
    message="What's in this receipt?",
    images=["/path/to/receipt.jpg"]
)

# Chat with custom system prompt
response = llm.chat(
    message="Explain forecasting",
    system_prompt="You are a data science expert."
)

# Streaming chat
for chunk in llm.chat_stream("Tell me about forecasting"):
    print(chunk, end="", flush=True)

# Clear history
llm.clear_history()

# Get/set history
history = llm.get_history()
llm.set_history(history)
```

## Support

For issues or questions:
1. Check this documentation
2. Review application logs
3. Check Ollama documentation: [https://github.com/ollama/ollama](https://github.com/ollama/ollama)
4. Open an issue on P3-Edge GitHub repository

## Resources

- **Ollama:** [https://ollama.com](https://ollama.com)
- **Gemma Models:** [https://ollama.com/library/gemma2](https://ollama.com/library/gemma2)
- **P3-Edge Technical Plan:** See `plan/TECHNICAL_PLAN.md`
- **Phase 4 Details:** See Phase 4 section in technical plan
