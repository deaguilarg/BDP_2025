"""
Script para construir y guardar el índice FAISS.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import faiss
import torch
from tqdm import tqdm

from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/index_builder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FAISSIndexBuilder:
    """
    Clase para construir y guardar el índice FAISS.
    """
    
    def __init__(
        self,
        models_dir: str = "models",
        index_dir: str = "models/faiss_index",
        dimension: int = 768,  # Dimensión de los embeddings de MPNet
        nlist: int = 100,      # Número de clusters para IVF
        nprobe: int = 10       # Número de clusters a explorar durante la búsqueda
    ):
        """
        Inicializa el constructor del índice FAISS.
        
        Args:
            models_dir: Directorio con los embeddings
            index_dir: Directorio donde se guardará el índice
            dimension: Dimensión de los embeddings
            nlist: Número de clusters para IVF
            nprobe: Número de clusters a explorar durante la búsqueda
        """
        self.models_dir = Path(models_dir)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.dimension = dimension
        self.nlist = nlist
        self.nprobe = nprobe
        
        # Inicializar logger y monitor
        self.logger = RAGLogger()
        self.performance_monitor = PerformanceMonitor()
        
        # Crear índice FAISS
        quantizer = faiss.IndexFlatL2(dimension)
        self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
        
        self.logger.info(
            "Inicializado FAISSIndexBuilder",
            dimension=dimension,
            nlist=nlist,
            nprobe=nprobe
        )
    
    def load_embeddings(self) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Carga los embeddings y metadatos desde el archivo JSON.
        
        Returns:
            Tupla con matriz de embeddings y lista de metadatos
        """
        embeddings_path = self.models_dir / "processed_documents.json"
        
        if not embeddings_path.exists():
            raise FileNotFoundError("No se encontró el archivo de embeddings")
        
        with open(embeddings_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        # Extraer embeddings y metadatos
        all_embeddings = []
        all_metadata = []
        
        for doc in documents:
            embeddings = doc["embeddings"]
            metadata = {
                "filename": doc["filename"],
                "chunk_index": len(all_embeddings),
                "text": doc["chunks"][0],  # Texto del chunk
                "metadata": doc["metadata"]  # Metadatos del documento
            }
            
            all_embeddings.extend(embeddings)
            all_metadata.extend([metadata] * len(embeddings))
        
        return np.array(all_embeddings, dtype=np.float32), all_metadata
    
    @PerformanceMonitor.function_timer("index_training")
    def train_index(self, embeddings: np.ndarray) -> None:
        """
        Entrena el índice FAISS con los embeddings.
        
        Args:
            embeddings: Matriz de embeddings
        """
        if not self.index.is_trained:
            self.index.train(embeddings)
            self.index.nprobe = self.nprobe
    
    @PerformanceMonitor.function_timer("index_adding")
    def add_to_index(self, embeddings: np.ndarray) -> None:
        """
        Añade los embeddings al índice.
        
        Args:
            embeddings: Matriz de embeddings
        """
        self.index.add(embeddings)
    
    def save_index(self) -> None:
        """
        Guarda el índice FAISS y los metadatos.
        """
        # Guardar índice
        index_path = self.index_dir / "insurance_docs.index"
        faiss.write_index(self.index, str(index_path))
        
        self.logger.info(
            "Índice FAISS guardado",
            path=str(index_path),
            total_vectors=self.index.ntotal
        )
    
    def build_index(self) -> None:
        """
        Construye el índice FAISS con los embeddings.
        """
        try:
            # Cargar embeddings
            embeddings, metadata = self.load_embeddings()
            
            # Entrenar índice
            self.train_index(embeddings)
            
            # Añadir vectores
            self.add_to_index(embeddings)
            
            # Guardar índice y metadatos
            self.save_index()
            
            # Guardar metadatos
            metadata_path = self.index_dir / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.info(
                "Construcción del índice completada",
                total_vectors=self.index.ntotal,
                metadata_path=str(metadata_path)
            )
            
        except Exception as e:
            self.logger.error(
                "Error construyendo el índice",
                error=str(e)
            )
            raise

def main():
    """Función principal para construir el índice"""
    try:
        # Inicializar builder
        builder = FAISSIndexBuilder()
        
        # Construir índice
        builder.build_index()
        
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 