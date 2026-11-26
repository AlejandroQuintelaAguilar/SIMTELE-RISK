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
    """Parámetros de ejecución para sistemas lineales del Módulo 2 (Semana 1)."""

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
    """Resultado consolidado por método numérico (Semana 1)."""

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


class ModuleRunRequest(BaseModel):
    """Solicitud unificada de ejecución y persistencia para cualquiera de los 4 módulos."""

    escenario: Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"] = "NORMAL"
    parametros_override: dict[str, Any] | None = None
    usuario_equipo: str = Field(default="Equipo_SIMTELE", min_length=1, max_length=100)
    notas_usuario: str | None = None


class ChartSeriesOut(BaseModel):
    """Serie de datos para renderizado gráfico en el frontend."""

    name: str
    x: list[float]
    y: list[float]
    mode: Literal["line", "markers"] = "line"


class ChartPayloadOut(BaseModel):
    """Definición de un gráfico comparativo."""

    id: str
    titulo: str
    x_label: str
    y_label: str
    y_scale: Literal["linear", "log"] = "linear"
    series: list[ChartSeriesOut]


class UnifiedMethodOut(BaseModel):
    """Resultado unificado por método para cualquiera de los 4 módulos."""

    familia: str
    metodo: str
    convergio: bool
    iteraciones_realizadas: int
    tiempo_ms: float
    valor_principal: float | None = None
    etiqueta_valor: str = ""
    residual: float | None = None
    error_abs: float | None = None
    error_rel: float | None = None
    error_pct: float | None = None
    motivo_parada: str
    detalle_tabla: list[dict[str, Any]] = []


class UnifiedModuleResponse(BaseModel):
    """Respuesta unificada de ejecución/recuperación para los 4 módulos."""

    simulacion_id: int | None = None
    fecha: str | None = None
    estado: str | None = None
    usuario_equipo: str | None = None
    caso_codigo: str
    escenario: Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]
    nombre_descriptivo: str
    parametros_usados: dict[str, Any]
    referencia: dict[str, Any]
    metodos: list[UnifiedMethodOut]
    graficos: list[ChartPayloadOut]
    interpretacion_numerica: str
    interpretacion_problema: str


class SimulacionListItemOut(BaseModel):
    """Resumen de una simulación guardada en el historial."""

    simulacion_id: int
    fecha: str
    usuario_equipo: str
    estado: str
    caso_codigo: str
    caso_nombre: str
    escenario: str
    nombre_descriptivo: str
    parametros_usados: dict[str, Any]
    total_metodos: int
    notas_usuario: str | None = None


class RerunComparisonMethodOut(BaseModel):
    """Comparación numérica por método al relanzar una simulación."""

    metodo: str
    valor_original: float | None
    valor_relanzado: float | None
    diferencia_abs: float
    coincide_en_tolerancia: bool


class RerunResponseOut(BaseModel):
    """Resultado de verificación al relanzar una simulación histórica."""

    simulacion_original_id: int
    simulacion_nueva: UnifiedModuleResponse
    diferencia_maxima: float
    coincidencia_exacta: bool
    comparacion_metodos: list[RerunComparisonMethodOut]


class GlobalComparisonRowOut(BaseModel):
    """Fila de la matriz comparativa global 4x3."""

    modulo_index: int
    caso_codigo: str
    modulo_nombre: str
    escenario: Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]
    nombre_descriptivo: str
    total_metodos: int
    metodos_convergentes: int
    metodos_advertencia: int
    mejor_metodo: str
    mejor_error_abs: float | None = None
    mejor_error_rel: float | None = None
    alerta_o_mayor_error: str
    tiempo_total_ms: float
    metrica_clave: str
    interpretacion_numerica: str
    interpretacion_problema: str


class GlobalComparisonResponseOut(BaseModel):
    """Respuesta consolidada del panel general de comparación."""

    total_modulos: int
    total_escenarios: int
    filas: list[GlobalComparisonRowOut]
    graficos: list[ChartPayloadOut]
