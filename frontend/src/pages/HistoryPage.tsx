import { useEffect, useState } from "react";
import {
  fetchSimulacionById,
  fetchSimulaciones,
  relanzarSimulacion,
  type RerunResponse,
  type SimulacionListItem,
  type UnifiedModuleResponse,
} from "../services/api";

interface HistoryPageProps {
  onOpenSimulation: (sim: UnifiedModuleResponse) => void;
}

export function HistoryPage({ onOpenSimulation }: HistoryPageProps) {
  const [items, setItems] = useState<SimulacionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterCaso, setFilterCaso] = useState("");
  const [filterEscenario, setFilterEscenario] = useState("");
  const [rerunResult, setRerunResult] = useState<RerunResponse | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function loadList() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSimulaciones(
        filterCaso || undefined,
        filterEscenario || undefined
      );
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar historial");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadList();
  }, [filterCaso, filterEscenario]);

  async function handleInspect(id: number) {
    setBusyId(id);
    setError(null);
    try {
      const loaded = await fetchSimulacionById(id);
      onOpenSimulation(loaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al abrir simulación");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRerun(id: number) {
    setBusyId(id);
    setError(null);
    try {
      const res = await relanzarSimulacion(id);
      setRerunResult(res);
      await loadList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al relanzar simulación");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section>
      <div style={{ marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Historial de Simulaciones Persistidas</h2>
        <p style={{ margin: "0.25rem 0 0", color: "var(--muted)" }}>
          Recupera parámetros, iteraciones, métricas y gráficos almacenados en PostgreSQL/SQLite y
          relanza cualquier experimento para comprobar repetibilidad numérica.
        </p>
      </div>

      <div className="controls-bar">
        <label className="param-field" style={{ minWidth: "200px" }}>
          <span>Filtrar por Módulo</span>
          <select value={filterCaso} onChange={(e) => setFilterCaso(e.target.value)}>
            <option value="">Todos los módulos</option>
            <option value="MOD1_DETENCION">MOD1 — Detención</option>
            <option value="MOD2_DETERIORO">MOD2 — Deterioro</option>
            <option value="MOD3_OSCILACIONES">MOD3 — Oscilaciones</option>
            <option value="MOD4_SENSORES">MOD4 — Sensores</option>
          </select>
        </label>

        <label className="param-field" style={{ minWidth: "180px" }}>
          <span>Filtrar por Escenario</span>
          <select value={filterEscenario} onChange={(e) => setFilterEscenario(e.target.value)}>
            <option value="">Todos</option>
            <option value="NORMAL">NORMAL</option>
            <option value="ESTRES">ESTRÉS</option>
            <option value="MAL_CONDICIONADO">MAL CONDICIONADO</option>
          </select>
        </label>

        <button className="btn" style={{ marginLeft: "auto" }} onClick={loadList}>
          Actualizar Lista
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {rerunResult && (
        <div className="card card-active" style={{ marginBottom: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong>
              Verificación de Relanzamiento: Simulación #{rerunResult.simulacion_original_id} → #
              {rerunResult.simulacion_nueva.simulacion_id}
            </strong>
            <span className={`badge ${rerunResult.coincidencia_exacta ? "badge-ok" : "badge-danger"}`}>
              {rerunResult.coincidencia_exacta
                ? `Coincidencia exacta (Δmax=${rerunResult.diferencia_maxima.toExponential(2)})`
                : `Diferencia=${rerunResult.diferencia_maxima.toExponential(2)}`}
            </span>
          </div>
          <div className="table-wrapper" style={{ marginBottom: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Método</th>
                  <th>Valor Original</th>
                  <th>Valor Relanzado</th>
                  <th>|Δ|</th>
                  <th>En Tolerancia</th>
                </tr>
              </thead>
              <tbody>
                {rerunResult.comparacion_metodos.map((c) => (
                  <tr key={c.metodo}>
                    <td>{c.metodo}</td>
                    <td>{c.valor_original !== null ? c.valor_original.toFixed(8) : "N/A"}</td>
                    <td>{c.valor_relanzado !== null ? c.valor_relanzado.toFixed(8) : "N/A"}</td>
                    <td>{c.diferencia_abs.toExponential(2)}</td>
                    <td>{c.coincide_en_tolerancia ? "Sí" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {loading ? (
        <p style={{ color: "var(--muted)" }}>Cargando historial desde base de datos...</p>
      ) : items.length === 0 ? (
        <div className="card">
          <p>
            Aún no hay simulaciones guardadas para este filtro. Ejecuta cualquier módulo para
            registrar la primera simulación.
          </p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Fecha</th>
                <th>Módulo</th>
                <th>Escenario</th>
                <th>Estado</th>
                <th>Métodos</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.simulacion_id}>
                  <td>#{item.simulacion_id}</td>
                  <td>{new Date(item.fecha).toLocaleString()}</td>
                  <td>{item.caso_codigo}</td>
                  <td>{item.escenario}</td>
                  <td>
                    <span
                      className={`badge ${
                        item.estado === "COMPLETADO" ? "badge-ok" : "badge-pending"
                      }`}
                    >
                      {item.estado}
                    </span>
                  </td>
                  <td>{item.total_metodos}</td>
                  <td style={{ display: "flex", gap: "0.4rem" }}>
                    <button
                      className="btn btn-primary"
                      style={{ padding: "0.3rem 0.65rem", fontSize: "0.8rem" }}
                      disabled={busyId === item.simulacion_id}
                      onClick={() => handleInspect(item.simulacion_id)}
                    >
                      Recuperar
                    </button>
                    <button
                      className="btn"
                      style={{ padding: "0.3rem 0.65rem", fontSize: "0.8rem" }}
                      disabled={busyId === item.simulacion_id}
                      onClick={() => handleRerun(item.simulacion_id)}
                    >
                      Relanzar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
