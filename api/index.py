"""
Vercel entrypoint exposing the FastAPI `app`.

Vercel looks for an app-level ASGI variable named `app` in files like
`api/index.py`. We import the application from `backend.main`.
"""

import os
import sys

# Ensure project root is in sys.path when running in Vercel's Python runtime
_this_dir = os.path.dirname(__file__)
_project_root = os.path.dirname(_this_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.main import app  # FastAPI instance defined in backend/main.py


