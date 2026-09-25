import sys
import os
import asyncio
import traceback

# -----------------------------------------------------------------------------
# Patch Vercel vc_init.py Python 3.12 compatibility bug:
# Vercel's ASGI runtime internally invokes asyncio primitives with `loop=loop`,
# which was deprecated in Python 3.8 and removed in Python 3.10+.
# This monkeypatch allows Vercel's vc_init.py to instantiate queues and locks safely.
# -----------------------------------------------------------------------------
for _cls in (asyncio.Queue, asyncio.Event, asyncio.Lock, asyncio.Semaphore, asyncio.Condition):
    _orig_init = _cls.__init__
    def _create_compat_init(orig_fn):
        def _compat_init(self, *args, **kwargs):
            kwargs.pop("loop", None)
            return orig_fn(self, *args, **kwargs)
        return _compat_init
    _cls.__init__ = _create_compat_init(_orig_init)

# Add project root directory to sys.path so 'backend' is directly importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Top-level 'app' instance initialized statically for Vercel CLI scanner detection
app = FastAPI(title="AcadFormat API Bridge", debug=True)

try:
    from backend.main import app as backend_app
    app = backend_app

    @app.api_route("/__debug_routes__", methods=["GET"])
    async def list_routes():
        return {
            "routes": [getattr(r, "path", str(r)) for r in app.routes]
        }

    @app.api_route("/{unmatched_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def debug_unmatched(unmatched_path: str, request: Request):
        return {
            "debug": "unmatched_route",
            "unmatched_path": unmatched_path,
            "url_path": request.url.path,
            "scope_path": request.scope.get("path"),
            "scope_root_path": request.scope.get("root_path"),
            "routes": [getattr(r, "path", str(r)) for r in app.routes if getattr(r, "path", None)]
        }
except Exception as e:
    _err_msg = str(e)
    _err_trace = traceback.format_exc()
    print(f"[AcadFormat Vercel Init Error] {_err_msg}\n{_err_trace}", file=sys.stderr)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def fallback_diagnostic_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Backend initialization failed on Vercel runtime",
                "error": _err_msg,
                "traceback": _err_trace.split("\n"),
                "python": sys.version,
                "sys_path": sys.path
            }
        )


