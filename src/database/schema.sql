-- P3-Edge Database Schema
-- All tables use encrypted SQLCipher database

-- Inventory table - tracks current household items
CREATE TABLE IF NOT EXISTS inventory (
    item_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    unit TEXT,
    quantity_current REAL,
    quantity_min REAL,
    quantity_max REAL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    location TEXT,
    perishable INTEGER DEFAULT 0,
    expiry_date DATE,
    consumption_rate REAL,
    metadata TEXT,  -- JSON for extensibility
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category);
CREATE INDEX IF NOT EXISTS idx_inventory_location ON inventory(location);
CREATE INDEX IF NOT EXISTS idx_inventory_name ON inventory(name);

-- Inventory history - time-series data for consumption tracking
CREATE TABLE IF NOT EXISTS inventory_history (
    history_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    quantity REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source TEXT,  -- 'smart_fridge', 'receipt', 'manual', 'system'
    notes TEXT,
    FOREIGN KEY (item_id) REFERENCES inventory(item_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_item_time ON inventory_history(item_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON inventory_history(timestamp);

-- Forecasts - predicted run-out dates and recommendations
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    predicted_runout_date DATE,
    confidence REAL,  -- 0.0 to 1.0
    recommended_order_date DATE,
    recommended_quantity REAL,
    model_version TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    features_used TEXT,  -- JSON array
    actual_runout_date DATE,  -- Filled in after observation
    FOREIGN KEY (item_id) REFERENCES inventory(item_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_forecast_item ON forecasts(item_id);
CREATE INDEX IF NOT EXISTS idx_forecast_order_date ON forecasts(recommended_order_date);

-- Orders - shopping cart and order history
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    vendor TEXT NOT NULL,  -- 'amazon', 'walmart'
    status TEXT NOT NULL,  -- 'pending_approval', 'approved', 'placed', 'delivered', 'cancelled'
    items TEXT NOT NULL,  -- JSON array of {item_id, quantity, price, product_id}
    total_cost REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME,
    placed_at DATETIME,
    delivered_at DATETIME,
    user_notes TEXT,
    auto_generated INTEGER DEFAULT 1,  -- 0 = manual, 1 = auto
    vendor_order_id TEXT  -- External order ID from Amazon/Walmart
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_vendor ON orders(vendor);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);

-- User preferences - configuration and settings
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,  -- JSON for complex values
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Audit log - all system actions for transparency
CREATE TABLE IF NOT EXISTS audit_log (
    log_id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL,  -- 'inventory_update', 'forecast_generated', 'order_placed', etc.
    actor TEXT NOT NULL,  -- 'user', 'system', 'llm'
    details TEXT,  -- JSON with action-specific data
    outcome TEXT,  -- 'success', 'failure', 'pending'
    item_id TEXT,  -- Optional reference to inventory item
    order_id TEXT  -- Optional reference to order
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor);

-- Model metadata - ML model versions and performance
CREATE TABLE IF NOT EXISTS model_metadata (
    model_id TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,  -- 'forecasting', 'llm', etc.
    version TEXT NOT NULL,
    trained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    performance_metrics TEXT,  -- JSON with MAE, RMSE, etc.
    feature_names TEXT,  -- JSON array
    checkpoint_path TEXT,
    active INTEGER DEFAULT 1  -- 0 = archived, 1 = active
);

CREATE INDEX IF NOT EXISTS idx_model_type ON model_metadata(model_type);
CREATE INDEX IF NOT EXISTS idx_model_active ON model_metadata(active);

-- Vendor products - cached product information from Amazon/Walmart
CREATE TABLE IF NOT EXISTS vendor_products (
    product_id TEXT PRIMARY KEY,
    vendor TEXT NOT NULL,
    item_name TEXT NOT NULL,
    brand TEXT,
    price REAL,
    unit TEXT,
    quantity REAL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    product_url TEXT,
    image_url TEXT,
    in_stock INTEGER DEFAULT 1,
    metadata TEXT  -- JSON for additional vendor-specific data
);

CREATE INDEX IF NOT EXISTS idx_vendor_products_name ON vendor_products(item_name);
CREATE INDEX IF NOT EXISTS idx_vendor_products_vendor ON vendor_products(vendor);

-- User conversations - LLM chat history
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL,  -- 'user', 'assistant'
    message TEXT NOT NULL,
    context TEXT,  -- JSON with relevant context (item_ids, forecast_ids, etc.)
    auto_purge INTEGER DEFAULT 1  -- Purge after 30 days for privacy
);

CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);

-- Agent memory - autonomous agent's persistent memory stream
CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id TEXT PRIMARY KEY,
    cycle_id TEXT,  -- Groups memories from same autonomous cycle
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    memory_type TEXT NOT NULL,  -- 'observation', 'action', 'plan', 'summary', 'reflection'
    content TEXT NOT NULL,  -- The actual memory content
    importance INTEGER DEFAULT 1,  -- 1-10 scale for pruning strategy
    context TEXT,  -- JSON with relevant context (item_ids, tool_calls, etc.)
    outcome TEXT,  -- 'success', 'failure', 'pending', 'skipped'
    consolidated INTEGER DEFAULT 0,  -- 0 = raw memory, 1 = already summarized
    embedding BLOB  -- Future: vector embeddings for semantic search
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_timestamp ON agent_memory(timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_memory_cycle ON agent_memory(cycle_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_memory_importance ON agent_memory(importance);

-- User preferences - learned dietary preferences, allergies, and product preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,  -- 'dietary', 'allergy', 'product_preference', 'brand_preference', 'general'
    preference_key TEXT NOT NULL,  -- e.g., 'milk_type', 'peanut_allergy', 'organic_preference'
    preference_value TEXT NOT NULL,  -- e.g., 'oat milk', 'true', 'yes'
    confidence REAL DEFAULT 0.5,  -- 0.0-1.0 confidence score (increases with repeated mentions)
    source TEXT,  -- 'chat', 'autonomous', 'manual'
    learned_from TEXT,  -- conversation_id or cycle_id where this was learned
    first_mentioned DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_confirmed DATETIME DEFAULT CURRENT_TIMESTAMP,
    mention_count INTEGER DEFAULT 1,
    metadata TEXT  -- JSON for additional context
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_category ON user_preferences(category);
CREATE INDEX IF NOT EXISTS idx_user_preferences_key ON user_preferences(preference_key);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_preferences_key_value ON user_preferences(preference_key, preference_value);
