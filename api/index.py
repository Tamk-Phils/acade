import sys
import os
import json
import traceback

# Search for the directory containing 'backend' across all common deployment layouts
file_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(file_dir)
cwd = os.getcwd()

search_candidates = [
    parent_dir,
    cwd,
    file_dir,
    "/var/task",
    "/var/task/api",
    os.path.join(cwd, ".."),
    os.path.join(file_dir, "..")
]

for candidate in search_candidates:
    abs_cand = os.path.abspath(candidate)
    if os.path.isdir(os.path.join(abs_cand, "backend")) and abs_cand not in sys.path:
        sys.path.insert(0, abs_cand)

# Also ensure root and cwd are always on path
for p in [parent_dir, cwd]:
    if p and p not in sys.path:
        sys.path.insert(0, p)

# Attempt to load main FastAPI application
main_app = None
init_error = None
init_traceback = None

try:
    from backend.main import app as main_app
except Exception as e:
    init_error = str(e)
    init_traceback = traceback.format_exc()
    print(f"[FATAL Vercel Init Error] {init_error}\n{init_traceback}", file=sys.stderr)

if main_app is not None:
    app = main_app
else:
    # Diagnostic fallback ASGI application to reveal exact error if import fails
    async def app(scope, receive, send):
        if scope["type"] == "http":
            debug_info = {
                "status": "error",
                "message": f"Backend initialization failed on Vercel: {init_error}",
                "traceback": init_traceback,
                "python_version": sys.version,
                "cwd": os.getcwd(),
                "file": __file__,
                "sys_path": sys.path,
                "cwd_files": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else [],
                "parent_files": os.listdir(parent_dir) if os.path.exists(parent_dir) else []
            }
            body = json.dumps(debug_info, indent=2).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("utf-8")),
                    (b"access-control-allow-origin", b"*"),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })

