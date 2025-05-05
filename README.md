# Sistema RAG para Documentos de Seguros

## Requisitos del Sistema
- Python 3.9 o superior
- Git (opcional)
- 8GB de espacio libre
- RAM: mínimo 8GB, ideal 16GB+
- GPU NVIDIA GTX 1050 (4GB VRAM)

## Instalación

1. Clonar el repositorio (opcional):
```bash
git clone https://github.com/tu-usuario/rag-seguros.git
cd rag-seguros
```

2. Ejecutar el script de configuración:
```bash
setup.bat
```

3. Copiar y configurar variables de entorno:
```bash
copy .env.example .env
```
Edita el archivo `.env` con los valores apropiados para tu sistema.

## Estructura del Proyecto

```
rag-seguros/
├── data/
│   ├── raw/                  # PDFs de documentos de seguros originales
│   ├── processed/            # Texto extraído de los PDFs
│   └── metadata/             # Archivo de metadatos de los documentos
├── models/                   # Directorio para almacenar modelos y embeddings
│   └── faiss_index/          # Índice FAISS generado
├── src/                      # Código fuente del proyecto
├── app/                      # Aplicación Streamlit
├── logs/                     # Logs del sistema
├── visualizations/           # Visualizaciones generadas
└── notebooks/                # Jupyter notebooks para experimentación
```

## Configuración de GPU

El sistema está configurado para usar una GPU NVIDIA GTX 1050 con 4GB de VRAM. Las variables relevantes en el archivo `.env` son:

```
USE_GPU=true
GPU_DEVICE=0
MAX_GPU_MEMORY=4G
```

## Uso

1. Coloca tus documentos PDF en el directorio `data/raw/`
2. Ejecuta el script de extracción de texto:
```bash
python src/data/extract_text.py
```
3. Inicia la aplicación Streamlit:
```bash
streamlit run app/streamlit_app.py
```

## Notas Importantes

- El sistema está optimizado para documentos en español
- Los tiempos de respuesta están configurados para ser menores a 30 segundos
- El sistema de logging se implementará en fases
- No hay requisitos específicos de seguridad en esta fase 