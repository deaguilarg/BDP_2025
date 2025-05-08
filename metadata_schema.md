# Estructura de Metadatos para Documentos de Seguros

La correcta estructura de metadatos es esencial para un sistema RAG eficiente. A continuación se presenta la estructura recomendada para los documentos de seguros en español.

## Formato del Archivo

Se recomienda usar formato CSV para los metadatos, con la siguiente estructura:

```csv
filename,producto,insurance_type,file_path,coverage_type,num_pages,keywords
```

## Campos de Metadatos

### Campos Obligatorios

| Campo | Descripción | Tipo | Ejemplo |
|-------|-------------|------|---------|
| `filename` | Nombre del archivo PDF | string | `auto-plus-basico.pdf` |
| `producto` | Nombre del producto de seguro | string | `Automóviles PLUS Básico` |
| `insurance_type` | Tipo principal de seguro | string | `Hogar`, `Vida`, `Salud`, `Automóvil`, `Responsabilidad Civil`, `Accidentes`, `Accidentes` |
| `file_path` | Ruta relativa al archivo | string | `data/raw/auto-plus-basico.pdf` |
| `coverage_type` | Subtipos o coberturas específicas | string | `Básico`, `Premium`, `Todo Riesgo`, `Básico con daños`, `Pérdida total`, `Todo riesgo con franquicia`|
| `num_pages` | Número de páginas | integer | `2` |
| `keywords` | Palabras clave separadas por punto y coma | string | `incendio;robo;responsabilidad;terceros` |

## Script de Generación Automática

El script `src/data/metadata_generator.py` generará automáticamente estos metadatos a partir de los PDFs, utilizando:

1. **Extracción de texto**: Para identificar información clave
2. **Análisis de patrones**: Para detectar tipo de seguro, compañía, etc.
3. **Procesamiento de lenguaje natural**: Para extraer keywords y clasificar documentos


## Integración con el Sistema RAG

Los metadatos se utilizarán para:

1. **Filtrado de resultados**: Permitir búsquedas específicas por tipo de seguro o compañía
2. **Enriquecimiento de contexto**: Proporcionar información adicional al modelo LLM
3. **Organización de documentos**: Agrupar y categorizar documentos similares
4. **Mejora de visualizaciones**: Presentar información estructurada al usuario

El sistema de logging registrará qué campos de metadatos son más útiles en las búsquedas para futuras optimizaciones.
