"""Métodos numéricos de integración implementados desde cero en float64.

Incluye:
- Regla del Trapecio compuesto (funcional y sobre muestras discretas)
- Regla de Simpson 1/3 compuesto (funcional y sobre muestras discretas)
- Integración de Romberg con tabla de extrapolación de Richardson
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

from app.core.error_metrics import (
    absolute_error,
    percentage_error,
    relative_error,
)


class IntegrationError(ValueError):
    """Excepción controlada para parámetros inválidos de integración."""


@dataclass(frozen=True)
class RefinementStep:
    """Registro de un paso de refinamiento para integración numérica."""

    numero: int
    subintervalos: int
    paso_h: float
    valor_aprox: float
    error_abs: float | None = None
    error_rel: float | None = None
    error_pct: float | None = None


@dataclass(frozen=True)
class IntegrationResult:
    """Resultado consolidado de un método de integración numérica."""

    metodo: str
    familia: str
    valor: float
    convergio: bool
    iteraciones_realizadas: int
    motivo_parada: str
    tiempo_ms: float
    error_abs: float | None
    error_rel: float | None
    error_pct: float | None
    refinamiento: list[RefinementStep] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _eval_trapezoid_once(f: Callable[[float], float], a: float, b: float, n: int) -> float:
    if n < 1:
        raise IntegrationError("Trapecio compuesto requiere n >= 1 subintervalos.")
    h = (b - a) / n
    total = 0.5 * (float(f(a)) + float(f(b)))
    for k in range(1, n):
        total += float(f(a + k * h))
    return float(h * total)


def _eval_simpson_once(f: Callable[[float], float], a: float, b: float, n: int) -> float:
    if n < 2 or n % 2 != 0:
        raise IntegrationError("Simpson 1/3 compuesto requiere un número par de subintervalos n >= 2.")
    h = (b - a) / n
    total = float(f(a)) + float(f(b))
    for k in range(1, n):
        xk = a + k * h
        weight = 4.0 if k % 2 == 1 else 2.0
        total += weight * float(f(xk))
    return float((h / 3.0) * total)


def composite_trapezoid(
    f: Callable[[float], float],
    a: float,
    b: float,
    subintervals_list: list[int] | None = None,
    ref_value: float | None = None,
) -> IntegrationResult:
    """Ejecuta Trapecio compuesto con estudio de refinamiento de malla."""
    t_start = perf_counter()
    if a > b:
        raise IntegrationError(f"Límites inválidos [{a}, {b}]: se requiere a <= b.")
    if a == b:
        return IntegrationResult(
            metodo="Trapecio Compuesto",
            familia="INTEGRACION",
            valor=0.0,
            convergio=True,
            iteraciones_realizadas=1,
            motivo_parada="Intervalo degenerado a == b",
            tiempo_ms=0.0,
            error_abs=absolute_error(ref_value, 0.0) if ref_value is not None else None,
            error_rel=relative_error(ref_value, 0.0) if ref_value is not None else None,
            error_pct=percentage_error(ref_value, 0.0) if ref_value is not None else None,
        )

    n_list = subintervals_list or [4, 8, 16, 32, 64]
    steps: list[RefinementStep] = []
    val = 0.0
    for idx, n in enumerate(n_list, start=1):
        val = _eval_trapezoid_once(f, float(a), float(b), int(n))
        h = (float(b) - float(a)) / int(n)
        steps.append(
            RefinementStep(
                numero=idx,
                subintervalos=int(n),
                paso_h=h,
                valor_aprox=val,
                error_abs=absolute_error(ref_value, val) if ref_value is not None else None,
                error_rel=relative_error(ref_value, val) if ref_value is not None else None,
                error_pct=percentage_error(ref_value, val) if ref_value is not None else None,
            )
        )

    last = steps[-1]
    return IntegrationResult(
        metodo="Trapecio Compuesto",
        familia="INTEGRACION",
        valor=last.valor_aprox,
        convergio=True,
        iteraciones_realizadas=len(steps),
        motivo_parada=f"Refinamiento completado hasta n={last.subintervalos} (h={last.paso_h:.4e})",
        tiempo_ms=(perf_counter() - t_start) * 1000.0,
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        refinamiento=steps,
        diagnostics={"intervalo": [float(a), float(b)]},
    )


def composite_simpson_13(
    f: Callable[[float], float],
    a: float,
    b: float,
    subintervals_list: list[int] | None = None,
    ref_value: float | None = None,
) -> IntegrationResult:
    """Ejecuta Simpson 1/3 compuesto con estudio de refinamiento de malla."""
    t_start = perf_counter()
    if a > b:
        raise IntegrationError(f"Límites inválidos [{a}, {b}]: se requiere a <= b.")
    if a == b:
        return IntegrationResult(
            metodo="Simpson 1/3 Compuesto",
            familia="INTEGRACION",
            valor=0.0,
            convergio=True,
            iteraciones_realizadas=1,
            motivo_parada="Intervalo degenerado a == b",
            tiempo_ms=0.0,
            error_abs=absolute_error(ref_value, 0.0) if ref_value is not None else None,
            error_rel=relative_error(ref_value, 0.0) if ref_value is not None else None,
            error_pct=percentage_error(ref_value, 0.0) if ref_value is not None else None,
        )

    n_list = subintervals_list or [4, 8, 16, 32, 64]
    steps: list[RefinementStep] = []
    for idx, n in enumerate(n_list, start=1):
        val = _eval_simpson_once(f, float(a), float(b), int(n))
        h = (float(b) - float(a)) / int(n)
        steps.append(
            RefinementStep(
                numero=idx,
                subintervalos=int(n),
                paso_h=h,
                valor_aprox=val,
                error_abs=absolute_error(ref_value, val) if ref_value is not None else None,
                error_rel=relative_error(ref_value, val) if ref_value is not None else None,
                error_pct=percentage_error(ref_value, val) if ref_value is not None else None,
            )
        )

    last = steps[-1]
    return IntegrationResult(
        metodo="Simpson 1/3 Compuesto",
        familia="INTEGRACION",
        valor=last.valor_aprox,
        convergio=True,
        iteraciones_realizadas=len(steps),
        motivo_parada=f"Refinamiento completado hasta n={last.subintervalos} (h={last.paso_h:.4e})",
        tiempo_ms=(perf_counter() - t_start) * 1000.0,
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        refinamiento=steps,
        diagnostics={"intervalo": [float(a), float(b)]},
    )


def romberg_integrate(
    f: Callable[[float], float],
    a: float,
    b: float,
    max_levels: int = 8,
    tol: float = 1e-10,
    ref_value: float | None = None,
) -> IntegrationResult:
    """Ejecuta integración de Romberg desde cero mediante extrapolación de Richardson."""
    t_start = perf_counter()
    if a > b:
        raise IntegrationError(f"Límites inválidos [{a}, {b}]: se requiere a <= b.")
    if max_levels < 2:
        raise IntegrationError("Romberg requiere max_levels >= 2.")
    if a == b:
        return IntegrationResult(
            metodo="Romberg",
            familia="INTEGRACION",
            valor=0.0,
            convergio=True,
            iteraciones_realizadas=1,
            motivo_parada="Intervalo degenerado a == b",
            tiempo_ms=0.0,
            error_abs=absolute_error(ref_value, 0.0) if ref_value is not None else None,
            error_rel=relative_error(ref_value, 0.0) if ref_value is not None else None,
            error_pct=percentage_error(ref_value, 0.0) if ref_value is not None else None,
        )

    a_f = float(a)
    b_f = float(b)
    R = np.zeros((max_levels, max_levels), dtype=np.float64)
    h = b_f - a_f
    R[0, 0] = 0.5 * h * (float(f(a_f)) + float(f(b_f)))

    steps: list[RefinementStep] = [
        RefinementStep(
            numero=1,
            subintervalos=1,
            paso_h=h,
            valor_aprox=float(R[0, 0]),
            error_abs=absolute_error(ref_value, float(R[0, 0])) if ref_value is not None else None,
            error_rel=relative_error(ref_value, float(R[0, 0])) if ref_value is not None else None,
            error_pct=percentage_error(ref_value, float(R[0, 0])) if ref_value is not None else None,
        )
    ]

    convergio = False
    motivo = f"Máximo de niveles Romberg alcanzado ({max_levels})"
    best_val = float(R[0, 0])

    for i in range(1, max_levels):
        h *= 0.5
        n_sub = 2**i
        # Puntos medios nuevos para reutilizar evaluaciones previas
        subtotal = 0.0
        for k in range(1, n_sub, 2):
            subtotal += float(f(a_f + k * h))
        R[i, 0] = 0.5 * R[i - 1, 0] + h * subtotal

        for j in range(1, i + 1):
            factor = 4.0**j
            R[i, j] = R[i, j - 1] + (R[i, j - 1] - R[i - 1, j - 1]) / (factor - 1.0)

        best_val = float(R[i, i])
        steps.append(
            RefinementStep(
                numero=i + 1,
                subintervalos=n_sub,
                paso_h=h,
                valor_aprox=best_val,
                error_abs=absolute_error(ref_value, best_val) if ref_value is not None else None,
                error_rel=relative_error(ref_value, best_val) if ref_value is not None else None,
                error_pct=percentage_error(ref_value, best_val) if ref_value is not None else None,
            )
        )

        if abs(R[i, i] - R[i - 1, i - 1]) <= tol:
            convergio = True
            motivo = f"Convergencia Romberg |R[{i},{i}]-R[{i-1},{i-1}]| <= {tol:.1e}"
            break

    last = steps[-1]
    return IntegrationResult(
        metodo="Romberg",
        familia="INTEGRACION",
        valor=best_val,
        convergio=convergio,
        iteraciones_realizadas=len(steps),
        motivo_parada=motivo,
        tiempo_ms=(perf_counter() - t_start) * 1000.0,
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        refinamiento=steps,
        diagnostics={
            "niveles_usados": len(steps),
            "tabla_romberg_diagonal": [float(R[k, k]) for k in range(len(steps))],
        },
    )


def trapezoid_from_samples(x: NDArray[np.float64] | list[float], y: NDArray[np.float64] | list[float]) -> float:
    """Trapecio compuesto sobre muestras discretas (x_i, y_i)."""
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    if len(x_arr) != len(y_arr) or len(x_arr) < 2:
        raise IntegrationError("Se requieren al menos 2 puntos de igual longitud.")
    dx = np.diff(x_arr)
    return float(np.sum(0.5 * (y_arr[:-1] + y_arr[1:]) * dx))


def simpson_from_samples(x: NDArray[np.float64] | list[float], y: NDArray[np.float64] | list[float]) -> float:
    """Simpson 1/3 compuesto sobre muestras equiespaciadas (si n es impar, cierra último tramo con trapecio)."""
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    n = len(x_arr) - 1
    if len(x_arr) != len(y_arr) or n < 2:
        raise IntegrationError("Se requieren al menos 3 puntos (2 subintervalos) para Simpson 1/3.")

    h = float(x_arr[1] - x_arr[0])
    even_limit = n if n % 2 == 0 else n - 1
    total = float(y_arr[0] + y_arr[even_limit])
    for k in range(1, even_limit):
        total += (4.0 if k % 2 == 1 else 2.0) * float(y_arr[k])
    area = (h / 3.0) * total
    if even_limit < n:
        area += 0.5 * (x_arr[n] - x_arr[n - 1]) * (y_arr[n] + y_arr[n - 1])
    return float(area)
