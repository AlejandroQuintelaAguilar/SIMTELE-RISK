"""Módulo 2 completo: Deterioro Mecánico y Mantenimiento.

Combina:
- Sistemas lineales SPD (Jacobi, Gauss-Seidel, LU pivoteo parcial, Gradiente Conjugado) + sensibilidad
- Búsqueda de raíces (Bisección, Newton-Raphson, Secante) para D(t) - D_umbral = 0
- Dos gráficos comparativos (evolución D(t) y convergencia de residuales lineales)
"""

from __future__ import annotations

from dataclasses import asdict
import math
from typing import Any, Literal

import numpy as np

from app.modules.modulo2_s1 import run_modulo2_scenario
from app.numerical.roots import bisection_solve, newton_raphson_solve, secant_solve

ScenarioType = Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]


def _default_wear_params(tipo: ScenarioType) -> dict[str, Any]:
    if tipo == "NORMAL":
        return {
            "D0": 0.12,
            "alpha": 0.015,
            "beta": 0.0008,
            "D_umbral": 0.80,
            "tol": 1e-8,
            "max_iter": 500,
        }
    if tipo == "ESTRES":
        return {
            "D0": 0.25,
            "alpha": 0.028,
            "beta": 0.0019,
            "D_umbral": 0.85,
            "tol": 1e-11,
            "max_iter": 2000,
        }
    if tipo == "MAL_CONDICIONADO":
        return {
            "D0": 0.12,
            "alpha": 0.015,
            "beta": 0.0008,
            "D_umbral": 0.80,
            "tol": 1e-8,
            "max_iter": 5000,
        }
    raise ValueError(f"Escenario no reconocido: {tipo}")


