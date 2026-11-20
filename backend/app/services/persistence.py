"""Servicio unificado de ejecución y persistencia de simulaciones.

Guarda cada simulación completa (parámetros, métodos, iteraciones, métricas
de error, gráficos y conclusiones dobles) en PostgreSQL/SQLite y permite
recuperarla o relanzarla tras reiniciar la aplicación.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from sqlalchemy.orm import Session, selectinload

from app.models.db_models import (
    CasoEstudio,
    EjecucionMetodo,
    Escenario,
    IteracionResultado,
    ResultadoResumen,
    Simulacion,
)
from app.modules.modulo1 import run_modulo1
from app.modules.modulo2 import run_modulo2
from app.modules.modulo3 import run_modulo3
from app.modules.modulo4 import run_modulo4

ScenarioType = Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]
CasoCodigo = Literal["MOD1_DETENCION", "MOD2_DETERIORO", "MOD3_OSCILACIONES", "MOD4_SENSORES"]


def sanitize_json(obj: Any) -> Any:
    """Convierte NaN/Inf y tipos numpy a valores compatibles con JSON estricto."""
    if isinstance(obj, dict):
        return {str(k): sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_json(v) for v in obj]
    if isinstance(obj, float):
        if not math.isfinite(obj):
            return None
        return obj
    if hasattr(obj, "item"):
        return sanitize_json(obj.item())
    return obj


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    f = float(val)
    return f if math.isfinite(f) else None


def execute_module_logic(
    caso_codigo: str,
    escenario_tipo: ScenarioType,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Despacha la ejecución matemática del módulo correspondiente."""
    if caso_codigo == "MOD1_DETENCION":
        return sanitize_json(run_modulo1(escenario_tipo, overrides=overrides))
    if caso_codigo == "MOD2_DETERIORO":
        return sanitize_json(run_modulo2(escenario_tipo, overrides=overrides))
    if caso_codigo == "MOD3_OSCILACIONES":
        return sanitize_json(run_modulo3(escenario_tipo, overrides=overrides))
    if caso_codigo == "MOD4_SENSORES":
        return sanitize_json(run_modulo4(escenario_tipo, overrides=overrides))
    raise ValueError(f"Código de módulo desconocido: {caso_codigo}")


