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

## Shelf Monitoring

The project currently supports an end-to-end shelf monitoring workflow using an OpenCV ROI-based detector.

The monitoring pipeline is:

```text
HTTP Request
    ↓
ShelfConfiguration
    ↓
StockDetectorFactory
    ↓
OpenCVROIDetector
    ↓
StockDetectionService
    ↓
StockObservationService
    ↓
PostgreSQL
```

A shelf configuration defines:

- Camera
- Product
- Detector type
- Empty shelf reference image
- Detection threshold
- Regions of interest (ROIs)

Each ROI represents one physical product slot on the shelf.

### Demo Dataset

The current controlled dataset contains a shelf with four slots:

```text
data/
├── references/
│   └── shelf_01_empty.png
└── samples/
    ├── shelf_01_full.png
    ├── shelf_01_75.png
    ├── shelf_01_50.png
    ├── shelf_01_25.png
    └── shelf_01_empty.png
```

Ground truth:

| Image | Units | Stock |
| --- | ---: | ---: |
| `shelf_01_empty.png` | 0 / 4 | 0% |
| `shelf_01_25.png` | 1 / 4 | 25% |
| `shelf_01_50.png` | 2 / 4 | 50% |
| `shelf_01_75.png` | 3 / 4 | 75% |
| `shelf_01_full.png` | 4 / 4 | 100% |

### OpenCV ROI Baseline

The first detector implementation uses classical computer vision.

For every configured ROI:

1. Extract the same region from the empty reference image.
2. Extract the region from the current shelf image.
3. Convert both regions to grayscale.
4. Calculate their absolute pixel difference using OpenCV.
5. Calculate the mean difference score.
6. Mark the slot as occupied when the score exceeds the configured threshold.

The current controlled dataset uses:

```text
difference_threshold = 20.0
```

During baseline evaluation, the detector produced:

| Image | Expected | Detected | Absolute Error |
| --- | ---: | ---: | ---: |
| `shelf_01_empty.png` | 0 | 0 | 0 |
| `shelf_01_25.png` | 1 | 1 | 0 |
| `shelf_01_50.png` | 2 | 2 | 0 |
| `shelf_01_75.png` | 3 | 3 | 0 |
| `shelf_01_full.png` | 4 | 4 | 0 |

```text
MAE = 0.00 units
```

This result represents a controlled baseline and should not be interpreted as real-world model accuracy. The generated images can contain small differences in lighting, geometry, and background, while real camera environments introduce additional variation.

Future experiments will compare this classical approach against ML-based detectors using the same ground-truth evaluation strategy.

### ROI Visualization

ROIs can be visually inspected before running the detector:

```bash
cd apps/backend
uv run python scripts/preview_rois.py
```

The generated preview is stored under:

```text
data/generated/shelf_01_rois.png
```

This is useful for verifying that each ROI corresponds to the intended physical shelf slot.

### Evaluate the OpenCV Detector

Run the controlled evaluation with:

```bash
cd apps/backend
uv run python scripts/evaluate_opencv_roi.py
```

The script reports:

- Expected units
- Detected units
- Difference score for every ROI
- Mean Absolute Error (MAE)

Example:

```text
OpenCV ROI evaluation
----------------------------------------------------------------------------------------------
Image                   Expected  Detected     ROI 1     ROI 2     ROI 3     ROI 4
----------------------------------------------------------------------------------------------
shelf_01_empty.png             0         0      0.00      0.00      0.00      0.00
shelf_01_25.png                1         1     24.84     17.36     13.32     13.28
shelf_01_50.png                2         2     24.29     24.26     10.96      6.40
shelf_01_75.png                3         3     24.74     24.70     22.15      6.96
shelf_01_full.png              4         4     25.12     25.42     23.65     23.47
----------------------------------------------------------------------------------------------
MAE: 0.00 units
Difference threshold: 20.00
```

### Create a Shelf Configuration

A shelf configuration must exist before running the monitoring pipeline.

Example:

```bash
curl -X POST \
  "http://localhost:8000/shelf-configurations" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "<CAMERA_ID>",
    "product_id": "<PRODUCT_ID>",
    "detector_type": "opencv_roi",
    "reference_image_path": "../../data/references/shelf_01_empty.png",
    "detector_config": {
      "difference_threshold": 20.0,
      "regions": [
        {
          "x": 20,
          "y": 94,
          "width": 378,
          "height": 639
        },
        {
          "x": 438,
          "y": 94,
          "width": 378,
          "height": 639
        },
        {
          "x": 856,
          "y": 94,
          "width": 378,
          "height": 639
        },
        {
          "x": 1274,
          "y": 94,
          "width": 378,
          "height": 639
        }
      ]
    }
  }'
```

Use the ROI coordinates validated for the actual reference image.

### Run Shelf Monitoring

Once a configuration exists, manually trigger a monitoring cycle:

```bash
curl -X POST \
  "http://localhost:8000/shelf-configurations/<CONFIGURATION_ID>/monitor" \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "../../data/samples/shelf_01_50.png"
  }'
```

For the 50% sample, the expected result is:

```json
{
  "camera_id": "<CAMERA_ID>",
  "product_id": "<PRODUCT_ID>",
  "detected_units": 2,
  "shelf_capacity": 4,
  "stock_percentage": 50.0,
  "detector_name": "opencv_roi"
}
```

The resulting `StockObservation` is persisted in PostgreSQL and can be retrieved with:

```bash
curl http://localhost:8000/stock-observations
```

This validates the current end-to-end workflow:

```text
Shelf image
    ↓
ShelfConfiguration (PostgreSQL)
    ↓
StockDetectorFactory
    ↓
OpenCV ROI detection
    ↓
Stock calculation
    ↓
StockObservation (PostgreSQL)
```

At this stage monitoring is triggered manually through the API. Periodic execution and automatic image acquisition will be introduced in a later milestone.