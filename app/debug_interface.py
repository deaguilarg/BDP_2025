"""
Interfaz de depuración para visualizar chunks y embeddings.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
from typing import Dict, Any, List, Tuple
from sklearn.decomposition import PCA
import umap

from src.retrieval.search_engine import SearchEngine
from src.monitoring.logger import RAGLogger

# Configuración de la página
st.set_page_config(
    page_title="Debug - Visualización de Embeddings",
    page_icon="🔬",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .debug-section {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .chunk-viewer {
        font-family: monospace;
        background-color: #f1f3f5;
        padding: 1rem;
        border-radius: 0.3rem;
        white-space: pre-wrap;
    }
    .result-card {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 5px solid #0066cc;
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
    return SearchEngine(top_k=10)  # Aumentamos el número de resultados

@st.cache_data
def load_embeddings_data() -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Carga los embeddings y metadatos (cacheado).
    """
    embeddings_dir = Path("data/embeddings")
    if not embeddings_dir.exists():
        st.error("No se encontró el directorio de embeddings")
        return np.array([]), []
    
    all_embeddings = []
    all_metadata = []
    
    # Cargar metadatos generales
    metadata_path = Path("models/processed_documents.json")
    if not metadata_path.exists():
        st.error("No se encontró el archivo de metadatos")
        return np.array([]), []
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        documents_metadata = json.load(f)
    
    # Crear diccionario de metadatos por filename
    metadata_dict = {doc['filename']: doc['metadata'] for doc in documents_metadata}
    
    # Cargar embeddings y metadatos individuales
    for npy_file in embeddings_dir.glob("*.npy"):
        try:
            # Cargar embeddings
            embeddings = np.load(npy_file)
            
            # Cargar metadatos correspondientes
            metadata_file = npy_file.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    doc_metadata = json.load(f)
                
                # Obtener metadatos generales
                filename = doc_metadata['filename']
                general_metadata = metadata_dict.get(filename, {})
                
                # Combinar metadatos
                combined_metadata = {**general_metadata, **doc_metadata['metadata']}
                
                # Agregar embeddings y metadatos
                all_embeddings.extend(embeddings)
                all_metadata.extend([{
                    'filename': filename,
                    'chunk': f"Chunk {i+1}",
                    'metadata': combined_metadata
                } for i in range(len(embeddings))])
                
        except Exception as e:
            st.warning(f"Error cargando {npy_file.name}: {str(e)}")
            continue
    
    if not all_embeddings:
        st.error("No se encontraron embeddings para visualizar")
        return np.array([]), []
    
    return np.array(all_embeddings), all_metadata

@st.cache_data
def reduce_dimensions(embeddings: np.ndarray, method: str = "pca") -> np.ndarray:
    """
    Reduce la dimensionalidad de los embeddings para visualización.
    """
    if len(embeddings) == 0:
        return np.array([])
        
    if method == "pca":
        reducer = PCA(n_components=2)
    else:  # umap
        reducer = umap.UMAP(n_components=2, random_state=42)
    
    return reducer.fit_transform(embeddings)

def plot_embeddings(embeddings_2d: np.ndarray, metadata: List[Dict[str, Any]], color_by: str) -> None:
    """
    Genera un gráfico interactivo de embeddings.
    """
    if len(embeddings_2d) == 0:
        st.warning("No hay embeddings para visualizar")
        return
        
    df = pd.DataFrame(
        embeddings_2d,
        columns=['x', 'y']
    )
    
    # Añadir metadatos
    df['filename'] = [m['filename'] for m in metadata]
    for key in metadata[0]['metadata'].keys():
        df[key] = [m['metadata'][key] for m in metadata]
    
    # Crear gráfico
    fig = px.scatter(
        df,
        x='x',
        y='y',
        color=color_by,
        hover_data=['filename'] + list(metadata[0]['metadata'].keys()),
        title=f"Visualización de Embeddings (coloreado por {color_by})"
    )
    
    fig.update_layout(
        showlegend=True,
        width=800,
        height=600
    )
    
    st.plotly_chart(fig)

