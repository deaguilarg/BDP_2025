@echo off
echo Creando entorno virtual...
python -m venv venv

echo Activando entorno virtual...
call venv\Scripts\activate

echo Instalando dependencias...
pip install -r requirements.txt

echo Creando estructura de directorios...
mkdir data\raw
mkdir data\processed
mkdir data\metadata
mkdir models\faiss_index
mkdir src\data
mkdir src\embeddings
mkdir src\retrieval
mkdir src\generation
mkdir src\monitoring
mkdir app
mkdir logs\performance
mkdir logs\user_queries
mkdir visualizations
mkdir notebooks

echo Configuración completada.
echo Por favor, copia el archivo .env.example a .env y ajusta las variables según sea necesario. 