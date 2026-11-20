"""Módulo 3: Oscilaciones por Viento.

Simulación de respuesta dinámica amortiguada forzada:
    m * x'' + c * x' + k * x = F0 * sin(omega * t)
mediante EDO (RK2 Heun y RK4) e integración de energía acumulada
int_0^T x(t)^2 dt (Trapecio, Simpson 1/3 y Romberg).
"""

from __future__ import annotations

import math
from typing import Any, Callable, Literal

import numpy as np

from app.core.error_metrics import FloatArray
from app.numerical.integration import composite_simpson_13, composite_trapezoid, romberg_integrate
from app.numerical.ode import rk2_heun_solve, rk4_solve

ScenarioType = Literal["NORMAL", "ESTRES", "MAL_CONDICIONADO"]


def _default_params(tipo: ScenarioType) -> dict[str, Any]:
    if tipo == "NORMAL":
        return {
            "m": 1200.0,
            "c": 480.0,
            "k": 3000.0,
            "F0": 150.0,
            "omega": 0.8,
            "x0": 0.05,
            "v0": 0.0,
            "h": 0.02,
            "T": 20.0,
        }
    if tipo == "ESTRES":
        return {
            "m": 1200.0,
            "c": 180.0,
            "k": 3000.0,
            "F0": 850.0,
            "omega": 1.55,
            "x0": 0.10,
            "v0": 0.0,
            "h": 0.05,
            "T": 120.0,
        }
    if tipo == "MAL_CONDICIONADO":
        return {
            "m": 1200.0,
            "c": 2400.0,
            "k": 450000.0,
            "F0": 200.0,
            "omega": 2.0,
            "x0": 0.05,
            "v0": 0.0,
            "h": 0.12,
            "T": 10.0,
        }
    raise ValueError(f"Escenario no reconocido: {tipo}")


def _build_analytical_fn(
    m: float, c: float, k: float, f0: float, omega: float, x0: float, v0: float
) -> tuple[Callable[[float], FloatArray] | None, dict[str, float]]:
    """Construye la solución analítica exacta para régimen subamortiguado (zeta < 1)."""
    omega0 = math.sqrt(k / m)
    zeta = c / (2.0 * math.sqrt(m * k))
    meta = {"omega0": omega0, "zeta": zeta}

    if zeta >= 1.0:
        return None, meta

    omega_d = omega0 * math.sqrt(1.0 - zeta**2)
    denom = (k - m * omega**2) ** 2 + (c * omega) ** 2
    ap = f0 * (k - m * omega**2) / denom if denom > 1e-15 else 0.0
    bp = -f0 * (c * omega) / denom if denom > 1e-15 else 0.0

    c1 = x0 - bp
    v_h0 = v0 - omega * ap
    c2 = (v_h0 + zeta * omega0 * c1) / omega_d
    decay = zeta * omega0

    def exact_vec(t: float) -> FloatArray:
        env = math.exp(-decay * t)
        cos_d = math.cos(omega_d * t)
        sin_d = math.sin(omega_d * t)
        x_h = env * (c1 * cos_d + c2 * sin_d)
        v_h = env * (
            (-decay * c1 + omega_d * c2) * cos_d
            + (-decay * c2 - omega_d * c1) * sin_d
        )
        x_p = ap * math.sin(omega * t) + bp * math.cos(omega * t)
        v_p = ap * omega * math.cos(omega * t) - bp * omega * math.sin(omega * t)
        return np.array([x_h + x_p, v_h + v_p], dtype=np.float64)

    return exact_vec, {**meta, "omega_d": omega_d}