def render_result_card(result: Dict[str, Any]) -> None:
    """
    Renderiza una tarjeta de resultado con información detallada.
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
            <div class="chunk-viewer" style="margin: 1rem 0;">
                {result.get('text', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal de la interfaz de depuración"""
    
    st.title("🔬 Debug - Visualización de Embeddings")
    
    # Inicializar componentes
    searcher = load_searcher()
    embeddings, metadata = load_embeddings_data()
    logger = RAGLogger()
    
    if len(embeddings) == 0:
        st.error("No se encontraron embeddings para visualizar. Por favor, ejecute primero el generador de embeddings.")
        return
    
    # Tabs para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs([
        "📊 Visualización de Embeddings",
        "📝 Explorador de Chunks",
        "🔍 Pruebas de Búsqueda"
    ])
    
    # Tab 1: Visualización de Embeddings
    with tab1:
        st.markdown("### Visualización de Embeddings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            reduction_method = st.selectbox(
                "Método de reducción de dimensionalidad",
                ["PCA", "UMAP"],
                key="reduction_method"
            )
        
        with col2:
            color_by = st.selectbox(
                "Colorear por",
                ["filename"] + list(metadata[0]['metadata'].keys()),
                key="color_by"
            )
        
        # Reducir dimensionalidad y visualizar
        embeddings_2d = reduce_dimensions(
            embeddings,
            method=reduction_method.lower()
        )
        
        plot_embeddings(embeddings_2d, metadata, color_by)
        
        # Métricas de embeddings
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total de embeddings",
                embeddings.shape[0]
            )
        
        with col2:
            st.metric(
                "Dimensión original",
                embeddings.shape[1]
            )
        
        with col3:
            st.metric(
                "Documentos únicos",
                len(set(m['filename'] for m in metadata))
            )
    
    # Tab 2: Explorador de Chunks
    with tab2:
        st.markdown("### Explorador de Chunks")
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            selected_file = st.selectbox(
                "Seleccionar documento",
                sorted(set(m['filename'] for m in metadata))
            )
        
        # Mostrar chunks del documento seleccionado
        doc_chunks = [
            (i, m['chunk']) for i, m in enumerate(metadata)
            if m['filename'] == selected_file
        ]
        
        for i, chunk in doc_chunks:
            with st.expander(f"Chunk {i + 1}"):
                st.markdown(f"""
                <div class="chunk-viewer">
                {chunk}
                </div>
                """, unsafe_allow_html=True)
                
                # Mostrar metadatos del chunk
                st.json(metadata[i]['metadata'])
    
    # Tab 3: Pruebas de Búsqueda
    with tab3:
        st.markdown("### Pruebas de Búsqueda")
        
        # Consulta de prueba
        query = st.text_input(
            "Consulta de prueba",
            placeholder="Escribe una consulta para probar la búsqueda"
        )
        
        # Filtros de búsqueda
        with st.expander("Filtros de búsqueda"):
            col1, col2 = st.columns(2)
            
            filter_params = {}
            for i, (key, values) in enumerate(set((k, v) for m in metadata for k, v in m['metadata'].items() if v)):
                with col1 if i % 2 == 0 else col2:
                    selected = st.multiselect(
                        f"Filtrar por {key}",
                        options=sorted(set(str(v) for m in metadata if m['metadata'].get(key) == v)),
                        key=f"filter_{key}"
                    )
                    if selected:
                        filter_params[key] = selected
        
        if st.button("Buscar", type="primary"):
            if query:
                try:
                    # Realizar búsqueda
                    results = searcher.search(query, filters=filter_params if filter_params else None)
                    
                    # Mostrar resultados
                    st.markdown(f"#### 📄 Resultados ({len(results)})")
                    
                    # Agrupar resultados por documento
                    grouped_results = {}
                    for result in results:
                        filename = result['metadata'].get('filename', 'Desconocido')
                        if filename not in grouped_results:
                            grouped_results[filename] = []
                        grouped_results[filename].append(result)
                    
                    # Mostrar resultados agrupados
                    for filename, doc_results in grouped_results.items():
                        with st.expander(f"📄 {filename} ({len(doc_results)} chunks)"):
                            for result in doc_results:
                                render_result_card(result)
                    
                    # Visualizar embedding de la consulta junto con los resultados
                    st.markdown("#### 📊 Visualización de la consulta")
                    
                    # Generar embedding de la consulta
                    query_embedding = searcher.process_query(query)
                    
                    # Combinar embeddings
                    combined_embeddings = np.vstack([
                        embeddings,
                        query_embedding
                    ])
                    
                    # Reducir dimensionalidad
                    combined_2d = reduce_dimensions(combined_embeddings)
                    
                    # Crear gráfico
                    fig = go.Figure()
                    
                    # Plotear embeddings existentes
                    fig.add_trace(go.Scatter(
                        x=combined_2d[:-1, 0],
                        y=combined_2d[:-1, 1],
                        mode='markers',
                        name='Documentos',
                        marker=dict(
                            color='blue',
                            size=8,
                            opacity=0.5
                        )
                    ))
                    
                    # Plotear consulta
                    fig.add_trace(go.Scatter(
                        x=[combined_2d[-1, 0]],
                        y=[combined_2d[-1, 1]],
                        mode='markers',
                        name='Consulta',
                        marker=dict(
                            color='red',
                            size=12,
                            symbol='star'
                        )
                    ))
                    
                    fig.update_layout(
                        title="Visualización de la consulta en el espacio de embeddings",
                        showlegend=True,
                        width=800,
                        height=600
                    )
                    
                    st.plotly_chart(fig)
                    
                except Exception as e:
                    st.error(f"Error al realizar la búsqueda: {str(e)}")
            else:
                st.warning("Por favor, ingresa una consulta para buscar.")

if __name__ == "__main__":
    main() 