"""
AcadFormat Database Layer: Supabase Integration with Local SQLite Fallback.
Provides comprehensive persistence for users, RBAC (user/admin/super_admin),
device locking, 72-hour free trials, MTN MoMo / Orange Money paywall (250 FCFA),
document audits, reformatting history, and platform analytics.
"""
import os
import json
import sqlite3
import datetime
import hashlib
import secrets
import httpx
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _resolve_storage_dir():
    if os.environ.get("STORAGE_DIR"):
        return os.environ["STORAGE_DIR"]
    local_storage = os.path.join(BASE_DIR, "storage")
    try:
        os.makedirs(local_storage, exist_ok=True)
        test_file = os.path.join(local_storage, ".write_test")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return local_storage
    except Exception:
        fallback = "/tmp/acadformat_storage"
        os.makedirs(fallback, exist_ok=True)
        return fallback

STORAGE_DIR = _resolve_storage_dir()
LOCAL_DB_PATH = os.path.join(STORAGE_DIR, "acadformat.db")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))).strip()

# Cloudflare D1 Serverless Database Configuration
CLOUDFLARE_DATABASE_ID = os.getenv("CLOUDFLARE_DATABASE_ID", "1ce80e78-f367-494d-aa47-5c87a8e02613").strip()
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()

def is_cloudflare_configured() -> bool:
    """Returns True if Cloudflare D1 Database ID, Account ID, and API Token are provided."""
    return bool(CLOUDFLARE_DATABASE_ID and CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN)

def is_supabase_configured() -> bool:
    """Returns True if valid Supabase URL and Key are provided."""
    return bool(SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL.startswith("http"))

def get_database_status() -> Dict[str, Any]:
    """Returns current active database provider status."""
    active_engine = "sqlite_fallback"
    if is_cloudflare_configured():
        active_engine = "cloudflare_d1"
    elif is_supabase_configured():
        active_engine = "supabase"

    return {
        "active_engine": active_engine,
        "cloudflare_d1": {
            "configured": is_cloudflare_configured(),
            "database_id": CLOUDFLARE_DATABASE_ID,
            "account_id_configured": bool(CLOUDFLARE_ACCOUNT_ID),
            "api_token_configured": bool(CLOUDFLARE_API_TOKEN)
        },
        "supabase": {
            "configured": is_supabase_configured()
        },
        "local_sqlite": {
            "ready": os.path.exists(LOCAL_DB_PATH),
            "path": LOCAL_DB_PATH
        }
    }

