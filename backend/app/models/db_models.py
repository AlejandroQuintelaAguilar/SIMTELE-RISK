"""Modelos ORM (SQLAlchemy) alineados con database/schema.sql."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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
    simulaciones: Mapped[list[Simulacion]] = relationship(
        "Simulacion", back_populates="escenario", cascade="all, delete-orphan"
    )


class Simulacion(Base):
    """Registra cada corrida lanzada sobre un escenario y sus parámetros efectivos."""

    __tablename__ = "simulacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    escenario_id: Mapped[int] = mapped_column(ForeignKey("escenario.id", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    usuario_equipo: Mapped[str] = mapped_column(String(100), nullable=False, default="Equipo_SIMTELE")
    estado: Mapped[str] = mapped_column(String(25), nullable=False)
    parametros_override_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notas_usuario: Mapped[str | None] = mapped_column(Text, nullable=True)

    escenario: Mapped[Escenario] = relationship("Escenario", back_populates="simulaciones")
    ejecuciones: Mapped[list[EjecucionMetodo]] = relationship(
        "EjecucionMetodo", back_populates="simulacion", cascade="all, delete-orphan"
    )


class EjecucionMetodo(Base):
    """Detalla cada algoritmo numérico ejecutado dentro de una simulación."""

    __tablename__ = "ejecucion_metodo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulacion_id: Mapped[int] = mapped_column(ForeignKey("simulacion.id", ondelete="CASCADE"), nullable=False)
    familia_metodo: Mapped[str] = mapped_column(String(30), nullable=False)
    metodo: Mapped[str] = mapped_column(String(60), nullable=False)
    tolerancia: Mapped[float | None] = mapped_column(Float, nullable=True)
    paso: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_iter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iteraciones_realizadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    convergio: Mapped[bool] = mapped_column(Boolean, nullable=False)
    motivo_parada: Mapped[str | None] = mapped_column(String(150), nullable=True)
    tiempo_ms: Mapped[float] = mapped_column(Float, nullable=False)

    simulacion: Mapped[Simulacion] = relationship("Simulacion", back_populates="ejecuciones")
    iteraciones: Mapped[list[IteracionResultado]] = relationship(
        "IteracionResultado", back_populates="ejecucion", cascade="all, delete-orphan"
    )
    resumen: Mapped[ResultadoResumen | None] = relationship(
        "ResultadoResumen", back_populates="ejecucion", uselist=False, cascade="all, delete-orphan"
    )


class IteracionResultado(Base):
    """Traza paso a paso (iteración, refinamiento o paso temporal) de una ejecución."""

    __tablename__ = "iteracion_resultado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ejecucion_id: Mapped[int] = mapped_column(ForeignKey("ejecucion_metodo.id", ondelete="CASCADE"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    aproximacion_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    residual: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_abs: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_rel: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_porcentual: Mapped[float | None] = mapped_column(Float, nullable=True)

    ejecucion: Mapped[EjecucionMetodo] = relationship("EjecucionMetodo", back_populates="iteraciones")


class ResultadoResumen(Base):
    """Consolidado final, referencia, errores globales y dobles conclusiones."""

    __tablename__ = "resultado_resumen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ejecucion_id: Mapped[int] = mapped_column(
        ForeignKey("ejecucion_metodo.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    referencia: Mapped[float | None] = mapped_column(Float, nullable=True)
    tipo_referencia: Mapped[str] = mapped_column(String(40), nullable=False)
    valor_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metrica_error_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    interpretacion_numerica: Mapped[str] = mapped_column(Text, nullable=False)
    interpretacion_problema: Mapped[str] = mapped_column(Text, nullable=False)

    ejecucion: Mapped[EjecucionMetodo] = relationship("EjecucionMetodo", back_populates="resumen")
