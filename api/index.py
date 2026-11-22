"""Punto de entrada ASGI para Vercel Serverless Functions."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from urllib.parse import parse_qsl, urlencode

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import init_db_and_seed
from app.main import app as fastapi_app

init_db_and_seed()


class _VercelRewritePathMiddleware:
    """Restaura el path original /api/... cuando Vercel reescribe hacia /api/index.py."""

    def __init__(self, asgi_app: Any) -> None:
        self.asgi_app = asgi_app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            raw_qs = scope.get("query_string", b"").decode("latin-1")
            pairs = parse_qsl(raw_qs, keep_blank_values=True)
            target_path: str | None = None
            filtered: list[tuple[str, str]] = []
            for k, v in pairs:
                if k == "__path" and target_path is None:
                    target_path = v
                else:
                    filtered.append((k, v))
            if target_path:
                scope = dict(scope)
                scope["path"] = target_path
                scope["raw_path"] = target_path.encode("utf-8")
                scope["query_string"] = urlencode(filtered).encode("latin-1")
        await self.asgi_app(scope, receive, send)


app = _VercelRewritePathMiddleware(fastapi_app)
