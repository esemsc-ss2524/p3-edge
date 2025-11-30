# Technical Plan: P3-Edge - Autonomous Grocery Shopping Agent

## Executive Summary

P3-Edge is an edge-computing autonomous grocery shopping agent that leverages on-device AI to track household inventory, predict needs, and execute seamless grocery orders through Amazon and Walmart. The system prioritizes privacy through local processing, encrypted data storage, and minimal internet usage.

**Key Differentiators:**
- Edge-first architecture with on-device LLM (Gemma 3n)
- Self-improving forecasting through online learning
- LLM-driven feature engineering and model adaptation
- Privacy-by-design with encrypted local storage
- MVP deployable on laptop, scalable to dedicated edge devices

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     P3-Edge System                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐      ┌──────────────────────────────┐  │
│  │  UI Layer     │◄────►│   Core Agent Engine          │  │
│  │  (Qt/PyQt)    │      │   (LLM Orchestrator)         │  │
│  └───────────────┘      └──────────────────────────────┘  │
│                                    │                        │
│                         ┌──────────┴──────────┐            │
│                         ▼                     ▼            │
│              ┌──────────────────┐  ┌──────────────────┐   │
│              │ Forecasting      │  │ Data Ingestion   │   │
│              │ Engine           │  │ Engine           │   │
│              │ (State Space     │  │ (OCR, Smart      │   │
│              │  Models)         │  │  Fridge API)     │   │
│              └──────────────────┘  └──────────────────┘   │
│                         │                     │            │
│                         ▼                     ▼            │
│              ┌────────────────────────────────────┐        │
│              │   Local Encrypted Storage          │        │
│              │   (SQLite + SQLCipher)             │        │
│              └────────────────────────────────────┘        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         External Integrations (Internet-Only)         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │ │
│  │  │ Amazon API   │  │ Walmart API  │  │ Phone App  │  │ │
│  │  │ (Orders)     │  │ (Orders)     │  │ (Receipts) │  │ │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Breakdown

#### **1.2.1 UI Layer (Qt/PyQt)**
- **Responsibility:** User interaction, visualization, approval flows
- **Features:**
  - Initial setup wizard (10-question onboarding)
  - Inventory dashboard with real-time status
  - Forecast visualization with confidence intervals
  - Shopping cart review and approval interface
  - Settings and controls (spend caps, vendor preferences, approval modes)
  - Audit log viewer
  - Manual inventory adjustment interface

#### **1.2.2 Core Agent Engine (LLM Orchestrator)**
- **Responsibility:** Central intelligence, decision-making, model management
- **Technology:** Gemma 3n (max quantization, CPU-only)
- **Features:**
  - Natural language conversation interface
  - Feature engineering suggestions for forecasting models
  - Model training orchestration
  - Forecast generation and evaluation
  - User preference learning
  - Decision explanation generation
  - Adaptive questioning based on uncertainty

#### **1.2.3 Forecasting Engine**
- **Responsibility:** Predict when items will run out
- **Technology:** PyTorch-based state space models
- **Features:**
  - Online learning (continuous model updates)
  - Per-item consumption models
  - Seasonal pattern detection
  - Household event adaptation (holidays, guests)
  - Dynamic feature sets (LLM-suggested)
  - Confidence estimation

#### **1.2.4 Data Ingestion Engine**
- **Responsibility:** Collect inventory data from multiple sources
- **Input Sources:**
  1. Smart refrigerator/pantry APIs (simulated for MVP)
  2. OCR-based receipt scanning (phone app integration)
  3. Email parsing for online order confirmations
  4. Manual user entries via UI
- **Technology:**
  - Tesseract OCR or lightweight vision model
  - Email parsing libraries (imaplib, email)
  - RESTful API for phone app integration

#### **1.2.5 Local Encrypted Storage**
- **Responsibility:** Privacy-first data persistence
- **Technology:** SQLite with SQLCipher extension
- **Data Stored:**
  - Inventory history (timestamped snapshots)
  - Consumption patterns
  - User preferences and constraints
  - Order history and audit logs
  - Model checkpoints and training metadata
  - Conversation history (encrypted)

#### **1.2.6 External Integrations**
- **Amazon Integration:**
  - Product search and pricing API
  - Shopping cart management
  - Order placement (OAuth 2.0)
  - Use Amazon Product Advertising API + SP-API
