# 🛡️ Asistente de Seguros Allianz

**Sistema inteligente para consultar información de seguros de manera rápida y precisa**

¿Necesitas información específica sobre los productos de seguros de Allianz? Este asistente te ayuda a encontrar respuestas precisas en segundos, consultando automáticamente toda la documentación disponible.

## 🚀 Instalación Rápida (Para No Técnicos)

### Paso 1: Instalar Python
1. Ve a [python.org](https://www.python.org/downloads/)
2. Descarga Python 3.9 o superior
3. **IMPORTANTE**: Durante la instalación, marca la casilla "Add Python to PATH"

### Paso 2: Obtener el Código
1. Descarga este proyecto como ZIP o clónalo
2. Extrae todos los archivos en una carpeta (ej: `C:\AsistenteAllianz\`)

### Paso 3: Configuración Automática

**Opción A: Instalación Automática (Recomendada)**
1. Abre la carpeta del proyecto
2. Haz doble clic en `instalar.bat` (se creará automáticamente)
3. Espera a que termine la instalación

**Opción B: Instalación Manual**
1. Abre "Símbolo del sistema" o "PowerShell" como administrador
2. Navega a la carpeta del proyecto:
   ```
   cd C:\AsistenteAllianz
   ```
3. Ejecuta:
   ```
   pip install -r requirements.txt
   ```

### Paso 4: Configurar API de OpenAI
1. Obtén tu clave API de OpenAI (contacta a tu supervisor de TI)
2. Crea un archivo llamado `.env` en la carpeta principal
3. Dentro del archivo `.env`, escribe:
   ```
   OPENAI_API_KEY=tu-clave-aqui
   ```

### Paso 5: ¡Usar el Asistente!
1. Ejecuta `iniciar.bat` (doble clic) O abre terminal y ejecuta:
   ```
   python run_app.py
   ```
2. Se abrirá automáticamente en tu navegador web
3. ¡Ya puedes hacer preguntas sobre seguros!

---

## 📱 Cómo Usar el Asistente

### Tipos de Preguntas que Puedes Hacer:
- "¿Qué cubre el seguro de motocicleta en caso de robo?"
- "¿Cuáles son las exclusiones del seguro de hogar?"
- "¿Cuánto cuesta el seguro básico para furgonetas?"
- "¿Qué documentos necesito para hacer un reclamo?"

### Funciones Disponibles:
- 🔍 **Búsqueda inteligente**: Encuentra información específica
- 🏷️ **Filtros**: Busca por tipo de seguro, vehículo, etc.
- 📊 **Visualizaciones**: Ve qué tan relevantes son los resultados
- 📄 **Fuentes**: Consulta los documentos originales

---

## 🛠️ Para Técnicos

### Requisitos del Sistema
- Python 3.9+
- 4GB RAM mínimo
- Conexión a internet
- Clave API de OpenAI

### Estructura Técnica
```
insurance-rag/
├── app/                    # Interfaz Streamlit
│   └── streamlit_app.py   # Aplicación principal
├── data/                   # Documentos de seguros
│   ├── raw/               # PDFs originales
│   ├── processed/         # Textos procesados
│   └── embeddings/        # Vectores generados
├── src/                    # Código fuente
│   ├── embeddings/        # Generación de embeddings
│   ├── retrieval/         # Motor de búsqueda
│   ├── generation/        # Generación de respuestas
│   └── monitoring/        # Logging y métricas
├── models/                 # Índices FAISS
└── logs/                  # Registros del sistema
```

### Comandos de Desarrollo
```bash
# Instalar en modo desarrollo
pip install -e .

# Regenerar índices
python src/embeddings/embed_documents.py
python src/embeddings/index_builder.py

# Ejecutar aplicación
python run_app.py
```

---

## 🔧 Solución de Problemas

### Error: "No se encuentra Python"
- Reinstala Python y marca "Add to PATH"
- Reinicia tu computadora

### Error: "API Key no válida"
- Verifica que tu clave API esté correcta en el archivo `.env`
- Contacta a TI para una nueva clave

### Error: "Puerto ocupado"
- El sistema automáticamente buscará un puerto disponible
- Si persiste, reinicia tu computadora

### Error: "No se encuentran documentos"
- Verifica que los archivos PDF estén en la carpeta `data/raw/`
- Ejecuta la regeneración del índice

### La aplicación no responde bien
- Verifica tu conexión a internet
- Prueba con preguntas más específicas
- Contacta al equipo técnico

---

## 📞 Soporte

**Para usuarios no técnicos:**
- Contacta a tu supervisor o equipo de TI
- Incluye el mensaje de error exacto si hay algún problema

**Para técnicos:**
- Revisa los logs en la carpeta `logs/`
- Verifica la configuración en `src/`
- Consulta la documentación técnica en el código

---

## 🔒 Seguridad y Privacidad

- Todas las consultas se registran para mejorar el servicio
- No se almacena información personal de clientes
- La API de OpenAI cumple con estándares de seguridad empresarial
- Los documentos se procesan localmente en tu equipo

---

## 📈 Actualizaciones

Para actualizar el sistema:
1. Descarga la nueva versión
2. Reemplaza los archivos (mantén tu archivo `.env`)
3. Ejecuta `python run_app.py` - el sistema se actualizará automáticamente

---

*Desarrollado por el Equipo BDP para Allianz - Versión 1.0* 