"""Esquemas Pydantic de entrada/salida para la API REST de SIMTELE-RISK."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EscenarioOut(BaseModel):
    """Esquema de salida para un escenario predefinido."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    nombre_descriptivo: str
    parametros_json: dict[str, Any]
    fuente_datos: str
    es_predefinido: bool


class CasoEstudioOut(BaseModel):
    """Esquema de salida para un módulo de estudio y sus escenarios."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: str
    modelo_version: str
    escenarios: list[EscenarioOut] = []


class HealthOut(BaseModel):
    """Estado de salud del servicio."""

    status: str
    version: str
    database_backend: str


class Modulo2ExecuteRequest(BaseModel):
    """Parámetros de ejecución para sistemas lineales del Módulo 2."""

    escenario: Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"] = "NORMAL"
    tol: float | None = Field(default=None, gt=0.0, le=1.0)
    max_iter: int | None = Field(default=None, ge=1, le=50000)


class IterationOut(BaseModel):
    """Registro de una iteración o paso de resolución."""

    numero: int
    x: list[float]
    residual: float
    residual_rel: float
    step_diff: float | None = None
    error_abs: float | None = None
    error_rel: float | None = None
    error_pct: float | None = None


class MethodResultOut(BaseModel):
    """Resultado consolidado por método numérico."""

    metodo: str
    familia: str
    convergio: bool
    iteraciones_realizadas: int
    motivo_parada: str
    tiempo_ms: float
    residual_final: float
    residual_rel_final: float
    error_abs: float | None
    error_rel: float | None
    error_pct: float | None
    x_aprox: list[float]
    diagnostics: dict[str, Any]
    historial: list[IterationOut]


class SensitivityOut(BaseModel):
    """Métricas de sensibilidad ante perturbación controlada delta_b."""

    relative_perturbation_b: float
    relative_change_x: float
    amplification_factor: float
    condition_number_2: float
    delta_b_norm: float
    delta_x_norm: float


class Modulo2ExecuteResponse(BaseModel):
    """Respuesta completa del endpoint POST /api/modulo2/sistemas-lineales/ejecutar."""

    escenario: Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]
    nombre_descriptivo: str
    dimension_n: int
    tol: float
    max_iter: int
    kappa_2: float
    x_referencia: list[float]
    sensibilidad: SensitivityOut
    resultados_metodos: list[MethodResultOut]
    interpretacion_numerica: str
    interpretacion_problema: str
