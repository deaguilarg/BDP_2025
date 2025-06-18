@echo off
echo ========================================
echo   ASISTENTE DE SEGUROS ALLIANZ
echo ========================================
echo.
echo Iniciando aplicación...
echo.
echo La aplicación se abrirá en tu navegador web
echo Para detenerla, cierra esta ventana o presiona Ctrl+C
echo.

python run_app.py

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo iniciar la aplicación
    echo.
    echo Posibles soluciones:
    echo 1. Ejecuta primero: instalar.bat
    echo 2. Verifica que Python esté instalado
    echo 3. Contacta al equipo técnico
    echo.
    pause
) 
 