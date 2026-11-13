import { useEffect, useState } from "react";
import { fetchCasos, fetchHealth, type CasoEstudio } from "./services/api";
import { HomePage } from "./pages/HomePage";
import { Module2Page } from "./pages/Module2Page";

type ViewTab = "inicio" | "modulo2";

export function App() {
  const [tab, setTab] = useState<ViewTab>("inicio");
  const [casos, setCasos] = useState<CasoEstudio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dbBackend, setDbBackend] = useState<string>("desconectado");

  useEffect(() => {
    let active = true;
    async function loadInitial() {
      try {
        const [healthData, casosData] = await Promise.all([fetchHealth(), fetchCasos()]);
        if (!active) return;
        setDbBackend(healthData.database_backend);
        setCasos(casosData);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Error de conexión con el backend");
      } finally {
        if (active) setLoading(false);
      }
    }
    loadInitial();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="brand">
          <h1>SIMTELE-RISK</h1>
          <p>
            Simulación Numérica y Análisis de Riesgos · BD:{" "}
            <strong>{dbBackend}</strong>
          </p>
        </div>

        <nav className="nav-tabs">
          <button
            className={`btn ${tab === "inicio" ? "btn-primary" : ""}`}
            onClick={() => setTab("inicio")}
          >
            Inicio (4 Módulos)
          </button>
          <button
            className={`btn ${tab === "modulo2" ? "btn-primary" : ""}`}
            onClick={() => setTab("modulo2")}
          >
            Módulo 2: Sistemas Lineales
          </button>
        </nav>
      </header>

      <main>
        {tab === "inicio" ? (
          <HomePage
            casos={casos}
            loading={loading}
            error={error}
            onSelectModulo2={() => setTab("modulo2")}
          />
        ) : (
          <Module2Page />
        )}
      </main>
    </div>
  );
}

export default App;
