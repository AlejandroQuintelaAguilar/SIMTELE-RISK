"""Solvers de sistemas lineales A x = b implementados desde cero en float64.

Incluye:
- Jacobi (iterativo estacionario)
- Gauss-Seidel (iterativo estacionario)
- Factorización LU con pivoteo parcial (directo: PA = LU)
- Gradiente Conjugado (iterativo Krylov para matrices SPD)
- Solución de referencia con np.linalg.solve para contraste de precisión
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
    relative_residual,
    residual_norm,
    vector_error_metrics,
)


class NonSPDError(ValueError):
    """Excepción controlada cuando una matriz no es Simétrica Definida Positiva."""


@dataclass(frozen=True)
class IterationRecord:
    """Registro de una iteración o paso de resolución."""

    numero: int
    x: list[float]
    residual: float
    residual_rel: float
    step_diff: float | None = None
    error_abs: float | None = None
    error_rel: float | None = None
    error_pct: float | None = None


@dataclass(frozen=True)
class LinearSystemResult:
    """Resultado estandarizado de un solver de sistemas lineales."""

    metodo: str
    familia: str
    x: FloatArray
    convergio: bool
    iteraciones_realizadas: int
    motivo_parada: str
    tiempo_ms: float
    residual_final: float
    residual_rel_final: float
    error_abs: float | None
    error_rel: float | None
    error_pct: float | None
    historial: list[IterationRecord] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _validate_system(
    A: NDArray[np.float64] | list[list[float]],
    b: NDArray[np.float64] | list[float],
    x0: NDArray[np.float64] | list[float] | None = None,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Valida dimensiones y convierte A, b, x0 a float64."""
    mat_a = np.asarray(A, dtype=np.float64)
    vec_b = np.asarray(b, dtype=np.float64)

    if mat_a.ndim != 2 or mat_a.shape[0] != mat_a.shape[1]:
        raise ValueError(f"La matriz A debe ser cuadrada 2D; forma recibida: {mat_a.shape}.")
    n = mat_a.shape[0]
    if n == 0:
        raise ValueError("La matriz A no puede ser vacía.")
    if vec_b.ndim != 1 or vec_b.shape[0] != n:
        raise ValueError(
            f"El vector b debe tener dimensión ({n},); forma recibida: {vec_b.shape}."
        )

    if x0 is None:
        vec_x0 = np.zeros(n, dtype=np.float64)
    else:
        vec_x0 = np.asarray(x0, dtype=np.float64).copy()
        if vec_x0.ndim != 1 or vec_x0.shape[0] != n:
            raise ValueError(
                f"El vector inicial x0 debe tener dimensión ({n},); forma recibida: {vec_x0.shape}."
            )

    return mat_a, vec_b, vec_x0


def is_strictly_diagonally_dominant(A: FloatArray) -> bool:
    """Verifica si A es estrictamente diagonalmente dominante por filas."""
    diag = np.abs(np.diag(A))
    off_diag = np.sum(np.abs(A), axis=1) - diag
    return bool(np.all(diag > off_diag))


def _spectral_radius(matrix: FloatArray) -> float:
    """Calcula el radio espectral max(|lambda_i|) de una matriz cuadrada."""
    eigvals = np.linalg.eigvals(matrix)
    return float(np.max(np.abs(eigvals)))


def validate_spd(A: FloatArray, sym_rtol: float = 1e-10, sym_atol: float = 1e-12) -> float:
    """Valida estrictamente que A sea Simétrica Definida Positiva (SPD).

    Criterios:
    1. Simetría: ||A - A^T|| dentro de tolerancia (A = A^T).
    2. Definida positiva: todos los eigenvalores de A son estrictamente > 0.

    Retorna el eigenvalor mínimo si es SPD; lanza NonSPDError en caso contrario.
    """
    if not np.allclose(A, A.T, rtol=sym_rtol, atol=sym_atol):
        asym_norm = float(np.linalg.norm(A - A.T, ord=2))
        raise NonSPDError(
            f"La matriz A no es simétrica (||A - A^T||_2 = {asym_norm:.3e} > 0). "
            "El método de Gradiente Conjugado requiere A = A^T."
        )

    sym_a = 0.5 * (A + A.T)
    eigvals = np.linalg.eigvalsh(sym_a)
    min_eig = float(np.min(eigvals))
    if min_eig <= 0.0:
        raise NonSPDError(
            f"La matriz A es simétrica pero NO es definida positiva "
            f"(autovalor mínimo lambda_min = {min_eig:.6e} <= 0). "
            "Gradiente Conjugado requiere x^T A x > 0 para todo x != 0."
        )
    return min_eig


