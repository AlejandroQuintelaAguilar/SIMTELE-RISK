"""Módulo 1: Detención de Emergencia de Cabinas.

Modelado cinemático y dinámico mediante EDO (RK2 Heun, RK4),
integración de velocidad (Trapecio, Simpson 1/3, Romberg) y búsqueda de
instante de detención v(t) = 0 (Bisección, Newton-Raphson, Secante).
"""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np

from app.core.error_metrics import FloatArray, absolute_error, percentage_error, relative_error
from app.numerical.integration import composite_simpson_13, composite_trapezoid, romberg_integrate
from app.numerical.ode import rk2_heun_solve, rk4_solve
from app.numerical.roots import (
    RootFindingError,
    RootResult,
    bisection_solve,
    newton_raphson_solve,
    secant_solve,
)

ScenarioType = Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]


def _default_params(tipo: ScenarioType) -> dict[str, Any]:
    if tipo == "NORMAL":
        return {
            "v0": 6.0,
            "x0": 0.0,
            "a0": 1.2,
            "kd": 0.0,
            "h": 0.05,
            "t_max": 10.0,
            "tol": 1e-8,
            "modelo": "lineal_o_arrastre",
        }
    if tipo == "ESTRES":
        return {
            "v0": 8.5,
            "x0": 0.0,
            "a0": 0.75,
            "kd": 0.02,
            "h": 0.4,
            "t_max": 15.0,
            "tol": 1e-8,
            "modelo": "lineal_o_arrastre",
        }
    if tipo == "MAL_CONDICIONADO":
        return {
            "v0": 6.0,
            "x0": 0.0,
            "a0": 1.2,
            "kd": 0.0,
            "t_det_objetivo": 5.0,
            "h": 0.05,
            "tol": 1e-10,
            "modelo": "asintotico_tangencial",
        }
    raise ValueError(f"Escenario no reconocido: {tipo}")


