"""Punto de entrada ASGI para Vercel Serverless Functions."""

from __future__ import annotations

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import init_db_and_seed
from app.main import app

init_db_and_seed()
