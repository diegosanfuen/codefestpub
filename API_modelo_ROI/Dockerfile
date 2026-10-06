# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ENV PYTHONPATH=/app:/app/app
WORKDIR /app

# Dependencia típica para scikit-learn (OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Instalar dependencias (poda)
COPY requirements-prod.txt /app/requirements-prod.txt
RUN pip install --upgrade pip \
 && pip install -r /app/requirements-prod.txt

# Copiamos el proyecto
# (Ajusta si tu repo tiene más cosas; lo normal es copiar todo)
COPY . /app

# Ejecutar tests unitarios (quality gate en build)
# Ruta de tests en tu repo: app/tests
RUN python -m unittest discover -s app/tests -v

# Asegurar directorios que tu app espera (por si vienen vacíos)
RUN mkdir -p /app/modelos /app/database /app/backups

# Usuario no-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck opcional
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# Gunicorn: 1-2 workers suele ir bien si haces carga de modelos en RAM.
# Si el modelo es pesado, mejor 1 worker para no duplicar memoria.
#ENV APP_MODULE="wsgi:app"
#ENV PORT=8000
#CMD ["sh", "-c", "gunicorn ${APP_MODULE} --bind 0.0.0.0:${PORT}"]

COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "-c", "tr -d '\\r' < /entrypoint.sh > /tmp/entrypoint.sh && sh /tmp/entrypoint.sh"]