def _build_iteration_record(
    numero: int,
    mat_a: FloatArray,
    vec_x: FloatArray,
    vec_b: FloatArray,
    step_diff: float | None,
    x_ref: FloatArray | None,
) -> IterationRecord:
    """Construye un registro de iteración con residual y errores respecto a x_ref."""
    res = residual_norm(mat_a, vec_x, vec_b)
    res_rel = relative_residual(mat_a, vec_x, vec_b)
    err_abs: float | None = None
    err_rel: float | None = None
    err_pct: float | None = None
    if x_ref is not None:
        errs = vector_error_metrics(x_ref, vec_x)
        err_abs = errs["error_abs"]
        err_rel = errs["error_rel"]
        err_pct = errs["error_pct"]

    return IterationRecord(
        numero=numero,
        x=[float(val) for val in vec_x],
        residual=res,
        residual_rel=res_rel,
        step_diff=step_diff,
        error_abs=err_abs,
        error_rel=err_rel,
        error_pct=err_pct,
    )


def reference_solve(
    A: NDArray[np.float64] | list[list[float]],
    b: NDArray[np.float64] | list[float],
) -> FloatArray:
    """Solución de referencia en precisión float64 usando np.linalg.solve."""
    mat_a, vec_b, _ = _validate_system(A, b)
    return np.asarray(np.linalg.solve(mat_a, vec_b), dtype=np.float64)


def jacobi_solve(
    A: NDArray[np.float64] | list[list[float]],
    b: NDArray[np.float64] | list[float],
    x0: NDArray[np.float64] | list[float] | None = None,
    tol: float = 1e-8,
    max_iter: int = 1000,
    x_ref: NDArray[np.float64] | list[float] | None = None,
) -> LinearSystemResult:
    """Resuelve A x = b mediante el método iterativo de Jacobi desde cero."""
    t_start = perf_counter()
    mat_a, vec_b, vec_x = _validate_system(A, b, x0)
    ref_arr = np.asarray(x_ref, dtype=np.float64) if x_ref is not None else None
    n = mat_a.shape[0]

    diag = np.diag(mat_a)
    if np.any(np.abs(diag) < EPS_MACH):
        raise ValueError("La matriz A tiene ceros en la diagonal; Jacobi no es aplicable.")

    diag_dom = is_strictly_diagonally_dominant(mat_a)
    lower_upper = mat_a - np.diag(diag)
    iter_matrix = -(lower_upper / diag[:, np.newaxis])
    rho_j = _spectral_radius(iter_matrix)

    historial: list[IterationRecord] = []
    convergio = False
    motivo = f"Máximo de iteraciones alcanzado ({max_iter})"

    for k in range(1, max_iter + 1):
        x_new = np.empty(n, dtype=np.float64)
        for i in range(n):
            sigma = float(np.dot(mat_a[i, :], vec_x) - mat_a[i, i] * vec_x[i])
            x_new[i] = (vec_b[i] - sigma) / mat_a[i, i]

        step_diff = float(np.linalg.norm(x_new - vec_x, ord=2))
        vec_x = x_new

        rec = _build_iteration_record(k, mat_a, vec_x, vec_b, step_diff, ref_arr)
        historial.append(rec)

        if not np.isfinite(rec.residual) or rec.residual > 1e100:
            motivo = f"Divergencia numérica detectada en iteración {k} (rho(T_J)={rho_j:.4f})"
            break

        if rec.residual <= tol:
            convergio = True
            motivo = f"Residual ||b - Ax||_2 <= {tol:.1e} alcanzado en iteración {k}"
            break

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    last = historial[-1] if historial else _build_iteration_record(0, mat_a, vec_x, vec_b, None, ref_arr)

    return LinearSystemResult(
        metodo="Jacobi",
        familia="SISTEMAS_LINEALES",
        x=vec_x,
        convergio=convergio,
        iteraciones_realizadas=len(historial),
        motivo_parada=motivo,
        tiempo_ms=elapsed_ms,
        residual_final=last.residual,
        residual_rel_final=last.residual_rel,
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        historial=historial,
        diagnostics={
            "diagonalmente_dominante_estricta": diag_dom,
            "radio_espectral_TJ": rho_j,
            "criterio_convergencia_satisfecho": rho_j < 1.0,
        },
    )


