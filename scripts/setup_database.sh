#!/bin/bash

echo "🔧 Configurando base de datos de SMGI..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[1/6] Eliminando migraciones antiguas...${NC}"
find apps/*/migrations -type f -name "*.py" ! -name "__init__.py" -delete
find apps/*/migrations -type f -name "*.pyc" -delete

echo -e "${YELLOW}[2/6] Creando migraciones para cada app...${NC}"
python manage.py makemigrations users
python manage.py makemigrations geodata
python manage.py makemigrations agents
python manage.py makemigrations monitoring
python manage.py makemigrations alerts
python manage.py makemigrations automation

echo -e "${YELLOW}[3/6] Verificando migraciones...${NC}"
python manage.py showmigrations

echo -e "${YELLOW}[4/6] Aplicando migraciones...${NC}"
python manage.py migrate

echo -e "${YELLOW}[5/6] Creando superusuario...${NC}"
python manage.py shell << PYTHON_EOF
from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@smgi.com',
        password='admin123',
        first_name='Admin',
        last_name='SMGI',
        role='admin'
    )
    print("✅ Superusuario creado: admin / admin123")
else:
    print("ℹ️  Superusuario 'admin' ya existe")
PYTHON_EOF

echo -e "${YELLOW}[6/6] Creando usuarios de prueba...${NC}"
python manage.py shell << PYTHON_EOF
from django.contrib.auth import get_user_model
User = get_user_model()

# Analyst
if not User.objects.filter(username='analyst').exists():
    User.objects.create_user(
        username='analyst',
        email='analyst@smgi.com',
        password='analyst123',
        first_name='Ana',
        last_name='Analyst',
        role='analyst',
        is_verified=True
    )
    print("✅ Usuario analyst creado: analyst / analyst123")

# Developer
if not User.objects.filter(username='developer').exists():
    User.objects.create_user(
        username='developer',
        email='developer@smgi.com',
        password='dev123',
        first_name='Dev',
        last_name='Developer',
        role='developer',
        is_verified=True
    )
    print("✅ Usuario developer creado: developer / dev123")

# Viewer
if not User.objects.filter(username='viewer').exists():
    User.objects.create_user(
        username='viewer',
        email='viewer@smgi.com',
        password='viewer123',
        first_name='View',
        last_name='Viewer',
        role='viewer',
        is_verified=True
    )
    print("✅ Usuario viewer creado: viewer / viewer123")
PYTHON_EOF

echo ""
echo -e "${GREEN}✅ Base de datos configurada correctamente${NC}"
echo ""
echo "📋 Usuarios creados:"
echo "   Admin:     admin / admin123"
echo "   Analyst:   analyst / analyst123"
echo "   Developer: developer / dev123"
echo "   Viewer:    viewer / viewer123"
echo ""
