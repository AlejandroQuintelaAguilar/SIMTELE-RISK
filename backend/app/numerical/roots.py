"""Métodos numéricos para búsqueda de raíces f(x) = 0 implementados desde cero en float64.

Incluye:
- Bisección
- Newton-Raphson
- Secante
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

import numpy as np

from app.core.error_metrics import (
    EPS_MACH,
    absolute_error,
    percentage_error,
    relative_error,
)


class RootFindingError(ValueError):
    """Excepción controlada cuando los parámetros iniciales de búsqueda de raíces no son válidos."""


@dataclass(frozen=True)
class RootIterationRecord:
    """Registro paso a paso de una iteración de búsqueda de raíces."""

    numero: int
    x: float
    f_x: float
    residual: float
    step_diff: float | None = None
    interval_a: float | None = None
    interval_b: float | None = None
    error_abs: float | None = None
    error_rel: float | None = None
    error_pct: float | None = None


@dataclass(frozen=True)
class RootResult:
    """Resultado consolidado de un algoritmo de búsqueda de raíces."""

    metodo: str
    familia: str
    raiz: float
    f_raiz: float
    convergio: bool
    iteraciones_realizadas: int
    motivo_parada: str
    tiempo_ms: float
    residual_final: float
    error_abs: float | None
    error_rel: float | None
    error_pct: float | None
    historial: list[RootIterationRecord] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _make_root_record(
    numero: int,
    x: float,
    fx: float,
    step_diff: float | None,
    x_ref: float | None,
    a: float | None = None,
    b: float | None = None,
) -> RootIterationRecord:
    err_abs = absolute_error(x_ref, x) if x_ref is not None else None
    err_rel = relative_error(x_ref, x) if x_ref is not None else None
    err_pct = percentage_error(x_ref, x) if x_ref is not None else None
    return RootIterationRecord(
        numero=numero,
        x=float(x),
        f_x=float(fx),
        residual=float(abs(fx)),
        step_diff=float(step_diff) if step_diff is not None else None,
        interval_a=float(a) if a is not None else None,
        interval_b=float(b) if b is not None else None,
        error_abs=err_abs,
        error_rel=err_rel,
        error_pct=err_pct,
    )


def bisection_solve(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float = 1e-8,
    max_iter: int = 100,
    x_ref: float | None = None,
) -> RootResult:
    """Encuentra una raíz de f(x) = 0 en [a, b] mediante el método de Bisección."""
    t_start = perf_counter()
    left = float(np.float64(a))
    right = float(np.float64(b))
    if left >= right:
        raise RootFindingError(f"Intervalo inválido [{left}, {right}]: se requiere a < b.")

    fa = float(np.float64(f(left)))
    fb = float(np.float64(f(right)))
    if not (np.isfinite(fa) and np.isfinite(fb)):
        raise RootFindingError("La función evaluó a valor no finito en los extremos.")

    if abs(fa) <= tol:
        rec = _make_root_record(0, left, fa, 0.0, x_ref, left, right)
        return RootResult(
            metodo="Bisección",
            familia="RAICES",
            raiz=left,
            f_raiz=fa,
            convergio=True,
            iteraciones_realizadas=0,
            motivo_parada=f"Extremo izquierdo a={left:.6g} ya satisface |f(a)| <= {tol:.1e}",
            tiempo_ms=(perf_counter() - t_start) * 1000.0,
            residual_final=abs(fa),
            error_abs=rec.error_abs,
            error_rel=rec.error_rel,
            error_pct=rec.error_pct,
            historial=[rec],
            diagnostics={"intervalo_inicial": [float(a), float(b)]},
        )
    if abs(fb) <= tol:
        rec = _make_root_record(0, right, fb, 0.0, x_ref, left, right)
        return RootResult(
            metodo="Bisección",
            familia="RAICES",
            raiz=right,
            f_raiz=fb,
            convergio=True,
            iteraciones_realizadas=0,
            motivo_parada=f"Extremo derecho b={right:.6g} ya satisface |f(b)| <= {tol:.1e}",
            tiempo_ms=(perf_counter() - t_start) * 1000.0,
            residual_final=abs(fb),
            error_abs=rec.error_abs,
            error_rel=rec.error_rel,
            error_pct=rec.error_pct,
            historial=[rec],
            diagnostics={"intervalo_inicial": [float(a), float(b)]},
        )

    if fa * fb > 0.0:
        raise RootFindingError(
            f"No hay cambio de signo en [{left}, {right}]: f(a)={fa:.4e}, f(b)={fb:.4e}."
        )

    historial: list[RootIterationRecord] = []
    convergio = False
    motivo = f"Máximo de iteraciones alcanzado ({max_iter})"
    c_prev: float | None = None
    c = left
    fc = fa

    for k in range(1, max_iter + 1):
        c = 0.5 * (left + right)
        fc = float(np.float64(f(c)))
        half_width = 0.5 * (right - left)
        step_diff = abs(c - c_prev) if c_prev is not None else half_width

        rec = _make_root_record(k, c, fc, step_diff, x_ref, left, right)
        historial.append(rec)

        if abs(fc) <= tol or half_width <= tol:
            convergio = True
            motivo = f"Tolerancia {tol:.1e} alcanzada en iteración {k} (semiancho={half_width:.2e})"
            break

        if fa * fc < 0.0:
            right = c
            fb = fc
        else:
            left = c
            fa = fc
        c_prev = c

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    last = historial[-1]
    return RootResult(
        metodo="Bisección",
        familia="RAICES",
        raiz=c,
        f_raiz=fc,
        convergio=convergio,
        iteraciones_realizadas=len(historial),
        motivo_parada=motivo,
        tiempo_ms=elapsed_ms,
        residual_final=abs(fc),
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        historial=historial,
        diagnostics={"intervalo_inicial": [float(a), float(b)], "semiancho_final": 0.5 * (right - left)},
    )


def newton_raphson_solve(
    f: Callable[[float], float],
    df: Callable[[float], float],
    x0: float,
    tol: float = 1e-8,
    max_iter: int = 100,
    x_ref: float | None = None,
) -> RootResult:
    """Encuentra una raíz de f(x) = 0 mediante el método de Newton-Raphson."""
    t_start = perf_counter()
    x = float(np.float64(x0))
    fx = float(np.float64(f(x)))
    historial: list[RootIterationRecord] = [
        _make_root_record(0, x, fx, None, x_ref)
    ]

    convergio = abs(fx) <= tol
    motivo = (
        f"Semilla x0={x:.6g} ya satisface |f(x0)| <= {tol:.1e}"
        if convergio
        else f"Máximo de iteraciones alcanzado ({max_iter})"
    )

    if not convergio:
        for k in range(1, max_iter + 1):
            dfx = float(np.float64(df(x)))
            if not np.isfinite(dfx) or abs(dfx) < EPS_MACH:
                motivo = (
                    f"Derivada nula o casi nula en iteración {k} (f'(x)={dfx:.3e}); "
                    "no se puede continuar Newton-Raphson."
                )
                break

            x_next = x - fx / dfx
            if not np.isfinite(x_next):
                motivo = f"Divergencia numérica en iteración {k}."
                break

            step_diff = abs(x_next - x)
            x = x_next
            fx = float(np.float64(f(x)))
            rec = _make_root_record(k, x, fx, step_diff, x_ref)
            historial.append(rec)

            if abs(fx) <= tol and step_diff <= tol:
                convergio = True
                motivo = f"Tolerancia {tol:.1e} alcanzada en iteración {k}"
                break
            if abs(fx) <= tol * 1e-2 or step_diff <= tol * 1e-2:
                convergio = True
                motivo = f"Criterio de parada satisfecho en iteración {k} (|dx|={step_diff:.2e})"
                break

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    last = historial[-1]
    return RootResult(
        metodo="Newton-Raphson",
        familia="RAICES",
        raiz=x,
        f_raiz=fx,
        convergio=convergio,
        iteraciones_realizadas=max(len(historial) - 1, 0),
        motivo_parada=motivo,
        tiempo_ms=elapsed_ms,
        residual_final=abs(fx),
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        historial=historial,
        diagnostics={"semilla_x0": float(x0)},
    )


def secant_solve(
    f: Callable[[float], float],
    x0: float,
    x1: float,
    tol: float = 1e-8,
    max_iter: int = 100,
    x_ref: float | None = None,
) -> RootResult:
    """Encuentra una raíz de f(x) = 0 mediante el método de la Secante."""
    t_start = perf_counter()
    x_prev = float(np.float64(x0))
    x_curr = float(np.float64(x1))
    f_prev = float(np.float64(f(x_prev)))
    f_curr = float(np.float64(f(x_curr)))

    historial: list[RootIterationRecord] = [
        _make_root_record(0, x_curr, f_curr, abs(x_curr - x_prev), x_ref)
    ]

    convergio = abs(f_curr) <= tol
    motivo = (
        f"Semilla x1={x_curr:.6g} ya satisface |f(x1)| <= {tol:.1e}"
        if convergio
        else f"Máximo de iteraciones alcanzado ({max_iter})"
    )

    if not convergio:
        for k in range(1, max_iter + 1):
            denom = f_curr - f_prev
            if not np.isfinite(denom) or abs(denom) < EPS_MACH:
                motivo = (
                    f"Denominador nulo en iteración {k} (f(x_k)-f(x_{{k-1}})={denom:.3e}); "
                    "pendiente secante indefinida."
                )
                break

            x_next = x_curr - f_curr * (x_curr - x_prev) / denom
            if not np.isfinite(x_next):
                motivo = f"Divergencia numérica en iteración {k}."
                break

            step_diff = abs(x_next - x_curr)
            x_prev, f_prev = x_curr, f_curr
            x_curr = x_next
            f_curr = float(np.float64(f(x_curr)))

            rec = _make_root_record(k, x_curr, f_curr, step_diff, x_ref)
            historial.append(rec)

            if abs(f_curr) <= tol and step_diff <= tol:
                convergio = True
                motivo = f"Tolerancia {tol:.1e} alcanzada en iteración {k}"
                break
            if abs(f_curr) <= tol * 1e-2 or step_diff <= tol * 1e-2:
                convergio = True
                motivo = f"Criterio de parada satisfecho en iteración {k} (|dx|={step_diff:.2e})"
                break

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    last = historial[-1]
    return RootResult(
        metodo="Secante",
        familia="RAICES",
        raiz=x_curr,
        f_raiz=f_curr,
        convergio=convergio,
        iteraciones_realizadas=max(len(historial) - 1, 0),
        motivo_parada=motivo,
        tiempo_ms=elapsed_ms,
        residual_final=abs(f_curr),
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        historial=historial,
        diagnostics={"semillas": [float(x0), float(x1)]},
    )
