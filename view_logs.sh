#!/bin/bash

echo "=========================================="
echo "📋 LOGS DEL SISTEMA"
echo "=========================================="
echo ""
echo "Presiona Ctrl+C para salir"
echo ""
echo "Backend (primeras 50 líneas):"
echo "----------------------------------------"
tail -n 50 /tmp/smgi_backend.log
echo ""
echo "Frontend (primeras 50 líneas):"
echo "----------------------------------------"
tail -n 50 /tmp/smgi_frontend.log
echo ""
echo "Para ver logs en tiempo real:"
echo "  Backend:  tail -f /tmp/smgi_backend.log"
echo "  Frontend: tail -f /tmp/smgi_frontend.log"
