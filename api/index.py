"""
Vercel entrypoint exposing the FastAPI `app`.

Vercel looks for an app-level ASGI variable named `app` in files like
`api/index.py`. We import the application from `backend.main`.
"""

from backend.main import app  # FastAPI instance defined in backend/main.py


