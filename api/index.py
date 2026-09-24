import sys
import os

# Insert repository root directory and current working directory into sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
curr_dir = os.getcwd()
for p in [root_dir, curr_dir]:
    if p and p not in sys.path:
        sys.path.insert(0, p)

from backend.main import app

# Vercel Serverless Function entry point
app = app
