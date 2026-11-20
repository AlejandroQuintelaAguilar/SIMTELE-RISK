"""Pruebas unitarias para los motores numéricos de la Semana 2 (Raíces, Interpolación, Integración, EDO)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.numerical.integration import (
    IntegrationError,
    composite_simpson_13,
    composite_trapezoid,
    romberg_integrate,
)
from app.numerical.interpolation import (
    build_natural_cubic_spline,
    lagrange_evaluate,
    newton_evaluate,
)
from app.numerical.ode import rk2_heun_solve, rk4_solve
from app.numerical.roots import (
    RootFindingError,
    bisection_solve,
    newton_raphson_solve,
    secant_solve,
)


def test_roots_methods_against_analytical() -> None:
    """Verifica Bisección, Newton-Raphson y Secante en x^2 - 2 = 0."""
    f = lambda x: x**2 - 2.0
    df = lambda x: 2.0 * x
    ref = math.sqrt(2.0)

    r_bis = bisection_solve(f, 1.0, 2.0, tol=1e-10, max_iter=80, x_ref=ref)
    r_newt = newton_raphson_solve(f, df, x0=1.5, tol=1e-10, max_iter=30, x_ref=ref)
    r_sec = secant_solve(f, x0=1.0, x1=2.0, tol=1e-10, max_iter=30, x_ref=ref)

    for res in (r_bis, r_newt, r_sec):
        assert res.convergio is True
        assert res.raiz == pytest.approx(ref, abs=1e-9)
        assert res.error_abs is not None and res.error_abs < 1e-9

    # Intervalo sin cambio de signo debe lanzar RootFindingError
    with pytest.raises(RootFindingError):
        bisection_solve(f, 2.0, 3.0)

    # Derivada nula en Newton-Raphson se maneja de forma controlada
    r_flat = newton_raphson_solve(lambda x: (x - 1.0) ** 2, lambda x: 2.0 * (x - 1.0), x0=1.0)
    assert r_flat.convergio is True

    r_zero_df = newton_raphson_solve(lambda x: x**2 + 1.0, lambda x: 2.0 * x, x0=0.0)
    assert r_zero_df.convergio is False
    assert "Derivada nula" in r_zero_df.motivo_parada


def test_interpolation_lagrange_newton_spline() -> None:
    """Verifica equivalencia Lagrange/Newton en polinomios y estabilidad de Splines."""
    x_nodes = np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float64)
    poly = lambda x: 2.0 * x**2 - 3.0 * x + 1.0
    y_nodes = np.array([poly(float(v)) for v in x_nodes], dtype=np.float64)
    x_eval = np.array([0.5, 1.5, 2.5], dtype=np.float64)
    y_expected = np.array([poly(float(v)) for v in x_eval], dtype=np.float64)

    y_lag = lagrange_evaluate(x_nodes, y_nodes, x_eval)
    y_newt, _ = newton_evaluate(x_nodes, y_nodes, x_eval)
    spline = build_natural_cubic_spline(x_nodes, y_nodes)
    y_spl = spline.evaluate(x_eval)

    np.testing.assert_allclose(y_lag, y_expected, atol=1e-12)
    np.testing.assert_allclose(y_newt, y_expected, atol=1e-12)
    assert np.max(np.abs(y_spl - y_expected)) < 0.25  # Spline natural tiene S''=0 en bordes

    # En función de Runge con 15 nodos, spline cúbico supera ampliamente a Lagrange en bordes
    x_runge = np.linspace(-5.0, 5.0, 15, dtype=np.float64)
    runge = lambda t: 1.0 / (1.0 + 25.0 * t**2)
    y_runge = np.array([runge(float(t)) for t in x_runge], dtype=np.float64)
    mask = np.ones(15, dtype=bool)
    mask[[1, 13]] = False
    x_vis, y_vis = x_runge[mask], y_runge[mask]
    x_hid, y_hid = x_runge[~mask], y_runge[~mask]

    err_lag = float(np.max(np.abs(lagrange_evaluate(x_vis, y_vis, x_hid) - y_hid)))
    err_spl = float(np.max(np.abs(build_natural_cubic_spline(x_vis, y_vis).evaluate(x_hid) - y_hid)))
    assert err_spl < err_lag


def test_integration_trapezoid_simpson_romberg() -> None:
    """Verifica Trapecio, Simpson 1/3 y Romberg contra integral analítica exacta."""
    # int_0^pi sin(x) dx = 2.0
    ref = 2.0
    r_trap = composite_trapezoid(math.sin, 0.0, math.pi, [4, 8, 16, 32, 64], ref_value=ref)
    r_simp = composite_simpson_13(math.sin, 0.0, math.pi, [4, 8, 16, 32, 64], ref_value=ref)
    r_romb = romberg_integrate(math.sin, 0.0, math.pi, max_levels=8, tol=1e-11, ref_value=ref)

    assert r_trap.error_abs is not None and r_trap.error_abs < 5e-4
    assert r_simp.error_abs is not None and r_simp.error_abs < 1e-7
    assert r_romb.convergio is True
    assert r_romb.error_abs is not None and r_romb.error_abs < 1e-11

    # Refinamiento en Trapecio debe reducir error al aumentar n
    assert r_trap.refinamiento[-1].error_abs < r_trap.refinamiento[0].error_abs

    # Simpson 1/3 rechaza subintervalos impares
    with pytest.raises(IntegrationError):
        composite_simpson_13(math.sin, 0.0, math.pi, [3])


def test_ode_rk2_and_rk4_accuracy_and_stability() -> None:
    """Verifica RK2 (Heun) y RK4 frente a solución analítica e inestabilidad rígida."""
    # y' = -2y, y(0) = 1 => y(t) = exp(-2t)
    rhs = lambda _t, y: np.array([-2.0 * y[0]], dtype=np.float64)
    ref = lambda t: np.array([math.exp(-2.0 * t)], dtype=np.float64)

    res_rk2 = rk2_heun_solve(rhs, 0.0, 2.0, [1.0], h=0.05, ref_fn=ref)
    res_rk4 = rk4_solve(rhs, 0.0, 2.0, [1.0], h=0.05, ref_fn=ref)

    assert res_rk2.convergio and res_rk4.convergio
    assert res_rk4.error_abs_max is not None and res_rk2.error_abs_max is not None
    assert res_rk4.error_abs_max < res_rk2.error_abs_max
    assert res_rk4.error_abs_max < 1e-6

    # Sistema muy rígido con paso h demasiado grande detecta desbordamiento
    stiff_rhs = lambda _t, y: np.array([-1000.0 * y[0]], dtype=np.float64)
    res_unstable = rk2_heun_solve(stiff_rhs, 0.0, 5.0, [1.0], h=0.5)
    assert res_unstable.convergio is False
