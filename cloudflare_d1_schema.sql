CREATE TABLE IF NOT EXISTS acadformat_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    school_type TEXT NOT NULL,
    compliance_score INTEGER DEFAULT 0,
    title TEXT,
    author TEXT,
    reg_number TEXT,
    department TEXT,
    page_count INTEGER DEFAULT 1,
    status TEXT DEFAULT 'audited',
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_d1_docs_token ON acadformat_documents(token);
CREATE INDEX IF NOT EXISTS idx_d1_docs_created ON acadformat_documents(created_at DESC);

CREATE TABLE IF NOT EXISTS acadformat_reformats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    docx_path TEXT,
    pdf_path TEXT,
    page_count INTEGER DEFAULT 1,
    reformatted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (token) REFERENCES acadformat_documents(token) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_d1_reformats_token ON acadformat_reformats(token);

CREATE TABLE IF NOT EXISTS acadformat_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'super_admin')),
    registered_device_id TEXT,
    trial_expires_at TEXT NOT NULL,
    paid_until TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_d1_users_username ON acadformat_users(username);
CREATE INDEX IF NOT EXISTS idx_d1_users_email ON acadformat_users(email);
CREATE INDEX IF NOT EXISTS idx_d1_users_role ON acadformat_users(role);

CREATE TABLE IF NOT EXISTS acadformat_sessions (
    session_token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    device_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES acadformat_users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_d1_sessions_user ON acadformat_sessions(user_id);

CREATE TABLE IF NOT EXISTS acadformat_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 250,
    currency TEXT DEFAULT 'XAF',
    operator TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    transaction_ref TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'completed',
    paid_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    device_id TEXT,
    FOREIGN KEY (user_id) REFERENCES acadformat_users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_d1_payments_user ON acadformat_payments(user_id);
CREATE INDEX IF NOT EXISTS idx_d1_payments_ref ON acadformat_payments(transaction_ref);

CREATE TABLE IF NOT EXISTS acadformat_system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO acadformat_system_config (key, value) VALUES ('trial_duration_hours', '72');
INSERT OR IGNORE INTO acadformat_system_config (key, value) VALUES ('subscription_price_xaf', '250');
INSERT OR IGNORE INTO acadformat_system_config (key, value) VALUES ('subscription_duration_days', '7');

INSERT OR IGNORE INTO acadformat_users (id, full_name, username, email, password_hash, role, registered_device_id, trial_expires_at, paid_until, created_at)
VALUES (1, 'System Super Administrator', 'superadmin', 'superadmin@acadformat.uba.cm', 'e9b031b3e8a4a50d2bb812a64c4897f1$97b370ce5ebaa795493b2a265691ea4489bf7ae843f5546adfc2c253c306dfbc', 'super_admin', 'master_device', '2036-12-31T23:59:59Z', '2036-12-31T23:59:59Z', CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO acadformat_users (id, full_name, username, email, password_hash, role, registered_device_id, trial_expires_at, paid_until, created_at)
VALUES (2, 'UBa Academic Identity Admin', 'admin', 'admin@acadformat.uba.cm', '7993a61f307301c255e2d8ee34685ff8$85876609f984fe7e923b72c4ce05feefaf2284c47fcfaf248740c2a52df03d51', 'admin', 'admin_device', '2036-12-31T23:59:59Z', '2036-12-31T23:59:59Z', CURRENT_TIMESTAMP);