def execute_d1_query(sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    """
    Executes a SQL query against Cloudflare D1 via the official REST API v4.
    Endpoint: POST https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query
    """
    if not is_cloudflare_configured():
        return []
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "sql": sql,
        "params": params or []
    }
    with httpx.Client(timeout=5.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") and data.get("result"):
            res_obj = data["result"][0]
            return res_obj.get("results", [])
    return []

def sync_to_cloudflare_d1(sql: str, params: Optional[List[Any]] = None):
    """Syncs a write query to Cloudflare D1 in the cloud if credentials are configured."""
    if is_cloudflare_configured():
        try:
            execute_d1_query(sql, params)
        except Exception as e:
            print(f"[Cloudflare D1 Sync Error] {e}")

def get_supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

# ---------------------------------------------------------
# Password Security (Salted PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${pw_hash.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, pw_hash = stored_hash.split("$", 1)
        calc_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        return secrets.compare_digest(calc_hash, pw_hash)
    except Exception:
        return False

# ---------------------------------------------------------
# Database Initialization & Default Seeding
# ---------------------------------------------------------
def init_local_db():
    """Initializes local SQLite database with all required tables and default seeds."""
    try:
        os.makedirs(STORAGE_DIR, exist_ok=True)
        conn = sqlite3.connect(LOCAL_DB_PATH)
    except Exception as e:
        print(f"[AcadFormat] SQLite storage init warning: {e}")
        return

    try:
        cursor = conn.cursor()

        # 1. Documents & Reformats
        cursor.execute("""
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
            created_at TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS acadformat_reformats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            docx_path TEXT,
            pdf_path TEXT,
            page_count INTEGER DEFAULT 1,
            reformatted_at TEXT NOT NULL,
            FOREIGN KEY (token) REFERENCES acadformat_documents(token)
        )
        """)

        # 2. Users & RBAC
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS acadformat_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            registered_device_id TEXT,
            trial_expires_at TEXT NOT NULL,
            paid_until TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # 3. User Sessions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS acadformat_sessions (
            session_token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            device_id TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES acadformat_users(id)
        )
        """)

        # 4. Mobile Money Payments
        cursor.execute("""
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
            paid_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES acadformat_users(id)
        )
        """)

        # 5. System Configuration
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS acadformat_system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)

        # Insert default config values if missing
        default_configs = {
            "trial_duration_hours": "72",
            "subscription_price_xaf": "250",
            "subscription_duration_days": "7"
        }
        for k, v in default_configs.items():
            cursor.execute("INSERT OR IGNORE INTO acadformat_system_config (key, value) VALUES (?, ?)", (k, v))

        # Seed Default Super Admin and Admin if not present
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        far_future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650)).isoformat()

        # Super Admin
        cursor.execute("SELECT id FROM acadformat_users WHERE username = 'superadmin' OR email = 'superadmin@acadformat.uba.cm'")
        if not cursor.fetchone():
            sadmin_pw = hash_password("SuperAdmin@2026")
            cursor.execute("""
            INSERT INTO acadformat_users (full_name, username, email, password_hash, role, registered_device_id, trial_expires_at, paid_until, created_at)
            VALUES (?, ?, ?, ?, 'super_admin', 'master_device', ?, ?, ?)
            """, ("System Super Administrator", "superadmin", "superadmin@acadformat.uba.cm", sadmin_pw, far_future, far_future, now_iso))

        # Admin
        cursor.execute("SELECT id FROM acadformat_users WHERE username = 'admin' OR email = 'admin@acadformat.uba.cm'")
        if not cursor.fetchone():
            admin_pw = hash_password("Admin@2026")
            cursor.execute("""
            INSERT INTO acadformat_users (full_name, username, email, password_hash, role, registered_device_id, trial_expires_at, paid_until, created_at)
            VALUES (?, ?, ?, ?, 'admin', 'admin_device', ?, ?, ?)
            """, ("UBa Academic Identity Admin", "admin", "admin@acadformat.uba.cm", admin_pw, far_future, far_future, now_iso))

        conn.commit()
    except Exception as e:
        print(f"[AcadFormat] Database initialization notice: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

# Initialize DB on module load safely
try:
    init_local_db()
except Exception as e:
    print(f"[AcadFormat] Startup init notice: {e}")

# ---------------------------------------------------------
# User Authentication & Management
# ---------------------------------------------------------
def create_user(
    full_name: str,
    username: str,
    email: str,
    password: str,
    device_id: str,
    role: str = "user"
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registers a new user, initiates the 72-hour free trial, and locks account to the initial device.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    config = get_system_config()
    trial_hours = int(config.get("trial_duration_hours", 72))
    trial_expires = (now + datetime.timedelta(hours=trial_hours)).isoformat()
    now_iso = now.isoformat()

    pw_hash = hash_password(password)

    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    try:
        # Check existing
        cursor.execute("SELECT id, username, email FROM acadformat_users WHERE username = ? OR email = ?", (username.strip(), email.strip().lower()))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return False, "Username or email is already registered.", None

        cursor.execute("""
        INSERT INTO acadformat_users 
        (full_name, username, email, password_hash, role, registered_device_id, trial_expires_at, paid_until, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """, (full_name.strip(), username.strip(), email.strip().lower(), pw_hash, role, device_id.strip(), trial_expires, now_iso))
        user_id = cursor.lastrowid
        conn.commit()

        # Fetch created user
        conn.row_factory = sqlite3.Row
        cur2 = conn.cursor()
        cur2.execute("SELECT id, full_name, username, email, role, registered_device_id, trial_expires_at, paid_until, created_at FROM acadformat_users WHERE id = ?", (user_id,))
        user_row = dict(cur2.fetchone())
        conn.close()

        # Sync to Cloudflare D1 if configured
        sync_to_cloudflare_d1(
            "INSERT INTO acadformat_users (id, full_name, username, email, password_hash, role, registered_device_id, trial_expires_at, paid_until, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
            [user_id, full_name.strip(), username.strip(), email.strip().lower(), pw_hash, role, device_id.strip(), trial_expires, now_iso]
        )

        # Sync to Supabase if available
        if is_supabase_configured():
            try:
                url = f"{SUPABASE_URL}/rest/v1/acadformat_users"
                with httpx.Client(timeout=4.0) as client:
                    client.post(url, headers=get_supabase_headers(), json={
                        "full_name": full_name.strip(),
                        "username": username.strip(),
                        "email": email.strip().lower(),
                        "password_hash": pw_hash,
                        "role": role,
                        "registered_device_id": device_id.strip(),
                        "trial_expires_at": trial_expires,
                        "created_at": now_iso
                    })
            except Exception as e:
                print(f"[Supabase Sync] Error syncing user: {e}")

        return True, "Account created successfully.", user_row
    except Exception as e:
        conn.close()
        return False, f"Registration failed: {str(e)}", None


def authenticate_user(identifier: str, password: str, current_device_id: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticates user by email or username, and returns status including device lock evaluation.
    """
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, full_name, username, email, password_hash, role, registered_device_id, trial_expires_at, paid_until, created_at
    FROM acadformat_users 
    WHERE LOWER(username) = ? OR LOWER(email) = ?
    """, (identifier.strip().lower(), identifier.strip().lower()))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, "Invalid email/username or password.", None

    user = dict(row)
    if not verify_password(password, user["password_hash"]):
        return False, "Invalid email/username or password.", None

    # Remove password hash from returned object
    del user["password_hash"]

    # Device check: if registered_device_id was empty, auto-bind
    if current_device_id and not user.get("registered_device_id"):
        bind_device(user["id"], current_device_id)
        user["registered_device_id"] = current_device_id

    # Check device match
    user["device_matched"] = bool(
        user["role"] in ["admin", "super_admin"] or
        not user.get("registered_device_id") or
        user.get("registered_device_id") == current_device_id
    )

    return True, "Authentication successful.", user


def bind_device(user_id: int, device_id: str) -> bool:
    """Updates the registered device for a user."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE acadformat_users SET registered_device_id = ? WHERE id = ?", (device_id, user_id))
    conn.commit()
    conn.close()
    return True


