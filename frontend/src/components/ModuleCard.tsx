import type { CasoEstudio } from "../services/api";

interface ModuleCardProps {
  caso: CasoEstudio;
  onOpen: () => void;
}

export function ModuleCard({ caso, onOpen }: ModuleCardProps) {
  return (
    <article className="card card-active">
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.5rem",
          }}
        >
          <span className="metric-label">{caso.codigo}</span>
          <span className="badge badge-ok">Activo (Semana 2)</span>
        </div>
        <h3>{caso.nombre}</h3>
        <p style={{ marginTop: "0.45rem" }}>{caso.descripcion}</p>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "0.5rem",
        }}
      >
        <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
          {caso.escenarios.length > 0 ? `${caso.escenarios.length} escenarios (3×)` : "3 escenarios"}
        </span>
        <button className="btn btn-primary" onClick={onOpen}>
          Abrir Módulo
        </button>
      </div>
    </article>
  );
}
