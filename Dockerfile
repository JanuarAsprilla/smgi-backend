# Usa Python como base
FROM python:3.11-slim

# Evita preguntas interactivas
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema (incluye GDAL, GEOS, PROJ y Postgres client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    postgresql-client \
    gcc \
    python3-dev \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

# Configurar variable de entorno para GDAL
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
ENV PATH="/usr/lib/gdal-bin:$PATH"

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements/ /app/requirements/

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install -r requirements/base.txt && \
    pip install -r requirements/dev.txt || true && \
    pip install gunicorn

# Copiar el resto del proyecto
COPY . .

# Exponer puerto de Django
EXPOSE 8000

# Comando de inicio
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
