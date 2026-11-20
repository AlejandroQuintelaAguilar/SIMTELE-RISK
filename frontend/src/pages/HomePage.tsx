import type { CasoCodigo, CasoEstudio } from "../services/api";
import { ModuleCard } from "../components/ModuleCard";

interface HomePageProps {
  casos: CasoEstudio[];
  loading: boolean;
  error: string | null;
  onOpenModule: (codigo: CasoCodigo) => void;
}

const FALLBACK_CASOS: CasoEstudio[] = [
  {
    id: 1,
    codigo: "MOD1_DETENCION",
    nombre: "Detención de Emergencia de Cabinas",
    descripcion:
      "Modelado cinemático y dinámico de frenado de emergencia mediante EDO, integración de velocidad y búsqueda de instante de detención.",
    modelo_version: "v1.0",
    escenarios: [],
  },
  {
    id: 2,
    codigo: "MOD2_DETERIORO",
    nombre: "Deterioro Mecánico y Mantenimiento",
    descripcion:
      "Calibración de modelo polinómico de desgaste mediante sistemas lineales SPD y predicción de tiempo a umbral crítico.",
    modelo_version: "v1.0",
    escenarios: [],
  },
  {
    id: 3,
    codigo: "MOD3_OSCILACIONES",
    nombre: "Oscilaciones por Viento",
    descripcion:
      "Simulación de respuesta dinámica amortiguada ante ráfagas de viento e integración de energía acumulada.",
    modelo_version: "v1.0",
    escenarios: [],
  },
  {
    id: 4,
    codigo: "MOD4_SENSORES",
    nombre: "Reconstrucción de Señales de Sensores",
    descripcion:
      "Interpolación de telemetría con datos ocultados, evaluación de ruido y detección de cruce de umbrales.",
    modelo_version: "v1.0",
    escenarios: [],
  },
];

export function HomePage({ casos, loading, error, onOpenModule }: HomePageProps) {
  const items = casos.length > 0 ? casos : FALLBACK_CASOS;

  return (
    <section>
      <div className="banner">
        <strong>Contexto Académico:</strong> Plataforma de simulación numérica inspirada en{" "}
        <em>Mi Teleférico</em> (La Paz, Bolivia). Todos los modelos, parámetros y escenarios son
        sintéticos con fines educativos.
      </div>

      {error && (
        <div className="error-box">
          No se pudo consultar <code>/api/casos</code>: {error}. Mostrando tarjetas base.
        </div>
      )}

      {loading ? (
        <p style={{ color: "var(--muted)" }}>Cargando módulos de estudio...</p>
      ) : (
        <div className="grid-cards">
          {items.map((caso) => (
            <ModuleCard
              key={caso.codigo}
              caso={caso}
              onOpen={() => onOpenModule(caso.codigo)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
