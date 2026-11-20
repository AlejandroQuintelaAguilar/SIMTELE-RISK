"""Módulo 4: Reconstrucción de Señales de Sensores.

Interpolación de telemetría con datos ocultados y ruido mediante:
- Lagrange
- Newton (Diferencias Divididas)
- Splines Cúbicos Naturales
y detección de cruce de umbral sobre el spline reconstruido (Bisección, Newton-Raphson, Secante).
"""

from __future__ import annotations

from dataclasses import asdict
import math
from typing import Any, Callable, Literal

import numpy as np

from app.numerical.interpolation import run_interpolation_comparison
from app.numerical.roots import bisection_solve, newton_raphson_solve, secant_solve

ScenarioType = Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]


def _default_params(tipo: ScenarioType) -> dict[str, Any]:
    if tipo == "NORMAL":
        return {
            "funcion": "sin_t",
            "a": 0.0,
            "b": 2.0 * math.pi,
            "n_nodos": 8,
            "indices_ocultos": [2, 5],
            "ruido_sigma": 0.0,
            "umbral_alerta": 0.75,
        }
    if tipo == "ESTRES":
        return {
            "funcion": "exp_cos",
            "a": 0.0,
            "b": 5.0,
            "n_nodos": 12,
            "indices_ocultos": [3, 4, 7, 8],
            "ruido_sigma": 0.04,
            "umbral_alerta": 0.50,
        }
    if tipo == "MAL_CONDICIONADO":
        return {
            "funcion": "runge",
            "a": -5.0,
            "b": 5.0,
            "n_nodos": 15,
            "indices_ocultos": [1, 13],
            "ruido_sigma": 0.0,
            "umbral_alerta": 0.50,
        }
    raise ValueError(f"Escenario no reconocido: {tipo}")


def _get_signal_fn(nombre: str) -> Callable[[float], float]:
    if nombre == "sin_t":
        return lambda t: math.sin(t)
    if nombre == "exp_cos":
        return lambda t: math.exp(-t) * math.cos(2.0 * t)
    if nombre == "runge":
        return lambda t: 1.0 / (1.0 + 25.0 * (t**2))
    raise ValueError(f"Función sintética no reconocida: {nombre}")


