"""
Script para generar embeddings de documentos de seguros.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/embed_documents.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DocumentEmbedder:
    """
    Clase para generar embeddings de documentos de seguros.
    """
    
    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-mpnet-base-v2",
        device: str = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        Inicializa el generador de embeddings.
        
        Args:
            model_name: Nombre del modelo de Sentence Transformers
            device: Dispositivo a usar (cuda/cpu)
            chunk_size: Tamaño de los chunks de texto
            chunk_overlap: Superposición entre chunks
        """
        # Determinar dispositivo
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        # Cargar modelo
        self.model = SentenceTransformer(model_name, device=self.device)
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Inicializar logger y monitor
        self.logger = RAGLogger()
        self.performance_monitor = PerformanceMonitor()
        
        self.logger.info(
            "Inicializado DocumentEmbedder",
            model=model_name,
            device=self.device,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def load_documents(self, data_dir: str = "data/processed") -> List[Dict[str, Any]]:
        """
        Carga los documentos procesados.
        
        Args:
            data_dir: Directorio con los documentos procesados
            
        Returns:
            Lista de documentos con su texto y metadatos
        """
        data_path = Path(data_dir)
        documents = []
        
        # Cargar metadatos
        metadata_path = Path("data/metadata/metadata.csv")
        if not metadata_path.exists():
            raise FileNotFoundError("No se encontró el archivo de metadatos")
        
        # Procesar cada archivo de texto
        for txt_file in data_path.glob("*.txt"):
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Buscar metadatos correspondientes
                filename = txt_file.stem
                
                documents.append({
                    "filename": filename,
                    "text": text,
                    "metadata": {}  # Se completará con los metadatos
                })
                
            except Exception as e:
                self.logger.warning(
                    f"No se pudo procesar el archivo {txt_file}",
                    error=str(e)
                )
        
        return documents
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Divide el texto en chunks.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            chunks.append(chunk)
            
            if i + self.chunk_size >= len(words):
                break
        
        return chunks
    
    @PerformanceMonitor.function_timer("embedding_generation")
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Genera embeddings para una lista de textos.
        
        Args:
            texts: Lista de textos
            
        Returns:
            Matriz de embeddings
        """
        return self.model.encode(
            texts,
            convert_to_tensor=True,
            device=self.device
        ).cpu().numpy()
    
    def process_documents(self) -> None:
        """
        Procesa todos los documentos y genera sus embeddings.
        """
        try:
            # Cargar documentos
            documents = self.load_documents()
            
            # Procesar cada documento
            processed_docs = []
            
            for doc in tqdm(documents, desc="Procesando documentos"):
                # Dividir en chunks
                chunks = self.chunk_text(doc["text"])
                
                # Generar embeddings
                embeddings = self.generate_embeddings(chunks)
                
                processed_docs.append({
                    "filename": doc["filename"],
                    "chunks": chunks,
                    "embeddings": embeddings.tolist(),
                    "metadata": doc["metadata"]
                })
            
            # Guardar resultados
            output_path = Path("models/processed_documents.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed_docs, f, ensure_ascii=False, indent=2)
            
            self.logger.info(
                "Procesamiento completado",
                total_documents=len(processed_docs)
            )
            
        except Exception as e:
            self.logger.error(
                "Error procesando documentos",
                error=str(e)
            )
            raise

def main():
    """Función principal para generar embeddings"""
    try:
        # Inicializar embedder
        embedder = DocumentEmbedder()
        
        # Procesar documentos
        embedder.process_documents()
        
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 