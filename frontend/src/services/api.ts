export type ScenarioType = "NORMAL" | "ESTRES" | "MAL_CONDICIONADO";

export interface Escenario {
  id: number;
  tipo: string;
  nombre_descriptivo: string;
  parametros_json: Record<string, unknown>;
  fuente_datos: string;
  es_predefinido: boolean;
}

export interface CasoEstudio {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string;
  modelo_version: string;
  escenarios: Escenario[];
}

export interface IterationRecord {
  numero: number;
  x: number[];
  residual: number;
  residual_rel: number;
  step_diff: number | null;
  error_abs: number | null;
  error_rel: number | null;
  error_pct: number | null;
}

export interface MethodResult {
  metodo: string;
  familia: string;
  convergio: boolean;
  iteraciones_realizadas: number;
  motivo_parada: string;
  tiempo_ms: number;
  residual_final: number;
  residual_rel_final: number;
  error_abs: number | null;
  error_rel: number | null;
  error_pct: number | null;
  x_aprox: number[];
  diagnostics: Record<string, unknown>;
  historial: IterationRecord[];
}

export interface SensitivityResult {
  relative_perturbation_b: number;
  relative_change_x: number;
  amplification_factor: number;
  condition_number_2: number;
  delta_b_norm: number;
  delta_x_norm: number;
}

export interface Modulo2ExecuteResponse {
  escenario: ScenarioType;
  nombre_descriptivo: string;
  dimension_n: number;
  tol: number;
  max_iter: number;
  kappa_2: number;
  x_referencia: number[];
  sensibilidad: SensitivityResult;
  resultados_metodos: MethodResult[];
  interpretacion_numerica: string;
  interpretacion_problema: string;
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

export async function executeModulo2(
  escenario: ScenarioType
): Promise<Modulo2ExecuteResponse> {
  const res = await fetch(`${API_BASE}/modulo2/sistemas-lineales/ejecutar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ escenario }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Error al ejecutar Módulo 2 (${res.status}): ${detail}`);
  }
  return res.json();
}