def gauss_seidel_solve(
    A: NDArray[np.float64] | list[list[float]],
    b: NDArray[np.float64] | list[float],
    x0: NDArray[np.float64] | list[float] | None = None,
    tol: float = 1e-8,
    max_iter: int = 1000,
    x_ref: NDArray[np.float64] | list[float] | None = None,
) -> LinearSystemResult:
    """Resuelve A x = b mediante el método iterativo de Gauss-Seidel desde cero."""
    t_start = perf_counter()
    mat_a, vec_b, vec_x = _validate_system(A, b, x0)
    ref_arr = np.asarray(x_ref, dtype=np.float64) if x_ref is not None else None
    n = mat_a.shape[0]

    diag = np.diag(mat_a)
    if np.any(np.abs(diag) < EPS_MACH):
        raise ValueError("La matriz A tiene ceros en la diagonal; Gauss-Seidel no es aplicable.")

    diag_dom = is_strictly_diagonally_dominant(mat_a)
    d_plus_l = np.tril(mat_a)
    u_strict = np.triu(mat_a, k=1)
    # Matriz de iteración T_GS = -(D + L)^{-1} U usando inversa solo para diagnóstico espectral
    t_gs = -np.linalg.inv(d_plus_l) @ u_strict
    rho_gs = _spectral_radius(t_gs)

    historial: list[IterationRecord] = []
    convergio = False
    motivo = f"Máximo de iteraciones alcanzado ({max_iter})"

    for k in range(1, max_iter + 1):
        x_prev = vec_x.copy()
        for i in range(n):
            sum_before = float(np.dot(mat_a[i, :i], vec_x[:i]))
            sum_after = float(np.dot(mat_a[i, i + 1 :], vec_x[i + 1 :]))
            vec_x[i] = (vec_b[i] - sum_before - sum_after) / mat_a[i, i]

        step_diff = float(np.linalg.norm(vec_x - x_prev, ord=2))
        rec = _build_iteration_record(k, mat_a, vec_x, vec_b, step_diff, ref_arr)
        historial.append(rec)

        if not np.isfinite(rec.residual) or rec.residual > 1e100:
            motivo = f"Divergencia numérica detectada en iteración {k} (rho(T_GS)={rho_gs:.4f})"
            break

        if rec.residual <= tol:
            convergio = True
            motivo = f"Residual ||b - Ax||_2 <= {tol:.1e} alcanzado en iteración {k}"
            break

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    last = historial[-1] if historial else _build_iteration_record(0, mat_a, vec_x, vec_b, None, ref_arr)

    return LinearSystemResult(
        metodo="Gauss-Seidel",
        familia="SISTEMAS_LINEALES",
        x=vec_x,
        convergio=convergio,
        iteraciones_realizadas=len(historial),
        motivo_parada=motivo,
        tiempo_ms=elapsed_ms,
        residual_final=last.residual,
        residual_rel_final=last.residual_rel,
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        historial=historial,
        diagnostics={
            "diagonalmente_dominante_estricta": diag_dom,
            "radio_espectral_TGS": rho_gs,
            "criterio_convergencia_satisfecho": rho_gs < 1.0,
        },
    )


def lu_partial_pivot_solve(
    A: NDArray[np.float64] | list[list[float]],
    b: NDArray[np.float64] | list[float],
    x_ref: NDArray[np.float64] | list[float] | None = None,
) -> LinearSystemResult:
    """Resuelve A x = b mediante factorización LU con pivoteo parcial (PA = LU)."""
    t_start = perf_counter()
    mat_a, vec_b, _ = _validate_system(A, b)
    ref_arr = np.asarray(x_ref, dtype=np.float64) if x_ref is not None else None
    n = mat_a.shape[0]

    U = mat_a.copy()
    L = np.eye(n, dtype=np.float64)
    P = np.eye(n, dtype=np.float64)
    swaps = 0

    for k in range(n - 1):
        pivot_rel = int(np.argmax(np.abs(U[k:, k])))
        pivot_row = k + pivot_rel
        if abs(U[pivot_row, k]) < EPS_MACH:
            raise ValueError(f"La matriz A es singular o casi singular en columna {k}.")

        if pivot_row != k:
            U[[k, pivot_row], :] = U[[pivot_row, k], :]
            P[[k, pivot_row], :] = P[[pivot_row, k], :]
            if k > 0:
                L[[k, pivot_row], :k] = L[[pivot_row, k], :k]
            swaps += 1

        for i in range(k + 1, n):
            factor = U[i, k] / U[k, k]
            L[i, k] = factor
            U[i, k:] = U[i, k:] - factor * U[k, k:]

    if abs(U[n - 1, n - 1]) < EPS_MACH:
        raise ValueError("La matriz A es singular; pivote final nulo en U.")

    # Sustitución hacia adelante: L y = P b
    pb = P @ vec_b
    y = np.zeros(n, dtype=np.float64)
    for i in range(n):
        y[i] = pb[i] - float(np.dot(L[i, :i], y[:i]))

    # Sustitución hacia atrás: U x = y
    x = np.zeros(n, dtype=np.float64)
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - float(np.dot(U[i, i + 1 :], x[i + 1 :]))) / U[i, i]

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    rec = _build_iteration_record(1, mat_a, x, vec_b, None, ref_arr)
    fact_err = float(np.linalg.norm(P @ mat_a - L @ U, ord=2))

    return LinearSystemResult(
        metodo="Factorización LU (Pivoteo Parcial)",
        familia="SISTEMAS_LINEALES",
        x=x,
        convergio=True,
        iteraciones_realizadas=1,
        motivo_parada="Factorización directa PA = LU completada",
        tiempo_ms=elapsed_ms,
        residual_final=rec.residual,
        residual_rel_final=rec.residual_rel,
        error_abs=rec.error_abs,
        error_rel=rec.error_rel,
        error_pct=rec.error_pct,
        historial=[rec],
        diagnostics={
            "permutaciones_pivoteo": swaps,
            "error_factorizacion_PA_LU": fact_err,
        },
    )


