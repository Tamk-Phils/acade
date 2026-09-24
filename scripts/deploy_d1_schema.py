"""
Cloudflare D1 Schema Provisioning Script.
Executes all SQL statements from cloudflare_d1_schema.sql directly on the remote Cloudflare D1 database.
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "a7c6482a2abf7ecbaac3a466f83822cb").strip()
DATABASE_ID = os.getenv("CLOUDFLARE_DATABASE_ID", "1ce80e78-f367-494d-aa47-5c87a8e02613").strip()
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()

if not API_TOKEN or not ACCOUNT_ID or not DATABASE_ID:
    print("Error: Missing Cloudflare credentials in .env")
    sys.exit(1)

URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def execute_query(sql: str, params: list = None):
    payload = {
        "sql": sql,
        "params": params or []
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(URL, headers=HEADERS, json=payload)
        return resp.status_code, resp.json()

def main():
    print(f"Connecting to Cloudflare D1 Database: {DATABASE_ID} (Account: {ACCOUNT_ID})...")
    
    # 1. Test connection with simple SELECT 1
    code, res = execute_query("SELECT 1 as connected")
    if code != 200 or not res.get("success"):
        print(f"Connection test failed (HTTP {code}): {res}")
        sys.exit(1)
    print("Connection successful! D1 database is active and accepting queries.\n")

    # 2. Read schema file
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cloudflare_d1_schema.sql")
    with open(schema_path, "r") as f:
        content = f.read()

    # Split into clean individual statements
    statements = [stmt.strip() for stmt in content.split(";") if stmt.strip()]

    print(f"Provisioning {len(statements)} SQL statements on Cloudflare D1:")
    for idx, stmt in enumerate(statements, 1):
        first_line = stmt.split("\n")[0][:60]
        code, res = execute_query(stmt)
        if code == 200 and res.get("success"):
            print(f"  [{idx}/{len(statements)}] OK: {first_line}...")
        else:
            print(f"  [{idx}/{len(statements)}] FAILED: {first_line}")
            print(f"    Errors: {res.get('errors')}")

    # 3. Verify tables
    print("\nVerifying tables on Cloudflare D1:")
    code, res = execute_query("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
    if code == 200 and res.get("success"):
        tables = [row["name"] for row in res["result"][0]["results"]]
        print("  Existing tables in D1:", tables)

    # 4. Verify seeded users
    code, res = execute_query("SELECT id, username, role FROM acadformat_users")
    if code == 200 and res.get("success"):
        users = res["result"][0]["results"]
        print("  Seeded users in D1:", users)

    print("\n--- Cloudflare D1 Database Provisioning Complete! ---")

if __name__ == "__main__":
    main()

