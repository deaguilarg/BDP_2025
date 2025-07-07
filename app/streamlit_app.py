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
    if password == "allianz2024":  # Cambiar por tu contraseña
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
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stTextInput > div > div > input {
        font-size: 1.2rem;
    }
    .result-card {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 5px solid #0066cc;
    }
    .score-badge {
        background-color: #0066cc;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
    }
    .metadata-tag {
        background-color: #e9ecef;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        margin-right: 0.5rem;
        font-size: 0.8rem;
    }
    .answer-box {
        background-color: #e8f4ff;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 5px solid #0066cc;
    }
    .disclaimer {
        font-size: 0.8rem;
        color: #666;
        font-style: italic;
        margin-top: 1rem;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 0.3rem;
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

def main():
    """Función principal de la aplicación Streamlit"""
    
    # Título y descripción
    st.title("🛡️ Asistente de Seguros Allianz")
    st.markdown("""
    Bienvenido al Asistente de Seguros de Allianz. Este sistema te ayudará a encontrar información específica 
    y generar recomendaciones personalizadas para tus clientes.
    """)
    
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
        max_value=20,
        value=5
    )
    
    # Botón de búsqueda
    if st.button("Obtener Recomendación", type="primary"):
        if query:
            try:
                with st.spinner("Buscando información relevante..."):
                    # Realizar búsqueda
                    results = searcher.search(
                        query=query,
                        top_k=num_results * 2  # Buscar más para filtrado
                    )
                    
                    # Aplicar filtros si se especificaron
                    if filter_params:
                        results = searcher.filter_by_metadata(results, filter_params)
                    
                    if results:
                        # Generar respuesta
                        response = answer_generator.generate_answer(
                            query=query,
                            context_docs=results[:num_results]
                        )
                        
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
        st.markdown("### 📖 Guía de uso")
        st.markdown("""
        1. Escribe la consulta de tu cliente
        2. Usa los filtros para refinar la búsqueda
        3. Ajusta el número de documentos a consultar
        4. Haz clic en "Obtener Recomendación"
        
        **Tipos de consultas sugeridas:**
        - ¿Qué cubre el seguro de motocicleta?
        - ¿Cuáles son las exclusiones del seguro de comunidad?
        - ¿Cómo funciona la cobertura de responsabilidad civil?
        """)
        
        st.markdown("### 🔍 Estadísticas")
        st.metric(
            "Documentos disponibles",
            len(metadata_options.get('filename', []))
        )

if __name__ == "__main__":
    main() 