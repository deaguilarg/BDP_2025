#!/bin/bash

echo "Cerrando procesos de Streamlit existentes..."
pkill -f streamlit 2>/dev/null || true
sleep 2

echo "Iniciando aplicación Streamlit..."
echo ""
echo "Aplicación iniciando en: http://localhost:8502"
echo ""
echo "Presiona Ctrl+C para detener la aplicación"
echo ""

python -m streamlit run streamlit_app.py --server.port 8502 