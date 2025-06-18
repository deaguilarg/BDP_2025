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
import logging
from typing import Dict, Any, List, Tuple
from sklearn.decomposition import PCA
import umap

from src.retrieval.search_engine import SearchEngine

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
    Usa el índice FAISS optimizado en lugar de archivos .npy individuales.
    """
    try:
        return SearchEngine(top_k=20)  # Aumentamos para incluir más resultados
    except Exception as e:
        st.error(f"Error cargando SearchEngine: {str(e)}")
        raise

@st.cache_data
def load_embeddings_data() -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Carga los embeddings y metadatos desde el índice FAISS optimizado.
    NUEVA VERSIÓN: Usa el mismo índice FAISS que SearchEngine para consistencia.
    """
    try:
        # Cargar SearchEngine que tiene el índice FAISS
        searcher = SearchEngine()
        
        if not hasattr(searcher, 'id_mapping') or not searcher.id_mapping:
            st.error("No se encontró el índice FAISS. Por favor, ejecute rebuild_index.py")
            return np.array([]), []
        
        if not hasattr(searcher, 'index') or searcher.index is None:
            st.error("Índice FAISS no cargado correctamente")
            return np.array([]), []
        
        # Extraer embeddings del índice FAISS
        total_vectors = searcher.index.ntotal
        if total_vectors == 0:
            st.error("El índice FAISS está vacío")
            return np.array([]), []
        
        # Obtener todos los embeddings del índice FAISS
        all_embeddings = searcher.index.reconstruct_n(0, total_vectors)
        
        # Crear metadata list en el mismo orden que los embeddings
        all_metadata = []
        for i in range(total_vectors):
            if str(i) in searcher.id_mapping:  # Convertir a string para la clave
                metadata = searcher.id_mapping[str(i)].copy()
                filename = metadata.get('filename', f'chunk_{i}')
                
                all_metadata.append({
                    'filename': filename,
                    'chunk': f"Chunk {i+1}",
                    'metadata': metadata,
                    'text': metadata.get('text', ''),  # Incluir texto si está disponible
                    'faiss_id': i
                })
            else:
                # Metadata por defecto para IDs faltantes
                all_metadata.append({
                    'filename': f'unknown_{i}',
                    'chunk': f"Chunk {i+1}",
                    'metadata': {},
                    'text': '',
                    'faiss_id': i
                })
        
        st.success(f"✅ Cargados {total_vectors} embeddings desde índice FAISS")
        return all_embeddings, all_metadata
        
    except Exception as e:
        st.error(f"Error cargando desde índice FAISS: {str(e)}")
        st.info("💡 Consejo: Ejecute 'python rebuild_index.py' para reconstruir el índice")
        return np.array([]), []

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
    Ahora usa datos del índice FAISS que incluye el texto real.
    """
    # Obtener el texto del resultado (ya viene del índice FAISS)
    chunk_text = result.get('text', '')
    if not chunk_text:
        chunk_text = result.get('metadata', {}).get('text', 'Texto no disponible')
    
    # Truncar texto si es muy largo para la visualización
    if len(chunk_text) > 500:
        chunk_text = chunk_text[:500] + "..."
        
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
                {chunk_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal de la interfaz de depuración"""
    
    st.title("🔬 Debug - Visualización de Embeddings")
    
    try:
        # Inicializar componentes
        searcher = load_searcher()
        embeddings, metadata = load_embeddings_data()
        logger = logging.getLogger("debug_interface")
        
        if len(embeddings) == 0:
            st.error("No se encontraron embeddings para visualizar.")
            st.info("💡 Posibles soluciones:")
            st.code("python -c \"import sys; sys.path.append('src'); from embeddings.embed_documents import DocumentEmbedder; embedder = DocumentEmbedder(); embedder.process_documents()\"")
            st.code("python rebuild_index.py")
            return
            
    except Exception as e:
        st.error(f"Error inicializando la aplicación: {str(e)}")
        st.info("💡 Intente reiniciar la aplicación o reconstruir el índice FAISS")
        return
    
    # Información del sistema (NUEVA)
    st.sidebar.markdown("### 🔧 Estado del Sistema")
    st.sidebar.metric("Total de chunks", len(embeddings))
    st.sidebar.metric("Fuente de datos", "Índice FAISS")
    
    # Contar documentos de moto
    moto_count = len([m for m in metadata if 'moto' in m['filename'].lower() or 'ciclomotor' in m['filename'].lower()])
    st.sidebar.metric("Documentos de moto", moto_count)
    
    if hasattr(searcher, 'index') and searcher.index:
        st.sidebar.success("✅ Índice FAISS cargado")
        st.sidebar.metric("Vectores en FAISS", searcher.index.ntotal)
    else:
        st.sidebar.error("❌ Índice FAISS no cargado")
    
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
            (i, m) for i, m in enumerate(metadata)
            if m['filename'] == selected_file
        ]
        
        if doc_chunks:
            st.success(f"Encontrados {len(doc_chunks)} chunks para {selected_file}")
            
            for i, chunk_data in doc_chunks:
                chunk_text = chunk_data.get('text', 'Texto no disponible')
                if not chunk_text:
                    chunk_text = f"Chunk {i + 1} - Contenido no disponible"
                
                with st.expander(f"Chunk {i + 1} (ID FAISS: {chunk_data.get('faiss_id', i)})"):
                    st.markdown(f"""
                    <div class="chunk-viewer">
                    {chunk_text[:1000]}{'...' if len(chunk_text) > 1000 else ''}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Mostrar metadatos del chunk
                    if chunk_data.get('metadata'):
                        st.json(chunk_data['metadata'])
                    else:
                        st.info("Metadatos no disponibles para este chunk")
        else:
            st.warning(f"No se encontraron chunks para {selected_file}")
    
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
            # Crear un conjunto de claves únicas de metadatos
            unique_metadata_keys = sorted(set(
                k for m in metadata 
                for k in m['metadata'].keys() 
                if m['metadata'].get(k) is not None
            ))
            
            for i, key in enumerate(unique_metadata_keys):
                with col1 if i % 2 == 0 else col2:
                    # Obtener todos los valores únicos para esta clave
                    unique_values = sorted(set(
                        str(m['metadata'].get(key)) 
                        for m in metadata 
                        if m['metadata'].get(key) is not None
                    ))
                    selected = st.multiselect(
                        f"Filtrar por {key}",
                        options=unique_values,
                        key=f"filter_{key}_{i}"  # Hacemos la clave única añadiendo el índice
                    )
                    if selected:
                        filter_params[key] = selected
        
        if st.button("Buscar", type="primary"):
            if query:
                try:
                    # Realizar búsqueda usando el mismo motor que los tests exitosos
                    # El parámetro filters no está implementado en SearchEngine.search()
                    results = searcher.search(query=query)
                    
                    # Mostrar estadísticas
                    st.markdown(f"#### 📄 Resultados ({len(results)})")
                    
                    # Contar documentos de moto en resultados
                    moto_results = 0
                    for result in results:
                        filename = result['metadata'].get('filename', '')
                        if 'moto' in filename.lower() or 'ciclomotor' in filename.lower():
                            moto_results += 1
                    
                    if moto_results > 0:
                        st.success(f"🏍️ {moto_results} documentos de moto encontrados!")
                    else:
                        st.warning("❌ No se encontraron documentos de moto en los resultados")
                    
                    # Agrupar resultados por documento
                    grouped_results = {}
                    for result in results:
                        filename = result['metadata'].get('filename', 'Desconocido')
                        if filename not in grouped_results:
                            grouped_results[filename] = []
                        grouped_results[filename].append(result)
                    
                    # Mostrar resultados agrupados
                    for filename, doc_results in grouped_results.items():
                        # Destacar documentos de moto
                        is_moto = 'moto' in filename.lower() or 'ciclomotor' in filename.lower()
                        icon = "🏍️" if is_moto else "📄"
                        
                        with st.expander(f"{icon} {filename} ({len(doc_results)} chunks)"):
                            for result in doc_results:
                                render_result_card(result)
                    
                    # Visualizar embedding de la consulta junto con los resultados
                    st.markdown("#### 📊 Visualización de la consulta")
                    
                    try:
                        # Generar embedding de la consulta
                        query_embedding_2d = searcher.process_query(query)
                        
                        # Convertir de 2D a 1D para la visualización
                        if query_embedding_2d.ndim > 1:
                            query_embedding = query_embedding_2d.flatten()
                        else:
                            query_embedding = query_embedding_2d
                        
                        # Verificar que las dimensiones coincidan
                        if query_embedding.shape[0] != embeddings.shape[1]:
                            st.warning(f"Dimensiones no coinciden: query={query_embedding.shape[0]}, embeddings={embeddings.shape[1]}")
                        else:
                            # Combinar embeddings
                            combined_embeddings = np.vstack([
                                embeddings,
                                query_embedding.reshape(1, -1)
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
                                ),
                                hovertemplate='Documento: %{text}<extra></extra>',
                                text=[m['filename'] for m in metadata]
                            ))
                            
                            # Plotear consulta
                            fig.add_trace(go.Scatter(
                                x=[combined_2d[-1, 0]],
                                y=[combined_2d[-1, 1]],
                                mode='markers',
                                name='Consulta',
                                marker=dict(
                                    color='red',
                                    size=15,
                                    symbol='star'
                                ),
                                hovertemplate=f'Consulta: {query}<extra></extra>'
                            ))
                            
                            fig.update_layout(
                                title="Visualización de la consulta en el espacio de embeddings",
                                showlegend=True,
                                width=800,
                                height=600
                            )
                            
                            st.plotly_chart(fig)
                    
                    except Exception as e:
                        st.error(f"Error en visualización: {str(e)}")
                        st.info("La visualización de la consulta no está disponible en este momento.")
                    
                except Exception as e:
                    st.error(f"Error al realizar la búsqueda: {str(e)}")
            else:
                st.warning("Por favor, ingresa una consulta para buscar.")

if __name__ == "__main__":
    main() 