def run_modulo3(
    tipo: ScenarioType,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta el Módulo 3 completo para el escenario y parámetros indicados."""
    params = _default_params(tipo)
    if overrides:
        for key, val in overrides.items():
            if val is not None and key in params:
                params[key] = val

    m = float(params["m"])
    c = float(params["c"])
    k = float(params["k"])
    f0 = float(params["F0"])
    omega = float(params["omega"])
    x0 = float(params["x0"])
    v0 = float(params["v0"])
    h = float(params["h"])
    T = float(params["T"])

    if m <= 0.0 or k <= 0.0 or c < 0.0 or h <= 0.0 or T <= 0.0:
        raise ValueError("Se requiere m > 0, k > 0, c >= 0, h > 0 y T > 0.")

    def ode_rhs(t: float, y: FloatArray) -> FloatArray:
        pos = float(y[0])
        vel = float(y[1])
        accel = (f0 * math.sin(omega * t) - c * vel - k * pos) / m
        return np.array([vel, accel], dtype=np.float64)

    exact_fn, dyn_meta = _build_analytical_fn(m, c, k, f0, omega, x0, v0)
    ref_type = "ANALITICA"

    if exact_fn is None:
        ref_type = "NUMERICA_ALTA_PRECISION"
        h_ref = min(h / 20.0, 0.002)
        ref_run = rk4_solve(ode_rhs, 0.0, T, [x0, v0], h=h_ref)
        t_ref_arr = np.asarray(ref_run.t_values, dtype=np.float64)
        y_ref_arr = np.asarray(ref_run.y_values, dtype=np.float64)

        def ref_fn(t: float) -> FloatArray:
            x_i = float(np.interp(t, t_ref_arr, y_ref_arr[:, 0]))
            v_i = float(np.interp(t, t_ref_arr, y_ref_arr[:, 1]))
            return np.array([x_i, v_i], dtype=np.float64)
    else:
        ref_fn = exact_fn

    y0_vec = np.array([x0, v0], dtype=np.float64)
    res_rk2 = rk2_heun_solve(ode_rhs, 0.0, T, y0_vec, h=h, ref_fn=ref_fn)
    res_rk4 = rk4_solve(ode_rhs, 0.0, T, y0_vec, h=h, ref_fn=ref_fn)

    # Integración de energía/intensidad acumulada int_0^T x(t)^2 dt usando la señal de referencia
    def x_sq_fn(t: float) -> float:
        x_val = float(ref_fn(t)[0])
        return x_val * x_val

    energy_ref_romberg = romberg_integrate(x_sq_fn, 0.0, T, max_levels=10, tol=1e-11)
    energy_ref = energy_ref_romberg.valor

    sub_list = [16, 32, 64, 128] if T >= 50.0 else [8, 16, 32, 64]
    res_trap = composite_trapezoid(x_sq_fn, 0.0, T, sub_list, ref_value=energy_ref)
    res_simp = composite_simpson_13(x_sq_fn, 0.0, T, sub_list, ref_value=energy_ref)
    res_romb = romberg_integrate(x_sq_fn, 0.0, T, max_levels=9, tol=1e-7, ref_value=energy_ref)

    amp_max_ref = max(abs(float(ref_fn(float(t))[0])) for t in np.linspace(0.0, T, 250))
    amp_max_rk4 = max(abs(y[0]) for y in res_rk4.y_values)
    amp_max_rk2 = max(abs(y[0]) for y in res_rk2.y_values)

    metodos = []
    for ode_res, amp_max in ((res_rk2, amp_max_rk2), (res_rk4, amp_max_rk4)):
        metodos.append(
            {
                "familia": "EDO",
                "metodo": ode_res.metodo,
                "convergio": ode_res.convergio,
                "iteraciones_realizadas": ode_res.pasos_realizados,
                "tiempo_ms": ode_res.tiempo_ms,
                "valor_principal": amp_max,
                "etiqueta_valor": f"amp_max={amp_max:.6f} m",
                "residual": ode_res.error_abs_max,
                "error_abs": ode_res.error_abs_final,
                "error_rel": ode_res.error_rel_final,
                "error_pct": ode_res.error_pct_final,
                "motivo_parada": ode_res.motivo_parada,
                "detalle_tabla": [
                    {
                        "paso": s.numero,
                        "t": s.t,
                        "aprox": s.y,
                        "ref": s.y_ref,
                        "error_abs": s.error_abs,
                        "error_rel": s.error_rel,
                    }
                    for s in ode_res.historial[:80]
                ],
            }
        )

    for integ in (res_trap, res_simp, res_romb):
        metodos.append(
            {
                "familia": "INTEGRACION",
                "metodo": f"{integ.metodo} (∫x² dt)",
                "convergio": integ.convergio,
                "iteraciones_realizadas": integ.iteraciones_realizadas,
                "tiempo_ms": integ.tiempo_ms,
                "valor_principal": integ.valor,
                "etiqueta_valor": f"I={integ.valor:.6f} m²·s",
                "residual": integ.error_abs,
                "error_abs": integ.error_abs,
                "error_rel": integ.error_rel,
                "error_pct": integ.error_pct,
                "motivo_parada": integ.motivo_parada,
                "detalle_tabla": [
                    {
                        "paso": st.numero,
                        "subintervalos": st.subintervalos,
                        "paso_h": st.paso_h,
                        "aprox": st.valor_aprox,
                        "error_abs": st.error_abs,
                        "error_rel": st.error_rel,
                    }
                    for st in integ.refinamiento
                ],
            }
        )

    # Muestreo para gráficos (limitamos puntos si T es largo)
    t_dense = np.linspace(0.0, T, 160)
    x_ref_dense = [float(ref_fn(float(t))[0]) for t in t_dense]

    def _safe_clip(vals: list[float], limit: float = 5.0) -> list[float]:
        return [max(min(v, limit), -limit) for v in vals]

    graficos = [
        {
            "id": "modulo3_oscilacion",
            "titulo": "Desplazamiento Lateral x(t) [m] — RK2 vs RK4 vs Referencia",
            "x_label": "Tiempo t [s]",
            "y_label": "Desplazamiento x(t) [m]",
            "y_scale": "linear",
            "series": [
                {
                    "name": "Referencia Exacta",
                    "x": [float(t) for t in t_dense],
                    "y": x_ref_dense,
                    "mode": "line",
                },
                {
                    "name": "RK2 (Heun)",
                    "x": res_rk2.t_values[:200],
                    "y": _safe_clip([y[0] for y in res_rk2.y_values[:200]]),
                    "mode": "line",
                },
                {
                    "name": "RK4 (Clásico)",
                    "x": res_rk4.t_values[:200],
                    "y": _safe_clip([y[0] for y in res_rk4.y_values[:200]]),
                    "mode": "line",
                },
            ],
        },
        {
            "id": "modulo3_errores",
            "titulo": "Error Global EDO ||y_ref - y_aprox||_2 (Escala Logarítmica)",
            "x_label": "Tiempo t [s]",
            "y_label": "Error Absoluto L2",
            "y_scale": "log",
            "series": [
                {
                    "name": "Error RK2 (Heun)",
                    "x": [s.t for s in res_rk2.historial[1:200]],
                    "y": [max(min(s.error_abs or 1e-16, 1e12), 1e-16) for s in res_rk2.historial[1:200]],
                    "mode": "line",
                },
                {
                    "name": "Error RK4 (Clásico)",
                    "x": [s.t for s in res_rk4.historial[1:200]],
                    "y": [max(min(s.error_abs or 1e-16, 1e12), 1e-16) for s in res_rk4.historial[1:200]],
                    "mode": "line",
                },
            ],
        },
    ]

    if tipo == "NORMAL":
        interp_num = (
            f"Régimen subamortiguado (zeta={dyn_meta['zeta']:.3f}, omega0={dyn_meta['omega0']:.3f} rad/s). "
            f"Con paso h={h} s, RK4 reduce el error máximo a {res_rk4.error_abs_max:.2e} frente a "
            f"{res_rk2.error_abs_max:.2e} de RK2."
        )
        interp_prob = (
            f"Con brisa moderada (F0={f0} N), la amplitud máxima es {amp_max_ref:.4f} m y la energía "
            f"acumulada int x² dt = {energy_ref:.4f} m²·s, permaneciendo dentro de oscilaciones suaves."
        )
    elif tipo == "ESTRES":
        interp_num = (
            f"Ventana prolongada T={T} s cercana a resonancia (omega={omega} rad/s vs omega0={dyn_meta['omega0']:.3f} rad/s): "
            f"RK2 acumula deriva de fase/amplitud (error max={res_rk2.error_abs_max:.2e}), mientras RK4 conserva "
            f"fidelidad (error max={res_rk4.error_abs_max:.2e})."
        )
        interp_prob = (
            f"El forzamiento cercano a la frecuencia natural eleva la amplitud hasta {amp_max_ref:.3f} m "
            f"y exige evaluar criterios de parada operativa por confort/seguridad."
        )
    else:
        interp_num = (
            f"Sistema rígido (stiff) con k={k} N/m (omega0={dyn_meta['omega0']:.2f} rad/s) y paso explícito h={h} s: "
            f"h*omega0 = {h * dyn_meta['omega0']:.2f} supera la región de estabilidad absoluta de RK2/RK4 explícitos, "
            f"causando inestabilidad numérica (RK2 conv={res_rk2.convergio}, RK4 conv={res_rk4.convergio})."
        )
        interp_prob = (
            "La divergencia observada es una inestabilidad del integrador numérico explícito ante rigidez alta, "
            "no un colapso físico real de la cabina (la solución física exacta permanece acotada en ~"
            f"{amp_max_ref:.4f} m)."
        )

    return {
        "caso_codigo": "MOD3_OSCILACIONES",
        "escenario": tipo,
        "nombre_descriptivo": {
            "NORMAL": "Vibración subamortiguada con brisa moderada",
            "ESTRES": "Ráfagas cercanas a resonancia en ventana prolongada",
            "MAL_CONDICIONADO": "Sistema rígido (stiff) con alta rigidez y paso crítico",
        }[tipo],
        "parametros_usados": params,
        "referencia": {
            "tipo": ref_type,
            "omega0": dyn_meta["omega0"],
            "zeta": dyn_meta["zeta"],
            "amplitud_max_ref": amp_max_ref,
            "energia_acumulada_ref": energy_ref,
        },
        "metodos": metodos,
        "graficos": graficos,
        "interpretacion_numerica": interp_num,
        "interpretacion_problema": interp_prob,
    }
