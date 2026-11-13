"""Suite de pruebas unitarias e integración para la Semana 1 de SIMTELE-RISK."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.error_metrics import (
    EPS_MACH,
    absolute_error,
    condition_number_2,
    percentage_error,
    relative_error,
    relative_residual,
    residual_norm,
    sensitivity_perturbation_test,
    vector_error_metrics,
)
from app.main import app
from app.modules.modulo2_s1 import run_modulo2_scenario
from app.numerical.linear_systems import (
    NonSPDError,
    conjugate_gradient_solve,
    gauss_seidel_solve,
    jacobi_solve,
    lu_partial_pivot_solve,
    reference_solve,
)


def test_error_metrics_zero_division_protection() -> None:
    """Verifica protección contra división por cero cuando |v_ref| < 1e-15."""
    assert absolute_error(0.0, 1e-6) == pytest.approx(1e-6)
    rel = relative_error(0.0, 1e-12)
    assert np.isfinite(rel)
    assert rel == pytest.approx(1e-12 / EPS_MACH)

    pct = percentage_error(1e-20, 2e-15)
    assert np.isfinite(pct)
    assert pct == pytest.approx((abs(1e-20 - 2e-15) / EPS_MACH) * 100.0)


def test_error_metrics_vector_and_residual() -> None:
    """Verifica métricas vectoriales, residual L2 y número de condición."""
    A = np.array([[4.0, 1.0], [1.0, 3.0]], dtype=np.float64)
    x_ref = np.array([1.0, 2.0], dtype=np.float64)
    b = A @ x_ref
    x_approx = np.array([1.01, 1.99], dtype=np.float64)

    errs = vector_error_metrics(x_ref, x_approx)
    expected_abs = float(np.linalg.norm(x_ref - x_approx, ord=2))
    assert errs["error_abs"] == pytest.approx(expected_abs)
    assert errs["error_rel"] == pytest.approx(expected_abs / float(np.linalg.norm(x_ref, ord=2)))

    r = residual_norm(A, x_approx, b)
    assert r == pytest.approx(float(np.linalg.norm(b - A @ x_approx, ord=2)))
    assert relative_residual(A, x_ref, b) < 1e-15
    assert condition_number_2(A) < 5.0


def test_all_four_solvers_converge_to_x_star() -> None:
    """Verifica que los 4 solvers desde cero coinciden con x* en matriz SPD 4x4."""
    A = np.array(
        [
            [10.0, -1.0, 0.0, 0.0],
            [-1.0, 10.0, -1.0, 0.0],
            [0.0, -1.0, 10.0, -1.0],
            [0.0, 0.0, -1.0, 10.0],
        ],
        dtype=np.float64,
    )
    x_star = np.array([1.5, -0.5, 2.0, 0.75], dtype=np.float64)
    b = A @ x_star
    x_ref = reference_solve(A, b)
    np.testing.assert_allclose(x_ref, x_star, atol=1e-13)

    res_j = jacobi_solve(A, b, tol=1e-10, max_iter=200, x_ref=x_star)
    res_gs = gauss_seidel_solve(A, b, tol=1e-10, max_iter=200, x_ref=x_star)
    res_lu = lu_partial_pivot_solve(A, b, x_ref=x_star)
    res_cg = conjugate_gradient_solve(A, b, tol=1e-10, max_iter=50, x_ref=x_star)

    for res in (res_j, res_gs, res_lu, res_cg):
        assert res.convergio is True
        np.testing.assert_allclose(res.x, x_star, atol=1e-9)
        assert res.error_rel is not None and res.error_rel < 1e-9

    # Gauss-Seidel debe converger en menos o igual iteraciones que Jacobi aquí
    assert res_gs.iteraciones_realizadas <= res_j.iteraciones_realizadas


def test_lu_partial_pivoting_handles_zero_pivot() -> None:
    """Verifica que LU con pivoteo parcial resuelve sistemas con A[0, 0] == 0."""
    A = np.array(
        [
            [0.0, 2.0, 1.0, 0.0],
            [3.0, 1.0, 0.0, 1.0],
            [1.0, 0.0, 4.0, 1.0],
            [0.0, 1.0, 1.0, 5.0],
        ],
        dtype=np.float64,
    )
    x_star = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    b = A @ x_star

    res_lu = lu_partial_pivot_solve(A, b, x_ref=x_star)
    assert res_lu.convergio is True
    assert res_lu.diagnostics["permutaciones_pivoteo"] >= 1
    np.testing.assert_allclose(res_lu.x, x_star, atol=1e-12)


def test_conjugate_gradient_rejects_non_spd_matrices() -> None:
    """Verifica que Gradiente Conjugado lanza NonSPDError ante matrices no SPD."""
    # Matriz no simétrica
    A_asym = np.array(
        [
            [5.0, 2.0, 0.0, 0.0],
            [0.0, 5.0, 1.0, 0.0],
            [0.0, 1.0, 5.0, 1.0],
            [0.0, 0.0, 1.0, 5.0],
        ],
        dtype=np.float64,
    )
    b = np.ones(4, dtype=np.float64)
    with pytest.raises(NonSPDError, match="simétrica"):
        conjugate_gradient_solve(A_asym, b)

    # Matriz simétrica indefinida (tiene autovalor negativo)
    A_indef = np.array(
        [
            [2.0, 3.0, 0.0, 0.0],
            [3.0, 2.0, 0.0, 0.0],
            [0.0, 0.0, 4.0, 0.0],
            [0.0, 0.0, 0.0, 5.0],
        ],
        dtype=np.float64,
    )
    with pytest.raises(NonSPDError, match="definida positiva"):
        conjugate_gradient_solve(A_indef, b)


def test_modulo2_three_scenarios_and_sensitivity() -> None:
    """Valida los 3 escenarios obligatorios del Módulo 2."""
    rep_normal = run_modulo2_scenario("NORMAL")
    assert rep_normal.dimension_n == 4
    assert rep_normal.kappa_2 < 10.0
    assert all(r.convergio for r in rep_normal.resultados_metodos)

    rep_estres = run_modulo2_scenario("ESTRES")
    assert rep_estres.dimension_n == 12
    assert rep_estres.tol == pytest.approx(1e-11)
    assert all(r.convergio for r in rep_estres.resultados_metodos)

    rep_mal = run_modulo2_scenario("MAL_CONDICIONADO")
    assert rep_mal.dimension_n == 6
    assert rep_mal.kappa_2 > 1e5
    assert rep_mal.sensibilidad.amplification_factor > 1e3


def test_sensitivity_perturbation_direct() -> None:
    """Verifica la prueba de sensibilidad con perturbación controlada 1e-4."""
    A = np.diag([10.0, 10.0, 10.0, 10.0]).astype(np.float64)
    x_ref = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    b = A @ x_ref
    sens = sensitivity_perturbation_test(
        A, b, x_ref, solver_fn=lambda mat, vec: lu_partial_pivot_solve(mat, vec).x, rel_perturbation=1e-4
    )
    assert sens.relative_perturbation_b == pytest.approx(1e-4, rel=1e-6)
    assert sens.amplification_factor == pytest.approx(1.0, rel=1e-2)


def test_api_endpoints_semana1() -> None:
    """Valida /api/health, /api/casos y /api/modulo2/sistemas-lineales/ejecutar."""
    with TestClient(app) as client:
        r_health = client.get("/api/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "ok"

        r_casos = client.get("/api/casos")
        assert r_casos.status_code == 200
        casos = r_casos.json()
        assert len(casos) == 4
        codigos = [c["codigo"] for c in casos]
        assert codigos == [
            "MOD1_DETENCION",
            "MOD2_DETERIORO",
            "MOD3_OSCILACIONES",
            "MOD4_SENSORES",
        ]

        r_exec = client.post(
            "/api/modulo2/sistemas-lineales/ejecutar",
            json={"escenario": "NORMAL"},
        )
        assert r_exec.status_code == 200
        data = r_exec.json()
        assert data["escenario"] == "NORMAL"
        assert data["kappa_2"] < 10.0
        assert len(data["resultados_metodos"]) == 4
