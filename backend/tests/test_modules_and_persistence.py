"""Pruebas de integración para los 4 módulos (3x4 escenarios) y persistencia en BD."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(
    "caso_codigo",
    ["MOD1_DETENCION", "MOD2_DETERIORO", "MOD3_OSCILACIONES", "MOD4_SENSORES"],
)
@pytest.mark.parametrize("escenario", ["NORMAL", "ESTRES", "MAL_CONDICIONADO"])
def test_all_four_modules_three_scenarios_api(caso_codigo: str, escenario: str) -> None:
    """Verifica que los 4 módulos ejecutan NORMAL, ESTRES y MAL_CONDICIONADO con >=2 gráficos."""
    with TestClient(app) as client:
        resp = client.post(
            f"/api/modulos/{caso_codigo}/ejecutar",
            json={"escenario": escenario, "usuario_equipo": "Pytest_Suite"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["simulacion_id"] is not None
        assert data["caso_codigo"] == caso_codigo
        assert data["escenario"] == escenario
        assert len(data["metodos"]) >= 3
        assert len(data["graficos"]) >= 2
        assert len(data["interpretacion_numerica"]) > 20
        assert len(data["interpretacion_problema"]) > 20


def test_persistence_save_retrieve_and_rerun() -> None:
    """Prueba obligatoria: ejecutar -> guardar -> recuperar -> relanzar -> verificar coincidencia."""
    with TestClient(app) as client:
        # 1. Ejecutar con parámetros personalizados y guardar
        create_resp = client.post(
            "/api/modulos/MOD1_DETENCION/ejecutar",
            json={
                "escenario": "NORMAL",
                "parametros_override": {"v0": 7.2, "a0": 1.4, "h": 0.04},
                "usuario_equipo": "Test_Persistencia",
                "notas_usuario": "Prueba de trazabilidad Semana 2",
            },
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        sim_id = created["simulacion_id"]
        assert isinstance(sim_id, int)

        # 2. Listar en historial
        list_resp = client.get("/api/simulaciones", params={"caso_codigo": "MOD1_DETENCION"})
        assert list_resp.status_code == 200
        ids = [item["simulacion_id"] for item in list_resp.json()]
        assert sim_id in ids

        # 3. Recuperar simulación guardada por ID
        get_resp = client.get(f"/api/simulaciones/{sim_id}")
        assert get_resp.status_code == 200
        loaded = get_resp.json()
        assert loaded["simulacion_id"] == sim_id
        assert loaded["parametros_usados"]["v0"] == pytest.approx(7.2)
        assert len(loaded["graficos"]) >= 2
        assert len(loaded["metodos"]) == len(created["metodos"])

        # 4. Relanzar y verificar coincidencia dentro de tolerancia
        rerun_resp = client.post(f"/api/simulaciones/{sim_id}/relanzar")
        assert rerun_resp.status_code == 200
        rerun_data = rerun_resp.json()
        assert rerun_data["coincidencia_exacta"] is True
        assert rerun_data["diferencia_maxima"] <= 1e-12


def test_global_comparison_endpoint() -> None:
    """Verifica el Panel General de Comparación 4x3 en GET /api/comparacion-global."""
    with TestClient(app) as client:
        resp = client.get("/api/comparacion-global")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_modulos"] == 4
        assert data["total_escenarios"] == 12
        assert len(data["filas"]) == 12
        assert len(data["graficos"]) == 2
        for fila in data["filas"]:
            assert len(fila["interpretacion_numerica"]) > 10
            assert len(fila["interpretacion_problema"]) > 10
