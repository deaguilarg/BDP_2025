"""
Motor de búsqueda para recuperar documentos relevantes usando FAISS.
"""

import json
import numpy as np
import faiss
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer

from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

class SearchEngine:
    """
    Motor de búsqueda para documentos de seguros.
    """
    
    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-mpnet-base-v2",
        index_dir: str = "models/faiss_index",
        top_k: int = 5
    ):
        """
        Inicializa el motor de búsqueda.
        
        Args:
            model_name: Nombre del modelo de embeddings
            index_dir: Directorio con el índice FAISS
            top_k: Número de resultados a retornar
        """
        self.model = SentenceTransformer(model_name)
        self.index_dir = Path(index_dir)
        self.top_k = top_k
        
        # Inicializar logger y monitor
        self.logger = RAGLogger()
        self.performance_monitor = PerformanceMonitor()
        
        # Cargar índice y mapeo
        self.index = None
        self.id_mapping = None
        self.load_latest_index()
    
    def load_latest_index(self) -> None:
        """
        Carga el índice FAISS más reciente.
        """
        try:
            # Buscar archivos más recientes
            index_files = list(self.index_dir.glob("faiss_index_*.bin"))
            mapping_files = list(self.index_dir.glob("id_mapping_*.json"))
            
            if not index_files or not mapping_files:
                raise FileNotFoundError("No se encontraron archivos de índice")
            
            # Obtener archivos más recientes
            latest_index = str(sorted(index_files)[-1])
            latest_mapping = str(sorted(mapping_files)[-1])
            
            # Cargar índice
            self.index = faiss.read_index(latest_index)
            
            # Cargar mapeo
            with open(latest_mapping, 'r', encoding='utf-8') as f:
                self.id_mapping = json.load(f)
            
            self.logger.info(
                "Índice FAISS cargado exitosamente",
                index_file=latest_index,
                mapping_file=latest_mapping,
                num_vectors=len(self.id_mapping)
            )
            
        except Exception as e:
            self.logger.error(
                "Error cargando índice FAISS",
                error=str(e)
            )
            raise
    
    @PerformanceMonitor.function_timer("query_processing")
    def process_query(self, query: str) -> np.ndarray:
        """
        Procesa una consulta y genera su embedding.
        
        Args:
            query: Texto de la consulta
            
        Returns:
            Embedding de la consulta
        """
        return self.model.encode([query])[0]
    
    @PerformanceMonitor.function_timer("search")
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict]:
        """
        Busca documentos relevantes para una consulta.
        
        Args:
            query: Texto de la consulta
            filters: Filtros a aplicar (e.g. insurance_type, insurer)
            
        Returns:
            Lista de documentos relevantes con sus metadatos
        """
        try:
            # Generar embedding de la consulta
            query_vector = self.process_query(query)
            
            # Realizar búsqueda
            distances, indices = self.index.search(
                query_vector.reshape(1, -1),
                self.top_k
            )
            
            # Obtener resultados
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # No más resultados
                    continue
                    
                # Obtener metadatos
                metadata = self.id_mapping[str(idx)]
                
                # Aplicar filtros si existen
                if filters:
                    skip = False
                    for key, value in filters.items():
                        if key in metadata and metadata[key] != value:
                            skip = True
                            break
                    if skip:
                        continue
                
                # Agregar resultado
                results.append({
                    "score": float(1 - distance),  # Convertir distancia a score
                    "metadata": metadata
                })
            
            # Ordenar por score
            results.sort(key=lambda x: x["score"], reverse=True)
            
            self.logger.info(
                "Búsqueda completada",
                query=query,
                num_results=len(results),
                filters=filters
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Error en búsqueda",
                query=query,
                error=str(e)
            )
            raise
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict]:
        """
        Obtiene los metadatos de un documento por su ID.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            Metadatos del documento o None si no existe
        """
        return self.id_mapping.get(str(doc_id))
    
    def filter_by_metadata(
        self,
        results: List[Dict],
        filters: Dict[str, str]
    ) -> List[Dict]:
        """
        Filtra resultados según metadatos.
        
        Args:
            results: Lista de resultados
            filters: Filtros a aplicar
            
        Returns:
            Lista filtrada de resultados
        """
        filtered = []
        for result in results:
            metadata = result["metadata"]
            if all(metadata.get(k) == v for k, v in filters.items()):
                filtered.append(result)
        return filtered 