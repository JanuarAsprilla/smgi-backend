#!/bin/bash

echo "🔄 Iniciando Celery Worker y Beat..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Detener procesos existentes de Celery
echo -e "${YELLOW}Deteniendo procesos existentes de Celery...${NC}"
pkill -f 'celery worker'
pkill -f 'celery beat'
sleep 2

# Crear directorios para logs
mkdir -p logs

# Iniciar Celery Worker
echo -e "${YELLOW}Iniciando Celery Worker...${NC}"
celery -A config worker -l info --logfile=logs/celery_worker.log --detach

# Iniciar Celery Beat
echo -e "${YELLOW}Iniciando Celery Beat...${NC}"
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --logfile=logs/celery_beat.log --detach

sleep 3

echo ""
echo -e "${GREEN}✅ Celery iniciado correctamente${NC}"
echo ""
echo "📋 Logs disponibles en:"
echo "   Worker: logs/celery_worker.log"
echo "   Beat:   logs/celery_beat.log"
echo ""
echo "Para monitorear: tail -f logs/celery_worker.log"
echo "Para detener: pkill -f 'celery'"
