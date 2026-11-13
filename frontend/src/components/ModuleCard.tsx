import type { CasoEstudio } from "../services/api";

interface ModuleCardProps {
  caso: CasoEstudio;
  isActive: boolean;
  onOpen: () => void;
}

export function ModuleCard({ caso, isActive, onOpen }: ModuleCardProps) {
  return (
    <article className={`card ${isActive ? "card-active" : ""}`}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
          <span className="metric-label">{caso.codigo}</span>
          <span className={`badge ${isActive ? "badge-ok" : "badge-pending"}`}>
            {isActive ? "Activo (Semana 1)" : "Semana 2"}
          </span>
        </div>
        <h3>{caso.nombre}</h3>
        <p style={{ marginTop: "0.45rem" }}>{caso.descripcion}</p>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem" }}>
        <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
          {caso.escenarios.length} escenarios (3×)
        </span>
        <button
          className={`btn ${isActive ? "btn-primary" : ""}`}
          disabled={!isActive}
          onClick={onOpen}
        >
          {isActive ? "Abrir Módulo" : "Próximamente"}
        </button>
      </div>
    </article>
  );
}
