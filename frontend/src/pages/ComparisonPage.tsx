import { useEffect, useState } from "react";
import { SvgChart } from "../components/SvgChart";
import {
  fetchGlobalComparison,
  type CasoCodigo,
  type GlobalComparisonResponse,
  type GlobalComparisonRow,
  type ScenarioType,
} from "../services/api";

interface ComparisonPageProps {
  onOpenModule: (codigo: CasoCodigo) => void;
}

function fmtSci(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  if (value === 0) return "0.000e+0";
  return value.toExponential(2);
}

export function ComparisonPage({ onOpenModule }: ComparisonPageProps) {
  const [data, setData] = useState<GlobalComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterEsc, setFilterEsc] = useState<"ALL" | ScenarioType>("ALL");
  const [selectedRow, setSelectedRow] = useState<GlobalComparisonRow | null>(null);

  async function loadComparison() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchGlobalComparison();
      setData(res);
      setSelectedRow(res.filas[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar comparación global");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadComparison();
  }, []);

  const rows =
    data?.filas.filter((r) => filterEsc === "ALL" || r.escenario === filterEsc) ?? [];

  const totalAlerts =
    data?.filas.reduce((acc, r) => acc + r.metodos_advertencia, 0) ?? 0;

  return (
    <section>
      <div style={{ marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Panel General de Comparación (Matriz 4 × 3)</h2>
        <p style={{ margin: "0.25rem 0 0", color: "var(--muted)" }}>
          Contraste transversal de precisión, convergencia, estabilidad y tiempos entre los 4
          módulos y los 3 escenarios obligatorios (NORMAL, ESTRÉS y MAL CONDICIONADO).
        </p>
      </div>

      <div className="controls-bar">
        <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Filtrar escenario:</span>
        {(["ALL", "NORMAL", "ESTRES", "MAL_CONDICIONADO"] as const).map((esc) => (
          <button
            key={esc}
            className={`btn ${filterEsc === esc ? "btn-primary" : ""}`}
            onClick={() => setFilterEsc(esc)}
          >
            {esc === "ALL" ? "Todos (12)" : esc === "ESTRES" ? "ESTRÉS" : esc}
          </button>
        ))}

        <button
          className="btn"
          style={{ marginLeft: "auto" }}
          onClick={loadComparison}
          disabled={loading}
        >
          {loading ? "Calculando 4×3..." : "Recalcular Matriz"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loading && !data ? (
        <p style={{ color: "var(--muted)" }}>Ejecutando comparativa de los 12 escenarios...</p>
      ) : (
        data && (
          <>
            <div className="metrics-grid">
              <div className="metric-box">
                <div className="metric-label">Módulos Evaluados</div>
                <div className="metric-value">{data.total_modulos}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Escenarios (4 × 3)</div>
                <div className="metric-value">{data.total_escenarios}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Métodos con Advertencia</div>
                <div className="metric-value">{totalAlerts}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Tiempo Total (12 corridas)</div>
                <div className="metric-value">
                  {data.filas.reduce((a, r) => a + r.tiempo_total_ms, 0).toFixed(2)} ms
                </div>
              </div>
            </div>

            <div className="charts-grid">
              {data.graficos.map((chart) => (
                <SvgChart key={chart.id} chart={chart} />
              ))}
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Módulo</th>
                    <th>Escenario</th>
                    <th>Convergencia</th>
                    <th>Mejor Método</th>
                    <th>Mejor E_abs</th>
                    <th>Métrica / Hallazgo Clave</th>
                    <th>Alerta / Mayor Error</th>
                    <th>Tiempo (ms)</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const isSelected =
                      selectedRow?.caso_codigo === r.caso_codigo &&
                      selectedRow?.escenario === r.escenario;
                    return (
                      <tr
                        key={`${r.caso_codigo}-${r.escenario}`}
                        style={{
                          background: isSelected ? "rgba(56, 189, 248, 0.08)" : undefined,
                        }}
                      >
                        <td style={{ fontWeight: 600 }}>{r.modulo_nombre}</td>
                        <td>
                          <span
                            className={`badge ${
                              r.escenario === "NORMAL"
                                ? "badge-ok"
                                : r.escenario === "ESTRES"
                                ? "badge-pending"
                                : "badge-danger"
                            }`}
                          >
                            {r.escenario}
                          </span>
                        </td>
                        <td>
                          {r.metodos_convergentes}/{r.total_metodos}
                        </td>
                        <td>{r.mejor_metodo}</td>
                        <td>{fmtSci(r.mejor_error_abs)}</td>
                        <td style={{ fontSize: "0.82rem" }}>{r.metrica_clave}</td>
                        <td style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
                          {r.alerta_o_mayor_error}
                        </td>
                        <td>{r.tiempo_total_ms.toFixed(2)}</td>
                        <td style={{ display: "flex", gap: "0.4rem" }}>
                          <button
                            className={`btn ${isSelected ? "btn-primary" : ""}`}
                            style={{ padding: "0.3rem 0.6rem", fontSize: "0.78rem" }}
                            onClick={() => setSelectedRow(r)}
                          >
                            Conclusiones
                          </button>
                          <button
                            className="btn"
                            style={{ padding: "0.3rem 0.6rem", fontSize: "0.78rem" }}
                            onClick={() => onOpenModule(r.caso_codigo)}
                          >
                            Abrir
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {selectedRow && (
              <div className="interpretation-grid">
                <div className="card card-active">
                  <h3>
                    Conclusión Numérica — {selectedRow.modulo_nombre} ({selectedRow.escenario})
                  </h3>
                  <p>{selectedRow.interpretacion_numerica}</p>
                </div>
                <div className="card card-active">
                  <h3>
                    Conclusión del Problema — {selectedRow.modulo_nombre} ({selectedRow.escenario})
                  </h3>
                  <p>{selectedRow.interpretacion_problema}</p>
                </div>
              </div>
            )}
          </>
        )
      )}
    </section>
  );
}