def run_modulo2(
    tipo: ScenarioType,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta el Módulo 2 completo (Sistemas Lineales + Raíces de Desgaste)."""
    wear_params = _default_wear_params(tipo)
    if overrides:
        for k, v in overrides.items():
            if v is not None and k in wear_params:
                wear_params[k] = v

    tol = float(wear_params["tol"])
    max_iter = int(wear_params["max_iter"])
    d0 = float(wear_params["D0"])
    alpha = float(wear_params["alpha"])
    beta = float(wear_params["beta"])
    d_umbral = float(wear_params["D_umbral"])

    if beta <= 0.0 or alpha < 0.0:
        raise ValueError("Se requiere alpha >= 0 y beta > 0 en el modelo polinómico D(t).")
    if d0 >= d_umbral:
        raise ValueError("El desgaste inicial D0 debe ser menor que D_umbral.")

    # 1. Sistemas lineales (Semana 1)
    lin_report = run_modulo2_scenario(tipo, tol=tol, max_iter=max_iter)

    # 2. Raíces sobre D(t) - D_umbral = 0 (Semana 2)
    disc = alpha**2 - 4.0 * beta * (d0 - d_umbral)
    if disc < 0.0:
        raise ValueError("El modelo cuadrático no posee raíz real positiva para alcanzar D_umbral.")
    t_star = (-alpha + math.sqrt(disc)) / (2.0 * beta)

    def f_wear(t: float) -> float:
        return d0 + alpha * t + beta * (t**2) - d_umbral

    def df_wear(t: float) -> float:
        return alpha + 2.0 * beta * t

    hi_bracket = max(t_star * 1.6, 5.0)
    res_bis = bisection_solve(f_wear, 0.0, hi_bracket, tol=tol, max_iter=150, x_ref=t_star)
    res_newt = newton_raphson_solve(f_wear, df_wear, x0=max(t_star * 0.5, 1.0), tol=tol, max_iter=150, x_ref=t_star)
    res_sec = secant_solve(f_wear, x0=0.0, x1=max(t_star * 0.6, 1.5), tol=tol, max_iter=150, x_ref=t_star)

    metodos: list[dict[str, Any]] = []
    for m in lin_report.resultados_metodos:
        metodos.append(
            {
                "familia": "SISTEMAS_LINEALES",
                "metodo": m.metodo,
                "convergio": m.convergio,
                "iteraciones_realizadas": m.iteraciones_realizadas,
                "tiempo_ms": m.tiempo_ms,
                "valor_principal": float(np.linalg.norm(m.x, ord=2)),
                "etiqueta_valor": f"||x||_2={float(np.linalg.norm(m.x, ord=2)):.6f}",
                "residual": m.residual_final,
                "error_abs": m.error_abs,
                "error_rel": m.error_rel,
                "error_pct": m.error_pct,
                "motivo_parada": m.motivo_parada,
                "detalle_tabla": [asdict(it) for it in m.historial[:50]],
            }
        )

    for r in (res_bis, res_newt, res_sec):
        metodos.append(
            {
                "familia": "RAICES",
                "metodo": f"{r.metodo} (Desgaste)",
                "convergio": r.convergio,
                "iteraciones_realizadas": r.iteraciones_realizadas,
                "tiempo_ms": r.tiempo_ms,
                "valor_principal": r.raiz,
                "etiqueta_valor": f"t*={r.raiz:.6f} meses",
                "residual": r.residual_final,
                "error_abs": r.error_abs,
                "error_rel": r.error_rel,
                "error_pct": r.error_pct,
                "motivo_parada": r.motivo_parada,
                "detalle_tabla": [asdict(it) for it in r.historial],
            }
        )

    # 3. Dos gráficos obligatorios
    t_grid = np.linspace(0.0, max(t_star * 1.25, 10.0), 50)
    d_grid = [float(d0 + alpha * float(t) + beta * (float(t) ** 2)) for t in t_grid]
    umbral_line = [d_umbral for _ in t_grid]

    conv_series = []
    for m in lin_report.resultados_metodos:
        if len(m.historial) > 1:
            conv_series.append(
                {
                    "name": m.metodo,
                    "x": [it.numero for it in m.historial[:60]],
                    "y": [max(min(it.residual, 1e10), 1e-16) for it in m.historial[:60]],
                    "mode": "line",
                }
            )

    graficos = [
        {
            "id": "modulo2_desgaste",
            "titulo": "Evolución de Deterioro D(t) y Cruce de Umbral Crítico",
            "x_label": "Tiempo t [meses]",
            "y_label": "Índice de Desgaste D(t)",
            "y_scale": "linear",
            "series": [
                {
                    "name": "Curva D(t)",
                    "x": [float(t) for t in t_grid],
                    "y": d_grid,
                    "mode": "line",
                },
                {
                    "name": f"Umbral D_umbral = {d_umbral}",
                    "x": [float(t) for t in t_grid],
                    "y": umbral_line,
                    "mode": "line",
                },
                {
                    "name": f"Tiempo Crítico t* = {t_star:.2f} meses",
                    "x": [t_star],
                    "y": [d_umbral],
                    "mode": "markers",
                },
            ],
        },
        {
            "id": "modulo2_convergencia",
            "titulo": "Convergencia del Residual ||b - Ax^(k)||_2 (Sistemas Lineales)",
            "x_label": "Iteración k",
            "y_label": "Norma del Residual",
            "y_scale": "log",
            "series": conv_series,
        },
    ]

    interp_num = (
        f"{lin_report.interpretacion_numerica} En búsqueda de raíces de D(t)-D_umbral=0 "
        f"(t*={t_star:.6f} meses), Newton-Raphson converge en {res_newt.iteraciones_realizadas} "
        f"iteraciones frente a {res_bis.iteraciones_realizadas} de Bisección."
    )
    interp_prob = (
        f"{lin_report.interpretacion_problema} Bajo los parámetros actuales (D0={d0}, alpha={alpha}, "
        f"beta={beta}), el umbral de inspección ({d_umbral}) se alcanzaría a los {t_star:.2f} meses."
    )

    return {
        "caso_codigo": "MOD2_DETERIORO",
        "escenario": tipo,
        "nombre_descriptivo": lin_report.nombre_descriptivo,
        "parametros_usados": {
            **wear_params,
            "dimension_n": lin_report.dimension_n,
        },
        "referencia": {
            "tipo": "ANALITICA",
            "kappa_2": lin_report.kappa_2,
            "amplification_factor": lin_report.sensibilidad.amplification_factor,
            "t_umbral_analitico": t_star,
            "x_referencia_norm": float(np.linalg.norm(lin_report.x_referencia, ord=2)),
        },
        "metodos": metodos,
        "graficos": graficos,
        "interpretacion_numerica": interp_num,
        "interpretacion_problema": interp_prob,
    }
