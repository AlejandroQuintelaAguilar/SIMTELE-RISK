import { useState } from "react";
import {
  executeModulo2,
  type MethodResult,
  type Modulo2ExecuteResponse,
  type ScenarioType,
} from "../services/api";

const SCENARIOS: { value: ScenarioType; label: string }[] = [
  { value: "NORMAL", label: "NORMAL (n=4, SPD bien condicionada)" },
  { value: "ESTRES", label: "ESTRÉS (n=12, tol=1e-11)" },
  { value: "MAL_CONDICIONADO", label: "MAL CONDICIONADO (Hilbert n=6)" },
];

function fmtSci(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  if (value === 0) return "0.000e+0";
  return value.toExponential(digits);
}

export function Module2Page() {
  const [escenario, setEscenario] = useState<ScenarioType>("NORMAL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<Modulo2ExecuteResponse | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const data = await executeModulo2(escenario);
      setReport(data);
      setSelectedMethod(data.resultados_metodos[0]?.metodo ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  const activeMethod: MethodResult | undefined = report?.resultados_metodos.find(
    (m) => m.metodo === selectedMethod
  );

  return (
    <section>
      <div style={{ marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Módulo 2: Deterioro Mecánico y Calibración SPD</h2>
        <p style={{ margin: "0.25rem 0 0", color: "var(--muted)" }}>
          Resolución de sistemas lineales A·x = b mediante Jacobi, Gauss-Seidel, Factorización LU
          (pivoteo parcial) y Gradiente Conjugado en precisión float64.
        </p>
      </div>

      <div className="controls-bar">
        <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Escenario:</span>
        {SCENARIOS.map((sc) => (
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
          {loading ? "Ejecutando..." : "Ejecutar Simulación"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {report && (
        <>
          <div className="metrics-grid">
            <div className="metric-box">
              <div className="metric-label">Dimensión (n)</div>
              <div className="metric-value">{report.dimension_n}</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">Tolerancia</div>
              <div className="metric-value">{report.tol.toExponential(1)}</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">Número de Condición κ₂(A)</div>
              <div className="metric-value">{fmtSci(report.kappa_2, 3)}</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">Amplificación (δb/b = 1e-4)</div>
              <div className="metric-value">
                {report.sensibilidad.amplification_factor.toFixed(2)}×
              </div>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Método</th>
                  <th>Estado</th>
                  <th>Iteraciones</th>
                  <th>Tiempo (ms)</th>
                  <th>Residual ‖b − Ax‖₂</th>
                  <th>Error Abs.</th>
                  <th>Error Rel.</th>
                  <th>Error %</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {report.resultados_metodos.map((m) => (
                  <tr key={m.metodo}>
                    <td style={{ fontWeight: 600 }}>{m.metodo}</td>
                    <td>
                      <span className={`badge ${m.convergio ? "badge-ok" : "badge-danger"}`}>
                        {m.convergio ? "Convergió" : "No convergió"}
                      </span>
                    </td>
                    <td>{m.iteraciones_realizadas}</td>
                    <td>{m.tiempo_ms.toFixed(4)}</td>
                    <td>{fmtSci(m.residual_final)}</td>
                    <td>{fmtSci(m.error_abs)}</td>
                    <td>{fmtSci(m.error_rel)}</td>
                    <td>{fmtSci(m.error_pct)}</td>
                    <td>
                      <button
                        className={`btn ${selectedMethod === m.metodo ? "btn-primary" : ""}`}
                        style={{ padding: "0.3rem 0.65rem", fontSize: "0.8rem" }}
                        onClick={() => setSelectedMethod(m.metodo)}
                      >
                        Iteraciones ({m.historial.length})
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="interpretation-grid">
            <div className="card">
              <h3>Interpretación Numérica</h3>
              <p>{report.interpretacion_numerica}</p>
            </div>
            <div className="card">
              <h3>Interpretación del Problema (Mi Teleférico)</h3>
              <p>{report.interpretacion_problema}</p>
            </div>
          </div>

          {activeMethod && (
            <div className="table-wrapper">
              <div style={{ padding: "0.85rem 1rem", borderBottom: "1px solid var(--border)" }}>
                <strong>Historial de Iteraciones — {activeMethod.metodo}</strong>{" "}
                <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                  ({activeMethod.motivo_parada})
                </span>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>k</th>
                    <th>‖b − Ax⁽ᵏ⁾‖₂</th>
                    <th>Residual Rel.</th>
                    <th>‖x⁽ᵏ⁾ − x⁽ᵏ⁻¹⁾‖₂</th>
                    <th>Error Rel. vs x*</th>
                    <th>Vector x⁽ᵏ⁾ (primeras 4 comp.)</th>
                  </tr>
                </thead>
                <tbody>
                  {activeMethod.historial.slice(0, 30).map((it) => (
                    <tr key={it.numero}>
                      <td>{it.numero}</td>
                      <td>{fmtSci(it.residual)}</td>
                      <td>{fmtSci(it.residual_rel)}</td>
                      <td>{fmtSci(it.step_diff)}</td>
                      <td>{fmtSci(it.error_rel)}</td>
                      <td>
                        [{it.x.slice(0, 4).map((v) => v.toFixed(5)).join(", ")}
                        {it.x.length > 4 ? ", ..." : ""}]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {activeMethod.historial.length > 30 && (
                <div style={{ padding: "0.65rem 1rem", color: "var(--muted)", fontSize: "0.82rem" }}>
                  Mostrando las primeras 30 de {activeMethod.historial.length} iteraciones registradas.
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