- **Walmart Integration:**
  - Product search and pricing API
  - Cart and checkout API
  - OAuth 2.0 authentication
- **Phone App (Receipt Scanner):**
  - Lightweight mobile app (React Native/Flutter)
  - Camera interface for receipt capture
  - Local WiFi sync to edge device
  - End-to-end encryption for image transfer

---

## 2. Technology Stack

### 2.1 Core Technologies

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Programming Language** | Python 3.10+ | Rich ML ecosystem, rapid development, PyTorch support |
| **UI Framework** | PyQt6 | Native performance, cross-platform, suitable for edge devices |
| **Edge LLM** | Gemma 3n (2B params) | Small footprint, CPU-friendly, vision capabilities |
| **LLM Runtime** | PyTorch 2.x (CPU) | Efficient inference, quantization support |
| **Quantization** | llama.cpp or GGUF | Aggressive quantization (Q4_K_M or Q2_K) |
| **Forecasting Models** | PyTorch + State Space Models | Online learning support, efficient inference |
| **Database** | SQLite + SQLCipher | Lightweight, encrypted, zero-config |
| **OCR** | Tesseract or PaddleOCR | Accurate receipt text extraction |
| **Vision (optional)** | Gemma 3n vision mode | If receipt parsing needs image understanding |
| **API Framework** | FastAPI (internal) | For phone app communication |
| **Encryption** | cryptography (Fernet) | AES-256 for data at rest and in transit |
| **HTTP Client** | httpx | Async support for API calls |

### 2.2 Development Tools

- **Version Control:** Git + GitHub
- **Package Management:** Poetry or pip + requirements.txt
- **Testing:** pytest, pytest-qt, pytest-asyncio
- **Code Quality:** ruff (linting), black (formatting), mypy (type checking)
- **CI/CD:** GitHub Actions
- **Documentation:** Sphinx or MkDocs

### 2.3 External Services

- **Amazon SP-API:** Product search, pricing, order placement
- **Walmart Open API:** Product search, pricing, checkout
- **Smart Fridge API (Simulated):** Mock API for MVP, real integrations later

---

## 3. Data Models

### 3.1 Core Entities

#### **Inventory Item**
```python
{
  "item_id": "uuid",
  "name": "string",
  "category": "string",
  "brand": "string (optional)",
  "unit": "string (oz, lb, count)",
  "quantity_current": "float",
  "quantity_min": "float (user-defined threshold)",
  "quantity_max": "float (typical stock level)",
  "last_updated": "timestamp",
  "location": "string (fridge, pantry, freezer)",
  "perishable": "boolean",
  "expiry_date": "date (optional)",
  "consumption_rate": "float (units/day)",
  "preferred_vendors": ["amazon", "walmart"],
  "price_history": [{"vendor": "string", "price": "float", "timestamp": "datetime"}]
}
```

#### **Forecast**
```python
{
  "forecast_id": "uuid",
  "item_id": "uuid",
  "predicted_runout_date": "date",
  "confidence": "float (0-1)",
  "recommended_order_date": "date",
  "recommended_quantity": "float",
  "model_version": "string",
  "created_at": "timestamp",
  "features_used": ["feature_name1", "feature_name2", ...],
  "actual_runout_date": "date (null until observed)"
}
```

#### **Order**
```python
{
  "order_id": "uuid",
  "vendor": "amazon | walmart",
  "status": "pending_approval | approved | placed | delivered | cancelled",
  "items": [{"item_id": "uuid", "quantity": "float", "price": "float"}],
  "total_cost": "float",
  "created_at": "timestamp",
  "approved_at": "timestamp (optional)",
  "placed_at": "timestamp (optional)",
  "user_notes": "string (optional)",
  "auto_generated": "boolean"
}
```

#### **User Preferences**
```python
{
  "spend_cap_weekly": "float",
  "spend_cap_monthly": "float",
  "approved_vendors": ["amazon", "walmart"],
  "approval_mode": "always | threshold | never",
  "approval_threshold": "float (dollar amount)",
  "brand_preferences": {"category": ["preferred_brands"]},
  "dietary_restrictions": ["vegetarian", "gluten-free", ...],
  "household_size": "int",
  "notification_preferences": {"low_stock": "boolean", "forecast_ready": "boolean"}
}
```

