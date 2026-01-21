FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema (GDAL incluido)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    postgresql-client \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Variables para que Django encuentre GDAL
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/libgeos_c.so

WORKDIR /app

# Copiar requirements
COPY requirements.txt /app/

# Instalar dependencias Python
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copiar proyecto
COPY . /app/

# Render usa el puerto dinámico $PORT
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
