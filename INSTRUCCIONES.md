# Instrucciones de Ejecución — SIMTELE-RISK

> Guía paso a paso para configurar y ejecutar **SIMTELE-RISK**. Este documento se irá ampliando conforme se implementen el Backend y el Frontend en los siguientes pasos.

**Repositorio GitHub:** [https://github.com/AlejandroQuintelaAguilar/SIMTELE-RISK.git](https://github.com/AlejandroQuintelaAguilar/SIMTELE-RISK.git)

---

## 1. Clonar el Repositorio

```bash
git clone https://github.com/AlejandroQuintelaAguilar/SIMTELE-RISK.git
cd SIMTELE-RISK
```

*(Asegúrate de cumplir con los prerrequisitos descritos en [REQUIREMENTS.md](./REQUIREMENTS.md)).*

---

## 2. Levantar la Base de Datos con Docker (Paso 1)

El proyecto utiliza **Docker Compose** (`docker-compose.yml`) para orquestar PostgreSQL y cargar automáticamente el esquema y los datos semilla (`database/schema.sql`).

### Iniciar el contenedor

```bash
docker compose up -d
```

### Verificar el estado del servicio

```bash
docker compose ps
docker compose logs -f db
```

El contenedor estará listo cuando el `healthcheck` indique `healthy`.

### Conectarse por consola (opcional)

```bash
docker exec -it simtele_risk_db psql -U postgres -d simtele_risk
```

### Detener o reiniciar la base de datos

```bash
# Detener conservando los datos en el volumen
docker compose down

# Detener y eliminar el volumen (reinicia el esquema y datos semilla desde cero)
docker compose down -v
```

---

## 3. Ejecutar el Backend (Semana 1 — Activo)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Iniciar servidor FastAPI (usa PostgreSQL si está activo, o respaldo SQLite automático)
uvicorn app.main:app --reload --port 8000
```

La documentación interactiva de la API estará disponible en `http://localhost:8000/docs`.

---

## 4. Ejecutar el Frontend (Semana 1 — Activo)

```powershell
cd frontend
npm install
npm run dev
```

Acceder a la interfaz web en `http://localhost:5173`.

---

## 5. Verificación y Pruebas (Semana 1 — Activo)

```powershell
# Desde la raíz del proyecto
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\pytest.exe backend/tests -v

# Ejecutar el comparativo de los 3 escenarios del Módulo 2 por consola
.\backend\venv\Scripts\python.exe -m app.modules.modulo2_s1
```
