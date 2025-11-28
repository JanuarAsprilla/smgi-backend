#!/bin/bash

echo "=========================================="
echo "🚀 INICIANDO SMGI"
echo "=========================================="
echo ""

# Función para limpiar al salir
cleanup() {
    echo ""
    echo "=========================================="
    echo "🛑 DETENIENDO SERVICIOS"
    echo "=========================================="
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Backend detenido"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✅ Frontend detenido"
    fi
    
    exit 0
}

trap cleanup SIGINT SIGTERM

# Backend
cd ~/smgi-backend
echo "🔧 Iniciando Backend..."
python manage.py runserver > /tmp/smgi_backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend iniciado (PID: $BACKEND_PID)"
echo "   Log: /tmp/smgi_backend.log"
echo "   URL: http://localhost:8000"

# Esperar a que el backend esté listo
echo ""
echo "⏳ Esperando a que el backend esté disponible..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/ > /dev/null 2>&1; then
        echo "✅ Backend respondiendo"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Frontend
cd ~/smgi-frontend
echo ""
echo "🎨 Iniciando Frontend..."
npm run dev > /tmp/smgi_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend iniciado (PID: $FRONTEND_PID)"
echo "   Log: /tmp/smgi_frontend.log"
echo "   URL: http://localhost:5173"

echo ""
echo "=========================================="
echo "✅ SERVICIOS INICIADOS"
echo "=========================================="
echo ""
echo "🌐 Abre tu navegador en:"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000/admin/"
echo ""
echo "👤 Credenciales:"
echo "   Username: januar"
echo "   Password: asprilla2002"
echo ""
echo "📋 Ver logs:"
echo "   Backend:  tail -f /tmp/smgi_backend.log"
echo "   Frontend: tail -f /tmp/smgi_frontend.log"
echo ""
echo "🛑 Presiona Ctrl+C para detener los servicios"
echo ""

# Mantener el script corriendo
wait
