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

## 3. Ejecutar el Backend (Pendiente — Próximos Pasos)

*Esta sección se completará al implementar la carpeta `/backend` (FastAPI + Motor Numérico).*

```bash
# Referencia prevista:
# cd backend
# python -m venv venv
# venv\Scripts\activate   (Windows) | source venv/bin/activate (Linux/Mac)
# pip install -r requirements.txt
# uvicorn app.main:app --reload --port 8000
```

---

## 4. Ejecutar el Frontend (Pendiente — Próximos Pasos)

*Esta sección se completará al implementar la carpeta `/frontend`.*

```bash
# Referencia prevista:
# cd frontend
# npm install
# npm run dev
```

---

## 5. Verificación y Pruebas (Pendiente — Próximos Pasos)

*Aquí se documentarán los comandos de `pytest` y las pruebas de persistencia extremo a extremo.*
