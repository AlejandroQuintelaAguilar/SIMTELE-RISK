"""Motor transversal de teoría de errores en precisión float64.

Provee funciones puras y tipadas para cuantificar errores absolutos, relativos,
porcentuales, residuales, número de condición espectral y sensibilidad ante
perturbaciones controladas en sistemas lineales.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray

EPS_MACH: float = 1e-15

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PerturbationSensitivityResult:
    """Resultado de la prueba de sensibilidad ante perturbación controlada."""

    relative_perturbation_b: float
    relative_change_x: float
    amplification_factor: float
    condition_number_2: float
    delta_b_norm: float
    delta_x_norm: float


def _as_float64_vector(v: NDArray[np.float64] | list[float]) -> FloatArray:
    """Convierte una entrada en vector 1D de tipo float64."""
    arr = np.asarray(v, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"Se esperaba un vector 1D, se recibió dimensión {arr.ndim}.")
    return arr


def _as_float64_matrix(A: NDArray[np.float64] | list[list[float]]) -> FloatArray:
    """Convierte una entrada en matriz 2D cuadrada de tipo float64."""
    mat = np.asarray(A, dtype=np.float64)
    if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
        raise ValueError(f"Se esperaba una matriz cuadrada 2D, se recibió forma {mat.shape}.")
    return mat


def absolute_error(v_ref: float, v_approx: float) -> float:
    """Calcula el error absoluto escalar: E_abs = |v_ref - v_approx|."""
    return float(abs(np.float64(v_ref) - np.float64(v_approx)))


def relative_error(v_ref: float, v_approx: float, eps: float = EPS_MACH) -> float:
    """Calcula el error relativo escalar protegido contra división por cero.

    Cuando |v_ref| < eps, utiliza eps en el denominador para evitar desbordamiento
    o división por cero.
    """
    ref = float(np.float64(v_ref))
    approx = float(np.float64(v_approx))
    denom = abs(ref) if abs(ref) >= eps else eps
    return float(abs(ref - approx) / denom)


def percentage_error(v_ref: float, v_approx: float, eps: float = EPS_MACH) -> float:
    """Calcula el error porcentual escalar: E_% = E_rel * 100."""
    return float(relative_error(v_ref, v_approx, eps=eps) * 100.0)


def vector_error_metrics(
    v_ref: NDArray[np.float64] | list[float],
    v_approx: NDArray[np.float64] | list[float],
    eps: float = EPS_MACH,
) -> dict[str, float]:
    """Calcula E_abs, E_rel y E_% en norma euclidiana L2 para vectores."""
    ref_vec = _as_float64_vector(v_ref)
    approx_vec = _as_float64_vector(v_approx)
    if ref_vec.shape != approx_vec.shape:
        raise ValueError(
            f"Dimensiones incompatibles: v_ref={ref_vec.shape}, v_approx={approx_vec.shape}."
        )

    e_abs = float(np.linalg.norm(ref_vec - approx_vec, ord=2))
    ref_norm = float(np.linalg.norm(ref_vec, ord=2))
    denom = ref_norm if ref_norm >= eps else eps
    e_rel = float(e_abs / denom)
    e_pct = float(e_rel * 100.0)
    return {
        "error_abs": e_abs,
        "error_rel": e_rel,
        "error_pct": e_pct,
    }


def residual_norm(
    A: NDArray[np.float64] | list[list[float]],
    x: NDArray[np.float64] | list[float],
    b: NDArray[np.float64] | list[float],
) -> float:
    """Calcula la norma euclidiana del residual: ||r||_2 = ||b - A x||_2."""
    mat_a = _as_float64_matrix(A)
    vec_x = _as_float64_vector(x)
    vec_b = _as_float64_vector(b)
    if mat_a.shape[1] != vec_x.shape[0] or mat_a.shape[0] != vec_b.shape[0]:
        raise ValueError("Dimensiones incompatibles entre A, x y b.")
    r = vec_b - mat_a @ vec_x
    return float(np.linalg.norm(r, ord=2))


def relative_residual(
    A: NDArray[np.float64] | list[list[float]],
    x: NDArray[np.float64] | list[float],
    b: NDArray[np.float64] | list[float],
    eps: float = EPS_MACH,
) -> float:
    """Calcula el residual relativo: ||b - A x||_2 / max(||b||_2, eps)."""
    vec_b = _as_float64_vector(b)
    r_norm = residual_norm(A, x, vec_b)
    b_norm = float(np.linalg.norm(vec_b, ord=2))
    denom = b_norm if b_norm >= eps else eps
    return float(r_norm / denom)


def condition_number_2(A: NDArray[np.float64] | list[list[float]]) -> float:
    """Calcula el número de condición espectral kappa_2(A) = ||A||_2 ||A^{-1}||_2."""
    mat_a = _as_float64_matrix(A)
    return float(np.linalg.cond(mat_a, p=2))


def sensitivity_perturbation_test(
    A: NDArray[np.float64] | list[list[float]],
    b: NDArray[np.float64] | list[float],
    x_ref: NDArray[np.float64] | list[float],
    solver_fn: Callable[[FloatArray, FloatArray], FloatArray],
    rel_perturbation: float = 1e-4,
    seed: int = 42,
    eps: float = EPS_MACH,
) -> PerturbationSensitivityResult:
    """Evalúa la amplificación de error ante una perturbación controlada delta_b.

    Construye una perturbación determinista delta_b tal que
    ||delta_b||_2 / ||b||_2 = rel_perturbation (por defecto 1e-4), resuelve
    A x_pert = b + delta_b mediante solver_fn y calcula el factor de amplificación:
        (||delta_x||_2 / ||x_ref||_2) / (||delta_b||_2 / ||b||_2).
    """
    mat_a = _as_float64_matrix(A)
    vec_b = _as_float64_vector(b)
    vec_x = _as_float64_vector(x_ref)

    b_norm = float(np.linalg.norm(vec_b, ord=2))
    x_norm = float(np.linalg.norm(vec_x, ord=2))
    b_denom = b_norm if b_norm >= eps else eps
    x_denom = x_norm if x_norm >= eps else eps

    rng = np.random.default_rng(seed)
    direction = rng.standard_normal(vec_b.shape[0]).astype(np.float64)
    dir_norm = float(np.linalg.norm(direction, ord=2))
    if dir_norm < eps:
        direction = np.ones_like(vec_b, dtype=np.float64)
        dir_norm = float(np.linalg.norm(direction, ord=2))

    delta_b = (direction / dir_norm) * (rel_perturbation * b_denom)
    delta_b_norm = float(np.linalg.norm(delta_b, ord=2))
    rel_b = float(delta_b_norm / b_denom)

    x_pert = _as_float64_vector(solver_fn(mat_a, vec_b + delta_b))
    delta_x = x_pert - vec_x
    delta_x_norm = float(np.linalg.norm(delta_x, ord=2))
    rel_x = float(delta_x_norm / x_denom)

    amp_factor = float(rel_x / (rel_b if rel_b >= eps else eps))
    kappa_2 = condition_number_2(mat_a)

    return PerturbationSensitivityResult(
        relative_perturbation_b=rel_b,
        relative_change_x=rel_x,
        amplification_factor=amp_factor,
        condition_number_2=kappa_2,
        delta_b_norm=delta_b_norm,
        delta_x_norm=delta_x_norm,
    )
