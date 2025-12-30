# P3-Edge: Autonomous Grocery Shopping Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

**P3-Edge** is a privacy-first, edge-computing autonomous grocery shopping assistant that leverages on-device AI to intelligently track household inventory, predict consumption patterns, and assist with grocery shopping—all while keeping your data encrypted and under your control.

## 🌟 Key Features

### 🤖 Autonomous Agent System
- **Scheduled Autonomous Cycles**: Runs on configurable intervals (default: hourly) to proactively maintain system health
- **Persistent Memory**: Maintains long-term memory of actions, observations, and reflections
- **Automatic Memory Summarization**: Intelligently consolidates preferences at 90% capacity to prevent unbounded growth
- **Tool-Augmented AI**: Executes 28+ specialized tools across database, forecasting, shopping, and utility categories
- **Decision Transparency**: Complete audit trail of all autonomous actions and reasoning

### 🧠 Intelligent Memory Management
- **Long-Term Preference Learning**: Learns and stores user preferences with confidence scoring
- **Automatic Summarization**: LLM-powered consolidation of low-confidence preferences when approaching word limits
- **Memory Settings UI**: View, add, edit, and delete learned preferences through dedicated settings tab
- **Capacity Monitoring**: Real-time tracking with color-coded progress indicators (blue/orange/red)

### 📊 Advanced Forecasting Engine
- **State Space Models**: PyTorch-based consumption prediction with Kalman filtering
- **Online Learning**: Continuously adapts to changing consumption patterns
- **Confidence Intervals**: 95% prediction intervals for robust forecasting
- **Multi-Item Tracking**: Simultaneous forecasting for all inventory items
- **Low Stock Alerts**: Proactive notifications for items running low within 3 days
- **Visual Charts**: Interactive matplotlib-based forecast visualization

### 🏪 Smart Shopping Integration
- **Multi-Vendor Support**: Amazon and Walmart product search and comparison
- **Shopping Cart Management**: Full cart operations (add, remove, update quantities)
- **Price Comparison**: Find best prices across vendors
- **Spend Cap Enforcement**: Budget protection built into order workflow
- **Order Approval System**: Human-in-the-loop for all purchases

### 📸 Receipt OCR & Data Ingestion
- **Tesseract OCR**: Automatic receipt scanning and text extraction
- **LLM-Powered Parsing**: Intelligent item extraction with JSON schema validation
- **Smart Fridge Integration**: API integration for automatic inventory sync
- **Manual Entry**: Direct inventory management through UI
- **Background Processing**: Non-blocking receipt processing with QThread workers

### 💬 Conversational AI Interface
- **Chat with P3**: Natural language interface for inventory queries and shopping advice
- **Flexible LLM Backend**: Choose between on-device (Ollama) or cloud API (Gemini)
- **Multimodal Support**: Text and image understanding
- **Chat History Management**: Clear chat functionality with database persistence
- **Context-Aware Responses**: Leverages learned preferences and inventory state

### 🔐 Privacy & Security First
- **Encrypted Database**: AES-256 encryption via SQLCipher for all stored data
- **Encrypted Logs**: Fernet symmetric encryption for log files protecting user privacy
- **On-Device Processing**: All AI inference can run locally with Ollama (no cloud dependency)
- **Secure Credential Storage**: Fernet encryption for API keys and sensitive settings
- **Zero Telemetry**: No data collection or phone-home behavior
- **Complete Audit Trail**: Transparent logging of all system actions

### 🛠️ Comprehensive Tool Suite

The autonomous agent has access to 28 specialized tools across 5 categories:

**Database Tools (6)**
- `get_inventory_items` - Retrieve all inventory items with quantities
- `search_inventory` - Search inventory by name or category
- `get_expiring_items` - Find items expiring within N days
- `get_forecasts` - Retrieve consumption forecasts
- `get_order_history` - View past orders
- `get_pending_orders` - Check pending orders awaiting approval

**Forecast Tools (5)**
- `generate_forecast` - Create consumption prediction for specific item
- `get_low_stock_predictions` - Identify items running low soon
- `analyze_usage_trends` - Analyze historical consumption patterns
- `get_model_performance` - Retrieve forecasting model metrics
- `check_model_health` - Verify model training status and quality

