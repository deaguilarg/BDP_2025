# Instrucciones de Instalación y Ejecución: RAG para Documentos de Seguros

## Requisitos Previos
- Python 3.9 o superior
- Git (opcional, para control de versiones)
- Aproximadamente 8GB de espacio libre (para modelos y dependencias)
- RAM recomendada: mínimo 8GB, ideal 16GB+
- GPU (opcional, mejora significativamente el rendimiento)

## Instalación del Sistema

### 1. Clonar el Repositorio (opcional)
```bash
git clone https://github.com/tu-usuario/rag-seguros.git
cd rag-seguros
```

### 2. Crear un Entorno Virtual
#### Para Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

#### Para macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

#### Contenido sugerido para requirements.txt:
```
# Procesamiento de datos
pandas==2.0.3
numpy==1.24.3
PyPDF2==3.0.1
pdfplumber==0.10.2
langdetect==1.0.9  # Para detección de idioma

# Embedding y vectorización
sentence-transformers==2.2.2
faiss-gpu==1.7.4  # Para GPU NVIDIA
scikit-learn==1.2.2

# LLM y generación
torch==2.0.1
transformers==4.35.0
accelerate==0.23.0
bitsandbytes==0.41.1  # Para cuantización
optimum==1.12.0

# UI y aplicación
streamlit==1.28.0
streamlit-chat==0.1.1
plotly==5.14.1  # Para visualizaciones interactivas
matplotlib==3.7.1
seaborn==0.12.2

# Logging y monitoreo
loguru==0.7.0
psutil==5.9.5  # Monitoreo de recursos
py-spy==0.3.14  # Profiling

# Utilidades
python-dotenv==1.0.0
tqdm==4.66.1
nltk==3.8.1  # Para procesamiento de texto en español
```

### 4. Configuración de Variables de Entorno
1. Copia el archivo `.env.example` a `.env`
```bash
copy .env.example .env  # En Windows
```

2. Edita el archivo `.env` con los valores apropiados:
```
# Rutas de los archivos
DATA_DIR=./data
MODEL_DIR=./models
LOG_DIR=./logs

# Configuración del modelo
MODEL_ID=AtlaAI/Selene-1-Mini-Llama-3.1-8B
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2

# Parámetros de procesamiento
CHUNK_SIZE=512
CHUNK_OVERLAP=50
LANGUAGE=es

# Configuración de hardware
USE_GPU=true
GPU_DEVICE=0  # ID del dispositivo GPU a utilizar
MAX_GPU_MEMORY=4G  # Límite de memoria para GPU GTX 1050

# Configuración de rendimiento
MAX_RESPONSE_TIME=30  # Tiempo máximo de respuesta en segundos
LOG_LEVEL=INFO  # Nivel de detalle del logging (DEBUG, INFO, WARNING, ERROR)
ENABLE_PERFORMANCE_MONITORING=true
```

## Preparación de los Datos

### 1. Organización de Documentos
1. Coloca todos tus archivos PDF en el directorio `data/raw/`
2. Prepara tu archivo de metadatos y colócalo en `data/metadata/metadata.csv`

### 2. Procesamiento de Documentos
Ejecuta el script de extracción de texto:
```bash
python src/data/extract_text.py
```

### 3. Generación de Embeddings e Índice
```bash
python src/embeddings/embed_documents.py
python src/embeddings/index_builder.py
```

## Ejecución de la Aplicación

### Iniciar la Interfaz Streamlit
```bash
python -m streamlit run app/streamlit_app.py
```
La aplicación estará disponible en `http://localhost:8501` por defecto.

## Estructura de Archivos Clave

### `src/data/extract_text.py`
Este script se encarga de extraer el texto de los PDFs de seguros y convertirlo en formato adecuado para su procesamiento.

### `src/data/metadata_generator.py`
Genera automáticamente los metadatos para los documentos de seguros, incluyendo información como tipo de documento, compañía, fecha, etc.

### `src/embeddings/embed_documents.py`
Genera los embeddings para cada chunk de documento utilizando el modelo "paraphrase-multilingual-mpnet-base-v2".

### `src/embeddings/index_builder.py`
Construye el índice FAISS para búsqueda eficiente de similitud optimizado para español.

### `src/retrieval/search_engine.py`
Implementa la lógica de búsqueda para recuperar documentos relevantes dada una consulta.

### `src/generation/answer_generator.py`
Integra el modelo LLM para generar respuestas basadas en los documentos recuperados.

### `src/monitoring/logger.py`
Implementa un sistema de logging personalizado para registrar consultas, respuestas y métricas.

### `src/monitoring/performance.py`
Monitorea y registra métricas de rendimiento como tiempos de respuesta, uso de memoria y CPU/GPU.

### `app/streamlit_app.py`
Implementa la interfaz principal de usuario con Streamlit para preguntas y respuestas.

### `app/debug_interface.py`
Interfaz secundaria para visualizar chunks, probar el cruce de embeddings y analizar resultados de búsqueda.

## Consideraciones Importantes

### Optimización de Rendimiento
- **GPU vs CPU**: El rendimiento mejora significativamente con GPU, especialmente para el modelo LLM.
- **Memoria**: Ajusta `CHUNK_SIZE` según la memoria disponible y la naturaleza de tus documentos.
- **Cuantización**: Si el modelo es demasiado grande, considera usar técnicas de cuantización (4-bit o 8-bit).

### Portabilidad
- El sistema está diseñado para ser portable mediante el entorno virtual.
- Para compartir con otros usuarios, puedes:
  1. Compartir todo el repositorio y las instrucciones de instalación
  2. Crear un archivo Docker para mayor consistencia
  3. Exportar/importar el índice FAISS para evitar regenerarlo

### Limitaciones Conocidas
- El modelo puede tener dificultades con documentos muy específicos o técnicos.
- Preguntas mal formuladas pueden producir respuestas imprecisas.
- El sistema no actualiza automáticamente cuando se añaden nuevos documentos (requiere reprocesamiento).

### Mantenimiento
- Ejecuta `python src/embeddings/embed_documents.py --update` cuando añadas nuevos documentos.
- Monitorea el uso de memoria y CPU/GPU durante el funcionamiento.
- Realiza respaldos periódicos del índice FAISS.

## Scripts para Ejecución Rápida

### `run.bat` (Para Windows)

```batch
@echo off
:: Script para iniciar rápidamente el sistema RAG en Windows

:: Activar entorno virtual
call venv\Scripts\activate

:: Comprobar si la base de datos está inicializada
if not exist "models\faiss_index\index.faiss" (
    echo El índice FAISS no existe. Inicializando...
    python src\data\extract_text.py
    python src\data\metadata_generator.py
    python src\embeddings\embed_documents.py
    python src\embeddings\index_builder.py
)

:: Iniciar la aplicación Streamlit
echo Iniciando la aplicación principal...
start "" streamlit run app\streamlit_app.py
```

### `run_debug.bat` (Para Windows)

```batch
@echo off
:: Script para iniciar la interfaz de depuración en Windows

:: Activar entorno virtual
call venv\Scripts\activate

:: Comprobar si la base de datos está inicializada
if not exist "models\faiss_index\index.faiss" (
    echo El índice FAISS no existe. Inicializando...
    python src\data\extract_text.py
    python src\data\metadata_generator.py
    python src\embeddings\embed_documents.py
    python src\embeddings\index_builder.py
)

:: Iniciar la interfaz de depuración
echo Iniciando la interfaz de depuración...
start "" streamlit run app\debug_interface.py
```
