"""
Interfaz principal de Streamlit para búsqueda en documentos de seguros.
"""

import sys
import os
from pathlib import Path

# Configurar el path para imports
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from typing import Dict, Any, List
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Opcional: Agregar autenticación simple en streamlit_app.py
if 'authenticated' not in st.session_state:
    password = st.text_input("Contraseña de equipo:", type="password")
    if password == "allianz2025":  # Cambiar por tu contraseña
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# Verificar la clave API
api_key = os.getenv("OPENAI_API_KEY")

# Configuración para deployment público
if not api_key:
    st.error("🔑 **Configuración Requerida**")
    st.markdown("""
    Esta aplicación requiere una API key de OpenAI para funcionar.
    
    **Para administradores:**
    1. Configure la variable de entorno `OPENAI_API_KEY` en Streamlit Cloud
    2. O proporcione un sistema de autenticación para usuarios
    
    **Para usuarios:**
    - Contacte al administrador del sistema para obtener acceso
    """)
    
    # Opción para que usuarios ingresen su propia API key (para testing)
    with st.expander("🧪 Modo de Prueba (Solo para Testing)"):
        user_api_key = st.text_input(
            "Ingresa tu propia API key de OpenAI:", 
            type="password",
            help="Esta key solo se usa durante esta sesión y no se almacena"
        )
        if user_api_key and user_api_key.startswith("sk-"):
            st.session_state["user_api_key"] = user_api_key
            st.success("✅ API key configurada para esta sesión")
            st.rerun()
        elif user_api_key:
            st.error("❌ API key inválida (debe comenzar con 'sk-')")
    
    st.stop()

# Usar API key del usuario si existe, sino la del sistema
if "user_api_key" in st.session_state:
    api_key = st.session_state["user_api_key"]

if not api_key.startswith("sk-"):
    st.error("❌ La clave API no tiene el formato correcto. Debe comenzar con 'sk-'")
    st.stop()

from src.retrieval.search_engine import SearchEngine
from src.generation.answer_generator import AnswerGenerator

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración de la página
st.set_page_config(
    page_title="Asistente de Seguros Allianz",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.allianz.com/help',
        'Report a bug': "https://www.allianz.com/support",
        'About': """
        # Asistente de Seguros Allianz
        
        **Versión:** 2.0  
        **Desarrollado por:** Equipo BDP  
        **Tecnología:** RAG (Retrieval-Augmented Generation)
        
        Sistema inteligente de búsqueda para documentos de seguros.
        """
    }
)

