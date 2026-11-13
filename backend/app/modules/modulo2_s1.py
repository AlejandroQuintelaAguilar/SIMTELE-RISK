"""Módulo 2 (Semana 1): Deterioro Mecánico y Calibración SPD.

Construye y ejecuta los 3 escenarios obligatorios (NORMAL, ESTRES, MAL_CONDICIONADO)
para el sistema lineal de calibración A x = b con los 4 solvers desde cero
(Jacobi, Gauss-Seidel, LU con pivoteo parcial, Gradiente Conjugado) más la
solución de referencia y análisis transversal de errores y sensibilidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from app.core.error_metrics import (
    FloatArray,
    PerturbationSensitivityResult,
    condition_number_2,
    sensitivity_perturbation_test,
)
from app.numerical.linear_systems import (
    LinearSystemResult,
    conjugate_gradient_solve,
    gauss_seidel_solve,
    jacobi_solve,
    lu_partial_pivot_solve,
    reference_solve,
)

ScenarioType = Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]


@dataclass(frozen=True)
class ScenarioConfig:
    """Configuración matemática reproducible de un escenario del Módulo 2."""

    tipo: ScenarioType
    nombre_descriptivo: str
    dimension_n: int
    tol: float
    max_iter: int
    A: FloatArray
    b: FloatArray
    x_exact_planted: FloatArray


@dataclass(frozen=True)
class Modulo2ExecutionReport:
    """Reporte completo de ejecución de un escenario del Módulo 2."""

    escenario: ScenarioType
    nombre_descriptivo: str
    dimension_n: int
    tol: float
    max_iter: int
    kappa_2: float
    x_referencia: list[float]
    resultados_metodos: list[LinearSystemResult]
    sensibilidad: PerturbationSensitivityResult
    interpretacion_numerica: str
    interpretacion_problema: str


def build_scenario(tipo: ScenarioType, tol_override: float | None = None, max_iter_override: int | None = None) -> ScenarioConfig:
    """Construye la matriz SPD A, vector exacto x* y término independiente b."""
    if tipo == "NORMAL":
        n = 4
        A = np.diag(np.full(n, 10.0, dtype=np.float64))
        for i in range(n - 1):
            A[i, i + 1] = -1.5
            A[i + 1, i] = -1.5
        x_star = np.array([1.20, 0.85, 0.55, 0.30], dtype=np.float64)
        b = A @ x_star
        return ScenarioConfig(
            tipo="NORMAL",
            nombre_descriptivo="Calibración SPD bien condicionada (n=4, kappa_2 < 10)",
            dimension_n=n,
            tol=tol_override if tol_override is not None else 1e-8,
            max_iter=max_iter_override if max_iter_override is not None else 500,
            A=A,
            b=b,
            x_exact_planted=x_star,
        )

    if tipo == "ESTRES":
        n = 12
        A = np.diag(np.full(n, 6.0, dtype=np.float64))
        for i in range(n - 1):
            A[i, i + 1] = -1.0
            A[i + 1, i] = -1.0
        for i in range(n - 2):
            A[i, i + 2] = -0.25
            A[i + 2, i] = -0.25
        x_star = np.linspace(1.5, 0.4, n, dtype=np.float64)
        b = A @ x_star
        return ScenarioConfig(
            tipo="ESTRES",
            nombre_descriptivo="Sistema SPD ampliado (n=12) con tolerancia estricta 1e-11",
            dimension_n=n,
            tol=tol_override if tol_override is not None else 1e-11,
            max_iter=max_iter_override if max_iter_override is not None else 2000,
            A=A,
            b=b,
            x_exact_planted=x_star,
        )

    if tipo == "MAL_CONDICIONADO":
        n = 6
        idx = np.arange(n, dtype=np.float64)
        # Matriz de Hilbert 6x6 (SPD clásica severamente mal condicionada, kappa_2 > 10^7)
        H = 1.0 / (idx[:, None] + idx[None, :] + 1.0)
        A = H + 1e-10 * np.eye(n, dtype=np.float64)
        x_star = np.array([1.0, 0.8, 0.6, 0.4, 0.25, 0.15], dtype=np.float64)
        b = A @ x_star
        return ScenarioConfig(
            tipo="MAL_CONDICIONADO",
            nombre_descriptivo="Matriz SPD tipo Hilbert perturbada (n=6, kappa_2 > 10^5)",
            dimension_n=n,
            tol=tol_override if tol_override is not None else 1e-8,
            max_iter=max_iter_override if max_iter_override is not None else 5000,
            A=A,
            b=b,
            x_exact_planted=x_star,
        )

    raise ValueError(f"Escenario no reconocido: {tipo}")


def _build_interpretations(
    cfg: ScenarioConfig,
    kappa_2: float,
    resultados: list[LinearSystemResult],
    sensibilidad: PerturbationSensitivityResult,
) -> tuple[str, str]:
    """Genera interpretaciones técnica-numérica y física del problema."""
    converged_names = [r.metodo for r in resultados if r.convergio]
    failed_names = [r.metodo for r in resultados if not r.convergio]

    if cfg.tipo == "NORMAL":
        num_txt = (
            f"Matriz SPD estrictamente diagonalmente dominante con kappa_2(A) = {kappa_2:.3f} (< 10). "
            f"Los 4 métodos convergen con precisión cercana a 1e-8 y amplificación de perturbación "
            f"acotada ({sensibilidad.amplification_factor:.2f}x)."
        )
        prob_txt = (
            "Los parámetros calibrados de rigidez y desgaste por tramo de cable son numéricamente "
            "estables ante incertidumbre normal de sensores de inspección."
        )
    elif cfg.tipo == "ESTRES":
        gs_res = next(r for r in resultados if r.metodo == "Gauss-Seidel")
        cg_res = next(r for r in resultados if r.metodo == "Gradiente Conjugado (CG)")
        num_txt = (
            f"Sistema SPD de dimensión n={cfg.dimension_n} con tolerancia estricta {cfg.tol:.1e} "
            f"y kappa_2(A) = {kappa_2:.3f}. Todos los métodos convergen: CG logra la tolerancia en "
            f"{cg_res.iteraciones_realizadas} iteraciones ({cg_res.tiempo_ms:.3f} ms) frente a "
            f"{gs_res.iteraciones_realizadas} de Gauss-Seidel."
        )
        prob_txt = (
            "La calibración simultánea de 12 torres/tramos bajo operación continua mantiene buena "
            "estabilidad numérica y permite detectar tramos con mayor tasa de desgaste acumulado."
        )
    else:
        num_txt = (
            f"Sistema severamente mal condicionado con kappa_2(A) = {kappa_2:.3e} (> 10^5). "
            f"Una perturbación controlada de {sensibilidad.relative_perturbation_b:.1e} en b provoca "
            f"una variación relativa de {sensibilidad.relative_change_x:.3e} en x "
            f"(factor de amplificación = {sensibilidad.amplification_factor:.2f}x). "
            f"Métodos convergentes: {converged_names}; métodos sin convergencia: {failed_names} "
            "(distinguiendo fallo de convergencia iterativa del mal condicionamiento propio de A)."
        )
        prob_txt = (
            "Las ecuaciones de calibración están casi colineales: pequeñas imprecisiones en las "
            "mediciones de tensión/desgaste generan grandes distorsiones en los coeficientes estimados, "
            "por lo que se requiere regularización o mejor instrumentación antes de programar mantenimiento."
        )
    return num_txt, prob_txt


def run_modulo2_scenario(
    tipo: ScenarioType,
    tol: float | None = None,
    max_iter: int | None = None,
) -> Modulo2ExecutionReport:
    """Ejecuta los 4 métodos lineales + referencia y análisis de sensibilidad."""
    cfg = build_scenario(tipo, tol_override=tol, max_iter_override=max_iter)
    x_ref = reference_solve(cfg.A, cfg.b)
    kappa_2 = condition_number_2(cfg.A)

    res_jacobi = jacobi_solve(cfg.A, cfg.b, tol=cfg.tol, max_iter=cfg.max_iter, x_ref=x_ref)
    res_gs = gauss_seidel_solve(cfg.A, cfg.b, tol=cfg.tol, max_iter=cfg.max_iter, x_ref=x_ref)
    res_lu = lu_partial_pivot_solve(cfg.A, cfg.b, x_ref=x_ref)
    res_cg = conjugate_gradient_solve(cfg.A, cfg.b, tol=cfg.tol, max_iter=cfg.max_iter, x_ref=x_ref)

    resultados = [res_jacobi, res_gs, res_lu, res_cg]

    # Prueba de sensibilidad usando el solver directo propio LU con pivoteo parcial
    sensibilidad = sensitivity_perturbation_test(
        cfg.A,
        cfg.b,
        x_ref,
        solver_fn=lambda mat, vec: lu_partial_pivot_solve(mat, vec).x,
        rel_perturbation=1e-4,
    )

    num_txt, prob_txt = _build_interpretations(cfg, kappa_2, resultados, sensibilidad)

    return Modulo2ExecutionReport(
        escenario=cfg.tipo,
        nombre_descriptivo=cfg.nombre_descriptivo,
        dimension_n=cfg.dimension_n,
        tol=cfg.tol,
        max_iter=cfg.max_iter,
        kappa_2=kappa_2,
        x_referencia=[float(v) for v in x_ref],
        resultados_metodos=resultados,
        sensibilidad=sensibilidad,
        interpretacion_numerica=num_txt,
        interpretacion_problema=prob_txt,
    )


def run_all_scenarios() -> dict[ScenarioType, Modulo2ExecutionReport]:
    """Ejecuta los 3 escenarios obligatorios del Módulo 2."""
    return {
        "NORMAL": run_modulo2_scenario("NORMAL"),
        "ESTRES": run_modulo2_scenario("ESTRES"),
        "MAL_CONDICIONADO": run_modulo2_scenario("MAL_CONDICIONADO"),
    }


def _format_cli_summary(reports: dict[ScenarioType, Modulo2ExecutionReport]) -> str:
    """Formatea un resumen legible por consola de los 3 escenarios."""
    lines: list[str] = []
    for tipo, rep in reports.items():
        lines.append("=" * 88)
        lines.append(f"ESCENARIO: {tipo} | {rep.nombre_descriptivo}")
        lines.append(
            f"n={rep.dimension_n} | tol={rep.tol:.1e} | kappa_2(A)={rep.kappa_2:.4e} | "
            f"Amplificación(delta_b=1e-4)={rep.sensibilidad.amplification_factor:.2f}x"
        )
        lines.append("-" * 88)
        lines.append(
            f"{'Método':<34} {'Conv':<6} {'Iter':>6} {'Tiempo(ms)':>11} {'Residual':>12} {'E_rel':>12} {'E_%':>10}"
        )
        for m in rep.resultados_metodos:
            e_rel_str = f"{m.error_rel:.3e}" if m.error_rel is not None else "N/A"
            e_pct_str = f"{m.error_pct:.3e}" if m.error_pct is not None else "N/A"
            lines.append(
                f"{m.metodo:<34} {str(m.convergio):<6} {m.iteraciones_realizadas:>6} "
                f"{m.tiempo_ms:>11.4f} {m.residual_final:>12.3e} {e_rel_str:>12} {e_pct_str:>10}"
            )
        lines.append(f"Interpretación Numérica: {rep.interpretacion_numerica}")
    return "\n".join(lines)


if __name__ == "__main__":
    all_reports = run_all_scenarios()
    print(_format_cli_summary(all_reports))