**Vendor Tools (8)**
- `search_products` - Search for products by name/category
- `batch_search_products` - Search for multiple items simultaneously
- `get_product_details` - Get detailed product information
- `check_product_availability` - Verify product stock status
- `add_to_cart` - Add items to shopping cart
- `view_cart` - View current cart contents
- `remove_from_cart` - Remove items from cart
- `update_cart_quantity` - Adjust item quantities in cart

**Training Tools (3)**
- `start_model_training` - Initiate forecasting model training
- `get_training_status` - Check training progress
- `get_training_history` - View training run history

**Utility Tools (7)**
- `calculate_days_remaining` - Estimate days until item runs out
- `calculate_quantity_needed` - Compute required purchase quantity
- `check_budget` - Verify spending against budget limits
- `get_user_preferences` - Retrieve stored user preferences
- `convert_unit` - Convert between measurement units
- `learn_user_preference` - Store new user preferences
- `get_learned_preferences` - Retrieve all learned preferences

### 🚫 Safety Through Tool Blocking

The following tools are **permanently blocked** to ensure safety and require human approval via UI:
- `place_order` - Order placement requires human confirmation
- `approve_order` - Order approval requires human interaction
- `delete_inventory_item` - Deletion requires explicit user action
- `modify_preferences` - Preference changes must go through settings UI
- `clear_database` - Permanently blocked to prevent accidental data loss

### ⚡ Responsive UI Architecture
- **Background Workers**: All long-running operations use QThread workers to prevent UI freezing
  - Receipt processing (OCR + LLM parsing)
  - Model training (PyTorch operations)
  - Forecast generation (batch predictions)
  - Forecast refresh (database queries)
- **Real-Time Updates**: PyQt6 signals for seamless UI state management
- **Progress Indicators**: Visual feedback during background operations

## Team
- Simranjeet Singh
- Amritpal Singh

## 🚀 Installation

### Prerequisites

- **Python 3.10+** (Python 3.11 recommended)
- **8GB RAM minimum** (16GB recommended for LLM features)
- **10GB disk space** (13GB with Gemma 3 4b model)
- **SQLCipher** C library and headers
- **Tesseract OCR** for receipt scanning
- **Ollama** (optional, for on-device LLM) - [Installation Guide](https://ollama.com)

### Step-by-Step Installation

#### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y sqlcipher libsqlcipher-dev tesseract-ocr
```

**macOS:**
```bash
brew install sqlcipher tesseract
```

**Windows:**
- Download SQLCipher from [SQLCipher Downloads](https://www.zetetic.net/sqlcipher/)
- Download Tesseract from [Tesseract Windows](https://github.com/UB-Mannheim/tesseract/wiki)

#### 2. Clone Repository

```bash
git clone https://github.com/esemsc-ss2524/p3-edge.git
cd p3-edge
```

#### 3. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 4. Install Python Dependencies

**For on-device LLM (Ollama):**
```bash
pip install -r requirements.txt
```

**For cloud LLM (Gemini API):**
```bash
pip install -r requirements.txt
pip install -r requirements-gemini.txt
```

#### 5. Initialize Database

```bash
python scripts/init_db.py
```

You'll be prompted to create a **master password** for database encryption. Choose a strong password and remember it—this cannot be recovered if lost!

#### 6. Configure LLM Service

P3-Edge supports two LLM backends:

**Option A: On-Device (Ollama) - Recommended for Privacy**

1. Install Ollama:
   ```bash
   # Linux
   curl -fsSL https://ollama.com/install.sh | sh

   # macOS
   brew install ollama

   # Windows: Download from https://ollama.com/download
   ```

2. Start Ollama server (keep running):
   ```bash
   ollama serve
   ```

3. Download model:
   ```bash
   python scripts/download_model.py
   ```

4. Configure in `config/app_config.json`:
   ```json
   {
     "llm": {
       "provider": "ollama",
       "model": "gemma3n:e2b-it-q4_K_M"
     }
   }
   ```

**Option B: Cloud API (Gemini)**

1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

2. Set environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

3. Configure in `config/app_config.json`:
   ```json
   {
     "llm": {
       "provider": "gemini",
       "model": "gemini-2.5-flash-lite"
     }
   }
   ```

See [docs/LLM_SETUP.md](docs/LLM_SETUP.md) for detailed LLM configuration.

#### 7. Run the Application

```bash
python src/main.py
```

## 📖 Common Usage

### Using the Autonomous Agent

The autonomous agent runs automatically on a schedule (default: hourly). To control it:

1. Navigate to **Settings** > **Autonomous** tab
2. Enable/disable autonomous mode
3. Adjust cycle interval (in minutes)
4. View recent autonomous actions in the Activity Feed

The agent will:
- Check for items running low
- Train forecasting models when needed
- Add low-stock items to cart (but won't place orders)
- Learn from your shopping patterns

### Managing Memory & Preferences

1. Navigate to **Settings** > **Memory** tab
2. View memory usage with color-coded capacity bar
3. See all learned preferences with confidence scores
4. Add, edit, or delete preferences manually
5. Memory auto-summarizes at 90% capacity

### Chatting with P3

1. Click **AI Chat** in the navigation panel
2. Ask natural language questions:
   - "What items are running low?"
   - "Should I buy more milk this week?"
   - "What's a good brand for organic pasta?"
   - "Show me my order history"
3. Attach images for receipt scanning or product queries
4. Clear chat history with the 🗑️ button

### Processing Receipts

1. Navigate to **Inventory** page
2. Click **Upload Receipt**
3. Select receipt image (JPG, PNG)
4. Click **Process Receipt** (runs OCR + LLM parsing in background)
5. Review extracted items
6. Confirm to add to inventory

### Viewing Forecasts

1. Navigate to **Forecasts** page
2. View predicted runout dates with confidence intervals
3. Click **View Chart** for detailed visualization
4. Use **Train Models** to improve accuracy
5. Use **Generate All Forecasts** to update predictions
6. Check **Low Stock Alerts** for items needing attention

### Shopping Workflow

1. Navigate to **Shopping Cart** page
2. Search for products by name
3. Add items to cart
4. Review cart and adjust quantities
5. Click **Create Order**
6. Review order summary
7. Approve order through UI (agent cannot place orders)

### Viewing Encrypted Logs

Logs are encrypted by default. To view them:

```bash
python scripts/view_logs.py

# View last 50 lines
python scripts/view_logs.py --tail 50

# Search for errors
python scripts/view_logs.py --grep "ERROR"

# View specific log file
python scripts/view_logs.py --file logs/p3edge.log.enc
```

## 📁 Project Structure

```
p3-edge/
├── src/
│   ├── database/              # Database layer with SQLCipher
│   │   ├── db_manager.py
│   │   └── schema.sql
│   ├── models/                # Pydantic data models
│   │   ├── inventory.py
│   │   ├── order.py
│   │   ├── preference.py
│   │   └── tool_models.py
│   ├── services/              # Business logic services
│   │   ├── autonomous_agent.py    # Autonomous agent with QThread workers
│   │   ├── memory_service.py      # Memory management with summarization
│   │   ├── llm_factory.py         # LLM service factory (Ollama/Gemini)
│   │   ├── ollama_llm_service.py  # On-device LLM service
│   │   ├── gemini_llm_service.py  # Cloud LLM service
│   │   └── forecast_service.py    # State space forecasting
│   ├── tools/                 # Agent tools (28 total)
│   │   ├── database_tools.py      # Inventory & order queries
│   │   ├── forecast_tools.py      # Forecasting operations
│   │   ├── vendor_tools.py        # Shopping & cart management
│   │   ├── training_tools.py      # Model training
│   │   ├── utility_tools.py       # Calculations & preferences
│   │   ├── blocked_tools.py       # Safety-blocked operations
│   │   ├── executor.py            # Tool execution engine
│   │   └── registry.py            # Tool registration system
│   ├── ui/                    # PyQt6 user interface
│   │   ├── main_window.py         # Main application window
│   │   ├── settings_page.py       # Settings with Memory tab
│   │   ├── chat_page.py           # AI chat interface
│   │   ├── forecast_page.py       # Forecast visualization
│   │   ├── p3_dashboard.py        # Dashboard with chat
│   │   └── dialogs/
│   │       └── receipt_upload_dialog.py  # Receipt processing UI
│   ├── utils/                 # Utilities
│   │   ├── logger.py              # Encrypted logging with Fernet
│   │   └── encryption.py          # Encryption utilities
│   └── main.py                # Application entry point
├── scripts/
│   ├── init_db.py             # Database initialization
│   ├── download_model.py      # LLM model download
│   └── view_logs.py           # Encrypted log viewer
├── config/
│   ├── app_config.json        # Application configuration
│   └── .key                   # Encryption key (auto-generated)
├── data/                      # Encrypted database storage
├── logs/                      # Encrypted application logs
├── models/                    # Forecasting model checkpoints
├── docs/
│   ├── LLM_SETUP.md          # LLM configuration guide
│   └── ENCRYPTED_LOGGING.md  # Logging documentation
├── requirements.txt           # Python dependencies (Ollama)
├── requirements-gemini.txt    # Additional dependencies (Gemini)
└── LICENSE                    # GPLv3 license
```

## ⚙️ Configuration

Configuration is managed through `config/app_config.json`:

```json
{
  "database": {
    "path": "data/p3edge.db",
    "encrypted": true
  },
  "logging": {
    "level": "INFO",
    "max_file_size_mb": 10,
    "backup_count": 5,
    "encrypt_logs": true
  },
  "llm": {
    "provider": "ollama",
    "model": "gemma3n:e2b-it-q4_K_M",
    "temperature": 0.7
  },
  "autonomous_agent": {
    "enabled": true,
    "cycle_interval_minutes": 60
  },
  "memory": {
    "max_entries": 1000,
    "max_preference_words": 1000,
    "summarization_threshold": 90.0
  },
  "forecasting": {
    "update_interval_hours": 24,
    "confidence_threshold": 0.7,
    "default_forecast_days": 14
  },
  "orders": {
    "approval_threshold": 50.0,
    "max_spend_weekly": 200.0
  },
  "privacy": {
    "conversation_retention_days": 30,
    "data_retention_days": 365
  }
}
```

## 🏗️ Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.10+ | Rapid development, ML ecosystem |
| **UI Framework** | PyQt6 | Native performance, cross-platform |
| **Database** | SQLite + SQLCipher | AES-256 encrypted local storage |
| **Data Models** | Pydantic | Type safety, validation |
| **ML Framework** | PyTorch | State space models, forecasting |
| **LLM (On-Device)** | Ollama + Gemma 3 | Privacy-first local inference |
| **LLM (Cloud)** | Gemini API | Optional cloud inference |
| **OCR** | Tesseract | Receipt text extraction |
| **Encryption** | cryptography (Fernet) | Log and credential encryption |
| **Logging** | Python logging | Encrypted rotating file handler |
| **Testing** | pytest | Unit and integration tests |

### Database Schema

The encrypted SQLite database includes:

- **inventory**: Current household items and quantities
- **inventory_history**: Time-series consumption tracking
- **forecasts**: Predicted runout dates and recommendations
- **orders**: Shopping cart and order history
- **preferences**: User preferences with confidence scores
- **memory**: Agent memory (observations, actions, reflections)
- **audit_log**: Complete audit trail of all actions
- **model_metadata**: ML model versions and performance metrics
- **vendor_products**: Cached product information from vendors
- **conversations**: LLM chat history (auto-purged after 30 days)

## 📚 Documentation

- [LLM Setup Guide](docs/LLM_SETUP.md) - Detailed guide for Ollama and Gemini configuration
- [Encrypted Logging](docs/ENCRYPTED_LOGGING.md) - Log encryption and viewing
- [API Documentation](docs/API.md) - Developer API reference

## 📄 License

This project is licensed under the **GNU General Public License v3.0** (GPLv3) - see the [LICENSE](LICENSE) file for details.

P3-Edge uses PyQt6 and other GPL-licensed libraries, therefore the entire project is distributed under GPLv3 to comply with those licenses.

### Key License Points:
- ✅ **Free to use, modify, and distribute**
- ✅ **Source code must remain open**
- ✅ **Derivative works must also be GPLv3**
- ✅ **Commercial use allowed**
- ⚠️ **No warranty provided**

## 🙏 Acknowledgments

- **PyQt6** - Modern Qt6 bindings for Python (GPL)
- **SQLCipher** - Encrypted SQLite database
- **Pydantic** - Data validation and settings management
- **PyTorch** - Machine learning framework
- **Ollama** - On-device LLM inference
- **Tesseract OCR** - Optical character recognition
- **Google Gemini** - Cloud LLM API (optional)

---

**Privacy First. Edge Computing. Autonomous Intelligence.**

Built with ❤️ for privacy-conscious grocery shopping.