def execute_and_persist_simulation(
    db: Session,
    caso_codigo: str,
    escenario_tipo: ScenarioType,
    parametros_override: dict[str, Any] | None = None,
    usuario_equipo: str = "Equipo_SIMTELE",
    notas_usuario: str | None = None,
) -> dict[str, Any]:
    """Ejecuta un módulo y persiste toda la corrida en la base de datos."""
    caso = db.query(CasoEstudio).filter(CasoEstudio.codigo == caso_codigo).first()
    if caso is None:
        raise ValueError(f"No existe el caso de estudio {caso_codigo} en la base de datos.")

    escenario = (
        db.query(Escenario)
        .filter(Escenario.caso_id == caso.id, Escenario.tipo == escenario_tipo)
        .first()
    )
    if escenario is None:
        raise ValueError(f"No existe el escenario {escenario_tipo} para {caso_codigo}.")

    result = execute_module_logic(caso_codigo, escenario_tipo, overrides=parametros_override)
    all_converged = all(bool(m["convergio"]) for m in result["metodos"])
    estado = "COMPLETADO" if all_converged else "CON_ADVERTENCIAS"

    sim = Simulacion(
        escenario_id=escenario.id,
        usuario_equipo=usuario_equipo[:100],
        estado=estado,
        parametros_override_json=sanitize_json(result["parametros_usados"]),
        notas_usuario=notas_usuario,
    )
    db.add(sim)
    db.flush()

    tipo_ref = str(result["referencia"].get("tipo", "ANALITICA"))
    if tipo_ref not in ("ANALITICA", "NUMERICA_ALTA_PRECISION"):
        tipo_ref = "ANALITICA"

    tol_val = _safe_float(result["parametros_usados"].get("tol"))
    paso_val = _safe_float(result["parametros_usados"].get("h"))
    max_iter_val = result["parametros_usados"].get("max_iter")

    for idx, m in enumerate(result["metodos"]):
        ejec = EjecucionMetodo(
            simulacion_id=sim.id,
            familia_metodo=str(m["familia"])[:30],
            metodo=str(m["metodo"])[:60],
            tolerancia=tol_val,
            paso=paso_val,
            max_iter=int(max_iter_val) if max_iter_val is not None else None,
            iteraciones_realizadas=int(m["iteraciones_realizadas"]),
            convergio=bool(m["convergio"]),
            motivo_parada=str(m["motivo_parada"])[:150],
            tiempo_ms=max(float(m["tiempo_ms"]), 0.0),
        )
        db.add(ejec)
        db.flush()

        for row_idx, row in enumerate(m.get("detalle_tabla", []), start=1):
            num = int(row.get("paso", row.get("numero", row_idx)))
            db.add(
                IteracionResultado(
                    ejecucion_id=ejec.id,
                    numero=num,
                    aproximacion_json=sanitize_json(row),
                    residual=_safe_float(row.get("residual")),
                    error_abs=_safe_float(row.get("error_abs")),
                    error_rel=_safe_float(row.get("error_rel")),
                    error_porcentual=_safe_float(row.get("error_pct")),
                )
            )

        valor_payload: dict[str, Any] = {
            "valor_principal": _safe_float(m.get("valor_principal")),
            "etiqueta_valor": m.get("etiqueta_valor"),
        }
        if idx == 0:
            valor_payload["graficos"] = result["graficos"]
            valor_payload["referencia_completa"] = result["referencia"]
            valor_payload["nombre_descriptivo"] = result["nombre_descriptivo"]

        db.add(
            ResultadoResumen(
                ejecucion_id=ejec.id,
                referencia=_safe_float(m.get("valor_principal")),
                tipo_referencia=tipo_ref,
                valor_json=sanitize_json(valor_payload),
                metrica_error_json=sanitize_json(
                    {
                        "residual": _safe_float(m.get("residual")),
                        "error_abs": _safe_float(m.get("error_abs")),
                        "error_rel": _safe_float(m.get("error_rel")),
                        "error_pct": _safe_float(m.get("error_pct")),
                    }
                ),
                interpretacion_numerica=str(result["interpretacion_numerica"]),
                interpretacion_problema=str(result["interpretacion_problema"]),
            )
        )

    db.commit()
    db.refresh(sim)

    result["simulacion_id"] = sim.id
    result["fecha"] = sim.fecha.isoformat()
    result["estado"] = sim.estado
    return result


