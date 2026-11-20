"""Solvers de Ecuaciones Diferenciales Ordinarias (EDO) implementados desde cero en float64.

Incluye:
- Runge-Kutta de 2.º orden (variante declarada: Método de Heun / RK2 Mejorado)
- Runge-Kutta de 4.º orden (RK4 clásico)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

from app.core.error_metrics import (
    FloatArray,
    vector_error_metrics,
)


class ODEError(ValueError):
    """Excepción controlada para parámetros inválidos de EDO."""


@dataclass(frozen=True)
class ODEStepRecord:
    """Registro de un paso temporal (t_k, y_k) y errores frente a referencia."""

    numero: int
    t: float
    y: list[float]
    y_ref: list[float] | None = None
    error_abs: float | None = None
    error_rel: float | None = None
    error_pct: float | None = None


@dataclass(frozen=True)
class ODEResult:
    """Resultado consolidado de un solver de EDO."""

    metodo: str
    familia: str
    variante: str
    paso_h: float
    pasos_realizados: int
    convergio: bool
    motivo_parada: str
    tiempo_ms: float
    t_values: list[float]
    y_values: list[list[float]]
    y_final: list[float]
    error_abs_final: float | None
    error_rel_final: float | None
    error_pct_final: float | None
    error_abs_max: float | None
    rmse: float | None
    historial: list[ODEStepRecord] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _solve_ode_generic(
    method_name: str,
    variante: str,
    step_fn: Callable[[Callable[[float, FloatArray], FloatArray], float, FloatArray, float], FloatArray],
    f: Callable[[float, FloatArray], FloatArray],
    t0: float,
    t_end: float,
    y0: NDArray[np.float64] | list[float],
    h: float,
    ref_fn: Callable[[float], FloatArray] | None = None,
) -> ODEResult:
    t_start = perf_counter()
    if h <= 0.0:
        raise ODEError(f"El paso temporal h debe ser positivo; recibido h={h}.")
    if t_end <= t0:
        raise ODEError(f"Se requiere t_end > t0; recibido t0={t0}, t_end={t_end}.")

    y = np.asarray(y0, dtype=np.float64).copy()
    if y.ndim != 1 or y.shape[0] == 0:
        raise ODEError("La condición inicial y0 debe ser un vector 1D no vacío.")

    n_steps = int(np.ceil((t_end - t0) / h))
    t = float(t0)

    t_list: list[float] = [t]
    y_list: list[list[float]] = [[float(v) for v in y]]
    historial: list[ODEStepRecord] = []

    y_ref0 = np.asarray(ref_fn(t), dtype=np.float64) if ref_fn is not None else None
    err0 = vector_error_metrics(y_ref0, y) if y_ref0 is not None else None
    historial.append(
        ODEStepRecord(
            numero=0,
            t=t,
            y=[float(v) for v in y],
            y_ref=[float(v) for v in y_ref0] if y_ref0 is not None else None,
            error_abs=err0["error_abs"] if err0 else None,
            error_rel=err0["error_rel"] if err0 else None,
            error_pct=err0["error_pct"] if err0 else None,
        )
    )

    convergio = True
    motivo = f"Integración completada en {n_steps} pasos hasta t={t_end:.4f}"
    abs_errors: list[float] = [err0["error_abs"]] if err0 else []

    for k in range(1, n_steps + 1):
        h_curr = min(float(h), float(t_end - t))
        if h_curr <= 1e-15:
            break

        y_next = step_fn(f, t, y, h_curr)
        t_next = t + h_curr

        if not np.all(np.isfinite(y_next)) or float(np.linalg.norm(y_next, ord=2)) > 1e6:
            convergio = False
            motivo = (
                f"Inestabilidad numérica / desbordamiento en paso {k} (t={t_next:.4f}s, h={h}): "
                "el paso excede el límite de estabilidad explícita."
            )
            break

        t = t_next
        y = y_next
        t_list.append(t)
        y_list.append([float(v) for v in y])

        y_ref_k = np.asarray(ref_fn(t), dtype=np.float64) if ref_fn is not None else None
        err_k = vector_error_metrics(y_ref_k, y) if y_ref_k is not None else None
        if err_k is not None:
            abs_errors.append(err_k["error_abs"])

        historial.append(
            ODEStepRecord(
                numero=k,
                t=t,
                y=[float(v) for v in y],
                y_ref=[float(v) for v in y_ref_k] if y_ref_k is not None else None,
                error_abs=err_k["error_abs"] if err_k else None,
                error_rel=err_k["error_rel"] if err_k else None,
                error_pct=err_k["error_pct"] if err_k else None,
            )
        )

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    last = historial[-1]
    err_max = float(max(abs_errors)) if abs_errors else None
    rmse = float(np.sqrt(np.mean(np.square(abs_errors)))) if abs_errors else None

    return ODEResult(
        metodo=method_name,
        familia="EDO",
        variante=variante,
        paso_h=float(h),
        pasos_realizados=len(historial) - 1,
        convergio=convergio,
        motivo_parada=motivo,
        tiempo_ms=elapsed_ms,
        t_values=t_list,
        y_values=y_list,
        y_final=[float(v) for v in y],
        error_abs_final=last.error_abs,
        error_rel_final=last.error_rel,
        error_pct_final=last.error_pct,
        error_abs_max=err_max,
        rmse=rmse,
        historial=historial,
        diagnostics={"t0": float(t0), "t_final": t, "dimension": int(len(y))},
    )


def _rk2_heun_step(
    f: Callable[[float, FloatArray], FloatArray],
    t: float,
    y: FloatArray,
    h: float,
) -> FloatArray:
    k1 = np.asarray(f(t, y), dtype=np.float64)
    k2 = np.asarray(f(t + h, y + h * k1), dtype=np.float64)
    return y + 0.5 * h * (k1 + k2)


def _rk4_classic_step(
    f: Callable[[float, FloatArray], FloatArray],
    t: float,
    y: FloatArray,
    h: float,
) -> FloatArray:
    k1 = np.asarray(f(t, y), dtype=np.float64)
    k2 = np.asarray(f(t + 0.5 * h, y + 0.5 * h * k1), dtype=np.float64)
    k3 = np.asarray(f(t + 0.5 * h, y + 0.5 * h * k2), dtype=np.float64)
    k4 = np.asarray(f(t + h, y + h * k3), dtype=np.float64)
    return y + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def rk2_heun_solve(
    f: Callable[[float, FloatArray], FloatArray],
    t0: float,
    t_end: float,
    y0: NDArray[np.float64] | list[float],
    h: float,
    ref_fn: Callable[[float], FloatArray] | None = None,
) -> ODEResult:
    """Resuelve y' = f(t, y) mediante Runge-Kutta de 2.º orden (variante Heun)."""
    return _solve_ode_generic(
        method_name="Runge-Kutta 2 (Heun)",
        variante="Heun / Euler Mejorado (RK2)",
        step_fn=_rk2_heun_step,
        f=f,
        t0=t0,
        t_end=t_end,
        y0=y0,
        h=h,
        ref_fn=ref_fn,
    )


def rk4_solve(
    f: Callable[[float, FloatArray], FloatArray],
    t0: float,
    t_end: float,
    y0: NDArray[np.float64] | list[float],
    h: float,
    ref_fn: Callable[[float], FloatArray] | None = None,
) -> ODEResult:
    """Resuelve y' = f(t, y) mediante Runge-Kutta clásico de 4.º orden (RK4)."""
    return _solve_ode_generic(
        method_name="Runge-Kutta 4 (Clásico)",
        variante="RK4 Clásico",
        step_fn=_rk4_classic_step,
        f=f,
        t0=t0,
        t_end=t_end,
        y0=y0,
        h=h,
        ref_fn=ref_fn,
    )
