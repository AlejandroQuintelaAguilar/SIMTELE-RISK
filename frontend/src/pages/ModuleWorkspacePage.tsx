import { useEffect, useState } from "react";
import { SvgChart } from "../components/SvgChart";
import {
  runModule,
  type CasoCodigo,
  type CasoEstudio,
  type ScenarioType,
  type UnifiedMethodResult,
  type UnifiedModuleResponse,
} from "../services/api";

interface ModuleWorkspacePageProps {
  caso: CasoEstudio;
  initialResult?: UnifiedModuleResponse | null;
  onBack: () => void;
}

const SCENARIO_LABELS: { value: ScenarioType; label: string }[] = [
  { value: "NORMAL", label: "NORMAL" },
  { value: "ESTRES", label: "ESTRÉS" },
  { value: "MAL_CONDICIONADO", label: "MAL CONDICIONADO" },
];

const NUMERIC_EDITABLE_KEYS: Record<CasoCodigo, string[]> = {
  MOD1_DETENCION: ["v0", "a0", "kd", "h", "tol"],
  MOD2_DETERIORO: ["D0", "alpha", "beta", "D_umbral", "tol", "max_iter"],
  MOD3_OSCILACIONES: ["m", "c", "k", "F0", "omega", "x0", "h", "T"],
  MOD4_SENSORES: ["a", "b", "n_nodos", "ruido_sigma", "umbral_alerta"],
};

const MODULE_FORMULAS: Record<CasoCodigo, { ecuacion: string; unidades: string }> = {
  MOD1_DETENCION: {
    ecuacion: "dx/dt = v,  dv/dt = −(a₀ + k_d·v);  x_det = ∫ v(t) dt;  v(t_det) = 0",
    unidades: "t [s], x [m], v [m/s], a₀ [m/s²], k_d [s⁻¹]",
  },
  MOD2_DETERIORO: {
    ecuacion: "A·x = b (Calibración SPD);  D(t) = D₀ + α·t + β·t² = D_umbral",
    unidades: "t [meses], D(t) [adimensional 0..1], κ₂(A) [adimensional]",
  },
  MOD3_OSCILACIONES: {
    ecuacion: "m·x'' + c·x' + k·x = F₀·sin(ω·t);  Energía = ∫₀ᵀ x(t)² dt",
    unidades: "t [s], x [m], m [kg], c [N·s/m], k [N/m], F₀ [N], ω [rad/s]",
  },
  MOD4_SENSORES: {
    ecuacion: "P(t) ≈ y(t) (Lagrange, Newton, Splines Cúbicos);  S(t*) − y_umbral = 0",
    unidades: "t [s], y(t) [u. telemetría], σ [ruido gaussiano]",
  },
};

function fmtSci(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  if (value === 0) return "0.000e+0";
  return value.toExponential(digits);
}

function fmtCell(val: unknown): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    if (Math.abs(val) >= 1000 || (Math.abs(val) > 0 && Math.abs(val) < 1e-3)) {
      return val.toExponential(3);
    }
    return Number.isInteger(val) ? String(val) : val.toFixed(6);
  }
  if (Array.isArray(val)) {
    return `[${val.slice(0, 4).map((x) => (typeof x === "number" ? x.toFixed(4) : String(x))).join(", ")}${val.length > 4 ? ", ..." : ""}]`;
  }
  return String(val);
}

