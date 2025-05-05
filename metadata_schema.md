# Estructura de Metadatos para Documentos de Seguros

La correcta estructura de metadatos es esencial para un sistema RAG eficiente. A continuación se presenta la estructura recomendada para los documentos de seguros en español.

## Formato del Archivo

Se recomienda usar formato CSV para los metadatos, con la siguiente estructura:

```csv
filename,title,insurer,insurance_type,coverage_type,document_date,document_version,file_path,num_pages,language,keywords
```

## Campos de Metadatos

### Campos Obligatorios

| Campo | Descripción | Tipo | Ejemplo |
|-------|-------------|------|---------|
| `filename` | Nombre del archivo PDF | string | `poliza_hogar_mapfre_2023.pdf` |
| `title` | Título descriptivo del documento | string | `Condiciones Generales Seguro de Hogar` |
| `insurer` | Compañía aseguradora | string | `Mapfre` |
| `insurance_type` | Tipo principal de seguro | string | `Hogar`, `Vida`, `Salud`, `Auto`, `Responsabilidad Civil` |
| `file_path` | Ruta relativa al archivo | string | `data/raw/poliza_hogar_mapfre_2023.pdf` |
| `language` | Idioma del documento | string | `es` |

### Campos Recomendados

| Campo | Descripción | Tipo | Ejemplo |
|-------|-------------|------|---------|
| `coverage_type` | Subtipos o coberturas específicas | string | `Básico`, `Premium`, `Todo Riesgo` |
| `document_date` | Fecha del documento (YYYY-MM-DD) | date | `2023-09-15` |
| `document_version` | Versión del documento | string | `v2.1`, `2023/01` |
| `num_pages` | Número de páginas | integer | `42` |
| `keywords` | Palabras clave separadas por punto y coma | string | `incendio;robo;responsabilidad;terceros` |

### Campos Opcionales (según necesidades específicas)

| Campo | Descripción | Tipo | Ejemplo |
|-------|-------------|------|---------|
| `section_type` | Tipo de sección del documento | string | `Condiciones Generales`, `Anexo`, `Exclusiones` |
| `target_audience` | Público objetivo | string | `Particular`, `Empresa`, `Autónomo` |
| `document_id` | Identificador único del documento | string | `POL-HG-2023-0042` |
| `legal_jurisdiction` | Jurisdicción legal aplicable | string | `España`, `México`, `Colombia` |

## Script de Generación Automática

El script `src/data/metadata_generator.py` generará automáticamente estos metadatos a partir de los PDFs, utilizando:

1. **Extracción de texto**: Para identificar información clave
2. **Análisis de patrones**: Para detectar tipo de seguro, compañía, etc.
3. **Procesamiento de lenguaje natural**: Para extraer keywords y clasificar documentos

## Ejemplo de Archivo de Metadatos

```csv
filename,title,insurer,insurance_type,coverage_type,document_date,document_version,file_path,num_pages,language,keywords
poliza_hogar_mapfre_2023.pdf,Condiciones Generales Seguro de Hogar,Mapfre,Hogar,Premium,2023-09-15,v3.2,data/raw/poliza_hogar_mapfre_2023.pdf,48,es,incendio;robo;responsabilidad;terceros
seguro_auto_axa_2023.pdf,Póliza de Seguro de Automóvil,AXA,Auto,Todo Riesgo,2023-05-10,2023/02,data/raw/seguro_auto_axa_2023.pdf,52,es,colisión;robo;asistencia;cristales
seguro_salud_sanitas_2023.pdf,Condiciones Particulares Seguro de Salud,Sanitas,Salud,Completo,2023-01-20,v1.0,data/raw/seguro_salud_sanitas_2023.pdf,36,es,hospitalización;consultas;pruebas;especialistas
```

## Integración con el Sistema RAG

Los metadatos se utilizarán para:

1. **Filtrado de resultados**: Permitir búsquedas específicas por tipo de seguro o compañía
2. **Enriquecimiento de contexto**: Proporcionar información adicional al modelo LLM
3. **Organización de documentos**: Agrupar y categorizar documentos similares
4. **Mejora de visualizaciones**: Presentar información estructurada al usuario

El sistema de logging registrará qué campos de metadatos son más útiles en las búsquedas para futuras optimizaciones.