def conjugate_gradient_solve(
    A: NDArray[np.float64] | list[list[float]],
    b: NDArray[np.float64] | list[float],
    x0: NDArray[np.float64] | list[float] | None = None,
    tol: float = 1e-8,
    max_iter: int = 1000,
    x_ref: NDArray[np.float64] | list[float] | None = None,
) -> LinearSystemResult:
    """Resuelve A x = b mediante Gradiente Conjugado (requiere A SPD)."""
    t_start = perf_counter()
    mat_a, vec_b, vec_x = _validate_system(A, b, x0)
    ref_arr = np.asarray(x_ref, dtype=np.float64) if x_ref is not None else None

    min_eig = validate_spd(mat_a)

    r = vec_b - mat_a @ vec_x
    p = r.copy()
    rs_old = float(np.dot(r, r))

    historial: list[IterationRecord] = []
    convergio = False
    motivo = f"Máximo de iteraciones alcanzado ({max_iter})"

    if np.sqrt(rs_old) <= tol:
        rec = _build_iteration_record(0, mat_a, vec_x, vec_b, 0.0, ref_arr)
        historial.append(rec)
        convergio = True
        motivo = f"Vector inicial ya satisface ||b - Ax||_2 <= {tol:.1e}"
    else:
        for k in range(1, max_iter + 1):
            ap = mat_a @ p
            denom = float(np.dot(p, ap))
            if denom <= 0.0:
                motivo = f"Dirección no conjugada detectada (p^T A p = {denom:.3e} <= 0)"
                break

            alpha = rs_old / denom
            x_next = vec_x + alpha * p
            step_diff = float(np.linalg.norm(x_next - vec_x, ord=2))
            vec_x = x_next
            r = r - alpha * ap
            rs_new = float(np.dot(r, r))

            rec = _build_iteration_record(k, mat_a, vec_x, vec_b, step_diff, ref_arr)
            historial.append(rec)

            if np.sqrt(rs_new) <= tol and rec.residual <= tol:
                convergio = True
                motivo = f"Residual ||b - Ax||_2 <= {tol:.1e} alcanzado en iteración {k}"
                break

            beta = rs_new / (rs_old if rs_old >= EPS_MACH else EPS_MACH)
            p = r + beta * p
            rs_old = rs_new

    elapsed_ms = (perf_counter() - t_start) * 1000.0
    last = historial[-1] if historial else _build_iteration_record(0, mat_a, vec_x, vec_b, None, ref_arr)

    return LinearSystemResult(
        metodo="Gradiente Conjugado (CG)",
        familia="SISTEMAS_LINEALES",
        x=vec_x,
        convergio=convergio,
        iteraciones_realizadas=len(historial),
        motivo_parada=motivo,
        tiempo_ms=elapsed_ms,
        residual_final=last.residual,
        residual_rel_final=last.residual_rel,
        error_abs=last.error_abs,
        error_rel=last.error_rel,
        error_pct=last.error_pct,
        historial=historial,
        diagnostics={
            "es_spd": True,
            "autovalor_minimo": min_eig,
        },
    )
