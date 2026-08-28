# Shelf Stock Monitor

Sistema de monitoreo de stock en estanterías mediante visión computacional.

El proyecto compara diferentes motores de visión para estimar el stock disponible, comenzando con un baseline basado en OpenCV y posteriormente incorporando modelos YOLO.

Los experimentos serán evaluados mediante métricas reproducibles y registrados con MLflow.

## Stack

### Backend

- Python 3.12
- FastAPI
- Pydantic Settings
- SQLAlchemy 2
- Alembic
- PostgreSQL
- psycopg
- OpenCV

### Infraestructura

- Docker
- Docker Compose
- uv

### Machine Learning / Computer Vision

- OpenCV
- YOLO
- Roboflow
- MLflow

### Frontend

Se incorporará posteriormente cuando existan datos de stock e históricos que visualizar.

Stack previsto:

- React
- Vite
- TypeScript
- Tailwind CSS

---

## Estructura del proyecto

```text
shelf-stock-monitor/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   └── main.py
│   │   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   └── .env.example
│   │
│   └── frontend/
│
├── data/
│   ├── generated/
│   └── raw/
│
├── docs/
│   └── architecture/
│
├── ml/
│   ├── benchmarks/
│   ├── evaluation/
│   └── training/
│
├── docker-compose.yml
├── .env.example
├── .python-version
└── README.md
```

---

# Desarrollo local

## Requisitos

Se requiere:

- Git
- Docker
- Docker Compose
- uv

No es necesario instalar PostgreSQL localmente.

PostgreSQL se ejecuta mediante Docker.

Tampoco es necesario compilar OpenCV manualmente.

---

## 1. Clonar el repositorio

```bash
git clone git@github.com:juandtap/shelf-stock-monitor.git
cd shelf-stock-monitor
```

---

## 2. Instalar uv

### Linux / WSL

Instalar `uv` utilizando el instalador oficial:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reiniciar la terminal o cargar nuevamente el shell.

Verificar:

```bash
uv --version
```

---

## 3. Instalar Python

El proyecto utiliza Python 3.12.

Desde la raíz del repositorio:

```bash
uv python install 3.12
```

Verificar las versiones disponibles:

```bash
uv python list
```

---

## 4. Configurar el backend

Entrar al backend:

```bash
cd apps/backend
```

Crear el entorno virtual:

```bash
uv venv --python 3.12
```

Esto crea:

```text
apps/backend/.venv/
```

No se debe subir `.venv` al repositorio.

---

## 5. Instalar dependencias

Desde:

```text
apps/backend/
```

ejecutar:

```bash
uv sync --dev
```

`uv` utiliza:

```text
pyproject.toml
uv.lock
```

para reconstruir el entorno de desarrollo.

No es necesario ejecutar manualmente:

```text
pip install -r requirements.txt
```

---

## 6. Variables de entorno del backend

Desde:

```text
apps/backend/
```

crear el archivo `.env`:

```bash
cp .env.example .env
```

Ejemplo:

```env
APP_NAME=Shelf Stock Monitor API
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000

DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=shelf_stock
DATABASE_USER=shelf_stock
DATABASE_PASSWORD=change_me
```

El archivo `.env` contiene configuración local y no debe subirse a Git.

---

## 7. Variables de entorno de Docker

Volver a la raíz:

```bash
cd ../..
```

Crear:

```bash
cp .env.example .env
```

Ejemplo:

```env
POSTGRES_DB=shelf_stock
POSTGRES_USER=shelf_stock
POSTGRES_PASSWORD=change_me
POSTGRES_PORT=5432
```

Los valores de conexión deben coincidir con la configuración del backend.

---

## 8. Levantar PostgreSQL

Desde la raíz:

```bash
docker compose up -d postgres
```

Verificar:

```bash
docker compose ps
```

PostgreSQL debería aparecer como:

```text
healthy
```

Para revisar logs:

```bash
docker compose logs postgres
```

---

## 9. Ejecutar migraciones

Entrar nuevamente al backend:

```bash
cd apps/backend
```

Ejecutar:

```bash
uv run alembic upgrade head
```

Verificar la migración actual:

```bash
uv run alembic current
```

---

## 10. Ejecutar FastAPI

Desde:

```text
apps/backend/
```

ejecutar:

```bash
uv run uvicorn app.main:app --reload
```

La API estará disponible en:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "environment": "development"
}
```

Documentación OpenAPI:

```text
http://127.0.0.1:8000/docs
```

---

# Flujo rápido después de cambiar de PC

Una vez configurada la máquina por primera vez, normalmente solo será necesario:

```bash
git pull

docker compose up -d postgres

cd apps/backend

uv sync --dev

uv run alembic upgrade head

uv run uvicorn app.main:app --reload
```

---

# Calidad de código

Ejecutar Ruff:

```bash
uv run ruff check .
```

Verificar formato:

```bash
uv run ruff format --check .
```

Aplicar formato:

```bash
uv run ruff format .
```

Ejecutar MyPy:

```bash
uv run mypy app
```

Ejecutar tests:

```bash
uv run pytest
```

Antes de realizar un commit se recomienda ejecutar:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

---

# Alembic

Después de modificar modelos SQLAlchemy:

```bash
uv run alembic revision --autogenerate -m "migration description"
```

Revisar siempre el archivo generado antes de aplicarlo.

Aplicar:

```bash
uv run alembic upgrade head
```

Consultar estado:

```bash
uv run alembic current
```

Consultar historial:

```bash
uv run alembic history
```

---

# PostgreSQL

Acceder directamente a PostgreSQL:

```bash
docker compose exec postgres \
    psql -U shelf_stock -d shelf_stock
```

Listar tablas:

```sql
\dt
```

Salir:

```sql
\q
```

---

# Detener el entorno

Detener los contenedores:

```bash
docker compose down
```

Los datos de PostgreSQL permanecen almacenados en el volumen Docker.

Para eliminar también los datos locales:

```bash
docker compose down -v
```

> `docker compose down -v` elimina la base de datos local. Utilizarlo únicamente cuando se quiera reiniciar completamente el entorno.

---

# Git

El repositorio utiliza `master` como rama principal de desarrollo.

El flujo habitual será:

```text
feature/*
    ↓
master
    ↓
production
```

La rama `production` se preparará posteriormente como distribución limpia del sistema.

No deben subirse al repositorio:

- `.env`
- `.venv`
- datasets locales
- modelos entrenados
- artefactos de MLflow

Sí deben versionarse:

- `.env.example`
- `.python-version`
- `pyproject.toml`
- `uv.lock`
- migraciones de Alembic
- código fuente
- tests
- documentación