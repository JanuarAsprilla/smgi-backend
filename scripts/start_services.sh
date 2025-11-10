#!/bin/bash

echo "🚀 Iniciando servicios de SMGI..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[1/5] Limpiando servicios existentes...${NC}"
docker-compose down --remove-orphans 2>/dev/null

echo -e "${YELLOW}[2/5] Iniciando PostgreSQL y Redis con Docker...${NC}"
docker-compose up -d postgres redis

echo -e "${YELLOW}[3/5] Esperando a que PostgreSQL esté listo...${NC}"
for i in {1..30}; do
    if docker exec smgi_postgres pg_isready -U smgi_user -d smgi_db > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL está listo${NC}"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

echo -e "${YELLOW}[4/5] Creando base de datos y habilitando PostGIS...${NC}"
docker exec smgi_postgres psql -U smgi_user -d smgi_db -c "CREATE EXTENSION IF NOT EXISTS postgis;" 2>/dev/null
docker exec smgi_postgres psql -U smgi_user -d smgi_db -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;" 2>/dev/null

echo -e "${YELLOW}[5/5] Verificando Redis...${NC}"
if docker exec smgi_redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}Redis está listo${NC}"
fi

echo ""
echo -e "${GREEN}✅ Servicios iniciados correctamente${NC}"
echo ""
echo "PostgreSQL: localhost:5432"
echo "  Database: smgi_db"
echo "  User: smgi_user"
echo "  Password: smgi_password_2024"
echo ""
echo "Redis: localhost:6379"
echo ""
echo "Para detener los servicios: docker-compose down"
