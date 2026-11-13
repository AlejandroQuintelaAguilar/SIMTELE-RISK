"""Configuración centralizada del backend de SIMTELE-RISK."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Parámetros de configuración de la aplicación y base de datos."""

    app_name: str = "SIMTELE-RISK API"
    app_version: str = "1.0.0-semana1"
    postgres_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:simtele_pass@localhost:5433/simtele_risk",
    )
    sqlite_fallback_path: Path = Path(
        os.getenv("SQLITE_DB_PATH", str(Path(__file__).resolve().parents[2] / "simtele_risk.db"))
    )
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    )


settings = Settings()
