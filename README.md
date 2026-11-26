# SIMTELE-RISK — Plataforma de Simulación Numérica y Análisis de Riesgos

> **Contexto académico:** Sistema de transporte por cable inspirado en *Mi Teleférico* (La Paz, Bolivia). Todos los modelos, parámetros y escenarios son estrictamente sintéticos con fines educativos y no representan fallas reales ni tienen conexión con sistemas operativos reales.

**SIMTELE-RISK** es una aplicación web integrada diseñada para formular, resolver, verificar y comparar problemas matemáticos aplicados a la ingeniería de transporte por cable mediante métodos numéricos clásicos, incorporando análisis transversal de teoría de errores y persistencia completa de experimentos.

* **Repositorio GitHub:** [https://github.com/AlejandroQuintelaAguilar/SIMTELE-RISK.git](https://github.com/AlejandroQuintelaAguilar/SIMTELE-RISK.git)
* **Aplicación Web en Producción (Vercel + Neon):** [https://simtele-risk-peach.vercel.app/](https://simtele-risk-peach.vercel.app/)
* **Requerimientos:** [REQUIREMENTS.md](./REQUIREMENTS.md)
* **Instrucciones de ejecución:** [INSTRUCCIONES.md](./INSTRUCCIONES.md)

---

## 1. Arquitectura del Sistema

El proyecto sigue una arquitectura desacoplada en tres capas para garantizar precisión numérica, trazabilidad e independencia entre el motor de cálculo y la interfaz visual:

* **Frontend (`/frontend`):** Interfaz web interactiva con los 4 módulos de estudio, renderizado de fórmulas matemáticas, tablas de iteraciones/refinamiento, visualización gráfica comparativa (solución física vs. convergencia de error) e historial de simulaciones.
* **Backend & Motor Numérico (`/backend`):** API REST desarrollada en Python (FastAPI) con implementaciones propias en precisión `float64` para todos los métodos numéricos y un módulo transversal de teoría de errores (`error_metrics`).
* **Persistencia y Orquestación (`/database` y `docker-compose.yml`):** Base de datos relacional PostgreSQL orquestada mediante Docker Compose (`docker-compose.yml`), que almacena parámetros de entrada, escenarios, iteraciones detalladas, métricas de error y conclusiones técnicas, permitiendo recuperar y relanzar cualquier simulación tras reiniciar la aplicación.

### Estructura del Repositorio

```text
simtele-risk/
├── backend/
│   ├── app/
│   │   ├── api/            # Endpoints REST por módulo e historial
│   │   ├── core/           # Configuración y conexión a BD
│   │   ├── models/         # Modelos ORM (SQLAlchemy)
│   │   └── numerics/       # Motores matemáticos (EDO, Raíces, Sistemas, Interp, Integ, Errores)
│   ├── tests/              # Pruebas unitarias frente a soluciones analíticas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # Tablas de iteración, gráficas y tarjetas de módulos
│   │   ├── pages/          # Inicio, Módulos 1-4, Interpretación e Historial
│   │   └── services/       # Cliente HTTP para la API
│   └── package.json
├── database/
│   └── schema.sql          # DDL, restricciones, índices y datos semilla (3x4 escenarios)
├── docs/                   # Diagrama Entidad-Relación (DER) e informes técnicos
├── docker-compose.yml      # Orquestación de PostgreSQL con Docker
├── REQUIREMENTS.md         # Requerimientos técnicos y dependencias del proyecto
├── INSTRUCCIONES.md        # Guía paso a paso de ejecución
└── README.md
```

---

## 2. Cobertura Matemática y Módulos de Estudio

### Módulos Obligatorios y Escenarios ($4 \times 3$)

Cada módulo ejecuta y contrasta tres condiciones experimentales: **NORMAL**, **ESTRÉS** y **MAL CONDICIONADO**.

| Módulo | Fenómeno Modelado | Métodos Implementados | Solución Analítica / Referencia |
| :--- | :--- | :--- | :--- |
| **1. Detención de Emergencia** | Cinemática y frenado de cabina: $\frac{dx}{dt}=v$, $\frac{dv}{dt}=-a(v,t)$ | • **EDO:** RK2 (Heun), RK4<br>• **Integración:** Trapecio, Simpson 1/3, Romberg<br>• **Raíces:** Bisección, Newton-Raphson, Secante | Desaceleración constante $a_0$:<br>$v(t)=v_0-a_0 t$, $t_{det}=\frac{v_0}{a_0}$, $x_{det}=\frac{v_0^2}{2a_0}$ |
| **2. Deterioro Mecánico** | Evolución de desgaste $D(t)=D_0+\alpha t+\beta t^2$ y calibración $A\mathbf{x}=\mathbf{b}$ | • **Sistemas Lineales (SPD):** Jacobi, Gauss-Seidel, LU, Gradiente Conjugado<br>• **Raíces:** Bisección, Newton-Raphson, Secante | Raíz positiva de cuadrática $D(t)-D_{umbral}=0$ y vector exacto $\mathbf{x}^*$ conocido |
| **3. Oscilaciones por Viento** | Vibración amortiguada forzada: $m\ddot{x}+c\dot{x}+kx=F(t)$ | • **EDO:** RK2, RK4<br>• **Integración:** Trapecio, Simpson 1/3, Romberg sobre $\int x(t)^2\,dt$<br>• **Sistemas Lineales:** Calibración auxiliar SPD | Régimen libre subamortiguado ($F(t)=0$, $\zeta<1$):<br>$x(t)=e^{-\zeta\omega_0 t}[C_1\cos(\omega_d t)+C_2\sin(\omega_d t)]$ |
| **4. Reconstrucción de Sensores** | Interpolación de telemetría con datos ocultos y ruido | • **Interpolación:** Lagrange, Newton (Dif. Divididas), Splines Cúbicos<br>• **Raíces:** Cruce de umbral de alerta | Señales sintéticas $y(t)=\sin(t)$ y $y(t)=e^{-t}\cos(2t)$ con nodos ocultados para validación |

### Teoría de Errores Transversal

Todos los módulos calculan y almacenan sistemáticamente:
* **Error Absoluto:** $E_{abs} = |v_{ref} - v_{aprox}|$
* **Error Relativo y Porcentual:** $E_{rel} = \frac{|v_{ref} - v_{aprox}|}{\max(|v_{ref}|, 10^{-15})}$, $E_{\%} = E_{rel} \times 100\%$
* **Residuales:** $\|\mathbf{b} - A\mathbf{x}\|_2$ en sistemas lineales y $|f(x_k)|$ en búsqueda de raíces.
* **Condicionamiento y Sensibilidad:** Número de condición $\kappa_2(A) = \|A\|_2 \|A^{-1}\|_2$ y amplificación de error ante perturbaciones $\delta \mathbf{b}$.

---

## 3. Requisitos e Instalación

### Prerrequisitos
* **Docker** y **Docker Compose** (para orquestar la base de datos PostgreSQL)
* **Python** 3.10+
* **Node.js** 18+
* *(Alternativa sin Docker)* **PostgreSQL** 14+ instalado localmente

Para el detalle completo de requerimientos, consulta [REQUIREMENTS.md](./REQUIREMENTS.md).

### Paso 1: Configurar y Levantar la Base de Datos (Docker)

```bash
# Levantar PostgreSQL y cargar automáticamente el esquema y datos semilla
docker compose up -d
```

*(Opcional, en instalación local sin Docker):*
```bash
psql -U postgres -c "CREATE DATABASE simtele_risk;"
psql -U postgres -d simtele_risk -f database/schema.sql
```

### Paso 2: Levantar el Backend (API y Motor Numérico)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configurar variable de entorno
export DATABASE_URL="postgresql://postgres:tu_password@localhost:5432/simtele_risk"

# Iniciar servidor FastAPI
uvicorn app.main:app --reload --port 8000
```
La documentación interactiva de la API (Swagger) estará disponible en `http://localhost:8000/docs`.

### Paso 3: Levantar el Frontend

```bash
cd frontend
npm install
npm run dev
```
Acceder a la aplicación web en `http://localhost:5173`.

### Paso 4: Ejecutar Pruebas Unitarias y Scripts (Semanas 1 y 2)

```bash
# Desde la raíz del proyecto (Windows PowerShell)
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\pytest.exe backend/tests -v

# Ejecutar los 3 escenarios del Módulo 2 por consola
.\backend\venv\Scripts\python.exe -m app.modules.modulo2_s1
```

#### Endpoints Principales (API REST)
* `GET /api/health` — Estado de la API y motor de BD (`postgresql` o `sqlite`).
* `GET /api/casos` — Listado de los 4 módulos y sus 12 escenarios predefinidos.
* `POST /api/modulos/{caso_codigo}/ejecutar` — Ejecuta cualquiera de los 4 módulos (`MOD1_DETENCION`, `MOD2_DETERIORO`, `MOD3_OSCILACIONES`, `MOD4_SENSORES`), persiste en BD y retorna resultados + 2 gráficos.
* `GET /api/simulaciones` / `GET /api/simulaciones/{id}` / `POST /api/simulaciones/{id}/relanzar` — Historial persistente, recuperación completa y verificación por relanzamiento.
* `GET /api/comparacion-global` — Matriz comparativa $4 \times 3$ entre los cuatro módulos y sus tres escenarios.

---

## 4. Verificación de Persistencia y Pruebas

Para validar el requisito de trazabilidad de experimentos:
1. Ingresar a cualquiera de los 4 módulos y ejecutar un escenario (`NORMAL`, `ESTRÉS` o `MAL_CONDICIONADO`).
2. Verificar el guardado automático y anotar el `ID` de simulación en la pestaña **Historial**.
3. Detener completamente el servidor backend y reiniciar el servicio de PostgreSQL.
4. Volver a iniciar la aplicación, abrir la simulación desde **Historial**, recuperar sus parámetros, tablas e iteraciones, y ejecutar el botón **Relanzar Simulación** para comprobar la coincidencia numérica dentro de la tolerancia especificada.

---

## 5. Equipo y Menciones

* **Alejandro Quintela Aguilar** — Mención: Desarrollo de Software
* **Dayana Karen Rodriguez Chalco** — Mención: Ingeniería de Sistemas
* **Caleb Mendoza Calderon** — Mención: Desarrollo de Software
* **Aaron Osvaldo Calzada Nina** — Mención: Desarrollo de Software