export function ModuleWorkspacePage({
  caso,
  initialResult = null,
  onBack,
}: ModuleWorkspacePageProps) {
  const [escenario, setEscenario] = useState<ScenarioType>(
    initialResult?.escenario ?? "NORMAL"
  );
  const [paramDraft, setParamDraft] = useState<Record<string, string>>({});
  const [notas, setNotas] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<UnifiedModuleResponse | null>(initialResult);
  const [selectedMethod, setSelectedMethod] = useState<string | null>(
    initialResult?.metodos[0]?.metodo ?? null
  );

  // Sincroniza borradores editables al cambiar módulo o escenario
  useEffect(() => {
    const escObj = caso.escenarios.find((e) => e.tipo === escenario);
    const source =
      initialResult && initialResult.caso_codigo === caso.codigo && initialResult.escenario === escenario
        ? initialResult.parametros_usados
        : escObj?.parametros_json ?? {};

    const keys = NUMERIC_EDITABLE_KEYS[caso.codigo];
    const nextDraft: Record<string, string> = {};
    for (const k of keys) {
      if (source[k] !== undefined && source[k] !== null) {
        nextDraft[k] = String(source[k]);
      }
    }
    setParamDraft(nextDraft);
  }, [caso, escenario, initialResult]);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const overrides: Record<string, number> = {};
      for (const [k, raw] of Object.entries(paramDraft)) {
        if (raw.trim() !== "") {
          const parsed = Number(raw);
          if (!Number.isFinite(parsed)) {
            throw new Error(`El parámetro "${k}" debe ser un número válido.`);
          }
          overrides[k] = parsed;
        }
      }
      const data = await runModule(caso.codigo, escenario, overrides, notas);
      setReport(data);
      setSelectedMethod(data.metodos[0]?.metodo ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al ejecutar el módulo");
    } finally {
      setLoading(false);
    }
  }

  const activeMethod: UnifiedMethodResult | undefined = report?.metodos.find(
    (m) => m.metodo === selectedMethod
  );

  const detailCols =
    activeMethod && activeMethod.detalle_tabla.length > 0
      ? Object.keys(activeMethod.detalle_tabla[0])
      : [];

  return (
    <section>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1rem",
        }}
      >
        <div>
          <span className="metric-label">{caso.codigo}</span>
          <h2 style={{ margin: "0.15rem 0 0" }}>{caso.nombre}</h2>
          <p style={{ margin: "0.25rem 0 0", color: "var(--muted)", fontSize: "0.9rem" }}>
            {caso.descripcion}
          </p>
        </div>
        <button className="btn" onClick={onBack}>
          ← Volver a Inicio
        </button>
      </div>

      <div className="banner" style={{ marginBottom: "1rem" }}>
        <div>
          <strong>Modelo Matemático:</strong>{" "}
          <code>{MODULE_FORMULAS[caso.codigo].ecuacion}</code>
        </div>
        <div style={{ fontSize: "0.83rem", color: "var(--muted)", marginTop: "0.25rem" }}>
          <strong>Unidades:</strong> {MODULE_FORMULAS[caso.codigo].unidades}
          {(() => {
            const escMeta = caso.escenarios.find((e) => e.tipo === escenario);
            return escMeta ? (
              <>
                {" · "}
                <strong>Fuente ({escMeta.tipo}):</strong> {escMeta.fuente_datos}
              </>
            ) : null;
          })()}
        </div>
      </div>

      <div className="controls-bar">
        <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Escenario:</span>
        {SCENARIO_LABELS.map((sc) => (
          <button
            key={sc.value}
            className={`btn ${escenario === sc.value ? "btn-primary" : ""}`}
            onClick={() => setEscenario(sc.value)}
          >
            {sc.label}
          </button>
        ))}

        <button
          className="btn btn-primary"
          style={{ marginLeft: "auto" }}
          onClick={handleRun}
          disabled={loading}
        >
          {loading ? "Ejecutando y guardando..." : "Ejecutar y Guardar Simulación"}
        </button>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong style={{ fontSize: "0.92rem" }}>Parámetros del Modelo (Editables)</strong>
          {report?.simulacion_id && (
            <span className="badge badge-ok">
              Guardado en BD · Simulación #{report.simulacion_id} ({report.estado})
            </span>
          )}
        </div>
        <div className="params-grid">
          {Object.entries(paramDraft).map(([k, val]) => (
            <label key={k} className="param-field">
              <span>{k}</span>
              <input
                type="text"
                value={val}
                onChange={(e) =>
                  setParamDraft((prev) => ({ ...prev, [k]: e.target.value }))
                }
              />
            </label>
          ))}
          <label className="param-field" style={{ gridColumn: "span 2" }}>
            <span>Notas del experimento (opcional)</span>
            <input
              type="text"
              placeholder="Ej. Corrida de prueba Semana 2..."
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
            />
          </label>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {report && (
        <>
          <div className="metrics-grid">
            {Object.entries(report.referencia).map(([k, v]) => (
              <div key={k} className="metric-box">
                <div className="metric-label">{k}</div>
                <div className="metric-value" style={{ fontSize: "1.05rem" }}>
                  {typeof v === "number" ? fmtCell(v) : String(v ?? "N/A")}
                </div>
              </div>
            ))}
          </div>

          <div className="charts-grid">
            {report.graficos.map((chart) => (
              <SvgChart key={chart.id} chart={chart} />
            ))}
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Familia</th>
                  <th>Método</th>
                  <th>Estado</th>
                  <th>Iter./Pasos</th>
                  <th>Tiempo (ms)</th>
                  <th>Resultado</th>
                  <th>Residual</th>
                  <th>Error Abs.</th>
                  <th>Error Rel.</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {report.metodos.map((m) => (
                  <tr key={`${m.familia}-${m.metodo}`}>
                    <td>
                      <span className="metric-label">{m.familia}</span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{m.metodo}</td>
                    <td>
                      <span className={`badge ${m.convergio ? "badge-ok" : "badge-danger"}`}>
                        {m.convergio ? "Convergió" : "Advertencia"}
                      </span>
                    </td>
                    <td>{m.iteraciones_realizadas}</td>
                    <td>{m.tiempo_ms.toFixed(4)}</td>
                    <td>{m.etiqueta_valor || fmtSci(m.valor_principal)}</td>
                    <td>{fmtSci(m.residual)}</td>
                    <td>{fmtSci(m.error_abs)}</td>
                    <td>{fmtSci(m.error_rel)}</td>
                    <td>
                      <button
                        className={`btn ${selectedMethod === m.metodo ? "btn-primary" : ""}`}
                        style={{ padding: "0.3rem 0.65rem", fontSize: "0.8rem" }}
                        onClick={() => setSelectedMethod(m.metodo)}
                      >
                        Ver ({m.detalle_tabla.length})
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="interpretation-grid">
            <div className="card">
              <h3>Conclusión Numérica (Algoritmos y Estabilidad)</h3>
              <p>{report.interpretacion_numerica}</p>
            </div>
            <div className="card">
              <h3>Conclusión del Problema (Mi Teleférico)</h3>
              <p>{report.interpretacion_problema}</p>
            </div>
          </div>

          {activeMethod && activeMethod.detalle_tabla.length > 0 && (
            <div className="table-wrapper">
              <div style={{ padding: "0.85rem 1rem", borderBottom: "1px solid var(--border)" }}>
                <strong>Tabla de Trazabilidad — {activeMethod.metodo}</strong>{" "}
                <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                  ({activeMethod.motivo_parada})
                </span>
              </div>
              <table>
                <thead>
                  <tr>
                    {detailCols.map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activeMethod.detalle_tabla.slice(0, 35).map((row, idx) => (
                    <tr key={idx}>
                      {detailCols.map((col) => (
                        <td key={col}>{fmtCell(row[col])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {activeMethod.detalle_tabla.length > 35 && (
                <div style={{ padding: "0.65rem 1rem", color: "var(--muted)", fontSize: "0.82rem" }}>
                  Mostrando primeras 35 de {activeMethod.detalle_tabla.length} filas guardadas.
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
