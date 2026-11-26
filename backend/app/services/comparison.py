"""Servicio de comparación global 4x3 entre todos los módulos y escenarios."""

from __future__ import annotations

from typing import Any, Literal

from app.services.persistence import execute_module_logic, sanitize_json

ScenarioType = Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]

MODULES_META: list[tuple[str, str]] = [
    ("MOD1_DETENCION", "1. Detención de Emergencia"),
    ("MOD2_DETERIORO", "2. Deterioro Mecánico"),
    ("MOD3_OSCILACIONES", "3. Oscilaciones por Viento"),
    ("MOD4_SENSORES", "4. Reconstrucción de Sensores"),
]

SCENARIOS_ORDER: tuple[ScenarioType, ...] = ("NORMAL", "ESTRES", "MAL_CONDICIONADO")


def _extract_key_metric(caso_codigo: str, ref: dict[str, Any]) -> str:
    if caso_codigo == "MOD1_DETENCION":
        return f"t_det={ref.get('t_det_ref', 0):.3f} s · x_det={ref.get('x_det_ref', 0):.3f} m"
    if caso_codigo == "MOD2_DETERIORO":
        return (
            f"κ₂={ref.get('kappa_2', 0):.2e} · Amp={ref.get('amplification_factor', 0):.2f}× · "
            f"t*={ref.get('t_umbral_analitico', 0):.2f} m"
        )
    if caso_codigo == "MOD3_OSCILACIONES":
        return (
            f"amp_max={ref.get('amplitud_max_ref', 0):.4f} m · "
            f"E={ref.get('energia_acumulada_ref', 0):.3e}"
        )
    if caso_codigo == "MOD4_SENSORES":
        return (
            f"RMSE Lag={ref.get('rmse_lagrange', 0):.2e} · "
            f"Spline={ref.get('rmse_spline', 0):.2e}"
        )
    return ""


def build_global_comparison() -> dict[str, Any]:
    """Ejecuta y consolida la matriz comparativa 4x3 de todos los módulos y escenarios."""
    filas: list[dict[str, Any]] = []

    # Series para los 2 gráficos globales (eje X = índice de módulo 1..4)
    chart_err_series: dict[str, list[float]] = {esc: [] for esc in SCENARIOS_ORDER}
    chart_time_series: dict[str, list[float]] = {esc: [] for esc in SCENARIOS_ORDER}

    for mod_idx, (codigo, nombre) in enumerate(MODULES_META, start=1):
        for esc in SCENARIOS_ORDER:
            res = execute_module_logic(codigo, esc)
            metodos = res["metodos"]
            convergentes = [m for m in metodos if m["convergio"]]
            advertencias = [m for m in metodos if not m["convergio"]]

            valid_errors = [
                m for m in convergentes if m.get("error_abs") is not None
            ]
            if valid_errors:
                mejor = min(valid_errors, key=lambda m: float(m["error_abs"]))
            elif convergentes:
                mejor = convergentes[0]
            else:
                mejor = metodos[0]

            if advertencias:
                alerta_txt = ", ".join(m["metodo"] for m in advertencias) + " (no convergió)"
            else:
                with_err = [m for m in metodos if m.get("error_abs") is not None]
                peor = max(with_err, key=lambda m: float(m["error_abs"])) if with_err else metodos[-1]
                e_peor = peor.get("error_abs")
                alerta_txt = (
                    f"{peor['metodo']} (E_abs={e_peor:.2e})"
                    if e_peor is not None
                    else peor["metodo"]
                )

            tiempo_total = sum(float(m["tiempo_ms"]) for m in metodos)
            best_err = mejor.get("error_abs")
            chart_err_series[esc].append(
                max(float(best_err), 1e-16) if best_err is not None else 1e-16
            )
            chart_time_series[esc].append(round(tiempo_total, 4))

            filas.append(
                {
                    "modulo_index": mod_idx,
                    "caso_codigo": codigo,
                    "modulo_nombre": nombre,
                    "escenario": esc,
                    "nombre_descriptivo": res["nombre_descriptivo"],
                    "total_metodos": len(metodos),
                    "metodos_convergentes": len(convergentes),
                    "metodos_advertencia": len(advertencias),
                    "mejor_metodo": mejor["metodo"],
                    "mejor_error_abs": mejor.get("error_abs"),
                    "mejor_error_rel": mejor.get("error_rel"),
                    "alerta_o_mayor_error": alerta_txt,
                    "tiempo_total_ms": tiempo_total,
                    "metrica_clave": _extract_key_metric(codigo, res["referencia"]),
                    "interpretacion_numerica": res["interpretacion_numerica"],
                    "interpretacion_problema": res["interpretacion_problema"],
                }
            )

    x_mods = [1, 2, 3, 4]
    graficos = [
        {
            "id": "global_precision",
            "titulo": "Mejor Error Absoluto por Módulo (1–4) y Escenario (Escala Log)",
            "x_label": "Módulo (1: Detención, 2: Deterioro, 3: Viento, 4: Sensores)",
            "y_label": "Menor Error Absoluto",
            "y_scale": "log",
            "series": [
                {
                    "name": esc,
                    "x": x_mods,
                    "y": chart_err_series[esc],
                    "mode": "line",
                }
                for esc in SCENARIOS_ORDER
            ],
        },
        {
            "id": "global_tiempos",
            "titulo": "Tiempo Total de Ejecución por Módulo (1–4) [ms]",
            "x_label": "Módulo (1: Detención, 2: Deterioro, 3: Viento, 4: Sensores)",
            "y_label": "Tiempo Total [ms]",
            "y_scale": "linear",
            "series": [
                {
                    "name": esc,
                    "x": x_mods,
                    "y": chart_time_series[esc],
                    "mode": "line",
                }
                for esc in SCENARIOS_ORDER
            ],
        },
    ]

    return sanitize_json(
        {
            "total_modulos": len(MODULES_META),
            "total_escenarios": len(filas),
            "filas": filas,
            "graficos": graficos,
        }
    )
