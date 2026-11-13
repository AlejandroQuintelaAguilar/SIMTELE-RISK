"""Endpoints REST de la Semana 1 para SIMTELE-RISK."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import active_db_backend, get_db
from app.models.db_models import CasoEstudio
from app.models.schemas import (
    CasoEstudioOut,
    HealthOut,
    IterationOut,
    MethodResultOut,
    Modulo2ExecuteRequest,
    Modulo2ExecuteResponse,
    SensitivityOut,
)
from app.modules.modulo2_s1 import run_modulo2_scenario

router = APIRouter(prefix="/api", tags=["SIMTELE-RISK"])


@router.get("/health", response_model=HealthOut)
def health_check() -> HealthOut:
    """Verifica el estado operativo de la API y el motor de base de datos."""
    return HealthOut(
        status="ok",
        version=settings.app_version,
        database_backend=active_db_backend,
    )


@router.get("/casos", response_model=list[CasoEstudioOut])
def listar_casos_estudio(db: Session = Depends(get_db)) -> list[CasoEstudioOut]:
    """Retorna los 4 módulos de estudio y sus escenarios desde la base de datos."""
    casos = (
        db.query(CasoEstudio)
        .options(selectinload(CasoEstudio.escenarios))
        .order_by(CasoEstudio.id.asc())
        .all()
    )
    return [CasoEstudioOut.model_validate(c) for c in casos]


@router.post("/modulo2/sistemas-lineales/ejecutar", response_model=Modulo2ExecuteResponse)
def ejecutar_modulo2_sistemas_lineales(
    payload: Modulo2ExecuteRequest,
) -> Modulo2ExecuteResponse:
    """Ejecuta los 4 solvers lineales del Módulo 2 en el escenario seleccionado."""
    try:
        report = run_modulo2_scenario(
            tipo=payload.escenario,
            tol=payload.tol,
            max_iter=payload.max_iter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    metodos_out = [
        MethodResultOut(
            metodo=m.metodo,
            familia=m.familia,
            convergio=m.convergio,
            iteraciones_realizadas=m.iteraciones_realizadas,
            motivo_parada=m.motivo_parada,
            tiempo_ms=m.tiempo_ms,
            residual_final=m.residual_final,
            residual_rel_final=m.residual_rel_final,
            error_abs=m.error_abs,
            error_rel=m.error_rel,
            error_pct=m.error_pct,
            x_aprox=[float(val) for val in m.x],
            diagnostics=m.diagnostics,
            historial=[IterationOut(**asdict(it)) for it in m.historial],
        )
        for m in report.resultados_metodos
    ]

    return Modulo2ExecuteResponse(
        escenario=report.escenario,
        nombre_descriptivo=report.nombre_descriptivo,
        dimension_n=report.dimension_n,
        tol=report.tol,
        max_iter=report.max_iter,
        kappa_2=report.kappa_2,
        x_referencia=report.x_referencia,
        sensibilidad=SensitivityOut(**asdict(report.sensibilidad)),
        resultados_metodos=metodos_out,
        interpretacion_numerica=report.interpretacion_numerica,
        interpretacion_problema=report.interpretacion_problema,
    )
