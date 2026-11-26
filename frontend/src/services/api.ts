export type ScenarioType = "NORMAL" | "ESTRES" | "MAL_CONDICIONADO";
export type CasoCodigo =
  | "MOD1_DETENCION"
  | "MOD2_DETERIORO"
  | "MOD3_OSCILACIONES"
  | "MOD4_SENSORES";

export interface Escenario {
  id: number;
  tipo: ScenarioType;
  nombre_descriptivo: string;
  parametros_json: Record<string, unknown>;
  fuente_datos: string;
  es_predefinido: boolean;
}

export interface CasoEstudio {
  id: number;
  codigo: CasoCodigo;
  nombre: string;
  descripcion: string;
  modelo_version: string;
  escenarios: Escenario[];
}

export interface ChartSeries {
  name: string;
  x: number[];
  y: number[];
  mode: "line" | "markers";
}

export interface ChartPayload {
  id: string;
  titulo: string;
  x_label: string;
  y_label: string;
  y_scale: "linear" | "log";
  series: ChartSeries[];
}

export interface UnifiedMethodResult {
  familia: string;
  metodo: string;
  convergio: boolean;
  iteraciones_realizadas: number;
  tiempo_ms: number;
  valor_principal: number | null;
  etiqueta_valor: string;
  residual: number | null;
  error_abs: number | null;
  error_rel: number | null;
  error_pct: number | null;
  motivo_parada: string;
  detalle_tabla: Record<string, unknown>[];
}

export interface UnifiedModuleResponse {
  simulacion_id: number | null;
  fecha: string | null;
  estado: string | null;
  usuario_equipo: string | null;
  caso_codigo: CasoCodigo;
  escenario: ScenarioType;
  nombre_descriptivo: string;
  parametros_usados: Record<string, unknown>;
  referencia: Record<string, unknown>;
  metodos: UnifiedMethodResult[];
  graficos: ChartPayload[];
  interpretacion_numerica: string;
  interpretacion_problema: string;
}

export interface SimulacionListItem {
  simulacion_id: number;
  fecha: string;
  usuario_equipo: string;
  estado: string;
  caso_codigo: CasoCodigo;
  caso_nombre: string;
  escenario: ScenarioType;
  nombre_descriptivo: string;
  parametros_usados: Record<string, unknown>;
  total_metodos: number;
  notas_usuario: string | null;
}

export interface RerunComparisonMethod {
  metodo: string;
  valor_original: number | null;
  valor_relanzado: number | null;
  diferencia_abs: number;
  coincide_en_tolerancia: boolean;
}

export interface RerunResponse {
  simulacion_original_id: number;
  simulacion_nueva: UnifiedModuleResponse;
  diferencia_maxima: number;
  coincidencia_exacta: boolean;
  comparacion_metodos: RerunComparisonMethod[];
}

export interface GlobalComparisonRow {
  modulo_index: number;
  caso_codigo: CasoCodigo;
  modulo_nombre: string;
  escenario: ScenarioType;
  nombre_descriptivo: string;
  total_metodos: number;
  metodos_convergentes: number;
  metodos_advertencia: number;
  mejor_metodo: string;
  mejor_error_abs: number | null;
  mejor_error_rel: number | null;
  alerta_o_mayor_error: string;
  tiempo_total_ms: number;
  metrica_clave: string;
  interpretacion_numerica: string;
  interpretacion_problema: string;
}

export interface GlobalComparisonResponse {
  total_modulos: number;
  total_escenarios: number;
  filas: GlobalComparisonRow[];
  graficos: ChartPayload[];
}

const API_BASE = "/api";

export async function fetchHealth(): Promise<{
  status: string;
  version: string;
  database_backend: string;
}> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Error al verificar salud de API (${res.status})`);
  }
  return res.json();
}

export async function fetchCasos(): Promise<CasoEstudio[]> {
  const res = await fetch(`${API_BASE}/casos`);
  if (!res.ok) {
    throw new Error(`Error al obtener módulos (${res.status})`);
  }
  return res.json();
}

export async function runModule(
  casoCodigo: CasoCodigo,
  escenario: ScenarioType,
  parametrosOverride?: Record<string, unknown>,
  notasUsuario?: string
): Promise<UnifiedModuleResponse> {
  const res = await fetch(`${API_BASE}/modulos/${casoCodigo}/ejecutar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      escenario,
      parametros_override: parametrosOverride,
      usuario_equipo: "Equipo_SIMTELE",
      notas_usuario: notasUsuario || null,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Error al ejecutar ${casoCodigo} (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function fetchSimulaciones(
  casoCodigo?: string,
  escenario?: string
): Promise<SimulacionListItem[]> {
  const params = new URLSearchParams();
  if (casoCodigo) params.set("caso_codigo", casoCodigo);
  if (escenario) params.set("escenario", escenario);
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/simulaciones${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new Error(`Error al listar historial (${res.status})`);
  }
  return res.json();
}

export async function fetchSimulacionById(
  simulacionId: number
): Promise<UnifiedModuleResponse> {
  const res = await fetch(`${API_BASE}/simulaciones/${simulacionId}`);
  if (!res.ok) {
    throw new Error(`Error al recuperar simulación #${simulacionId} (${res.status})`);
  }
  return res.json();
}

export async function relanzarSimulacion(
  simulacionId: number
): Promise<RerunResponse> {
  const res = await fetch(`${API_BASE}/simulaciones/${simulacionId}/relanzar`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Error al relanzar simulación #${simulacionId} (${res.status})`);
  }
  return res.json();
}

export async function fetchGlobalComparison(): Promise<GlobalComparisonResponse> {
  const res = await fetch(`${API_BASE}/comparacion-global`);
  if (!res.ok) {
    throw new Error(`Error al cargar comparación global (${res.status})`);
  }
  return res.json();
}
