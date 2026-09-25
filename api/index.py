import sys
import os
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Add project root directory to sys.path so 'backend' is directly importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Top-level 'app' instance initialized statically for Vercel CLI scanner detection
app = FastAPI(title="AcadFormat API Bridge")

try:
    from backend.main import app as backend_app
    app = backend_app
except Exception as e:
    _err_trace = traceback.format_exc()
    print(f"[AcadFormat Vercel Init Error] {e}\n{_err_trace}", file=sys.stderr)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def fallback_diagnostic_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Backend initialization failed on Vercel runtime",
                "error": str(e),
                "traceback": _err_trace.split("\n"),
                "python": sys.version,
                "sys_path": sys.path
            }
        )