#### **Audit Log**
```python
{
  "log_id": "uuid",
  "timestamp": "datetime",
  "action_type": "inventory_update | forecast_generated | order_placed | user_approval | model_retrained",
  "actor": "user | system | llm",
  "details": "json (action-specific data)",
  "outcome": "success | failure | pending"
}
```

### 3.2 Database Schema (SQLite)

```sql
-- Inventory table
CREATE TABLE inventory (
    item_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    unit TEXT,
    quantity_current REAL,
    quantity_min REAL,
    quantity_max REAL,
    last_updated DATETIME,
    location TEXT,
    perishable INTEGER,
    expiry_date DATE,
    consumption_rate REAL,
    metadata TEXT  -- JSON for extensibility
);

-- Inventory history (time-series)
CREATE TABLE inventory_history (
    history_id TEXT PRIMARY KEY,
    item_id TEXT REFERENCES inventory(item_id),
    quantity REAL,
    timestamp DATETIME,
    source TEXT  -- 'smart_fridge', 'receipt', 'manual', etc.
);

-- Forecasts
CREATE TABLE forecasts (
    forecast_id TEXT PRIMARY KEY,
    item_id TEXT REFERENCES inventory(item_id),
    predicted_runout_date DATE,
    confidence REAL,
    recommended_order_date DATE,
    recommended_quantity REAL,
    model_version TEXT,
    created_at DATETIME,
    features_used TEXT,  -- JSON
    actual_runout_date DATE
);

-- Orders
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    vendor TEXT,
    status TEXT,
    items TEXT,  -- JSON
    total_cost REAL,
    created_at DATETIME,
    approved_at DATETIME,
    placed_at DATETIME,
    user_notes TEXT,
    auto_generated INTEGER
);

-- User preferences
CREATE TABLE preferences (
    key TEXT PRIMARY KEY,
    value TEXT  -- JSON for complex values
);

-- Audit logs
CREATE TABLE audit_log (
    log_id TEXT PRIMARY KEY,
    timestamp DATETIME,
    action_type TEXT,
    actor TEXT,
    details TEXT,  -- JSON
    outcome TEXT
);

-- Model metadata
CREATE TABLE model_metadata (
    model_id TEXT PRIMARY KEY,
    model_type TEXT,
    version TEXT,
    trained_at DATETIME,
    performance_metrics TEXT,  -- JSON
    feature_names TEXT,  -- JSON
    checkpoint_path TEXT
);
```

---

## 4. Core Algorithms

### 4.1 Forecasting Model (State Space Models)

**Approach:** Use state space models (SSM) with online learning for consumption rate estimation.

**Model Structure:**
- **State:** `[quantity, consumption_rate, trend, seasonal_component]`
- **Observations:** Inventory snapshots from multiple sources
- **Dynamics:** Linear Gaussian state space model with time-varying parameters

**PyTorch Implementation:**
```python
class ConsumptionForecaster(nn.Module):
    def __init__(self, feature_dim):
        super().__init__()
        # State transition matrix
        self.transition = nn.Linear(feature_dim, feature_dim)
        # Observation matrix
        self.observation = nn.Linear(feature_dim, 1)
        # Process noise
        self.process_noise = nn.Parameter(torch.tensor(0.1))
        # Observation noise
        self.obs_noise = nn.Parameter(torch.tensor(0.05))

    def forward(self, state, features):
        # Predict next state
        next_state = self.transition(state) + self.process_noise * torch.randn_like(state)
        # Predict observation
        predicted_quantity = self.observation(next_state)
        return next_state, predicted_quantity

    def update(self, state, observation, features):
        # Kalman filter update
        # ... (online update logic)
        return updated_state
```

**Online Learning Strategy:**
1. Initialize model with prior from LLM-suggested features
2. Update parameters incrementally with each new observation
3. Use exponential weighted moving average for stability
4. Retrain from scratch weekly with full history

**LLM-Driven Feature Engineering:**
- LLM analyzes forecast errors and suggests new features (e.g., "day_of_week", "holiday_indicator")
- User feedback on forecasts informs feature selection
- Features are dynamically added to the model input

### 4.2 LLM Orchestration (Gemma 3n)

**Model Selection:** Gemma 2B or 3B with 4-bit quantization (GGUF Q4_K_M)

**Key Prompts:**

1. **Initial Setup (Question Generation):**
```
You are a helpful grocery shopping assistant. Generate 10 concise questions to set up
household grocery management. Focus on: household size, dietary restrictions, typical
consumption patterns, budget constraints, and vendor preferences. Be conversational.
```

2. **Feature Suggestion:**
```
Current forecast error for "milk" is 25% (overestimating consumption).
Current features: [quantity, days_since_last_purchase, household_size]
Historical data shows patterns in consumption.
Suggest 3 new features that might improve forecast accuracy. Respond in JSON:
{"suggested_features": ["feature1", "feature2", "feature3"], "rationale": "..."}
```

3. **Conversational Interaction:**
```
User has low stock of [milk, eggs, bread]. Forecasts suggest runout in 2-3 days.
Ask the user a clarifying question about their shopping preferences for this week.
Be friendly and concise (max 2 sentences).
```

4. **Decision Explanation:**
```
Explain why the system is recommending to order [item] from [vendor] at [quantity].
Include: forecast confidence, price comparison, user preferences.
Provide a 2-sentence explanation.
```

**Inference Strategy:**
- Load model once at startup with quantization
- Use caching for repeated prompts
- Batch inference where possible (e.g., multiple item forecasts)
- Target <2s response time for conversational queries

### 4.3 Receipt OCR Pipeline

**Pipeline:**
1. **Preprocessing:** Deskew, binarize, enhance contrast
2. **OCR:** Tesseract or PaddleOCR with receipt-specific configuration
3. **Parsing:** Regex-based extraction of item names, quantities, prices
4. **Matching:** Fuzzy match items to existing inventory (LLM assistance if needed)
5. **Validation:** User review for ambiguous matches

**Gemma 3n Vision Alternative:**
- If OCR accuracy is insufficient, use Gemma 3n's vision capabilities
- Prompt: "Extract item names, quantities, and prices from this receipt image. Return JSON."
- Trade-off: Higher accuracy but slower processing

---

## 5. Privacy and Security Architecture

### 5.1 Data Encryption

**At Rest:**
- All SQLite databases encrypted with SQLCipher (AES-256)
- Encryption key derived from user-chosen password + device-specific salt
- Model checkpoints encrypted with same key
- Conversation logs encrypted and auto-purged after 30 days

**In Transit:**
- Phone app ↔ Edge device: TLS 1.3 + E2E encryption (Fernet)
- Edge device ↔ APIs: HTTPS only, certificate pinning for Amazon/Walmart

### 5.2 Privacy Guarantees

1. **No Cloud Processing:** All LLM inference and ML training on-device
2. **Minimal Internet Usage:** Only for price lookups and order placement
3. **User-Owned Storage:** All data stored locally, user controls backups
4. **Audit Trail:** Every system action logged for transparency
5. **Consent-Based Data Sharing:** No telemetry unless explicitly enabled by user

### 5.3 Security Controls

- **Authentication:** Master password for app access (optional biometrics)
- **API Credentials:** OAuth 2.0 tokens encrypted in keyring/secure storage
- **Network Isolation:** Firewall rules to restrict outbound connections
- **Secure Deletion:** Overwrite deleted data (secure_delete pragma in SQLite)

---

## 6. User Flows

### 6.1 First-Time Setup

1. **Welcome Screen:** Brief intro to P3-Edge capabilities
2. **Password Setup:** Create master password for data encryption
3. **10-Question Wizard:** LLM generates personalized questions
   - Household size and composition
   - Dietary preferences/restrictions
   - Budget constraints (weekly/monthly caps)
   - Vendor preferences (Amazon/Walmart)
   - Typical grocery categories
   - Shopping frequency
   - Approval mode preference
   - Smart appliance connectivity (if available)
4. **API Integration:** Guide user through Amazon/Walmart OAuth
5. **Initial Inventory:** User adds 10-20 core items manually or via receipt scan
6. **First Forecast:** System generates initial forecasts, explains methodology
7. **Notification Setup:** Configure alerts for low stock, pending orders

### 6.2 Daily Operation

1. **Background Monitoring:** System continuously ingests data from:
   - Smart fridge API (every 6 hours)
   - Phone app receipt uploads (on-demand)
   - Manual user edits
2. **Forecast Updates:** Models retrained daily at 2 AM with new data
3. **Low Stock Alerts:** User notified when items fall below threshold
4. **Shopping List Generation:** System proposes cart based on forecasts
5. **User Review:** User approves/modifies cart via UI
6. **Order Placement:** System places orders via Amazon/Walmart API
7. **Delivery Tracking:** User notified of order status
8. **Feedback Loop:** User confirms delivery, system updates inventory

### 6.3 Conversational Interaction

**Example:**
```
System: "Hi! I noticed you're low on milk and eggs. Based on your usual patterns,
         you'll run out in 2 days. Should I add them to your shopping list?"
User: "Yes, but I'm having guests this weekend."
System: "Got it! I'll adjust quantities for extra guests. How many people total?"
User: "6 people for 3 days."
System: "Thanks! I've updated the forecast. Adding 1 extra gallon of milk and
         1 dozen extra eggs. Total cart: $18.50 from Amazon. Approve?"
User: "Approved."
System: "Order placed! Delivery expected Friday. I'll update forecasts to learn
         from this event."
```

---

## 7. Development Phases

### Phase 1: Foundation (Weeks 1-2)

**Deliverables:**
- [ ] Project setup (repo, dependencies, dev environment)
- [ ] Basic PyQt UI shell (main window, navigation)
- [ ] SQLite database with encryption (SQLCipher)
- [ ] Core data models (inventory, orders, preferences)
- [ ] Configuration management (user prefs, API keys)
- [ ] Logging and audit trail infrastructure

**Technologies:**
- PyQt6, SQLite, SQLCipher, Python logging

### Phase 2: Data Ingestion (Weeks 3-4)

**Deliverables:**
- [ ] Manual inventory entry UI
- [ ] Receipt OCR pipeline (Tesseract)
- [ ] Smart fridge API simulator (mock data generator)
- [ ] Phone app stub (image upload over WiFi)
- [ ] Data normalization and validation
- [ ] Inventory history tracking

**Technologies:**
- Tesseract OCR, FastAPI (for phone app API), PIL/OpenCV

### Phase 3: Forecasting Engine (Weeks 5-6)

**Deliverables:**
- [ ] State space model implementation (PyTorch)
- [ ] Online learning trainer
- [ ] Per-item forecast generation
- [ ] Confidence interval estimation
- [ ] Forecast visualization in UI
- [ ] Model checkpointing and versioning

**Technologies:**
- PyTorch, NumPy, Matplotlib (for UI charts)

### Phase 4: LLM Integration (Weeks 7-8)

**Deliverables:**
- [ ] Gemma 3n model download and quantization
- [ ] LLM inference engine (llama.cpp or transformers)
- [ ] Initial setup wizard (10 questions)
- [ ] Feature suggestion module
- [ ] Conversational interface in UI
- [ ] Decision explanation generator

**Technologies:**
- Gemma 3n, llama.cpp or transformers, GGUF quantization

### Phase 5: E-Commerce Integration (Weeks 9-10)

**Deliverables:**
- [ ] Amazon SP-API client (OAuth, product search, cart, orders)
- [ ] Walmart API client (OAuth, product search, checkout)
- [ ] Price comparison logic
- [ ] Shopping cart builder
- [ ] Order approval UI
- [ ] Spend cap enforcement

**Technologies:**
- httpx, OAuth2 libraries (authlib), Amazon SP-API SDK

### Phase 6: Privacy & Controls (Week 11)

**Deliverables:**
- [ ] End-to-end encryption for phone app sync
- [ ] Vendor allowlist/blocklist
- [ ] Approval mode settings (always/threshold/never)
- [ ] Audit log viewer UI
- [ ] Secure credential storage (keyring)
- [ ] Data export/backup functionality

**Technologies:**
- cryptography (Fernet), keyring library

### Phase 7: Refinement & Testing (Week 12)

**Deliverables:**
- [ ] Unit tests (pytest, >80% coverage)
- [ ] Integration tests (API mocking)
- [ ] UI tests (pytest-qt)
- [ ] Performance optimization (model inference <2s)
- [ ] User documentation (setup guide, FAQ)
- [ ] Demo script with synthetic data

**Technologies:**
- pytest, pytest-qt, pytest-mock, locust (performance testing)

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Coverage Areas:**
- Data models (validation, serialization)
- Forecasting algorithms (accuracy, convergence)
- LLM prompt templates (output parsing)
- OCR pipeline (text extraction)
- Encryption/decryption (correctness)

**Tools:** pytest, pytest-cov

### 8.2 Integration Tests

**Test Scenarios:**
- End-to-end inventory update → forecast → order flow
- API integration (mocked Amazon/Walmart responses)
- Phone app sync (encrypted image transfer)
- Database migrations and schema changes

**Tools:** pytest-asyncio, responses (HTTP mocking)

### 8.3 UI Tests

**Test Cases:**
- Wizard navigation (10-question setup)
- Inventory CRUD operations
- Cart approval and modification
- Settings updates

**Tools:** pytest-qt, QTest

### 8.4 Performance Tests

**Benchmarks:**
- LLM inference time (<2s per query)
- Forecast generation for 100 items (<5s)
- UI responsiveness (no blocking operations)
- Database query performance (<100ms for common queries)

**Tools:** cProfile, pytest-benchmark

### 8.5 Privacy Tests

**Validation:**
- Encrypted data cannot be read without password
- Network traffic only to Amazon/Walmart (no telemetry)
- API credentials never logged in plaintext
- Audit log captures all system actions

**Tools:** Wireshark, mitmproxy (traffic inspection)

---

## 9. Deployment & Packaging

### 9.1 MVP Deployment (Laptop)

**Requirements:**
- Python 3.10+ (via pyenv or system)
- 8GB RAM minimum (4GB for LLM, 2GB for OS, 2GB buffer)
- 10GB disk space (models, database, logs)
- WiFi connectivity (for phone app, API calls)

**Installation:**
```bash
# Clone repo
git clone https://github.com/your-org/p3-edge.git
cd p3-edge

# Install dependencies
pip install -r requirements.txt

# Download Gemma 3n model
python scripts/download_model.py

# Initialize database
python scripts/init_db.py

# Run application
python main.py
```

### 9.2 Future Edge Device Deployment

**Target Hardware:**
- Raspberry Pi 5 (8GB) or equivalent ARM board
- 7-inch touchscreen display
- USB webcam (for future barcode scanning)
- WiFi module
- Optional: Coral TPU for faster OCR

**Packaging:**
- PyInstaller or Docker container
- systemd service for auto-start
- OTA update mechanism (future)

---

## 10. Risk Mitigation

### 10.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **LLM inference too slow on CPU** | High | Use aggressive quantization (Q2_K), limit context length, cache common prompts |
| **Forecast accuracy insufficient** | Medium | Combine ML with simple heuristics, allow manual overrides, continuous learning |
| **Amazon/Walmart API rate limits** | Medium | Implement exponential backoff, cache product data locally, batch requests |
| **OCR errors on receipts** | Low | Fallback to manual entry, use Gemma 3n vision for complex receipts |
| **Smart fridge API unavailable** | Low | Use simulated data for MVP, design modular connectors for future integrations |

### 10.2 Privacy Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Data breach (device theft)** | High | Full-disk encryption, master password requirement, auto-lock after inactivity |
| **API credential leakage** | High | Keyring storage, OAuth token rotation, never log credentials |
| **Unintended internet usage** | Medium | Firewall rules, network traffic monitoring, user-visible connection indicators |

### 10.3 User Experience Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Complex setup process** | Medium | LLM-guided wizard, sensible defaults, skip-able advanced settings |
| **False positives (incorrect forecasts)** | Low | Display confidence scores, easy cart editing, learn from user corrections |
| **Vendor lock-in (Amazon/Walmart)** | Low | Design modular vendor adapters for future expansion |

---

## 11. Success Metrics

### 11.1 MVP Success Criteria

**Functional:**
- [ ] 95%+ accuracy in inventory tracking (simulated smart fridge + receipts)
- [ ] Forecasts within ±3 days for 80% of items
- [ ] Successful order placement via Amazon and Walmart APIs
- [ ] <2s LLM response time for conversational queries
- [ ] Zero plaintext storage of sensitive data

**Usability:**
- [ ] Setup wizard completable in <10 minutes
- [ ] Cart approval flow requires <3 clicks
- [ ] User can understand forecast rationale from explanations

**Privacy:**
- [ ] All data encrypted at rest (verified via SQLCipher)
- [ ] No network traffic except to Amazon/Walmart/phone app (verified via Wireshark)
- [ ] Audit log captures 100% of system actions

### 11.2 Future KPIs