def run_modulo4(
    tipo: ScenarioType,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta el Módulo 4 completo para el escenario y parámetros indicados."""
    params = _default_params(tipo)
    if overrides:
        for k, v in overrides.items():
            if v is not None and k in params:
                params[k] = v

    a = float(params["a"])
    b = float(params["b"])
    n_nodos = int(params["n_nodos"])
    ruido_sigma = float(params["ruido_sigma"])
    umbral = float(params["umbral_alerta"])
    func_name = str(params["funcion"])
    indices_ocultos = [int(i) for i in params["indices_ocultos"]]

    if a >= b:
        raise ValueError("Se requiere a < b en el intervalo de muestreo.")
    if n_nodos < 5:
        raise ValueError("Se requieren al menos 5 nodos para ocultar puntos y reconstruir.")
    if ruido_sigma < 0.0:
        raise ValueError("ruido_sigma debe ser >= 0.")

    sig_fn = _get_signal_fn(func_name)
    t_all = np.linspace(a, b, n_nodos, dtype=np.float64)
    y_true_all = np.array([sig_fn(float(t)) for t in t_all], dtype=np.float64)

    # Ruido determinista reproducible cuando ruido_sigma > 0
    if ruido_sigma > 0.0:
        rng = np.random.default_rng(12345)
        noise = rng.normal(0.0, ruido_sigma, size=n_nodos).astype(np.float64)
        y_measured_all = y_true_all + noise
    else:
        y_measured_all = y_true_all.copy()

    valid_hidden = sorted({idx for idx in indices_ocultos if 0 < idx < n_nodos - 1})
    if not valid_hidden:
        valid_hidden = [n_nodos // 3, (2 * n_nodos) // 3]
        params["indices_ocultos"] = valid_hidden

    hidden_mask = np.zeros(n_nodos, dtype=bool)
    hidden_mask[valid_hidden] = True

    t_visible = t_all[~hidden_mask]
    y_visible = y_measured_all[~hidden_mask]
    t_hidden = t_all[hidden_mask]
    y_hidden_true = y_true_all[hidden_mask]

    t_dense = np.linspace(a, b, 140, dtype=np.float64)
    y_dense_true = np.array([sig_fn(float(t)) for t in t_dense], dtype=np.float64)

    interp_results, spline = run_interpolation_comparison(
        t_visible, y_visible, t_hidden, y_hidden_true, t_dense
    )

    metodos: list[dict[str, Any]] = []
    for res in interp_results:
        metodos.append(
            {
                "familia": "INTERPOLACION",
                "metodo": res.metodo,
                "convergio": True,
                "iteraciones_realizadas": len(t_visible),
                "tiempo_ms": res.tiempo_ms,
                "valor_principal": res.rmse_ocultos,
                "etiqueta_valor": f"RMSE={res.rmse_ocultos:.4e}, E_max={res.error_max_ocultos:.4e}",
                "residual": res.error_max_ocultos,
                "error_abs": res.error_max_ocultos,
                "error_rel": res.error_rel_ocultos,
                "error_pct": res.error_pct_ocultos,
                "motivo_parada": f"Reconstrucción sobre {len(t_visible)} nodos visibles",
                "detalle_tabla": [asdict(c) for c in res.comparacion_ocultos],
            }
        )

    # Detección de cruce de umbral sobre el Spline Cúbico S(t) - umbral = 0
    s_dense = spline.evaluate(t_dense)
    diff_dense = s_dense - umbral
    bracket: tuple[float, float] | None = None
    for i in range(len(t_dense) - 1):
        if diff_dense[i] == 0.0 or diff_dense[i] * diff_dense[i + 1] <= 0.0:
            bracket = (float(t_dense[i]), float(t_dense[i + 1]))
            break

    t_cross_ref: float | None = None
    if bracket is not None:
        f_cross = lambda t: spline.evaluate_scalar(t) - umbral
        df_cross = lambda t: spline.derivative_scalar(t)
        ref_bis = bisection_solve(f_cross, bracket[0], bracket[1], tol=1e-12, max_iter=120)
        t_cross_ref = ref_bis.raiz

        r_bis = bisection_solve(f_cross, bracket[0], bracket[1], tol=1e-8, max_iter=80, x_ref=t_cross_ref)
        r_newt = newton_raphson_solve(
            f_cross, df_cross, x0=0.5 * (bracket[0] + bracket[1]), tol=1e-8, max_iter=80, x_ref=t_cross_ref
        )
        r_sec = secant_solve(f_cross, bracket[0], bracket[1], tol=1e-8, max_iter=80, x_ref=t_cross_ref)

        for r in (r_bis, r_newt, r_sec):
            metodos.append(
                {
                    "familia": "RAICES",
                    "metodo": f"{r.metodo} (Cruce Umbral)",
                    "convergio": r.convergio,
                    "iteraciones_realizadas": r.iteraciones_realizadas,
                    "tiempo_ms": r.tiempo_ms,
                    "valor_principal": r.raiz,
                    "etiqueta_valor": f"t_cruce={r.raiz:.6f} s",
                    "residual": r.residual_final,
                    "error_abs": r.error_abs,
                    "error_rel": r.error_rel,
                    "error_pct": r.error_pct,
                    "motivo_parada": r.motivo_parada,
                    "detalle_tabla": [asdict(it) for it in r.historial],
                }
            )

    # Gráficos obligatorios: 1) Curvas superpuestas, 2) Error absoluto en el dominio
    def _clip_curve(vals: list[float], limit: float = 5.0) -> list[float]:
        return [max(min(v, limit), -limit) for v in vals]

    graficos = [
        {
            "id": "modulo4_curvas",
            "titulo": "Reconstrucción de Señal: Lagrange vs Newton vs Splines Cúbicos",
            "x_label": "Tiempo t [s]",
            "y_label": "Amplitud de Señal y(t)",
            "y_scale": "linear",
            "series": [
                {
                    "name": "Señal Real Analítica",
                    "x": [float(t) for t in t_dense],
                    "y": [float(y) for y in y_dense_true],
                    "mode": "line",
                },
                *[
                    {
                        "name": res.metodo,
                        "x": [float(t) for t in t_dense],
                        "y": _clip_curve(res.y_curva_densa),
                        "mode": "line",
                    }
                    for res in interp_results
                ],
                {
                    "name": "Nodos Visibles",
                    "x": [float(t) for t in t_visible],
                    "y": [float(y) for y in y_visible],
                    "mode": "markers",
                },
                {
                    "name": "Nodos Ocultados (Reales)",
                    "x": [float(t) for t in t_hidden],
                    "y": [float(y) for y in y_hidden_true],
                    "mode": "markers",
                },
            ],
        },
        {
            "id": "modulo4_errores",
            "titulo": "Error Absoluto |y_real(t) - P(t)| a lo largo del Intervalo",
            "x_label": "Tiempo t [s]",
            "y_label": "Error Absoluto",
            "y_scale": "log",
            "series": [
                {
                    "name": f"Error {res.metodo}",
                    "x": [float(t) for t in t_dense],
                    "y": [
                        max(min(abs(float(yt) - float(yp)), 1e6), 1e-16)
                        for yt, yp in zip(y_dense_true, res.y_curva_densa)
                    ],
                    "mode": "line",
                }
                for res in interp_results
            ],
        },
    ]

    lag_res, newt_res, spl_res = interp_results
    if tipo == "NORMAL":
        interp_num = (
            f"Sobre señal suave sin(t) con {len(t_visible)} nodos visibles, Lagrange y Newton producen el "
            f"mismo polinomio único (RMSE={lag_res.rmse_ocultos:.2e}), mientras Splines Cúbicos alcanzan "
            f"RMSE={spl_res.rmse_ocultos:.2e} con menor grado local."
        )
        interp_prob = (
            "La pérdida de 2 paquetes puntuales en telemetría limpia puede reconstruirse con alta fidelidad "
            "para verificar cruces de umbral de alerta."
        )
    elif tipo == "ESTRES":
        interp_num = (
            f"Con ruido gaussiano sigma={ruido_sigma} y 4 nodos ocultos, la interpolación polinomial global de grado "
            f"{len(t_visible)-1} amplifica oscilaciones (Lagrange RMSE={lag_res.rmse_ocultos:.3e}), mientras "
            f"Splines Cúbicos mantienen estabilidad local (RMSE={spl_res.rmse_ocultos:.3e})."
        )
        interp_prob = (
            "Ante pérdida múltiple de paquetes con ruido de sensor, los splines cúbicos ofrecen estimaciones más "
            "confiables sin introducir picos artificiales de falsa alarma."
        )
    else:
        interp_num = (
            f"Fenómeno de Runge clásico en f(t)=1/(1+25t²) con {n_nodos} nodos equiespaciados: Lagrange y Newton "
            f"presentan oscilación severa cerca de los extremos (RMSE_ocultos={lag_res.rmse_ocultos:.3e}, "
            f"E_max={lag_res.error_max_ocultos:.3e}), mientras Splines Cúbicos evitan la explosión polinomial "
            f"(RMSE_ocultos={spl_res.rmse_ocultos:.3e})."
        )
        interp_prob = (
            "Muestra que aumentar la cantidad de sensores equiespaciados usando un único polinomio global empeora "
            "la reconstrucción en los bordes de la ventana de monitoreo."
        )

    return {
        "caso_codigo": "MOD4_SENSORES",
        "escenario": tipo,
        "nombre_descriptivo": {
            "NORMAL": "Telemetría limpia con 8 nodos equiespaciados",
            "ESTRES": "Señal amortiguada con ruido gaussiano y pérdida de paquetes",
            "MAL_CONDICIONADO": "Fenómeno de Runge con nodos equiespaciados de alto grado",
        }[tipo],
        "parametros_usados": params,
        "referencia": {
            "tipo": "ANALITICA",
            "funcion": func_name,
            "n_visibles": len(t_visible),
            "n_ocultos": len(t_hidden),
            "t_cruce_umbral_spline": t_cross_ref,
            "rmse_lagrange": lag_res.rmse_ocultos,
            "rmse_newton": newt_res.rmse_ocultos,
            "rmse_spline": spl_res.rmse_ocultos,
        },
        "metodos": metodos,
        "graficos": graficos,
        "interpretacion_numerica": interp_num,
        "interpretacion_problema": interp_prob,
    }