def list_saved_simulations(
    db: Session,
    caso_codigo: str | None = None,
    escenario_tipo: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Lista las simulaciones guardadas ordenadas de más reciente a más antigua."""
    query = (
        db.query(Simulacion)
        .join(Simulacion.escenario)
        .join(Escenario.caso)
        .options(
            selectinload(Simulacion.escenario).selectinload(Escenario.caso),
            selectinload(Simulacion.ejecuciones),
        )
        .order_by(Simulacion.fecha.desc(), Simulacion.id.desc())
    )
    if caso_codigo:
        query = query.filter(CasoEstudio.codigo == caso_codigo)
    if escenario_tipo:
        query = query.filter(Escenario.tipo == escenario_tipo)

    sims = query.limit(limit).all()
    items: list[dict[str, Any]] = []
    for sim in sims:
        items.append(
            {
                "simulacion_id": sim.id,
                "fecha": sim.fecha.isoformat(),
                "usuario_equipo": sim.usuario_equipo,
                "estado": sim.estado,
                "caso_codigo": sim.escenario.caso.codigo,
                "caso_nombre": sim.escenario.caso.nombre,
                "escenario": sim.escenario.tipo,
                "nombre_descriptivo": sim.escenario.nombre_descriptivo,
                "parametros_usados": sim.parametros_override_json or sim.escenario.parametros_json,
                "total_metodos": len(sim.ejecuciones),
                "notas_usuario": sim.notas_usuario,
            }
        )
    return items


def get_saved_simulation(db: Session, simulacion_id: int) -> dict[str, Any]:
    """Recupera una simulación completa desde la base de datos por su ID."""
    sim = (
        db.query(Simulacion)
        .options(
            selectinload(Simulacion.escenario).selectinload(Escenario.caso),
            selectinload(Simulacion.ejecuciones).selectinload(EjecucionMetodo.iteraciones),
            selectinload(Simulacion.ejecuciones).selectinload(EjecucionMetodo.resumen),
        )
        .filter(Simulacion.id == simulacion_id)
        .first()
    )
    if sim is None:
        raise KeyError(f"Simulación {simulacion_id} no encontrada.")

    metodos: list[dict[str, Any]] = []
    graficos: list[dict[str, Any]] = []
    referencia: dict[str, Any] = {}
    nombre_desc = sim.escenario.nombre_descriptivo
    interp_num = ""
    interp_prob = ""

    sorted_execs = sorted(sim.ejecuciones, key=lambda e: e.id)
    for ejec in sorted_execs:
        resumen = ejec.resumen
        err_json = resumen.metrica_error_json if resumen else {}
        val_json = resumen.valor_json if resumen else {}

        if "graficos" in val_json and not graficos:
            graficos = val_json["graficos"]
        if "referencia_completa" in val_json and not referencia:
            referencia = val_json["referencia_completa"]
        if "nombre_descriptivo" in val_json:
            nombre_desc = val_json["nombre_descriptivo"]
        if resumen:
            interp_num = resumen.interpretacion_numerica
            interp_prob = resumen.interpretacion_problema

        sorted_iters = sorted(ejec.iteraciones, key=lambda it: it.numero)
        metodos.append(
            {
                "familia": ejec.familia_metodo,
                "metodo": ejec.metodo,
                "convergio": ejec.convergio,
                "iteraciones_realizadas": ejec.iteraciones_realizadas,
                "tiempo_ms": ejec.tiempo_ms,
                "valor_principal": val_json.get("valor_principal"),
                "etiqueta_valor": val_json.get("etiqueta_valor", ""),
                "residual": err_json.get("residual"),
                "error_abs": err_json.get("error_abs"),
                "error_rel": err_json.get("error_rel"),
                "error_pct": err_json.get("error_pct"),
                "motivo_parada": ejec.motivo_parada or "",
                "detalle_tabla": [it.aproximacion_json for it in sorted_iters],
            }
        )

    return {
        "simulacion_id": sim.id,
        "fecha": sim.fecha.isoformat(),
        "estado": sim.estado,
        "usuario_equipo": sim.usuario_equipo,
        "caso_codigo": sim.escenario.caso.codigo,
        "escenario": sim.escenario.tipo,
        "nombre_descriptivo": nombre_desc,
        "parametros_usados": sim.parametros_override_json or sim.escenario.parametros_json,
        "referencia": referencia,
        "metodos": metodos,
        "graficos": graficos,
        "interpretacion_numerica": interp_num,
        "interpretacion_problema": interp_prob,
    }


def rerun_saved_simulation(db: Session, simulacion_id: int) -> dict[str, Any]:
    """Relanza una simulación guardada con sus parámetros y compara contra la original."""
    original = get_saved_simulation(db, simulacion_id)
    nueva = execute_and_persist_simulation(
        db=db,
        caso_codigo=original["caso_codigo"],
        escenario_tipo=original["escenario"],
        parametros_override=original["parametros_usados"],
        usuario_equipo=original.get("usuario_equipo", "Equipo_SIMTELE"),
        notas_usuario=f"Relanzamiento de verificación de simulación #{simulacion_id}",
    )

    comparacion: list[dict[str, Any]] = []
    max_diff = 0.0
    for m_orig, m_new in zip(original["metodos"], nueva["metodos"]):
        v1 = m_orig.get("valor_principal")
        v2 = m_new.get("valor_principal")
        diff = abs(float(v1) - float(v2)) if (v1 is not None and v2 is not None) else 0.0
        max_diff = max(max_diff, diff)
        comparacion.append(
            {
                "metodo": m_orig["metodo"],
                "valor_original": v1,
                "valor_relanzado": v2,
                "diferencia_abs": diff,
                "coincide_en_tolerancia": diff <= 1e-12,
            }
        )

    return {
        "simulacion_original_id": simulacion_id,
        "simulacion_nueva": nueva,
        "diferencia_maxima": max_diff,
        "coincidencia_exacta": max_diff <= 1e-12,
        "comparacion_metodos": comparacion,
    }
