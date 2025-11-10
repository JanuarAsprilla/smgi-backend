#!/bin/bash

echo "🚀 SMGI - Sistema de Monitoreo Geoespacial Inteligente"
echo "========================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar si Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker no está corriendo${NC}"
    echo "Por favor inicia Docker Desktop y vuelve a intentar."
    exit 1
fi

echo -e "${YELLOW}Paso 1: Iniciando servicios (PostgreSQL + Redis)...${NC}"
./scripts/start_services.sh

echo ""
echo -e "${YELLOW}Paso 2: Configurando base de datos...${NC}"
./scripts/setup_database.sh

echo ""
echo -e "${YELLOW}Paso 3: Iniciando Celery (Worker + Beat)...${NC}"
./scripts/start_celery.sh

echo ""
echo -e "${GREEN}✅ ¡Todo listo! El sistema está configurado.${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📌 Para iniciar el servidor Django:"
echo "   python manage.py runserver"
echo ""
echo "🌐 URLs disponibles:"
echo "   Admin:    http://localhost:8000/admin/"
echo "   API:      http://localhost:8000/api/"
echo "   Docs:     http://localhost:8000/api/schema/swagger-ui/"
echo ""
echo "👤 Credenciales:"
echo "   Admin:     admin / admin123"
echo "   Analyst:   analyst / analyst123"
echo "   Developer: developer / dev123"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
