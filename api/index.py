import sys
import os

# Insert repository root directory into sys.path so 'backend' module is importable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.main import app

# Vercel Serverless Function entry point
app = app
