"""
Script para realizar búsquedas en el índice FAISS.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import faiss
import torch
from sentence_transformers import SentenceTransformer

from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/searcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DocumentSearcher:
    """
    Clase para realizar búsquedas en el índice FAISS.
    """
    
    def __init__(
        self,
        index_dir: str = "models/faiss_index",
        model_name: str = "all-MiniLM-L6-v2",
        device: str = None,
        top_k: int = 5
    ):
        """
        Inicializa el buscador de documentos.
        
        Args:
            index_dir: Directorio con el índice FAISS
            model_name: Nombre del modelo de Sentence Transformers
            device: Dispositivo a usar (cuda/cpu)
            top_k: Número de resultados a retornar
        """
        self.index_dir = Path(index_dir)
        self.top_k = top_k
        
        # Determinar dispositivo
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        # Cargar modelo
        self.model = SentenceTransformer(model_name, device=self.device)
        
        # Inicializar logger y monitor
        self.logger = RAGLogger()
        self.performance_monitor = PerformanceMonitor()
        
        # Cargar índice y metadatos
        self.load_index()
        self.load_metadata()
        
        self.logger.info(
            "Inicializado DocumentSearcher",
            model=model_name,
            device=self.device,
            top_k=top_k
        )
    
    def load_index(self) -> None:
        """
        Carga el índice FAISS.
        """
        index_path = self.index_dir / "insurance_docs.index"
        
        if not index_path.exists():
            raise FileNotFoundError("No se encontró el índice FAISS")
        
        self.index = faiss.read_index(str(index_path))
    
    def load_metadata(self) -> None:
        """
        Carga los metadatos de los documentos.
        """
        metadata_path = self.index_dir / "metadata.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError("No se encontró el archivo de metadatos")
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
    
    @PerformanceMonitor.function_timer("query_embedding")
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Genera el embedding para una consulta.
        
        Args:
            query: Texto de la consulta
            
        Returns:
            Embedding de la consulta
        """
        return self.model.encode(
            query,
            convert_to_tensor=True,
            device=self.device
        ).cpu().numpy()
    
    @PerformanceMonitor.function_timer("search")
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca documentos relevantes para una consulta.
        
        Args:
            query: Texto de la consulta
            
        Returns:
            Lista de documentos relevantes con sus scores
        """
        try:
            # Generar embedding de la consulta
            query_embedding = self.generate_query_embedding(query)
            
            # Realizar búsqueda
            distances, indices = self.index.search(
                query_embedding.reshape(1, -1).astype('float32'),
                self.top_k
            )
            
            # Preparar resultados
            results = []
            
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx != -1:  # FAISS retorna -1 para índices inválidos
                    metadata = self.metadata[idx].copy()
                    metadata['score'] = float(1 / (1 + distance))  # Convertir distancia a score
                    results.append(metadata)
            
            self.logger.info(
                "Búsqueda completada",
                query=query,
                num_results=len(results)
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Error en la búsqueda",
                error=str(e)
            )
            raise
    
    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Formatea los resultados de búsqueda para mostrarlos.
        
        Args:
            results: Lista de resultados de búsqueda
            
        Returns:
            Texto formateado con los resultados
        """
        output = []
        
        for i, result in enumerate(results, 1):
            output.append(f"\nResultado {i} (Score: {result['score']:.3f}):")
            output.append(f"Documento: {result['filename']}")
            output.append(f"Tipo de vehículo: {result['metadata']['tipo_vehiculo']}")
            output.append(f"Tipo de seguro: {result['metadata']['tipo_seguro']}")
            output.append(f"Franquicia: {'Sí' if result['metadata']['franquicia'] else 'No'}")
            output.append(f"Texto relevante:\n{result['text']}\n")
        
        return "\n".join(output)

def main():
    """Función principal para probar el buscador"""
    try:
        # Inicializar buscador
        searcher = DocumentSearcher()
        
        # Ejemplo de búsqueda
        query = "¿Qué cubre el seguro de todo riesgo para camiones?"
        results = searcher.search(query)
        
        # Mostrar resultados
        print(f"\nConsulta: {query}")
        print(searcher.format_results(results))
        
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 