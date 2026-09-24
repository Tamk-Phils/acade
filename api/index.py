import sys
import os

# Search for the directory containing 'backend' across common deployment layouts
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

for p in [parent_dir, cwd]:
    if p and p not in sys.path:
        sys.path.insert(0, p)

# Top-level FastAPI application export recognized by Vercel CLI
from backend.main import app
