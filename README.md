# P3-Edge: Autonomous Grocery Shopping Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An edge-computing autonomous grocery shopping agent that leverages on-device AI to track household inventory, predict needs, and execute seamless grocery orders through Amazon and Walmart.

## 🌟 Key Features

- **Edge-First Architecture**: All AI processing runs locally for maximum privacy
- **Encrypted Storage**: SQLCipher-encrypted database with AES-256 encryption
- **Smart Forecasting**: State space models with online learning for consumption prediction
- **LLM-Driven Intelligence**: Gemma 3n for conversational interface and adaptive learning
- **Privacy-By-Design**: Minimal internet usage, user-owned data, on-device processing
- **Multi-Vendor Support**: Amazon and Walmart integration with price comparison

## 📋 Current Status: Phase 4 - LLM Integration ✅

**Phase 1 (Foundation)** - COMPLETE ✅
- ✅ Project structure and directory layout
- ✅ PyQt6 UI shell with navigation
- ✅ SQLite database with SQLCipher encryption
- ✅ Core data models (Inventory, Order, Preference, AuditLog)
- ✅ Configuration management with encrypted credential storage
- ✅ Logging and audit trail infrastructure
- ✅ Initialization scripts

**Phase 2 (Data Ingestion)** - COMPLETE ✅
- ✅ Manual inventory entry UI
- ✅ Receipt OCR pipeline
- ✅ Smart fridge API integration
- ✅ Inventory history tracking

**Phase 3 (Forecasting Engine)** - COMPLETE ✅
- ✅ State space model implementation
- ✅ Online learning trainer
- ✅ Forecast generation and visualization
- ✅ Model checkpointing

**Phase 4 (LLM Integration)** - COMPLETE ✅
- ✅ Gemma 3 4b model integration via Ollama
- ✅ LLM inference service
- ✅ Conversational AI chat interface
- ✅ Feature suggestion capabilities
- ✅ Decision explanation generator
- ✅ Multimodal support (text + images)
- ✅ LLM-powered receipt parsing with JSON schema validation

