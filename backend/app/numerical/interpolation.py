"""Métodos numéricos de interpolación implementados desde cero en float64.

Incluye:
- Polinomio interpolante de Lagrange
- Polinomio de Newton por diferencias divididas
- Splines cúbicos naturales (sistema tridiagonal resuelto con algoritmo de Thomas)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray

from app.core.error_metrics import (
    EPS_MACH,
    FloatArray,
    absolute_error,
    percentage_error,
    relative_error,
    vector_error_metrics,
)


class InterpolationError(ValueError):
    """Excepción controlada para datos de interpolación inválidos."""


@dataclass(frozen=True)
class HiddenPointComparison:
    """Error de reconstrucción en un nodo ocultado específico."""

    t: float
    y_real: float
    y_aprox: float
    error_abs: float
    error_rel: float
    error_pct: float


@dataclass(frozen=True)
class CubicSplineModel:
    """Representación por tramos de un spline cúbico natural."""

    x_nodes: FloatArray
    a: FloatArray
    b: FloatArray
    c: FloatArray
    d: FloatArray

    def _find_segment(self, x_val: float) -> int:
        n = len(self.x_nodes)
        if x_val <= self.x_nodes[0]:
            return 0
        if x_val >= self.x_nodes[-1]:
            return n - 2
        idx = int(np.searchsorted(self.x_nodes, x_val, side="right") - 1)
        return max(0, min(idx, n - 2))

    def evaluate_scalar(self, x_val: float) -> float:
        """Evalúa S(x) en un punto escalar."""
        i = self._find_segment(x_val)
        dx = float(np.float64(x_val) - self.x_nodes[i])
        return float(
            self.a[i] + self.b[i] * dx + self.c[i] * dx**2 + self.d[i] * dx**3
        )

    def derivative_scalar(self, x_val: float) -> float:
        """Evalúa S'(x) en un punto escalar."""
        i = self._find_segment(x_val)
        dx = float(np.float64(x_val) - self.x_nodes[i])
        return float(self.b[i] + 2.0 * self.c[i] * dx + 3.0 * self.d[i] * dx**2)

    def evaluate(self, x_eval: NDArray[np.float64] | list[float]) -> FloatArray:
        """Evalúa S(x) sobre un arreglo de puntos."""
        pts = np.asarray(x_eval, dtype=np.float64)
        return np.array([self.evaluate_scalar(float(v)) for v in pts], dtype=np.float64)


@dataclass(frozen=True)
class InterpolationResult:
    """Resultado estandarizado de un método de interpolación."""

    metodo: str
    familia: str
    tiempo_ms: float
    y_ocultos_aprox: list[float]
    y_curva_densa: list[float]
    rmse_ocultos: float
    error_max_ocultos: float
    error_rel_ocultos: float
    error_pct_ocultos: float
    comparacion_ocultos: list[HiddenPointComparison] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _validate_nodes(
    x_nodes: NDArray[np.float64] | list[float],
    y_nodes: NDArray[np.float64] | list[float],
) -> tuple[FloatArray, FloatArray]:
    x = np.asarray(x_nodes, dtype=np.float64)
    y = np.asarray(y_nodes, dtype=np.float64)
    if x.ndim != 1 or y.ndim != 1 or x.shape[0] != y.shape[0]:
        raise InterpolationError("x_nodes e y_nodes deben ser vectores 1D de igual longitud.")
    if x.shape[0] < 2:
        raise InterpolationError("Se requieren al menos 2 nodos para interpolar.")
    if np.any(np.diff(np.sort(x)) <= EPS_MACH):
        raise InterpolationError("Los nodos x deben ser estrictamente distintos.")
    return x, y


def lagrange_evaluate(
    x_nodes: NDArray[np.float64] | list[float],
    y_nodes: NDArray[np.float64] | list[float],
    x_eval: NDArray[np.float64] | list[float],
) -> FloatArray:
    """Evalúa el polinomio interpolante de Lagrange en x_eval desde cero."""
    x, y = _validate_nodes(x_nodes, y_nodes)
    pts = np.asarray(x_eval, dtype=np.float64)
    n = len(x)
    out = np.zeros(len(pts), dtype=np.float64)

    for idx, x_val in enumerate(pts):
        total = 0.0
        for i in range(n):
            basis = 1.0
            for j in range(n):
                if i != j:
                    basis *= (x_val - x[j]) / (x[i] - x[j])
            total += y[i] * basis
        out[idx] = total
    return out


