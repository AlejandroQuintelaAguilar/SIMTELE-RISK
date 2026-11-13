"""Conexión a PostgreSQL con respaldo automático en SQLite y carga semilla."""

from __future__ import annotations

from collections.abc import Generator
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.db_models import Base, CasoEstudio, Escenario

logger = logging.getLogger(__name__)

_SEED_CASOS: list[dict[str, object]] = [
    {
        "id": 1,
        "codigo": "MOD1_DETENCION",
        "nombre": "Detención de Emergencia de Cabinas",
        "descripcion": "Modelado cinemático y dinámico de frenado de emergencia mediante EDO, integración de velocidad y búsqueda de instante de detención.",
        "modelo_version": "v1.0",
    },
    {
        "id": 2,
        "codigo": "MOD2_DETERIORO",
        "nombre": "Deterioro Mecánico y Mantenimiento",
        "descripcion": "Calibración de modelo polinómico de desgaste mediante sistemas lineales SPD y predicción de tiempo a umbral crítico.",
        "modelo_version": "v1.0",
    },
    {
        "id": 3,
        "codigo": "MOD3_OSCILACIONES",
        "nombre": "Oscilaciones por Viento",
        "descripcion": "Simulación de respuesta dinámica amortiguada ante ráfagas de viento e integración de energía acumulada.",
        "modelo_version": "v1.0",
    },
    {
        "id": 4,
        "codigo": "MOD4_SENSORES",
        "nombre": "Reconstrucción de Señales de Sensores",
        "descripcion": "Interpolación de telemetría con datos ocultados, evaluación de ruido y detección de cruce de umbrales.",
        "modelo_version": "v1.0",
    },
]

