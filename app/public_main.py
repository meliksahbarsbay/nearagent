"""Entry point for the public demo: python -m app.public_main

It runs in one process on purpose, because the limits are counted in memory.
"""
import os

import uvicorn

from app import main
from app.demo_guard import protect

DEFAULT_PORT = 8000

app = protect(main)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT") or DEFAULT_PORT))
