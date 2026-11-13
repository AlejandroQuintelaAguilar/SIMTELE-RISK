"""Punto de entrada de la aplicación FastAPI de SIMTELE-RISK."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.database import init_db_and_seed


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Inicializa el esquema y datos semilla al arrancar la API."""
    init_db_and_seed()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Plataforma de Simulación Numérica y Análisis de Riesgos (Mi Teleférico).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