_SEED_ESCENARIOS: list[dict[str, object]] = [
    {"caso_id": 1, "tipo": "NORMAL", "nombre_descriptivo": "Frenado nominal en tramo recto", "parametros_json": {"v0": 6.0, "x0": 0.0, "a0": 1.2, "kd": 0.0, "h": 0.05, "t_max": 10.0, "tol": 1e-8}, "fuente_datos": "Parámetros sintéticos nominales de cabina urbana"},
    {"caso_id": 1, "tipo": "ESTRES", "nombre_descriptivo": "Carga máxima, pendiente descendente y paso grueso", "parametros_json": {"v0": 8.5, "x0": 0.0, "a0": 0.75, "kd": 0.02, "h": 0.4, "t_max": 15.0, "tol": 1e-8}, "fuente_datos": "Simulación sintética de demanda pico con paso de integración exigente"},
    {"caso_id": 1, "tipo": "MAL_CONDICIONADO", "nombre_descriptivo": "Frenado asintótico con raíz múltiple (derivada nula)", "parametros_json": {"v0": 6.0, "x0": 0.0, "modelo": "asintotico_tangencial", "t_det_objetivo": 5.0, "h": 0.05, "tol": 1e-10}, "fuente_datos": "Subexperimento numérico con v(t_det)=0 y dv/dt(t_det)=0"},
    {"caso_id": 2, "tipo": "NORMAL", "nombre_descriptivo": "Calibración SPD bien condicionada y desgaste estándar", "parametros_json": {"dimension_n": 4, "condicion_objetivo": "baja", "D0": 0.12, "alpha": 0.015, "beta": 0.0008, "D_umbral": 0.80, "tol": 1e-8, "max_iter": 500}, "fuente_datos": "Serie sintética de inspección preventiva trimestral"},
    {"caso_id": 2, "tipo": "ESTRES", "nombre_descriptivo": "Sistema ampliado (n=12) y mantenimiento retrasado", "parametros_json": {"dimension_n": 12, "condicion_objetivo": "moderada", "D0": 0.25, "alpha": 0.028, "beta": 0.0019, "D_umbral": 0.85, "tol": 1e-11, "max_iter": 2000}, "fuente_datos": "Escenario sintético de operación continua sin ventana de mantenimiento"},
    {"caso_id": 2, "tipo": "MAL_CONDICIONADO", "nombre_descriptivo": "Matriz SPD casi singular (tipo Hilbert perturbada)", "parametros_json": {"dimension_n": 6, "condicion_objetivo": "alta_hilbert", "perturbacion_b": 1e-4, "D0": 0.12, "alpha": 0.015, "beta": 0.0008, "D_umbral": 0.80, "tol": 1e-8, "max_iter": 5000}, "fuente_datos": "Subexperimento numérico con número de condición kappa(A) > 10^5"},
    {"caso_id": 3, "tipo": "NORMAL", "nombre_descriptivo": "Vibración subamortiguada con brisa moderada", "parametros_json": {"m": 1200.0, "c": 480.0, "k": 3000.0, "F0": 150.0, "omega": 0.8, "x0": 0.05, "v0": 0.0, "h": 0.02, "T": 20.0}, "fuente_datos": "Modelo masa-resorte-amortiguador sintético equivalente"},
    {"caso_id": 3, "tipo": "ESTRES", "nombre_descriptivo": "Ráfagas cercanas a resonancia en ventana prolongada", "parametros_json": {"m": 1200.0, "c": 180.0, "k": 3000.0, "F0": 850.0, "omega": 1.55, "x0": 0.10, "v0": 0.0, "h": 0.05, "T": 120.0}, "fuente_datos": "Forzamiento armónico sintético cerca de frecuencia natural"},
    {"caso_id": 3, "tipo": "MAL_CONDICIONADO", "nombre_descriptivo": "Sistema rígido (stiff) con alta rigidez y paso crítico", "parametros_json": {"m": 1200.0, "c": 2400.0, "k": 450000.0, "F0": 200.0, "omega": 2.0, "x0": 0.05, "v0": 0.0, "h": 0.12, "T": 10.0}, "fuente_datos": "Subexperimento numérico para demostrar límite de estabilidad explícita RK2/RK4"},
    {"caso_id": 4, "tipo": "NORMAL", "nombre_descriptivo": "Telemetría limpia con 8 nodos equiespaciados", "parametros_json": {"funcion": "sin_t", "a": 0.0, "b": 6.283185307179586, "n_nodos": 8, "indices_ocultos": [2, 5], "ruido_sigma": 0.0, "umbral_alerta": 0.75}, "fuente_datos": "Señal sintética analítica y(t) = sin(t)"},
    {"caso_id": 4, "tipo": "ESTRES", "nombre_descriptivo": "Señal amortiguada con ruido gaussiano y pérdida de paquetes", "parametros_json": {"funcion": "exp_cos", "a": 0.0, "b": 5.0, "n_nodos": 12, "indices_ocultos": [3, 4, 7, 8], "ruido_sigma": 0.04, "umbral_alerta": 0.50}, "fuente_datos": "Señal sintética y(t) = exp(-t)*cos(2t) contaminada con ruido normal"},
    {"caso_id": 4, "tipo": "MAL_CONDICIONADO", "nombre_descriptivo": "Fenómeno de Runge con nodos equiespaciados de alto grado", "parametros_json": {"funcion": "runge", "a": -5.0, "b": 5.0, "n_nodos": 15, "indices_ocultos": [1, 13], "ruido_sigma": 0.0, "umbral_alerta": 0.50}, "fuente_datos": "Subexperimento numérico con f(t) = 1 / (1 + 25*t^2) en [-5, 5]"},
]


def _create_engine_with_fallback() -> tuple[Engine, str]:
    """Intenta conectar a PostgreSQL y usa SQLite local si PostgreSQL no responde."""
    try:
        pg_engine = create_engine(
            settings.postgres_url, pool_pre_ping=True, connect_args={"connect_timeout": 2}
        )
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return pg_engine, "postgresql"
    except Exception as exc:
        logger.warning("PostgreSQL no disponible (%s). Usando respaldo SQLite local.", exc)
        sqlite_url = f"sqlite:///{settings.sqlite_fallback_path.as_posix()}"
        sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        return sqlite_engine, "sqlite"


engine, active_db_backend = _create_engine_with_fallback()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db_and_seed() -> None:
    """Crea tablas si no existen y siembra los 4 casos y 12 escenarios si está vacío."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = db.query(CasoEstudio).count()
        if count == 0:
            for caso_data in _SEED_CASOS:
                db.add(CasoEstudio(**caso_data))
            db.flush()
            for esc_data in _SEED_ESCENARIOS:
                db.add(Escenario(**esc_data))
            db.commit()


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI que provee una sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
