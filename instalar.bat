@echo off
echo ========================================
echo   INSTALADOR AUTOMATICO - ALLIANZ RAG
echo ========================================
echo.

:: Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado o no está en PATH
    echo.
    echo Por favor:
    echo 1. Descarga Python desde https://python.org/downloads/
    echo 2. Durante la instalacion, marca "Add Python to PATH"
    echo 3. Reinicia tu computadora
    echo 4. Vuelve a ejecutar este archivo
    echo.
    pause
    exit /b 1
)

echo ✓ Python detectado correctamente
python --version

echo.
echo Instalando dependencias...
echo (Esto puede tomar varios minutos)
echo.

:: Actualizar pip
python -m pip install --upgrade pip

:: Instalar requirements
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Falló la instalación de dependencias
    echo Intenta ejecutar manualmente: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo ✓ Dependencias instaladas correctamente
echo.

:: Crear directorios necesarios
if not exist "logs" mkdir logs
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
if not exist "data\embeddings" mkdir data\embeddings
if not exist "data\metadata" mkdir data\metadata
if not exist "models\faiss_index" mkdir models\faiss_index

echo ✓ Directorios creados
echo.

:: Verificar archivo .env
if not exist ".env" (
    echo ATENCION: No se encontró archivo .env
    echo.
    echo Necesitas crear un archivo .env con tu API key de OpenAI
    echo.
    echo ¿Tienes tu API key lista? ^(s/n^)
    set /p respuesta="Respuesta: "
    
    if /i "%respuesta%"=="s" (
        echo.
        set /p apikey="Ingresa tu API key: "
        echo OPENAI_API_KEY=!apikey! > .env
        echo ✓ Archivo .env creado
    ) else (
        echo.
        echo Crea manualmente un archivo .env con:
        echo OPENAI_API_KEY=tu-clave-aqui
        echo.
    )
)

echo.
echo ========================================
echo   INSTALACION COMPLETADA
echo ========================================
echo.
echo Para usar el asistente:
echo 1. Ejecuta: iniciar.bat
echo 2. O ejecuta: python run_app.py
echo.
echo Si es la primera vez, el sistema generará 
echo automáticamente el índice de documentos.
echo.
pause 