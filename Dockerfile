FROM node:20-bookworm-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./ 
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim AS runtime

ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./backend
COPY --from=frontend /frontend/out /app/static
ENV PORT=8003
ENV DB_PATH=/app/db/finally.db
ENV FINALLY_STATIC_DIR=/app/static
ENV LLM_MOCK=false
ENV MASSIVE_API_KEY=""

EXPOSE 8003
VOLUME ["/app/db"]

WORKDIR /app/backend
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