def run_modulo1(
    tipo: ScenarioType,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta el Módulo 1 completo para el escenario y parámetros indicados."""
    params = _default_params(tipo)
    if overrides:
        for k, v in overrides.items():
            if v is not None and k in params:
                params[k] = v

    v0 = float(params["v0"])
    x0 = float(params["x0"])
    h = float(params["h"])
    tol = float(params["tol"])
    modelo = str(params.get("modelo", "lineal_o_arrastre"))

    if v0 <= 0.0:
        raise ValueError("La velocidad inicial v0 debe ser positiva (> 0).")
    if h <= 0.0:
        raise ValueError("El paso temporal h debe ser positivo (> 0).")

    if modelo == "asintotico_tangencial":
        t_det_ref = float(params.get("t_det_objetivo", 5.0))
        if t_det_ref <= 0.0:
            raise ValueError("t_det_objetivo debe ser positivo.")
        x_det_ref = x0 + (v0 * t_det_ref) / 3.0

        def v_exact(t: float) -> float:
            ratio = max(0.0, 1.0 - t / t_det_ref) if t <= t_det_ref else (1.0 - t / t_det_ref)
            return v0 * (ratio**2)

        def dv_dt_fn(t: float) -> float:
            return -2.0 * v0 * (1.0 - t / t_det_ref) / t_det_ref

        def x_exact(t: float) -> float:
            u = 1.0 - t / t_det_ref
            return x0 + (v0 * t_det_ref / 3.0) * (1.0 - u**3)

        def ode_rhs(t: float, y: FloatArray) -> FloatArray:
            vel = max(float(y[1]), 0.0)
            dv = -2.0 * math.sqrt(v0 * vel) / t_det_ref if t <= t_det_ref else 0.0
            return np.array([float(y[1]), dv], dtype=np.float64)

        def ref_vec(t: float) -> FloatArray:
            return np.array([x_exact(t), v_exact(t)], dtype=np.float64)

    else:
        a0 = float(params["a0"])
        kd = float(params["kd"])
        if a0 <= 0.0 or kd < 0.0:
            raise ValueError("Se requiere a0 > 0 y kd >= 0.")

        if kd == 0.0:
            t_det_ref = v0 / a0
            x_det_ref = x0 + (v0**2) / (2.0 * a0)

            def v_exact(t: float) -> float:
                return v0 - a0 * t

            def dv_dt_fn(t: float) -> float:
                return -a0

            def x_exact(t: float) -> float:
                return x0 + v0 * t - 0.5 * a0 * (t**2)
        else:
            t_det_ref = math.log(1.0 + (kd * v0) / a0) / kd
            c_const = v0 + a0 / kd
            x_det_ref = x0 + (c_const / kd) * (1.0 - math.exp(-kd * t_det_ref)) - (a0 / kd) * t_det_ref

            def v_exact(t: float) -> float:
                return c_const * math.exp(-kd * t) - a0 / kd

            def dv_dt_fn(t: float) -> float:
                return -kd * c_const * math.exp(-kd * t)

            def x_exact(t: float) -> float:
                return x0 + (c_const / kd) * (1.0 - math.exp(-kd * t)) - (a0 / kd) * t

        def ode_rhs(t: float, y: FloatArray) -> FloatArray:
            return np.array([float(y[1]), -(a0 + kd * float(y[1]))], dtype=np.float64)

        def ref_vec(t: float) -> FloatArray:
            return np.array([x_exact(t), v_exact(t)], dtype=np.float64)

    # 1. EDO: RK2 (Heun) y RK4 sobre [0, t_det_ref]
    y0_vec = np.array([x0, v0], dtype=np.float64)
    res_rk2 = rk2_heun_solve(ode_rhs, 0.0, t_det_ref, y0_vec, h=h, ref_fn=ref_vec)
    res_rk4 = rk4_solve(ode_rhs, 0.0, t_det_ref, y0_vec, h=h, ref_fn=ref_vec)

    # 2. Integración de v(t) en [0, t_det_ref] para distancia de frenado (x_det - x0)
    dist_ref = x_det_ref - x0
    res_trap = composite_trapezoid(v_exact, 0.0, t_det_ref, [4, 8, 16, 32, 64], ref_value=dist_ref)
    res_simp = composite_simpson_13(v_exact, 0.0, t_det_ref, [4, 8, 16, 32, 64], ref_value=dist_ref)
    res_romb = romberg_integrate(v_exact, 0.0, t_det_ref, max_levels=6, tol=tol, ref_value=dist_ref)

    # 3. Raíces para v(t) = 0
    bracket_hi = max(t_det_ref * 1.4, 2.0)
    try:
        res_bis: RootResult = bisection_solve(v_exact, 0.0, bracket_hi, tol=tol, max_iter=120, x_ref=t_det_ref)
    except RootFindingError as exc:
        res_bis = RootResult(
            metodo="Bisección",
            familia="RAICES",
            raiz=float("nan"),
            f_raiz=float("nan"),
            convergio=False,
            iteraciones_realizadas=0,
            motivo_parada=f"No aplicable en raíz tangencial sin cambio de signo: {exc}",
            tiempo_ms=0.0,
            residual_final=float("nan"),
            error_abs=None,
            error_rel=None,
            error_pct=None,
            historial=[],
            diagnostics={"intervalo": [0.0, bracket_hi]},
        )

    res_newt = newton_raphson_solve(
        v_exact, dv_dt_fn, x0=0.4 * t_det_ref, tol=tol, max_iter=120, x_ref=t_det_ref
    )
    res_sec = secant_solve(
        v_exact, x0=0.2 * t_det_ref, x1=0.6 * t_det_ref, tol=tol, max_iter=120, x_ref=t_det_ref
    )

    metodos = [
        {
            "familia": "EDO",
            "metodo": res_rk2.metodo,
            "convergio": res_rk2.convergio,
            "iteraciones_realizadas": res_rk2.pasos_realizados,
            "tiempo_ms": res_rk2.tiempo_ms,
            "valor_principal": res_rk2.y_final[0],
            "etiqueta_valor": f"x_det={res_rk2.y_final[0]:.6f} m, v_fin={res_rk2.y_final[1]:.3e} m/s",
            "residual": abs(res_rk2.y_final[1]),
            "error_abs": res_rk2.error_abs_final,
            "error_rel": res_rk2.error_rel_final,
            "error_pct": res_rk2.error_pct_final,
            "motivo_parada": res_rk2.motivo_parada,
            "detalle_tabla": [
                {
                    "paso": s.numero,
                    "t": s.t,
                    "aprox": s.y,
                    "ref": s.y_ref,
                    "error_abs": s.error_abs,
                    "error_rel": s.error_rel,
                }
                for s in res_rk2.historial
            ],
        },
        {
            "familia": "EDO",
            "metodo": res_rk4.metodo,
            "convergio": res_rk4.convergio,
            "iteraciones_realizadas": res_rk4.pasos_realizados,
            "tiempo_ms": res_rk4.tiempo_ms,
            "valor_principal": res_rk4.y_final[0],
            "etiqueta_valor": f"x_det={res_rk4.y_final[0]:.6f} m, v_fin={res_rk4.y_final[1]:.3e} m/s",
            "residual": abs(res_rk4.y_final[1]),
            "error_abs": res_rk4.error_abs_final,
            "error_rel": res_rk4.error_rel_final,
            "error_pct": res_rk4.error_pct_final,
            "motivo_parada": res_rk4.motivo_parada,
            "detalle_tabla": [
                {
                    "paso": s.numero,
                    "t": s.t,
                    "aprox": s.y,
                    "ref": s.y_ref,
                    "error_abs": s.error_abs,
                    "error_rel": s.error_rel,
                }
                for s in res_rk4.historial
            ],
        },
    ]

    for integ in (res_trap, res_simp, res_romb):
        metodos.append(
            {
                "familia": "INTEGRACION",
                "metodo": integ.metodo,
                "convergio": integ.convergio,
                "iteraciones_realizadas": integ.iteraciones_realizadas,
                "tiempo_ms": integ.tiempo_ms,
                "valor_principal": integ.valor,
                "etiqueta_valor": f"distancia={integ.valor:.8f} m",
                "residual": integ.error_abs,
                "error_abs": integ.error_abs,
                "error_rel": integ.error_rel,
                "error_pct": integ.error_pct,
                "motivo_parada": integ.motivo_parada,
                "detalle_tabla": [
                    {
                        "paso": st.numero,
                        "subintervalos": st.subintervalos,
                        "paso_h": st.paso_h,
                        "aprox": st.valor_aprox,
                        "error_abs": st.error_abs,
                        "error_rel": st.error_rel,
                    }
                    for st in integ.refinamiento
                ],
            }
        )

    for root in (res_bis, res_newt, res_sec):
        val_clean = None if not math.isfinite(root.raiz) else root.raiz
        metodos.append(
            {
                "familia": "RAICES",
                "metodo": root.metodo,
                "convergio": root.convergio,
                "iteraciones_realizadas": root.iteraciones_realizadas,
                "tiempo_ms": root.tiempo_ms,
                "valor_principal": val_clean,
                "etiqueta_valor": f"t_det={val_clean:.8f} s" if val_clean is not None else "No bracket",
                "residual": None if not math.isfinite(root.residual_final) else root.residual_final,
                "error_abs": root.error_abs,
                "error_rel": root.error_rel,
                "error_pct": root.error_pct,
                "motivo_parada": root.motivo_parada,
                "detalle_tabla": [
                    {
                        "paso": it.numero,
                        "x": it.x,
                        "f_x": it.f_x,
                        "residual": it.residual,
                        "error_abs": it.error_abs,
                        "error_rel": it.error_rel,
                    }
                    for it in root.historial
                ],
            }
        )

    # Curvas para los 2 gráficos obligatorios
    t_dense = np.linspace(0.0, t_det_ref, 60)
    graficos = [
        {
            "id": "modulo1_cinematica",
            "titulo": "Cinética de Frenado: Velocidad v(t) [m/s]",
            "x_label": "Tiempo t [s]",
            "y_label": "Velocidad v(t) [m/s]",
            "y_scale": "linear",
            "series": [
                {
                    "name": "Referencia Analítica v(t)",
                    "x": [float(t) for t in t_dense],
                    "y": [float(v_exact(float(t))) for t in t_dense],
                    "mode": "line",
                },
                {
                    "name": "RK2 (Heun) v(t)",
                    "x": res_rk2.t_values,
                    "y": [y[1] for y in res_rk2.y_values],
                    "mode": "line",
                },
                {
                    "name": "RK4 (Clásico) v(t)",
                    "x": res_rk4.t_values,
                    "y": [y[1] for y in res_rk4.y_values],
                    "mode": "markers",
                },
            ],
        },
        {
            "id": "modulo1_errores",
            "titulo": "Error Global EDO |y_ref - y_aprox|_2 en el Tiempo",
            "x_label": "Tiempo t [s]",
            "y_label": "Error Absoluto L2",
            "y_scale": "log",
            "series": [
                {
                    "name": "Error RK2 (Heun)",
                    "x": [s.t for s in res_rk2.historial if (s.error_abs or 0.0) > 0.0],
                    "y": [max(s.error_abs or 1e-16, 1e-16) for s in res_rk2.historial if (s.error_abs or 0.0) > 0.0],
                    "mode": "line",
                },
                {
                    "name": "Error RK4 (Clásico)",
                    "x": [s.t for s in res_rk4.historial if (s.error_abs or 0.0) > 0.0],
                    "y": [max(s.error_abs or 1e-16, 1e-16) for s in res_rk4.historial if (s.error_abs or 0.0) > 0.0],
                    "mode": "line",
                },
            ],
        },
    ]

    if tipo == "NORMAL":
        interp_num = (
            f"Con paso h={h} s y desaceleración constante, RK4 alcanza precisión cercana a épsilon de máquina "
            f"(E_abs_final={res_rk4.error_abs_final:.2e}), superando a RK2 (E_abs_final={res_rk2.error_abs_final:.2e}). "
            f"Simpson 1/3 y Romberg integran la distancia exacta ({dist_ref:.6f} m) por ser v(t) lineal."
        )
        interp_prob = (
            f"En operación nominal (v0={v0} m/s, a0={params['a0']} m/s^2), la cabina se detiene en "
            f"t_det={t_det_ref:.2f} s recorriendo {x_det_ref:.2f} m; permite validar márgenes de entrada a estación."
        )
    elif tipo == "ESTRES":
        interp_num = (
            f"El paso grueso h={h} s amplifica el error de truncamiento local en RK2 (E_abs={res_rk2.error_abs_final:.2e}) "
            f"frente a RK4 (E_abs={res_rk4.error_abs_final:.2e}). Para v(t) exponencial, Romberg y Simpson convergen "
            f"rápidamente al valor analítico {dist_ref:.6f} m."
        )
        interp_prob = (
            f"Bajo carga máxima y menor desaceleración efectiva, la distancia de frenado aumenta a {x_det_ref:.2f} m "
            f"en {t_det_ref:.2f} s; no pueden inferirse cargas estructurales reales de pinzas sin datos de campo."
        )
    else:
        interp_num = (
            f"Experimento de raíz múltiple donde v(t_det)=0 y v'(t_det)=0: Bisección falla por ausencia de cambio de signo, "
            f"mientras Newton-Raphson pierde convergencia cuadrática (requiere {res_newt.iteraciones_realizadas} iteraciones "
            f"y detiene por derivada pequeña)."
        )
        interp_prob = (
            "Modela un frenado suave asintótico donde el instante exacto de detención es altamente sensible a tolerancias "
            "del sensor de velocidad nula."
        )

    return {
        "caso_codigo": "MOD1_DETENCION",
        "escenario": tipo,
        "nombre_descriptivo": {
            "NORMAL": "Frenado nominal en tramo recto",
            "ESTRES": "Carga máxima, pendiente descendente y paso grueso",
            "MAL_CONDICIONADO": "Frenado asintótico con raíz múltiple (derivada nula)",
        }[tipo],
        "parametros_usados": params,
        "referencia": {
            "tipo": "ANALITICA",
            "t_det_ref": t_det_ref,
            "x_det_ref": x_det_ref,
            "distancia_frenado_ref": dist_ref,
            "error_dist_rk4_abs": absolute_error(x_det_ref, res_rk4.y_final[0]),
            "error_dist_rk4_rel": relative_error(x_det_ref, res_rk4.y_final[0]),
            "error_dist_rk4_pct": percentage_error(x_det_ref, res_rk4.y_final[0]),
        },
        "metodos": metodos,
        "graficos": graficos,
        "interpretacion_numerica": interp_num,
        "interpretacion_problema": interp_prob,
    }
