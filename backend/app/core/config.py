"""Configuración centralizada del backend de SIMTELE-RISK."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _resolve_postgres_url() -> str:
    """Obtiene y normaliza la URL de PostgreSQL (compatible con Docker, Neon y Vercel)."""
    raw = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or "postgresql+psycopg2://postgres:simtele_pass@localhost:5433/simtele_risk"
    )
    if raw.startswith("postgres://"):
        raw = "postgresql+psycopg2://" + raw[len("postgres://") :]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+psycopg2://" + raw[len("postgresql://") :]
    return raw


@dataclass(frozen=True)
class Settings:
    """Parámetros de configuración de la aplicación y base de datos."""

    app_name: str = "SIMTELE-RISK API"
    app_version: str = "2.0.0-semana2"
    postgres_url: str = _resolve_postgres_url()
    sqlite_fallback_path: Path = Path(
        os.getenv("SQLITE_DB_PATH", str(Path(__file__).resolve().parents[2] / "simtele_risk.db"))
    )
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    )


settings = Settings()