- User time saved per week (target: 30+ minutes)
- Cost savings from price comparison (target: 10%+)
- Food waste reduction (track perishables)
- Forecast accuracy improvement over time (online learning)

---

## 12. Future Enhancements

### 12.1 Post-MVP Features (Phase 2)

1. **Flare Character AI:** Personified robot with personality, animations, voice output
2. **Barcode Scanning:** Use webcam/phone camera for faster item entry
3. **Recipe Integration:** Suggest meals based on inventory, add ingredients to cart
4. **Multi-User Support:** Family accounts with individual preferences
5. **Advanced ML:** Deep learning models (LSTM, Transformer) for complex patterns
6. **Real Smart Appliance Integration:** LG ThinQ, Samsung SmartThings, etc.
7. **Subscription Management:** Track and optimize recurring orders

### 12.2 Hardware Evolution

- Custom edge device with touchscreen (7-10 inches)
- Built-in camera for barcode/receipt scanning
- Voice interface (wake word detection)
- Battery backup for mobility

---

## 13. Technical Debt Prevention

### 13.1 Code Quality Standards

- **Linting:** Ruff with strict rules
- **Formatting:** Black (line length 100)
- **Type Hints:** 100% coverage with mypy in strict mode
- **Documentation:** Docstrings for all public APIs (Google style)
- **Testing:** Minimum 80% code coverage

### 13.2 Architectural Principles

1. **Separation of Concerns:** UI, business logic, data access clearly separated
2. **Dependency Injection:** Facilitate testing and modularity
3. **Event-Driven:** Use pub/sub for cross-component communication
4. **Immutable Data:** Prefer immutable structures to prevent side effects
5. **Configuration as Code:** All settings externalized, version-controlled

### 13.3 Refactoring Checkpoints

- After Phase 3: Review data models and DB schema
- After Phase 5: Refactor API clients into generic vendor interface
- After Phase 7: Performance profiling and optimization pass

---

## 14. Documentation Plan

### 14.1 User Documentation

1. **Setup Guide:** Step-by-step installation and configuration
2. **User Manual:** Feature explanations, screenshots, FAQs
3. **Privacy Policy:** Data handling, encryption, user rights
4. **Troubleshooting Guide:** Common issues and solutions

### 14.2 Developer Documentation

1. **Architecture Document:** System design, component interactions
2. **API Reference:** All public interfaces (auto-generated from docstrings)
3. **Contributing Guide:** Code standards, PR process, testing requirements
4. **Model Documentation:** Forecasting algorithms, feature engineering, training process

### 14.3 Operational Documentation

1. **Deployment Guide:** Installation on edge devices
2. **Monitoring Guide:** Logs, metrics, health checks
3. **Backup and Recovery:** Data export/import procedures
4. **Security Incident Response:** Breach detection and mitigation

---

## 15. Project Timeline Summary

**Total Duration:** 12 weeks (MVP)

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 1. Foundation | 2 weeks | Database + UI shell |
| 2. Data Ingestion | 2 weeks | OCR + smart fridge simulator |
| 3. Forecasting | 2 weeks | State space models + online learning |
| 4. LLM Integration | 2 weeks | Gemma 3n + conversational UI |
| 5. E-Commerce | 2 weeks | Amazon/Walmart APIs |
| 6. Privacy & Controls | 1 week | Encryption + audit logs |
| 7. Testing & Refinement | 1 week | Testing + documentation |

**Buffer:** 2 weeks for unforeseen challenges

---

## 16. Conclusion

P3-Edge represents a privacy-first, edge-computing approach to autonomous grocery shopping. By combining on-device AI (Gemma 3n), adaptive forecasting (state space models with online learning), and user-centric controls, the system balances automation with user agency.

**Key Innovations:**
1. **LLM-driven feature engineering:** Models improve through AI-suggested features
2. **Edge-first architecture:** Zero cloud dependency for core operations
3. **Privacy by design:** Encryption, local storage, minimal internet usage
4. **Adaptive learning:** Continuous model updates from user feedback

**Next Steps:**
1. Review and refine this technical plan
2. Set up development environment and project repository
3. Begin Phase 1: Foundation implementation
4. Schedule weekly check-ins to track progress

This plan provides a comprehensive roadmap to build a production-ready MVP in 12 weeks, with clear pathways for future enhancements and scalability to dedicated edge hardware.
