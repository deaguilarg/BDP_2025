# Plan de Desarrollo: Sistema RAG para Documentos de Seguros

## Resumen del Proyecto
Implementar un sistema de Retrieval-Augmented Generation (RAG) que permita responder preguntas específicas sobre documentos de seguros utilizando embeddings, indexación FAISS y un modelo de lenguaje para la generación de respuestas.

## Estructura General del Proyecto

```
rag-seguros/
├── data/
│   ├── raw/                  # PDFs de documentos de seguros originales
│   ├── processed/            # Texto extraído de los PDFs
│   └── metadata/             # Archivo de metadatos de los documentos
├── models/                   # Directorio para almacenar modelos y embeddings
│   └── faiss_index/          # Índice FAISS generado
├── notebooks/                # Jupyter notebooks para experimentación
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── extract_text.py   # Script para extraer texto de PDFs
│   │   └── metadata_generator.py # Script para generar metadatos automáticamente
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── embed_documents.py # Generación de embeddings
│   │   └── index_builder.py   # Construcción del índice FAISS
│   ├── retrieval/
│   │   ├── __init__.py
│   │   └── search_engine.py   # Funciones de búsqueda en el índice
│   ├── generation/
│   │   ├── __init__.py
│   │   └── answer_generator.py # Generación de respuestas con LLM
│   └── monitoring/
│       ├── __init__.py
│       ├── logger.py          # Sistema de logging personalizado
│       └── performance.py     # Monitoreo de rendimiento y métricas
├── app/
│   ├── streamlit_app.py      # Interfaz principal de usuario con Streamlit
│   └── debug_interface.py    # Interfaz para visualizar chunks y embeddings
├── logs/                     # Directorio para almacenar logs del sistema
│   ├── performance/          # Logs de rendimiento
│   └── user_queries/         # Logs de consultas de usuarios
├── visualizations/           # Scripts para generar visualizaciones de rendimiento
├── requirements.txt          # Dependencias del proyecto
├── setup.py                  # Configuración para instalación como paquete
├── .env.example              # Plantilla para variables de entorno
├── README.md                 # Documentación general del proyecto
├── run.sh                    # Script para ejecutar la aplicación principal
└── run_debug.sh              # Script para ejecutar la interfaz de depuración
```

## Flujo de Trabajo

1. **Preparación de Datos**:
   - Extracción de texto de PDFs (30MB total, 52 archivos en español)
   - Generación automática de metadatos
   - Organización de documentos para embeddings

2. **Generación de Embeddings e Indexación**:
   - Tokenización y división de documentos en chunks apropiados
   - Generación de embeddings para cada chunk usando "paraphrase-multilingual-mpnet-base-v2"
   - Construcción y almacenamiento del índice FAISS

3. **Implementación del Motor de Búsqueda**:
   - Diseño de funciones para la recuperación de documentos relevantes
   - Integración con el índice FAISS
   - Lógica para ranking y filtrado de resultados

4. **Implementación del Generador de Respuestas**:
   - Integración del modelo text-embedding-3-small
   - Diseño del prompt para generar respuestas precisas en español
   - Optimización para tiempos de respuesta menores a 30 segundos

5. **Desarrollo de Interfaces de Usuario**:
   - Implementación de la aplicación principal Streamlit
   - Desarrollo de interfaz secundaria para depuración y visualización de chunks
   - Inclusión de controles para filtrado y personalización

6. **Sistema de Logging y Monitoreo**:
   - Implementación de registro detallado de consultas y respuestas
   - Monitoreo de tiempos de respuesta y uso de recursos
   - Generación de visualizaciones para análisis de rendimiento

## Cronograma Estimado

| Fase | Duración Estimada | Entregables |
|------|-------------------|-------------|
| Configuración inicial | 1 día | Estructura del proyecto, entorno virtual, repositorio |
| Preparación de datos | 2-3 días | Scripts de extracción, datos procesados, metadatos estructurados |
| Embeddings e indexación | 2-3 días | Sistema de embeddings, índice FAISS funcional |
| Motor de búsqueda | 2-3 días | Componente de recuperación de documentos implementado |
| Generación de respuestas | 2-3 días | Integración con LLM, generación de respuestas funcional |
| Interfaz Streamlit | 2-3 días | Aplicación web funcional |
| Pruebas y optimización | 3-5 días | Sistema completo optimizado |

## Tareas Específicas

### 1. Configuración del Entorno
- Crear un entorno virtual con Python 3.9+
- Instalar dependencias básicas (requirements.txt inicial)
- Configurar estructura de carpetas del proyecto
- Optimizar configuración para NVIDIA GTX 1050

### 2. Procesamiento de Documentos
- Implementar extracción de texto desde PDFs de seguros en español. Considerar que hay tildes.
- Eliminar caracteres extraños, más alla de letras, números, espacios en blanco, retornos de carro y letras con tildes.
- Desarrollar script para generación automática de metadatos de documentos. La metadata debe seguir el esquema propuesto en el markdown de metadata.
- El nombre del producto se encontrará en el documento "Producto: {producto}"

### 2.1 Chunking
- Dividir documentos en chunks apropiados para embeddings:
El programa debe identificar las siguientes secciones dentro de cada pdf:
1.- En qué consiste este tipo de seguro
2.- Qué se asegura
3.- Qué no está asegurado
4.- sumas aseguradas
5.- existen restricciones en lo que respecta a la cobertura
6.- Dónde estoy cubierto
7.- cuáles son mis obligaciones
8.- cuándo y cómo tengo que efectuar los pagos
9.- cuándo comienza y finaliza la cobertura
10.- cómo puedo rescindir el contrato
Si se encuentra una de estas secciones se debe crear un chunk con este nombre y con el contenido que hay hasta la siguiente sección

### 3. Sistema de Embeddings
- Implementar el modelo "paraphrase-multilingual-mpnet-base-v2" para embeddings
- Generar embeddings para todos los chunks de documentos
- Crear y optimizar el índice FAISS para búsqueda rápida
- Establecer parámetros de similitud adecuados para español, considerando tildes

### 4. Motor de Búsqueda
- Desarrollar funciones para buscar documentos relevantes
- Implementar ranking y filtrado de resultados
- Optimizar parámetros de búsqueda para documentos de seguros
- Implementar sistema de registro de consultas y resultados

### 5. Generación de Respuestas
- Integrar el modelo AtlaAI/Selene-1-Mini-Llama-3.1-8B
- Desarrollar sistema de prompting para generación de respuestas en español
- Implementar mecanismos para la cita y referencia a documentos originales
- Optimizar para mantener tiempos de respuesta menores a 30 segundos

### 6. Interfaces de Usuario
- Desarrollar la aplicación principal Streamlit para preguntas y respuestas
- Implementar interfaz secundaria para visualización de chunks y embeddings
- Añadir visualizaciones de documentos relevantes y confianza de respuestas
- Diseñar interfaz amigable y eficiente para usuarios no técnicos

### 7. Sistema de Logging y Monitoreo
- Implementar logging detallado de consultas, tiempos de respuesta y métricas
- Desarrollar componentes para monitoreo de rendimiento y uso de recursos
- Crear scripts para generar visualizaciones automáticas de métricas clave
- Diseñar estructura para recopilación de datos de rendimiento del sistema

### 8. Pruebas y Refinamiento
- Probar con preguntas típicas sobre documentos de seguros
- Optimizar rendimiento y precisión para el caso de uso específico
- Documentar limitaciones y mejores prácticas
- Elaborar plan para mejoras futuras basado en métricas recopiladas

## Consideraciones Técnicas
- Optimización para GPU NVIDIA GTX 1050 y 16GB de RAM
- Ajuste del modelo LLM para tiempos de respuesta menores a 30 segundos
- Balanceo entre precisión y rendimiento en la recuperación
- Estrategias para la gestión de dependencias y portabilidad en sistemas Windows
- Diseño de sistema de logging para análisis de rendimiento
- Estructura de metadatos optimizada para documentos de seguros en español