**Phase 5 (E-Commerce Integration)** - COMPLETE ✅
- ✅ Amazon vendor client with product search
- ✅ Shopping cart management service
- ✅ Order creation and approval workflow
- ✅ Spend cap enforcement
- ✅ Shopping cart UI with search, cart, and orders
- ✅ Simulated order placement (ready for real API integration)

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- 8GB RAM minimum (16GB recommended for LLM features)
- 10GB disk space (13GB with Gemma 3 4b model)
- **Ollama** (for LLM features) - [Installation Guide](https://ollama.com)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/p3-edge.git
   cd p3-edge
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   
   You might need to install SQLCipher C library and headers, Tesseract
   ```bash
   sudo apt update
   sudo apt install sqlcipher libsqlcipher-dev
   sudo apt install tesseract-ocr 
   ```

   Python libraries:
   ```bash
   pip install -r requirements.txt
   ```



4. **Initialize the database**
   ```bash
   python scripts/init_db.py
   ```

   You'll be prompted to create a master password for database encryption. Choose a strong password and remember it!

5. **(Optional) Set up LLM features**

   To use the AI Chat and LLM-powered features:

   a. Install Ollama:
   ```bash
   # Linux
   curl -fsSL https://ollama.com/install.sh | sh

   # macOS
   brew install ollama

   # Windows: Download from https://ollama.com/download
   ```

   b. Start Ollama server:
   ```bash
   ollama serve
   ```
   (Keep this running in a separate terminal)

   c. Download Gemma 3 4b model:
   ```bash
   python scripts/download_model.py
   ```

   See [docs/LLM_SETUP.md](docs/LLM_SETUP.md) for detailed setup instructions.

6. **Run the application**
   ```bash
   python src/main.py
   ```

## 📁 Project Structure

```
p3-edge/
├── src/
│   ├── database/          # Database layer with SQLCipher
│   │   ├── db_manager.py
│   │   └── schema.sql
│   ├── models/            # Pydantic data models
│   │   ├── inventory.py
│   │   ├── order.py
│   │   ├── preference.py
│   │   └── audit_log.py
│   ├── ui/                # PyQt6 user interface
│   │   └── main_window.py
│   ├── config/            # Configuration management
│   │   └── config_manager.py
│   ├── utils/             # Utilities (logging, encryption)
│   │   ├── logger.py
│   │   └── encryption.py
│   └── main.py            # Application entry point
├── scripts/
│   ├── init_db.py         # Database initialization
│   └── download_model.py  # Model download (Phase 4)
├── tests/                 # Unit and integration tests
├── data/                  # Database storage (encrypted)
├── logs/                  # Application logs
├── models/                # ML models (Phase 4)
├── plan/                  # Project planning documents
│   ├── Task.txt
│   ├── My-Plan.txt
│   └── TECHNICAL_PLAN.md
├── requirements.txt       # Python dependencies
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

## 🔒 Security & Privacy

P3-Edge is built with privacy as the top priority:

- **Encrypted Database**: All data encrypted at rest with SQLCipher (AES-256)
- **Secure Credentials**: API credentials encrypted using Fernet symmetric encryption
- **Local Processing**: All AI inference happens on-device, no cloud dependency
- **Minimal Internet**: Network access only for price lookups and order placement
- **Audit Trail**: Complete transparency with audit logs for all system actions
- **No Telemetry**: Zero data collection or phone-home behavior

## 🏗️ Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.10+ | Rapid development, ML ecosystem |
| **UI Framework** | PyQt6 | Native performance, cross-platform |
| **Database** | SQLite + SQLCipher | Encrypted local storage |
| **Data Models** | Pydantic | Type safety, validation |
| **Encryption** | cryptography (Fernet) | Credential and data encryption |
| **Logging** | Python logging | Structured logging with rotation |
| **Testing** | pytest | Unit and integration tests |

### Database Schema

The application uses an encrypted SQLite database with the following core tables:

- **inventory**: Current household items and their quantities
- **inventory_history**: Time-series consumption data
- **forecasts**: Predicted run-out dates and recommendations
- **orders**: Shopping cart and order history
- **preferences**: User settings and preferences
- **audit_log**: Complete audit trail of all actions
- **model_metadata**: ML model versions and performance
- **vendor_products**: Cached product information from vendors
- **conversations**: LLM chat history (auto-purged after 30 days)

## 🎯 Development Roadmap

### ✅ Phase 1: Foundation (Weeks 1-2) - COMPLETE
- ✅ Project setup and structure
- ✅ Database with encryption
- ✅ Core data models
- ✅ Basic UI shell
- ✅ Configuration management
- ✅ Logging infrastructure

### ✅ Phase 2: Data Ingestion (Weeks 3-4) - COMPLETE
- ✅ Manual inventory entry UI
- ✅ Receipt OCR pipeline
- ✅ Smart fridge API integration
- ✅ Phone app stub for image upload
- ✅ Data validation and normalization

### ✅ Phase 3: Forecasting Engine (Weeks 5-6) - COMPLETE
- ✅ State space model implementation
- ✅ Online learning trainer
- ✅ Forecast generation and visualization
- ✅ Model checkpointing

### ✅ Phase 4: LLM Integration (Weeks 7-8) - COMPLETE
- ✅ Gemma 3 4b model download via Ollama
- ✅ LLM inference service with Python bindings
- ✅ Conversational chat interface in UI
- ✅ Feature suggestion module
- ✅ Decision explanation generator
- ✅ Question generation for onboarding
- ✅ Multimodal support (text + images)
- ✅ LLM-powered receipt parsing with JSON schema

### ✅ Phase 5: E-Commerce Integration (Weeks 9-10) - COMPLETE
- ✅ Amazon vendor client with product search
- ✅ Shopping cart management and item operations
- ✅ Order creation and approval workflow
- ✅ Spend cap enforcement
- ✅ Full shopping cart UI (search, cart, orders)
- ✅ Simulated order placement (architecture for real API)
- ⏳ Walmart API client (pending)
- ⏳ Real Amazon SP-API integration (pending credentials)

### 🔐 Phase 6: Privacy & Controls (Week 11)
- End-to-end encryption for phone sync
- Vendor controls
- Approval modes
- Audit log viewer

### ✨ Phase 7: Refinement & Testing (Week 12)
- Comprehensive testing
- Performance optimization
- Documentation
- Demo preparation

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_database.py
```

## 📝 Configuration

Configuration is managed through `config/app_config.json` and environment variables. Key settings:

```json
{
  "database": {
    "path": "data/p3edge.db",
    "encrypted": true
  },
  "forecasting": {
    "update_interval_hours": 24,
    "confidence_threshold": 0.7
  },
  "orders": {
    "approval_threshold": 50.0
  },
  "privacy": {
    "conversation_retention_days": 30,
    "data_retention_days": 365
  }
}
```

## 🔧 Development

### Code Quality

The project uses the following tools:

- **ruff**: Linting and code quality checks
- **black**: Code formatting
- **mypy**: Static type checking

Run code quality checks:

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type check
mypy src
```

### Adding New Features

1. Create a new branch
2. Implement feature with tests
3. Run code quality checks
4. Update documentation
5. Submit pull request

## 📚 Documentation

- [Technical Plan](plan/TECHNICAL_PLAN.md) - Comprehensive technical architecture
- [LLM Setup Guide](docs/LLM_SETUP.md) - Detailed guide for setting up AI Chat features
- [Task Requirements](plan/Task.txt) - Original project requirements
- [Vision Document](plan/My-Plan.txt) - Project vision and implementation notes

## 💬 Using AI Chat

The AI Chat feature (Phase 4) provides a conversational interface powered by Gemma 3 4b:

1. **Access**: Click "AI Chat" in the navigation panel
2. **Chat**: Type your questions and get intelligent responses
3. **Features**:
   - Natural language conversations about groceries
   - Inventory queries and recommendations
   - Shopping advice and explanations
   - Image support (attach receipts, photos)

**Example queries:**
- "What items are running low?"
- "Should I buy more milk this week?"
- "Explain how the forecasting works"
- "What's a good brand for organic pasta?"

See [docs/LLM_SETUP.md](docs/LLM_SETUP.md) for setup instructions.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with PyQt6 for the user interface
- Uses SQLCipher for database encryption
- Pydantic for data validation
- Inspired by privacy-first edge computing principles

## 📞 Support

For questions or issues:

- Create an issue on GitHub
- Check existing documentation in `plan/`
- Review the technical plan for architecture details

---

**Note**: This project is in active development. Phases 1-5 are complete (Foundation, Data Ingestion, Forecasting, LLM Integration, and E-Commerce Integration). Phase 6 (Privacy & Controls) is next.

**Privacy First. Edge Computing. Autonomous Intelligence.**