def create_session(user_id: int, device_id: Optional[str] = None) -> str:
    """Creates and records a session token valid for 30 days."""
    token = secrets.token_urlsafe(32)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = (now + datetime.timedelta(days=30)).isoformat()
    now_iso = now.isoformat()

    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO acadformat_sessions (session_token, user_id, device_id, created_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
    """, (token, user_id, device_id, now_iso, expires))
    conn.commit()
    conn.close()
    return token


def get_user_by_session(session_token: str) -> Optional[Dict[str, Any]]:
    """Retrieves user info corresponding to active session."""
    if not session_token:
        return None
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT s.session_token, s.device_id as session_device_id, s.expires_at as session_expires_at,
           u.id, u.full_name, u.username, u.email, u.role, u.registered_device_id, u.trial_expires_at, u.paid_until, u.created_at
    FROM acadformat_sessions s
    JOIN acadformat_users u ON s.user_id = u.id
    WHERE s.session_token = ?
    """, (session_token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    data = dict(row)
    # Check session expiration
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if data["session_expires_at"] < now_iso:
        return None
    return data


# ---------------------------------------------------------
# Eligibility & Paywall Enforcement
# ---------------------------------------------------------
def check_download_eligibility(user_id: int, current_device_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates whether the user can download/export documents.
    Criteria:
      - Admin & Super Admin: Always eligible.
      - Device Check: Must match registered_device_id. If shared to a different device, payment is required.
      - Trial Check: Eligible if current UTC time < trial_expires_at.
      - Subscription Check: Eligible if current UTC time < paid_until.
      - Otherwise: Ineligible (requires 250 FCFA MoMo/Orange payment).
    """
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, username, email, role, registered_device_id, trial_expires_at, paid_until FROM acadformat_users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"allowed": False, "reason": "user_not_found", "message": "User account not found."}

    user = dict(row)
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()

    # 1. Admin bypass
    if user["role"] in ["admin", "super_admin"]:
        return {
            "allowed": True,
            "reason": "administrative_access",
            "message": f"Unlimited administrative access granted ({user['role']}).",
            "trial_active": True,
            "paid_active": True,
            "device_matched": True
        }

    # 2. Device match check
    registered_device = user.get("registered_device_id")
    device_matched = (not registered_device) or (registered_device == current_device_id)

    # 3. Check trial status
    trial_expires = datetime.datetime.fromisoformat(user["trial_expires_at"])
    trial_active = now < trial_expires
    trial_seconds_left = max(0, int((trial_expires - now).total_seconds()))

    # 4. Check paid subscription status
    paid_active = False
    paid_seconds_left = 0
    if user.get("paid_until"):
        paid_expires = datetime.datetime.fromisoformat(user["paid_until"])
        if now < paid_expires:
            paid_active = True
            paid_seconds_left = max(0, int((paid_expires - now).total_seconds()))

    # If device is NOT matched (account sharing detected):
    if not device_matched:
        return {
            "allowed": False,
            "reason": "device_mismatch",
            "message": "Account is locked to another device. Please pay 250 FCFA via MTN MoMo or Orange Money to authorize this device.",
            "device_matched": False,
            "trial_active": trial_active,
            "paid_active": paid_active,
            "registered_device": registered_device,
            "current_device": current_device_id
        }

    # If on registered device:
    if trial_active:
        return {
            "allowed": True,
            "reason": "free_trial",
            "message": f"Free trial active: {trial_seconds_left // 3600} hours remaining.",
            "trial_active": True,
            "paid_active": paid_active,
            "trial_seconds_left": trial_seconds_left,
            "device_matched": True
        }

    if paid_active:
        return {
            "allowed": True,
            "reason": "paid_subscription",
            "message": f"7-day access active: {paid_seconds_left // 86400} days remaining.",
            "trial_active": False,
            "paid_active": True,
            "paid_seconds_left": paid_seconds_left,
            "device_matched": True
        }

    return {
        "allowed": False,
        "reason": "trial_expired",
        "message": "Your 72-hour free trial has ended. Unlock 7 days of unlimited exports for only 250 FCFA via MTN MoMo or Orange Money.",
        "trial_active": False,
        "paid_active": False,
        "device_matched": True
    }


# ---------------------------------------------------------
# Mobile Money Payment Processing & Unlocking
# ---------------------------------------------------------
def record_payment(
    user_id: int,
    operator: str,
    phone_number: str,
    device_id: Optional[str] = None,
    amount: int = 250
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Records a completed Mobile Money transaction (MTN MoMo or Orange Money),
    extends paid_until by 7 days, and updates the registered device binding.
    """
    config = get_system_config()
    sub_days = int(config.get("subscription_duration_days", 7))
    price = int(config.get("subscription_price_xaf", 250))
    amount = price if amount <= 0 else amount

    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()

    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, paid_until, registered_device_id FROM acadformat_users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return False, "User not found.", {}

    # Calculate new expiry: if currently active, add to existing paid_until; else from now
    base_time = now
    if user["paid_until"]:
        try:
            curr_paid = datetime.datetime.fromisoformat(user["paid_until"])
            if curr_paid > now:
                base_time = curr_paid
        except Exception:
            pass

    new_paid_until = (base_time + datetime.timedelta(days=sub_days)).isoformat()
    tx_ref = f"MOMO-{secrets.token_hex(6).upper()}"

    # Update user record (and bind device if provided)
    if device_id:
        cursor.execute("UPDATE acadformat_users SET paid_until = ?, registered_device_id = ? WHERE id = ?", (new_paid_until, device_id, user_id))
    else:
        cursor.execute("UPDATE acadformat_users SET paid_until = ? WHERE id = ?", (new_paid_until, user_id))

    # Insert payment record
    cursor.execute("""
    INSERT INTO acadformat_payments 
    (user_id, username, amount, currency, operator, phone_number, transaction_ref, status, paid_at, expires_at)
    VALUES (?, ?, ?, 'XAF', ?, ?, ?, 'completed', ?, ?)
    """, (user_id, user["username"], amount, operator, phone_number, tx_ref, now_iso, new_paid_until))

    conn.commit()
    conn.close()

    # Sync payment to Cloudflare D1
    sync_to_cloudflare_d1(
        "INSERT INTO acadformat_payments (user_id, username, amount, currency, operator, phone_number, transaction_ref, status, paid_at, expires_at, device_id) VALUES (?, ?, ?, 'XAF', ?, ?, ?, 'completed', ?, ?, ?)",
        [user_id, user["username"], amount, operator, phone_number, tx_ref, now_iso, new_paid_until, device_id]
    )
    if device_id:
        sync_to_cloudflare_d1("UPDATE acadformat_users SET paid_until = ?, registered_device_id = ? WHERE id = ?", [new_paid_until, device_id, user_id])
    else:
        sync_to_cloudflare_d1("UPDATE acadformat_users SET paid_until = ? WHERE id = ?", [new_paid_until, user_id])

    # Sync payment to Supabase
    if is_supabase_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/acadformat_payments"
            with httpx.Client(timeout=4.0) as client:
                client.post(url, headers=get_supabase_headers(), json={
                    "user_id": user_id,
                    "username": user["username"],
                    "amount": amount,
                    "currency": "XAF",
                    "operator": operator,
                    "phone_number": phone_number,
                    "transaction_ref": tx_ref,
                    "status": "completed",
                    "paid_at": now_iso,
                    "expires_at": new_paid_until
                })
        except Exception as e:
            print(f"[Supabase Payment Sync] Error: {e}")

    return True, "Payment verified! 7 days of full export access unlocked.", {
        "transaction_ref": tx_ref,
        "amount": amount,
        "operator": operator,
        "phone_number": phone_number,
        "paid_until": new_paid_until,
        "valid_days": sub_days
    }


# ---------------------------------------------------------
# Admin & Super Admin Management Functions
# ---------------------------------------------------------
def list_all_users(search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Lists registered users with their device info, trial, and subscription state."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if search:
        s = f"%{search.strip().lower()}%"
        cursor.execute("""
        SELECT id, full_name, username, email, role, registered_device_id, trial_expires_at, paid_until, created_at
        FROM acadformat_users
        WHERE LOWER(full_name) LIKE ? OR LOWER(username) LIKE ? OR LOWER(email) LIKE ?
        ORDER BY id DESC LIMIT ?
        """, (s, s, s, limit))
    else:
        cursor.execute("""
        SELECT id, full_name, username, email, role, registered_device_id, trial_expires_at, paid_until, created_at
        FROM acadformat_users
        ORDER BY id DESC LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    now = datetime.datetime.now(datetime.timezone.utc)
    res = []
    for r in rows:
        d = dict(r)
        trial_exp = datetime.datetime.fromisoformat(d["trial_expires_at"])
        d["trial_active"] = now < trial_exp
        d["paid_active"] = False
        if d.get("paid_until"):
            try:
                paid_exp = datetime.datetime.fromisoformat(d["paid_until"])
                d["paid_active"] = now < paid_exp
            except Exception:
                pass
        res.append(d)
    return res


def extend_user_subscription(user_id: int, extra_days: int = 7) -> Tuple[bool, str]:
    """Admin tool: Manually grants extra subscription days to a user."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, paid_until FROM acadformat_users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return False, "User not found."

    now = datetime.datetime.now(datetime.timezone.utc)
    base_time = now
    if user["paid_until"]:
        try:
            curr = datetime.datetime.fromisoformat(user["paid_until"])
            if curr > now:
                base_time = curr
        except Exception:
            pass

    new_expiry = (base_time + datetime.timedelta(days=extra_days)).isoformat()
    cursor.execute("UPDATE acadformat_users SET paid_until = ? WHERE id = ?", (new_expiry, user_id))
    conn.commit()
    conn.close()
    return True, f"User extended successfully until {new_expiry}."


def update_user_role(target_user_id: int, new_role: str) -> Tuple[bool, str]:
    """Super Admin tool: Promotes or demotes user role ('user', 'admin', 'super_admin')."""
    if new_role not in ["user", "admin", "super_admin"]:
        return False, "Invalid role. Must be 'user', 'admin', or 'super_admin'."

    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE acadformat_users SET role = ? WHERE id = ?", (new_role, target_user_id))
    conn.commit()
    conn.close()
    return True, f"User role updated to '{new_role}'."


def get_financial_analytics() -> Dict[str, Any]:
    """Super Admin tool: Aggregates revenue, MoMo/Orange breakdown, and recent transactions."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total_count, COALESCE(SUM(amount), 0) as total_revenue FROM acadformat_payments WHERE status = 'completed'")
    summary = dict(cursor.fetchone())

    # Breakdown by operator
    cursor.execute("""
    SELECT operator, COUNT(*) as count, COALESCE(SUM(amount), 0) as revenue
    FROM acadformat_payments
    WHERE status = 'completed'
    GROUP BY operator
    """)
    by_operator = [dict(r) for r in cursor.fetchall()]

    # Recent payments
    cursor.execute("""
    SELECT id, username, amount, currency, operator, phone_number, transaction_ref, paid_at, expires_at
    FROM acadformat_payments
    ORDER BY id DESC LIMIT 20
    """)
    recent = [dict(r) for r in cursor.fetchall()]

    # User counts
    cursor.execute("SELECT COUNT(*) as user_count FROM acadformat_users")
    user_count = cursor.fetchone()["user_count"]

    conn.close()

    return {
        "total_revenue_xaf": summary["total_revenue"],
        "total_transactions": summary["total_count"],
        "total_users": user_count,
        "operator_breakdown": by_operator,
        "recent_payments": recent
    }


def get_system_config() -> Dict[str, str]:
    """Returns platform configuration (trial duration, subscription fee, validity)."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM acadformat_system_config")
    rows = cursor.fetchall()
    conn.close()
    configs = {k: v for k, v in rows}
    # Defaults fallback
    configs.setdefault("trial_duration_hours", "72")
    configs.setdefault("subscription_price_xaf", "250")
    configs.setdefault("subscription_duration_days", "7")
    return configs


def update_system_config(trial_hours: int, price_xaf: int, validity_days: int) -> bool:
    """Super Admin tool: Updates platform settings."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO acadformat_system_config (key, value) VALUES ('trial_duration_hours', ?)", (str(trial_hours),))
    cursor.execute("INSERT OR REPLACE INTO acadformat_system_config (key, value) VALUES ('subscription_price_xaf', ?)", (str(price_xaf),))
    cursor.execute("INSERT OR REPLACE INTO acadformat_system_config (key, value) VALUES ('subscription_duration_days', ?)", (str(validity_days),))
    conn.commit()
    conn.close()
    return True


# ---------------------------------------------------------
# Document Audit & Reformat Persistence
# ---------------------------------------------------------
def save_document_record(
    token: str,
    filename: str,
    doc_type: str,
    school_type: str,
    compliance_score: int,
    metadata: Dict[str, Any],
    issues_count: int = 0
) -> bool:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = {
        "token": token,
        "filename": filename,
        "doc_type": doc_type,
        "school_type": school_type,
        "compliance_score": compliance_score,
        "title": metadata.get("title", ""),
        "author": metadata.get("author", ""),
        "reg_number": metadata.get("reg_number", ""),
        "department": metadata.get("department", ""),
        "status": "audited",
        "created_at": now_iso
    }

    if is_supabase_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/acadformat_documents"
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(url, headers=get_supabase_headers(), json=record)
                if resp.status_code in [200, 201]:
                    return True
        except Exception as e:
            print(f"[Supabase Doc Write Failed] {e}")

    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO acadformat_documents 
        (token, filename, doc_type, school_type, compliance_score, title, author, reg_number, department, status, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            token, filename, doc_type, school_type, compliance_score,
            record["title"], record["author"], record["reg_number"], record["department"],
            record["status"], json.dumps(metadata), now_iso
        ))
        conn.commit()
        conn.close()

        # Sync document to Cloudflare D1
        sync_to_cloudflare_d1(
            "INSERT OR REPLACE INTO acadformat_documents (token, filename, doc_type, school_type, compliance_score, title, author, reg_number, department, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [token, filename, doc_type, school_type, compliance_score, record["title"], record["author"], record["reg_number"], record["department"], record["status"], json.dumps(metadata), now_iso]
        )
        return True
    except Exception as e:
        print(f"[Local DB Error] {e}")
        return False


def save_reformat_record(token: str, docx_path: str, pdf_path: str, page_count: int) -> bool:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if is_supabase_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/acadformat_reformats"
            data = {
                "token": token,
                "docx_path": docx_path,
                "pdf_path": pdf_path,
                "page_count": page_count,
                "reformatted_at": now_iso
            }
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(url, headers=get_supabase_headers(), json=data)
                if resp.status_code in [200, 201]:
                    return True
        except Exception as e:
            print(f"[Supabase Reformat Write Failed] {e}")

    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO acadformat_reformats (token, docx_path, pdf_path, page_count, reformatted_at)
        VALUES (?, ?, ?, ?, ?)
        """, (token, docx_path, pdf_path, page_count, now_iso))
        cursor.execute("UPDATE acadformat_documents SET page_count = ?, status = 'reformatted' WHERE token = ?", (page_count, token))
        conn.commit()
        conn.close()

        # Sync reformat to Cloudflare D1
        sync_to_cloudflare_d1(
            "INSERT OR REPLACE INTO acadformat_reformats (token, docx_path, pdf_path, page_count, reformatted_at) VALUES (?, ?, ?, ?, ?)",
            [token, docx_path, pdf_path, page_count, now_iso]
        )
        sync_to_cloudflare_d1("UPDATE acadformat_documents SET page_count = ?, status = 'reformatted' WHERE token = ?", [page_count, token])
        return True
    except Exception as e:
        print(f"[Local DB Reformat Error] {e}")
        return False


def get_document_record(token: str) -> Optional[Dict[str, Any]]:
    if is_supabase_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/acadformat_documents?token=eq.{token}&select=*"
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(url, headers=get_supabase_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        return data[0]
        except Exception:
            pass

    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM acadformat_documents WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception:
        pass
    return None


def list_recent_documents(limit: int = 25) -> List[Dict[str, Any]]:
    if is_supabase_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/acadformat_documents?order=created_at.desc&limit={limit}&select=*"
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(url, headers=get_supabase_headers())
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass

    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM acadformat_documents ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []
