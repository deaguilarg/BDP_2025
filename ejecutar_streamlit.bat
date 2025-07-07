@echo off
echo Cerrando procesos de Streamlit existentes...
taskkill /f /im streamlit.exe 2>nul
timeout /t 2 /nobreak >nul

echo Iniciando aplicación Streamlit...
echo.
echo Aplicación iniciando en: http://localhost:8502
echo.
echo Presiona Ctrl+C para detener la aplicación
echo.

python -m streamlit run streamlit_app.py --server.port 8502

pause 