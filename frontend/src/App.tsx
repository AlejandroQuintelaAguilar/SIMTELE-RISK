import { useEffect, useState } from "react";
import {
  fetchCasos,
  fetchHealth,
  type CasoCodigo,
  type CasoEstudio,
  type UnifiedModuleResponse,
} from "./services/api";
import { HomePage } from "./pages/HomePage";
import { ModuleWorkspacePage } from "./pages/ModuleWorkspacePage";
import { HistoryPage } from "./pages/HistoryPage";
import { ComparisonPage } from "./pages/ComparisonPage";

type ViewTab = "inicio" | CasoCodigo | "comparacion" | "historial";

const MODULE_TABS: { codigo: CasoCodigo; short: string }[] = [
  { codigo: "MOD1_DETENCION", short: "Mód. 1: Detención" },
  { codigo: "MOD2_DETERIORO", short: "Mód. 2: Deterioro" },
  { codigo: "MOD3_OSCILACIONES", short: "Mód. 3: Viento" },
  { codigo: "MOD4_SENSORES", short: "Mód. 4: Sensores" },
];

export function App() {
  const [tab, setTab] = useState<ViewTab>("inicio");
  const [casos, setCasos] = useState<CasoEstudio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dbBackend, setDbBackend] = useState<string>("desconectado");
  const [version, setVersion] = useState<string>("");
  const [recoveredSim, setRecoveredSim] = useState<UnifiedModuleResponse | null>(null);

  useEffect(() => {
    let active = true;
    async function loadInitial() {
      try {
        const [healthData, casosData] = await Promise.all([fetchHealth(), fetchCasos()]);
        if (!active) return;
        setDbBackend(healthData.database_backend);
        setVersion(healthData.version);
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

  function openModule(codigo: CasoCodigo) {
    setRecoveredSim(null);
    setTab(codigo);
  }

  function handleRecoveredSimulation(sim: UnifiedModuleResponse) {
    setRecoveredSim(sim);
    setTab(sim.caso_codigo);
  }

  const activeCaso = casos.find((c) => c.codigo === tab);

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="brand">
          <h1>SIMTELE-RISK</h1>
          <p>
            Simulación Numérica y Análisis de Riesgos · {version || "v2"} · BD:{" "}
            <strong>{dbBackend}</strong>
          </p>
        </div>

        <nav className="nav-tabs" style={{ flexWrap: "wrap" }}>
          <button
            className={`btn ${tab === "inicio" ? "btn-primary" : ""}`}
            onClick={() => setTab("inicio")}
          >
            Inicio
          </button>
          {MODULE_TABS.map((m) => (
            <button
              key={m.codigo}
              className={`btn ${tab === m.codigo ? "btn-primary" : ""}`}
              onClick={() => openModule(m.codigo)}
            >
              {m.short}
            </button>
          ))}
          <button
            className={`btn ${tab === "comparacion" ? "btn-primary" : ""}`}
            onClick={() => setTab("comparacion")}
          >
            Comparación 4×3
          </button>
          <button
            className={`btn ${tab === "historial" ? "btn-primary" : ""}`}
            onClick={() => setTab("historial")}
          >
            Historial
          </button>
        </nav>
      </header>

      <main>
        {tab === "inicio" ? (
          <HomePage
            casos={casos}
            loading={loading}
            error={error}
            onOpenModule={openModule}
          />
        ) : tab === "comparacion" ? (
          <ComparisonPage onOpenModule={openModule} />
        ) : tab === "historial" ? (
          <HistoryPage onOpenSimulation={handleRecoveredSimulation} />
        ) : activeCaso ? (
          <ModuleWorkspacePage
            key={`${activeCaso.codigo}-${recoveredSim?.simulacion_id ?? "fresh"}`}
            caso={activeCaso}
            initialResult={
              recoveredSim?.caso_codigo === activeCaso.codigo ? recoveredSim : null
            }
            onBack={() => setTab("inicio")}
          />
        ) : (
          <p style={{ color: "var(--muted)" }}>Cargando configuración del módulo...</p>
        )}
      </main>
    </div>
  );
}

export default App;