def newton_divided_differences(
    x_nodes: NDArray[np.float64] | list[float],
    y_nodes: NDArray[np.float64] | list[float],
) -> tuple[FloatArray, FloatArray]:
    """Calcula la tabla completa de diferencias divididas y sus coeficientes diagonales."""
    x, y = _validate_nodes(x_nodes, y_nodes)
    n = len(x)
    table = np.zeros((n, n), dtype=np.float64)
    table[:, 0] = y
    for j in range(1, n):
        for i in range(n - j):
            table[i, j] = (table[i + 1, j - 1] - table[i, j - 1]) / (x[i + j] - x[i])
    return table[0, :].copy(), table


def newton_evaluate(
    x_nodes: NDArray[np.float64] | list[float],
    y_nodes: NDArray[np.float64] | list[float],
    x_eval: NDArray[np.float64] | list[float],
) -> tuple[FloatArray, FloatArray]:
    """Evalúa el polinomio de Newton (Horner) en x_eval y retorna (valores, coeficientes)."""
    x, y = _validate_nodes(x_nodes, y_nodes)
    coeffs, _ = newton_divided_differences(x, y)
    pts = np.asarray(x_eval, dtype=np.float64)
    n = len(coeffs)

    out = np.empty(len(pts), dtype=np.float64)
    for idx, x_val in enumerate(pts):
        acc = coeffs[n - 1]
        for k in range(n - 2, -1, -1):
            acc = acc * (x_val - x[k]) + coeffs[k]
        out[idx] = acc
    return out, coeffs


def _solve_tridiagonal_thomas(
    lower: FloatArray,
    diag: FloatArray,
    upper: FloatArray,
    rhs: FloatArray,
) -> FloatArray:
    """Resuelve un sistema tridiagonal A x = rhs mediante el algoritmo de Thomas."""
    m = len(diag)
    if m == 1:
        return np.array([rhs[0] / diag[0]], dtype=np.float64)

    c_prime = np.zeros(m - 1, dtype=np.float64)
    d_prime = np.zeros(m, dtype=np.float64)

    c_prime[0] = upper[0] / diag[0]
    d_prime[0] = rhs[0] / diag[0]

    for i in range(1, m - 1):
        denom = diag[i] - lower[i - 1] * c_prime[i - 1]
        c_prime[i] = upper[i] / denom
        d_prime[i] = (rhs[i] - lower[i - 1] * d_prime[i - 1]) / denom

    denom_last = diag[m - 1] - lower[m - 2] * c_prime[m - 2]
    d_prime[m - 1] = (rhs[m - 1] - lower[m - 2] * d_prime[m - 2]) / denom_last

    sol = np.zeros(m, dtype=np.float64)
    sol[m - 1] = d_prime[m - 1]
    for i in range(m - 2, -1, -1):
        sol[i] = d_prime[i] - c_prime[i] * sol[i + 1]
    return sol


def build_natural_cubic_spline(
    x_nodes: NDArray[np.float64] | list[float],
    y_nodes: NDArray[np.float64] | list[float],
) -> CubicSplineModel:
    """Construye un spline cúbico natural (S''(x_0)=S''(x_{n-1})=0) desde cero."""
    x, y = _validate_nodes(x_nodes, y_nodes)
    order = np.argsort(x)
    x = x[order]
    y = y[order]

    n = len(x)
    h = np.diff(x)
    c = np.zeros(n, dtype=np.float64)

    if n > 2:
        m = n - 2
        lower = np.zeros(max(m - 1, 0), dtype=np.float64)
        diag = np.zeros(m, dtype=np.float64)
        upper = np.zeros(max(m - 1, 0), dtype=np.float64)
        rhs = np.zeros(m, dtype=np.float64)

        for i in range(m):
            idx = i + 1
            diag[i] = 2.0 * (h[idx - 1] + h[idx])
            rhs[i] = 3.0 * ((y[idx + 1] - y[idx]) / h[idx] - (y[idx] - y[idx - 1]) / h[idx - 1])
            if i > 0:
                lower[i - 1] = h[idx - 1]
            if i < m - 1:
                upper[i] = h[idx]

        c[1:-1] = _solve_tridiagonal_thomas(lower, diag, upper, rhs)

    a = y[:-1].copy()
    b = np.zeros(n - 1, dtype=np.float64)
    d = np.zeros(n - 1, dtype=np.float64)
    for i in range(n - 1):
        b[i] = (y[i + 1] - y[i]) / h[i] - h[i] * (2.0 * c[i] + c[i + 1]) / 3.0
        d[i] = (c[i + 1] - c[i]) / (3.0 * h[i])

    return CubicSplineModel(x_nodes=x, a=a, b=b, c=c[:-1].copy(), d=d)


