FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app/apps/backend

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY apps/backend/pyproject.toml apps/backend/uv.lock ./

RUN uv sync \
    --frozen \
    --no-dev \
    --no-install-project

COPY apps/backend/alembic.ini ./alembic.ini
COPY apps/backend/alembic ./alembic
COPY apps/backend/app ./app

RUN uv sync \
    --frozen \
    --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]