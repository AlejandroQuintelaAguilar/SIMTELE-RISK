# Requerimientos del Proyecto — SIMTELE-RISK

> Documento vivo de requerimientos técnicos y dependencias del proyecto **SIMTELE-RISK**. Se irá completando conforme avancen las etapas de implementación (Backend, Motor Numérico y Frontend).

**Repositorio oficial:** [https://github.com/AlejandroQuintelaAguilar/SIMTELE-RISK.git](https://github.com/AlejandroQuintelaAguilar/SIMTELE-RISK.git)

---

## 1. Prerrequisitos del Sistema

| Herramienta | Versión Mínima Recomendada | Propósito |
| :--- | :--- | :--- |
| **Git** | 2.30+ | Control de versiones y clonación del repositorio |
| **Docker** | 24.0+ | Contenerización y orquestación de la base de datos |
| **Docker Compose** | v2.20+ | Definición y levantamiento del servicio PostgreSQL (`docker-compose.yml`) |
| **Python** | 3.10+ | Ejecución del Backend (FastAPI) y motor numérico en `float64` |
| **Node.js / npm** | 18+ / 9+ | Ejecución y compilación del Frontend web |

---

## 2. Base de Datos y Orquestación (Paso 1 — Completado)

* **Motor:** PostgreSQL 16 (`postgres:16-alpine` mediante Docker).
* **Orquestación:** `docker-compose.yml` en la raíz del proyecto.
* **Inicialización automática:** El archivo `database/schema.sql` se monta en `/docker-entrypoint-initdb.d/01_schema.sql` para crear las 6 tablas (`caso_estudio`, `escenario`, `simulacion`, `ejecucion_metodo`, `iteracion_resultado`, `resultado_resumen`) y cargar los 12 escenarios semilla ($4 \times 3$).

### Variables de Entorno (Base de Datos)

| Variable | Valor por Defecto | Descripción |
| :--- | :--- | :--- |
| `POSTGRES_USER` | `postgres` | Usuario administrador de PostgreSQL |
| `POSTGRES_PASSWORD` | `simtele_pass` | Contraseña de conexión |
| `POSTGRES_DB` | `simtele_risk` | Nombre de la base de datos |
| `POSTGRES_PORT` | `5433` | Puerto expuesto en el host (evita conflicto con PostgreSQL local en 5432) |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:simtele_pass@localhost:5433/simtele_risk` | Cadena de conexión para el Backend |

---

## 3. Dependencias del Backend (Pendiente — Próximos Pasos)

Se definirán formalmente en `backend/requirements.txt`. Dependencias base previstas:
* `fastapi` — Framework API REST
* `uvicorn[standard]` — Servidor ASGI
* `sqlalchemy` — ORM para persistencia en PostgreSQL
* `psycopg2-binary` — Driver de conexión a PostgreSQL
* `pydantic` — Validación de esquemas de entrada/salida
* `numpy` — Soporte de arreglos en precisión `float64` (para verificación/referencias)
* `pytest` — Pruebas unitarias frente a soluciones analíticas

---

## 4. Dependencias del Frontend (Pendiente — Próximos Pasos)

Se definirán en `frontend/package.json`:
* Framework web (React + Vite)
* Cliente HTTP (`axios` o `fetch`)
* Librería de gráficas comparativas y renderizado matemático (KaTeX / MathJax)