def _summarize_interpolation(
    metodo: str,
    elapsed_ms: float,
    t_hidden: FloatArray,
    y_hidden_true: FloatArray,
    y_hidden_pred: FloatArray,
    y_dense_pred: FloatArray,
    diagnostics: dict[str, Any],
) -> InterpolationResult:
    comparaciones: list[HiddenPointComparison] = []
    for t_val, y_real, y_aprox in zip(t_hidden, y_hidden_true, y_hidden_pred):
        comparaciones.append(
            HiddenPointComparison(
                t=float(t_val),
                y_real=float(y_real),
                y_aprox=float(y_aprox),
                error_abs=absolute_error(float(y_real), float(y_aprox)),
                error_rel=relative_error(float(y_real), float(y_aprox)),
                error_pct=percentage_error(float(y_real), float(y_aprox)),
            )
        )

    vec_errs = vector_error_metrics(y_hidden_true, y_hidden_pred)
    rmse = float(np.sqrt(np.mean((y_hidden_true - y_hidden_pred) ** 2)))
    max_err = float(np.max(np.abs(y_hidden_true - y_hidden_pred)))

    return InterpolationResult(
        metodo=metodo,
        familia="INTERPOLACION",
        tiempo_ms=elapsed_ms,
        y_ocultos_aprox=[float(v) for v in y_hidden_pred],
        y_curva_densa=[float(v) for v in y_dense_pred],
        rmse_ocultos=rmse,
        error_max_ocultos=max_err,
        error_rel_ocultos=vec_errs["error_rel"],
        error_pct_ocultos=vec_errs["error_pct"],
        comparacion_ocultos=comparaciones,
        diagnostics=diagnostics,
    )


def run_interpolation_comparison(
    t_visible: NDArray[np.float64] | list[float],
    y_visible: NDArray[np.float64] | list[float],
    t_hidden: NDArray[np.float64] | list[float],
    y_hidden_true: NDArray[np.float64] | list[float],
    t_dense: NDArray[np.float64] | list[float],
) -> tuple[list[InterpolationResult], CubicSplineModel]:
    """Ejecuta Lagrange, Newton y Splines Cúbicos sobre los mismos nodos."""
    tv = np.asarray(t_visible, dtype=np.float64)
    yv = np.asarray(y_visible, dtype=np.float64)
    th = np.asarray(t_hidden, dtype=np.float64)
    yh = np.asarray(y_hidden_true, dtype=np.float64)
    td = np.asarray(t_dense, dtype=np.float64)

    # 1. Lagrange
    t0 = perf_counter()
    yh_lag = lagrange_evaluate(tv, yv, th)
    yd_lag = lagrange_evaluate(tv, yv, td)
    ms_lag = (perf_counter() - t0) * 1000.0
    res_lag = _summarize_interpolation(
        "Lagrange",
        ms_lag,
        th,
        yh,
        yh_lag,
        yd_lag,
        {"grado_polinomio": len(tv) - 1},
    )

    # 2. Newton (Diferencias Divididas)
    t0 = perf_counter()
    yh_newt, coeffs = newton_evaluate(tv, yv, th)
    yd_newt, _ = newton_evaluate(tv, yv, td)
    ms_newt = (perf_counter() - t0) * 1000.0
    res_newt = _summarize_interpolation(
        "Newton (Dif. Divididas)",
        ms_newt,
        th,
        yh,
        yh_newt,
        yd_newt,
        {"grado_polinomio": len(tv) - 1, "coef_max": float(np.max(np.abs(coeffs)))},
    )

    # 3. Splines Cúbicos Naturales
    t0 = perf_counter()
    spline = build_natural_cubic_spline(tv, yv)
    yh_spl = spline.evaluate(th)
    yd_spl = spline.evaluate(td)
    ms_spl = (perf_counter() - t0) * 1000.0
    res_spl = _summarize_interpolation(
        "Splines Cúbicos Naturales",
        ms_spl,
        th,
        yh,
        yh_spl,
        yd_spl,
        {"tramos": len(tv) - 1, "condicion_frontera": "Natural (S''=0)"},
    )

    return [res_lag, res_newt, res_spl], spline
