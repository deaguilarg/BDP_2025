"""
Interfaz principal de Streamlit para búsqueda en documentos de seguros.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import json
from typing import Dict, Any, List
import logging

from src.retrieval.search_engine import SearchEngine
from src.monitoring.logger import RAGLogger

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
    page_title="Buscador de Documentos de Seguros",
    page_icon="🔍",
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
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_searcher() -> SearchEngine:
    """
    Carga el motor de búsqueda (cacheado).
    """
    try:
        return SearchEngine()
    except Exception as e:
        logger.error(f"Error al cargar el motor de búsqueda: {str(e)}")
        st.error("Error al cargar el motor de búsqueda. Por favor, verifique que el índice FAISS existe.")
        return None

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

def render_result_card(result: Dict[str, Any], searcher: SearchEngine) -> None:
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

def main():
    """Función principal de la aplicación Streamlit"""
    
    # Título y descripción
    st.title("🔍 Buscador de Documentos de Seguros")
    st.markdown("""
    Busca información específica en la base de documentos de seguros.
    Utiliza lenguaje natural para hacer tus consultas.
    """)
    
    # Inicializar componentes
    searcher = load_searcher()
    if searcher is None:
        st.error("No se pudo inicializar el motor de búsqueda. Por favor, verifique que el índice FAISS existe.")
        return
        
    metadata_options = load_metadata_options()
    logger = RAGLogger()
    
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
        "¿Qué información buscas?",
        placeholder="Ejemplo: ¿Qué cubre el seguro de hogar en caso de robo?"
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
        "Número de resultados",
        min_value=1,
        max_value=20,
        value=5
    )
    
    # Botón de búsqueda
    if st.button("Buscar", type="primary"):
        if query:
            try:
                with st.spinner("Buscando documentos relevantes..."):
                    # Realizar búsqueda
                    results = searcher.search(
                        query=query,
                        filters=filter_params if filter_params else None
                    )
                    
                    # Mostrar resultados
                    if results:
                        st.markdown(f"### 📄 Resultados encontrados: {len(results)}")
                        
                        # Renderizar tarjetas de resultados
                        for result in results[:num_results]:
                            render_result_card(result, searcher)
                            
                        # Gráfico de scores
                        scores_df = pd.DataFrame({
                            'Documento': [r['metadata'].get('filename', 'Desconocido') for r in results[:num_results]],
                            'Score': [r['score'] for r in results[:num_results]]
                        })
                        
                        fig = go.Figure(data=[
                            go.Bar(
                                x=scores_df['Documento'],
                                y=scores_df['Score'],
                                marker_color='#0066cc'
                            )
                        ])
                        
                        fig.update_layout(
                            title="Relevancia de los resultados",
                            xaxis_title="Documento",
                            yaxis_title="Score",
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        st.warning("No se encontraron documentos relevantes para tu consulta.")
                    
                    # Registrar búsqueda
                    logger.info(
                        "Búsqueda realizada",
                        query=query,
                        num_results=len(results),
                        filters=filter_params
                    )
                    
            except Exception as e:
                st.error(f"Error al realizar la búsqueda: {str(e)}")
                logger.error(
                    "Error en la interfaz",
                    error=str(e),
                    query=query
                )
        else:
            st.warning("Por favor, ingresa una consulta para buscar.")
    
    # Información adicional
    with st.sidebar:
        st.markdown("### 📖 Guía de uso")
        st.markdown("""
        1. Escribe tu pregunta en la barra de búsqueda
        2. Usa los filtros para refinar los resultados
        3. Ajusta el número de resultados a mostrar
        4. Haz clic en "Buscar"
        
        **Tipos de preguntas sugeridas:**
        - ¿Qué cubre el seguro de hogar?
        - ¿Cuáles son las exclusiones del seguro de auto?
        - ¿Cómo funciona el seguro de vida?
        """)
        
        st.markdown("### 🔍 Estadísticas")
        st.metric(
            "Documentos indexados",
            len(metadata_options.get('filename', []))
        )

if __name__ == "__main__":
    main() 