"""
Motor de búsqueda para recuperar documentos relevantes usando FAISS.
"""

import json
import numpy as np
import faiss
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer
import time

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
        
        # Configurar logging simple
        self.logger = logging.getLogger("SearchEngine")
        self.logger.setLevel(logging.INFO)
        
        # Inicializar monitor de rendimiento
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
                f"Índice FAISS cargado: {latest_index}, "
                f"Mapping: {latest_mapping}, "
                f"Vectores: {len(self.id_mapping)}"
            )
            
        except Exception as e:
            self.logger.error(f"Error cargando índice FAISS: {str(e)}")
            raise
    
    @PerformanceMonitor.function_timer("query_processing")
    def process_query(self, query: str) -> np.ndarray:
        """
        Procesa una consulta y genera su embedding normalizado.
        
        Args:
            query: Texto de la consulta
            
        Returns:
            Embedding normalizado de la consulta como array 2D
        """
        embedding = self.model.encode([query])[0]
        # Normalizar el embedding de la consulta
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        # Convertir a array 2D para FAISS
        return embedding.reshape(1, -1)
    
    @PerformanceMonitor.function_timer("search")
    def search(self, query: str, top_k: int = 10, filter_vehicle_type: bool = True) -> List[Dict]:
        """
        Busca documentos similares a la consulta.
        
        Args:
            query: Consulta de búsqueda
            top_k: Número de resultados a devolver
            filter_vehicle_type: Si aplicar filtrado por tipo de vehículo
            
        Returns:
            Lista de resultados ordenados por relevancia
        """
        try:
            # Procesar consulta
            query_embedding = self.process_query(query)
            
            # Detectar tipo de vehículo en la consulta
            vehicle_types = self._detect_vehicle_type(query)
            
            # Buscar en el índice con más candidatos para filtrado posterior
            search_k = max(50, top_k * 5)  # Buscar más candidatos
            distances, indices = self.index.search(query_embedding, search_k)
            
            # Procesar resultados
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # Resultado inválido
                    continue
                    
                # Obtener metadatos
                metadata = self.id_mapping.get(str(idx), {})
                if not metadata:
                    continue
                    
                # Calcular score mejorado
                base_score = max(0.0, 1.0 - (dist / 2.0))
                
                # Bonus por contenido específico vs genérico
                text = metadata.get('text', '')
                section = metadata.get('section', 'general')
                
                # Aplicar bonus por sección específica
                if section == 'asegurado':  # La sección que contiene info específica
                    base_score *= 1.3
                elif section == 'consiste':  # La sección más genérica
                    base_score *= 0.7
                
                # Filtrar por tipo de vehículo si está habilitado
                if filter_vehicle_type and vehicle_types:
                    filename = metadata.get('filename', '').lower()
                    if not any(vtype in filename for vtype in vehicle_types):
                        continue  # Saltar si no coincide el tipo de vehículo
                
                # Bonus adicional por coincidencia de tipo de vehículo
                if vehicle_types:
                    filename = metadata.get('filename', '').lower()
                    if any(vtype in filename for vtype in vehicle_types):
                        base_score *= 1.2
                
                # Bonus por contenido específico en el texto
                if self._has_specific_content(text, vehicle_types):
                    base_score *= 1.4
                
                result = {
                    'text': text,
                    'metadata': metadata,
                    'score': min(1.0, base_score),  # Normalizar a máximo 1.0
                    'distance': float(dist),
                    'section': section
                }
                results.append(result)
            
            # Ordenar por score mejorado y aplicar filtro de score mínimo
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Filtrar resultados con score muy bajo
            min_score = 0.15  # Threshold más permisivo
            filtered_results = [r for r in results if r['score'] >= min_score]
            
            self.logger.info(
                f"Búsqueda completada: query='{query}', "
                f"candidates={len(results)}, filtered={len(filtered_results)}, "
                f"vehicle_types={vehicle_types}"
            )
            
            return filtered_results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {str(e)}")
            return []
    
    def _detect_vehicle_type(self, query: str) -> List[str]:
        """
        Detecta el tipo de vehículo en la consulta.
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            Lista de tipos de vehículo detectados
        """
        query_lower = query.lower()
        vehicle_types = []
        
        # Detectar motocicletas
        if any(keyword in query_lower for keyword in ['moto', 'motocicleta', 'ciclomotor']):
            vehicle_types.extend(['moto', 'ciclomotor'])
        
        # Detectar automóviles
        if any(keyword in query_lower for keyword in ['coche', 'auto', 'automóvil', 'turismo']):
            vehicle_types.extend(['auto', 'turismo'])
        
        # Detectar vehículos comerciales
        if any(keyword in query_lower for keyword in ['camión', 'furgón', 'furgoneta', 'remolque']):
            vehicle_types.extend(['camion', 'furgon', 'remolque'])
        
        return vehicle_types
    
    def _has_specific_content(self, text: str, vehicle_types: List[str]) -> bool:
        """
        Verifica si el texto contiene contenido específico relevante.
        
        Args:
            text: Texto a verificar
            vehicle_types: Tipos de vehículo buscados
            
        Returns:
            True si contiene contenido específico
        """
        text_lower = text.lower()
        
        # Verificar contenido específico de seguros
        specific_indicators = [
            '€', 'euros', 'muerte', 'invalidez', 'indemnización',
            'cobertura', 'asegurado', 'prima', 'franquicia'
        ]
        
        # Debe tener al menos 2 indicadores específicos
        specific_count = sum(1 for indicator in specific_indicators if indicator in text_lower)
        
        return specific_count >= 2
    
    def _debug_search_keywords(self, query: str) -> None:
        """
        Método de debug para buscar documentos por palabras clave cuando la búsqueda semántica falla.
        """
        try:
            keywords = query.lower().split()
            matching_docs = []
            
            for doc_id, doc_data in self.id_mapping.items():
                filename = doc_data.get('filename', '').lower()
                keywords_list = doc_data.get('metadata', {}).get('keywords', [])
                
                # Buscar coincidencias en nombre de archivo o keywords
                for keyword in keywords:
                    if keyword in filename or keyword in [k.lower() for k in keywords_list]:
                        matching_docs.append(filename)
                        break
            
            if matching_docs:
                self.logger.info(f"Documentos con keywords relacionadas: {matching_docs[:5]}")
            else:
                self.logger.info("No se encontraron documentos con keywords relacionadas")
                
        except Exception as e:
            self.logger.error(f"Error en debug de keywords: {e}")
    
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
        filters: Dict[str, List[str]]
    ) -> List[Dict]:
        """
        Filtra resultados según metadatos.
        
        Args:
            results: Lista de resultados
            filters: Filtros a aplicar (key: lista de valores permitidos)
            
        Returns:
            Lista filtrada de resultados
        """
        filtered = []
        for result in results:
            metadata = result["metadata"]
            # Verificar que el resultado coincida con al menos uno de los valores de cada filtro
            matches_all_filters = True
            for key, allowed_values in filters.items():
                metadata_value = str(metadata.get(key, ''))
                if not any(str(allowed_value) == metadata_value for allowed_value in allowed_values):
                    matches_all_filters = False
                    break
            
            if matches_all_filters:
                filtered.append(result)
        return filtered 