# Sistema RAG para Documentos de Seguros Allianz

Sistema de Retrieval-Augmented Generation (RAG) para responder preguntas sobre documentos de seguros de Allianz, utilizando embeddings, indexación FAISS y modelos de lenguaje.

## Características

- 🔍 Búsqueda semántica en documentos de seguros
- 🤖 Generación de respuestas precisas en español
- 📊 Interfaz web intuitiva con Streamlit
- 📝 Sistema de logging y monitoreo
- 🔄 Integración con OpenAI API

## Requisitos

- Python 3.9+
- OpenAI API Key

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/tu-usuario/BDP_2025.git
cd BDP_2025
```

2. Crear y activar entorno virtual:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
Crear archivo `.env` en la raíz del proyecto:
```
OPENAI_API_KEY=tu-clave-api-aqui
```

## Estructura del Proyecto

```
insurance-rag/
├── app/                    # Interfaz de usuario Streamlit
├── data/                   # Documentos y metadatos
├── models/                 # Modelos y embeddings
├── src/                    # Código fuente
│   ├── data/              # Procesamiento de datos
│   ├── embeddings/        # Generación de embeddings
│   ├── retrieval/         # Motor de búsqueda
│   ├── generation/        # Generación de respuestas
│   └── monitoring/        # Sistema de logging
├── logs/                  # Registros del sistema
└── visualizations/        # Gráficos y reportes
```

## Uso

1. Iniciar la aplicación:
```bash
python -m streamlit run app/streamlit_app.py
```

2. Acceder a la interfaz web en `http://localhost:8501`

3. Realizar consultas sobre documentos de seguros

## Desarrollo

- `src/`: Contiene el código fuente del sistema RAG
- `app/`: Interfaz de usuario con Streamlit
- `data/`: Documentos de seguros y metadatos
- `models/`: Modelos y embeddings generados

## Monitoreo

El sistema incluye:
- Logging detallado de consultas
- Métricas de rendimiento
- Visualizaciones de uso
- Reportes de calidad

## Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles. 