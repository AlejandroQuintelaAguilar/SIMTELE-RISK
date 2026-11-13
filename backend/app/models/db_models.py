"""Modelos ORM (SQLAlchemy) alineados con database/schema.sql."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Clase base declarativa de SQLAlchemy."""


class CasoEstudio(Base):
    """Representa uno de los 4 módulos obligatorios de estudio."""

    __tablename__ = "caso_estudio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    modelo_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0")

    escenarios: Mapped[list[Escenario]] = relationship(
        "Escenario", back_populates="caso", cascade="all, delete-orphan"
    )


class Escenario(Base):
    """Configuración reproducible NORMAL, ESTRES o MAL_CONDICIONADO por módulo."""

    __tablename__ = "escenario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("caso_estudio.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(25), nullable=False)
    nombre_descriptivo: Mapped[str] = mapped_column(String(150), nullable=False)
    parametros_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    fuente_datos: Mapped[str] = mapped_column(String(200), nullable=False)
    es_predefinido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    caso: Mapped[CasoEstudio] = relationship("CasoEstudio", back_populates="escenarios")