# Estilos CSS con branding de Allianz
st.markdown("""
<style>
    /* Colores corporativos de Allianz */
    :root {
        --allianz-blue: #0066cc;
        --allianz-dark-blue: #003366;
        --allianz-light-blue: #e8f4ff;
        --allianz-gray: #f8f9fa;
        --allianz-white: #ffffff;
    }
    
    /* Header personalizado */
    .allianz-header {
        background: linear-gradient(135deg, var(--allianz-blue) 0%, var(--allianz-dark-blue) 100%);
        padding: 1.5rem 2rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 8px rgba(0, 102, 204, 0.2);
    }
    
    .allianz-logo {
        height: 50px;
        width: auto;
        filter: brightness(1.1) contrast(1.1);
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .allianz-title {
        font-size: 2.2rem;
        font-weight: bold;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        line-height: 1.1;
    }
    
    .allianz-subtitle {
        font-size: 1.1rem;
        margin: 0;
        opacity: 0.9;
        line-height: 1.2;
        margin-top: 0.2rem;
    }
    
    /* Componentes principales */
    .main {
        padding: 2rem;
        background-color: var(--allianz-white);
    }
    
    .stTextInput > div > div > input {
        font-size: 1.2rem;
        border: 2px solid var(--allianz-blue);
        border-radius: 0.5rem;
        padding: 0.75rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--allianz-dark-blue);
        box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
    }
    
    /* Tarjetas de resultados */
    .result-card {
        background: linear-gradient(135deg, var(--allianz-white) 0%, var(--allianz-gray) 100%);
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 5px solid var(--allianz-blue);
        box-shadow: 0 4px 6px rgba(0, 102, 204, 0.1);
        transition: transform 0.2s ease;
    }
    
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 102, 204, 0.15);
    }
    
    .score-badge {
        background: linear-gradient(135deg, var(--allianz-blue) 0%, var(--allianz-dark-blue) 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1.5rem;
        font-size: 0.85rem;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0, 102, 204, 0.2);
    }
    
    .metadata-tag {
        background-color: var(--allianz-light-blue);
        color: var(--allianz-dark-blue);
        padding: 0.3rem 0.6rem;
        border-radius: 0.4rem;
        margin-right: 0.5rem;
        font-size: 0.8rem;
        font-weight: 500;
        border: 1px solid var(--allianz-blue);
    }
    
    /* Caja de respuestas */
    .answer-box {
        background: linear-gradient(135deg, var(--allianz-light-blue) 0%, var(--allianz-white) 100%);
        border-radius: 0.75rem;
        padding: 2rem;
        margin: 1.5rem 0;
        border-left: 5px solid var(--allianz-blue);
        box-shadow: 0 4px 6px rgba(0, 102, 204, 0.1);
    }
    
    .disclaimer {
        font-size: 0.85rem;
        color: var(--allianz-dark-blue);
        font-style: italic;
        margin-top: 1rem;
        padding: 0.75rem;
        background-color: var(--allianz-gray);
        border-radius: 0.4rem;
        border-left: 3px solid var(--allianz-blue);
    }
    
    /* Botones */
    .stButton > button {
        background: linear-gradient(135deg, var(--allianz-blue) 0%, var(--allianz-dark-blue) 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 2rem;
        font-weight: bold;
        font-size: 1.1rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 102, 204, 0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 102, 204, 0.3);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: var(--allianz-gray);
        border-right: 3px solid var(--allianz-blue);
    }
    
    /* Métricas */
    .metric-card {
        background: linear-gradient(135deg, var(--allianz-blue) 0%, var(--allianz-dark-blue) 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    /* Filtros */
    .stMultiSelect > div > div {
        border-color: var(--allianz-blue);
    }
    
    .stSlider > div > div > div {
        color: var(--allianz-blue);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--allianz-light-blue);
        border: 1px solid var(--allianz-blue);
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_components():
    """
    Carga los componentes necesarios (cacheado).
    """
    try:
        return SearchEngine(), AnswerGenerator(api_key=api_key)
    except Exception as e:
        logger.error(f"Error al cargar los componentes: {str(e)}")
        st.error("Error al cargar los componentes. Por favor, verifique la configuración.")
        return None, None

@st.cache_data
def load_metadata_options() -> Dict[str, List[str]]:
    """
    Carga las opciones de filtrado desde los metadatos (cacheado).
    """
    try:
        metadata_path = Path("models/processed_documents.json")
        if not metadata_path.exists():
            logger.error(f"No se encontró el archivo de metadatos en: {metadata_path}")
            st.error(f"No se encontró el archivo de metadatos. Por favor, ejecute primero el generador de embeddings.")
            return {}
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        if not isinstance(documents, list):
            logger.error("El archivo de metadatos no contiene una lista de documentos")
            st.error("Formato de metadatos inválido. El archivo debe contener una lista de documentos.")
            return {}
        
        options = {}
        for doc in documents:
            if not isinstance(doc, dict):
                logger.warning(f"Documento inválido encontrado: {doc}")
                continue
                
            metadata = doc.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"Metadatos inválidos encontrados en documento: {metadata}")
                continue
                
            for key, value in metadata.items():
                if key not in options:
                    options[key] = set()
                if value:  # Solo agregar valores no nulos
                    options[key].add(str(value))
        
        if not options:
            logger.warning("No se encontraron metadatos válidos en los documentos")
            st.warning("No se encontraron metadatos válidos en los documentos.")
            return {}
        
        logger.info(f"Metadatos cargados exitosamente. Campos encontrados: {list(options.keys())}")
        return {k: sorted(list(v)) for k, v in options.items()}
        
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar el archivo JSON: {str(e)}")
        st.error("Error en el formato del archivo de metadatos. El archivo debe ser un JSON válido.")
        return {}
    except Exception as e:
        logger.error(f"Error inesperado al cargar metadatos: {str(e)}")
        st.error(f"Error al cargar los metadatos: {str(e)}")
        return {}

def render_result_card(result: Dict[str, Any]) -> None:
    """
    Renderiza una tarjeta de resultado.
    """
    with st.container():
        st.markdown(f"""
        <div class="result-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0;">{result['metadata'].get('filename', 'Desconocido')}</h3>
                <span class="score-badge">Score: {result['score']:.2f}</span>
            </div>
            <div style="margin: 0.5rem 0;">
                {' '.join([f'<span class="metadata-tag">{k}: {v}</span>' 
                          for k, v in result['metadata'].items() if v])}
            </div>
            <p style="margin: 1rem 0;">{result.get('text', '')}</p>
        </div>
        """, unsafe_allow_html=True)

def render_answer(answer: str) -> None:
    """
    Renderiza la respuesta del asistente.
    """
    st.markdown(f"""
    <div class="answer-box">
        {answer}
        <div class="disclaimer">
            Esta recomendación está destinada a ayudar a los asesores de Allianz y es solo para fines informativos. 
            Los clientes deben consultar los términos completos de la póliza o consultar con un representante de Allianz 
            para obtener una cotización personalizada.
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_allianz_header():
    """
    Crea el header corporativo de Allianz con logo.
    """
    import base64
    
    # Intentar cargar el logo
    logo_html = ""
    logo_paths = ["allianz-logo.png", "assets/allianz-logo.png", "assets/allianz_logo.png"]
    
    for logo_path in logo_paths:
        try:
            if Path(logo_path).exists():
                with open(logo_path, "rb") as f:
                    logo_bytes = f.read()
                    logo_base64 = base64.b64encode(logo_bytes).decode()
                    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="allianz-logo" alt="Allianz Logo">'
                    break
        except Exception:
            continue
    
    # Si no hay logo, usar texto estilizado
    if not logo_html:
        logo_html = '<div class="allianz-title">Allianz</div>'
    
    st.markdown(f"""
    <div class="allianz-header">
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
            <div style="display: flex; align-items: center; gap: 1.5rem;">
                {logo_html}
                <div style="text-align: left;">
                    <div class="allianz-title">Asistente de Seguros</div>
                    <div class="allianz-subtitle">Inteligencia Artificial para Documentos</div>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.9rem; opacity: 0.8;">🛡️ Aseguramos tu futuro</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Función principal de la aplicación Streamlit"""
    
    # Header corporativo con logo
    create_allianz_header()
    
    # Descripción
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <p style="font-size: 1.2rem; color: #003366; margin-bottom: 1rem;">
            <strong>Sistema Inteligente de Búsqueda de Documentos de Seguros</strong>
        </p>
        <p style="color: #666; font-size: 1rem;">
            Obtén información precisa y recomendaciones personalizadas para tus clientes
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar componentes
    searcher, answer_generator = load_components()
    if searcher is None or answer_generator is None:
        st.error("No se pudieron inicializar los componentes. Por favor, verifique la configuración.")
        return
        
    metadata_options = load_metadata_options()
    
    if not metadata_options:
        st.error("""
        No se pudieron cargar las opciones de metadatos. Por favor, siga estos pasos:
        1. Ejecute `python src/embeddings/embed_documents.py` para generar los embeddings
        2. Ejecute `python src/embeddings/index_builder.py` para construir el índice
        3. Vuelva a intentar ejecutar esta aplicación
        """)
        return
    
    # Barra de búsqueda
    query = st.text_input(
        "¿Qué información necesitas para tu cliente?",
        placeholder="Ejemplo: ¿Qué cubre el seguro de motocicleta en caso de robo?"
    )
    
    # Filtros de búsqueda
    with st.expander("Filtros de búsqueda"):
        col1, col2 = st.columns(2)
        
        filter_params = {}
        for i, (key, values) in enumerate(metadata_options.items()):
            with col1 if i % 2 == 0 else col2:
                selected = st.multiselect(
                    f"Filtrar por {key}",
                    options=values,
                    key=f"filter_{key}"
                )
                if selected:
                    filter_params[key] = selected
    
    # Número de resultados
    num_results = st.slider(
        "Número de documentos a consultar",
        min_value=1,
        max_value=52,
        value=20
    )
    
    # Botón de búsqueda con estilo corporativo
    if st.button("🎯 Obtener Recomendación", type="primary"):
        if query:
            try:
                # Mensajes de carga profesionales
                with st.spinner("🔍 Analizando documentos de seguros..."):
                    # Realizar búsqueda
                    results = searcher.search(
                        query=query,
                        top_k=num_results * 2  # Buscar más para filtrado
                    )
                    
                    # Aplicar filtros si se especificaron
                    if filter_params:
                        results = searcher.filter_by_metadata(results, filter_params)
                    
                    if results:
                        # Mostrar progreso
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("🤖 Generando recomendación personalizada...")
                        progress_bar.progress(50)
                        
                        # Generar respuesta
                        response = answer_generator.generate_answer(
                            query=query,
                            context_docs=results[:num_results]
                        )
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Recomendación generada exitosamente")
                        
                        # Limpiar elementos de progreso
                        progress_bar.empty()
                        status_text.empty()
                        
                        # Mostrar respuesta
                        st.markdown("### 💡 Recomendación")
                        render_answer(response)
                        
                        # Mostrar documentos utilizados
                        st.markdown("### 📄 Documentos consultados")
                        for result in results[:num_results]:
                            render_result_card(result)
                            
                        # Gráfico de relevancia
                        scores_df = pd.DataFrame({
                            'Documento': [r['metadata'].get('filename', 'Desconocido') for r in results[:num_results]],
                            'Relevancia': [r['score'] for r in results[:num_results]]
                        })
                        
                        fig = go.Figure(data=[
                            go.Bar(
                                x=scores_df['Documento'],
                                y=scores_df['Relevancia'],
                                marker_color='#0066cc'
                            )
                        ])
                        
                        fig.update_layout(
                            title="Relevancia de los documentos consultados",
                            xaxis_title="Documento",
                            yaxis_title="Score de Relevancia",
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        st.warning("No se encontraron documentos relevantes para tu consulta.")
                    
                    # Registrar búsqueda
                    logger.info(f"Consulta procesada: '{query}', Resultados: {len(results)}, Filtros: {filter_params}")
                    
            except Exception as e:
                st.error(f"Error al procesar la consulta: {str(e)}")
                logger.error(f"Error en la interfaz: {str(e)}, Query: {query}")
        else:
            st.warning("Por favor, ingresa una consulta para obtener una recomendación.")
    
    # Información adicional
    with st.sidebar:
        # Header del sidebar
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0066cc 0%, #003366 100%); 
                    padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; color: white; text-align: center;">
            <h3 style="margin: 0; color: white;">📖 Centro de Ayuda</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🚀 Guía de uso")
        st.markdown("""
        **Pasos para obtener recomendaciones:**
        1. 💬 Escribe la consulta de tu cliente
        2. 🔍 Usa los filtros para refinar la búsqueda
        3. ⚙️ Ajusta el número de documentos a consultar
        4. 🎯 Haz clic en "Obtener Recomendación"
        
        **💡 Ejemplos de consultas:**
        - *¿Qué cubre el seguro de motocicleta?*
        - *¿Cuáles son las exclusiones del seguro de comunidad?*
        - *¿Cómo funciona la cobertura de responsabilidad civil?*
        - *¿Qué documentos necesito para una reclamación?*
        """)
        
        st.markdown("### 📊 Estadísticas del Sistema")
        
        # Métricas con estilo corporativo
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2rem; font-weight: bold;">{len(metadata_options.get('filename', []))}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Documentos Disponibles</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Información adicional
        st.markdown("### ℹ️ Información")
        st.info("""
        **🤖 Tecnología IA:**
        - Búsqueda semántica avanzada
        - Generación de respuestas contextualizadas
        - Procesamiento de documentos PDF
        
        **🔒 Seguridad:**
        - Datos procesados localmente
        - Acceso controlado por autenticación
        """)
        
        # Footer del sidebar
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.8rem;">
            <p>💼 <strong>Allianz Insurance</strong></p>
            <p>🔧 Sistema RAG v2.0</p>
            <p>📅 Actualizado: Julio 2025</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 