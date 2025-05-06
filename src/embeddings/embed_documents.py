"""
Script para generar embeddings de documentos de seguros.
"""

import os
import json
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
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
    
    # Campos requeridos según el esquema
    REQUIRED_METADATA_FIELDS = [
        'filename',
        'title',
        'insurer',
        'insurance_type',
        'file_path',
        'language'
    ]
    
    # Campos recomendados según el esquema
    RECOMMENDED_METADATA_FIELDS = [
        'coverage_type',
        'document_date',
        'document_version',
        'num_pages',
        'keywords'
    ]
    
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
    
    def validate_metadata(self, metadata: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """
        Valida y normaliza los metadatos según el esquema definido.
        
        Args:
            metadata: Diccionario de metadatos
            filename: Nombre del archivo para logging
            
        Returns:
            Diccionario de metadatos validado y normalizado
        """
        # Verificar campos requeridos
        missing_fields = [
            field for field in self.REQUIRED_METADATA_FIELDS 
            if field not in metadata or not metadata[field]
        ]
        
        # Agregar filename si no está presente
        if 'filename' not in metadata:
            metadata['filename'] = f"{filename}.pdf"
            if 'filename' in missing_fields:
                missing_fields.remove('filename')
        
        if missing_fields:
            self.logger.warning(
                f"Campos requeridos faltantes para {filename}",
                missing_fields=missing_fields
            )
            raise ValueError(f"Campos requeridos faltantes: {', '.join(missing_fields)}")
        
        # Normalizar campos
        normalized = metadata.copy()
        
        # Normalizar fecha si existe
        if 'document_date' in normalized:
            try:
                date = datetime.strptime(normalized['document_date'], '%Y-%m-%d')
                normalized['document_date'] = date.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                self.logger.warning(
                    f"Formato de fecha inválido para {filename}",
                    date=normalized.get('document_date')
                )
                normalized['document_date'] = None
        
        # Normalizar keywords si existen
        if 'keywords' in normalized:
            if isinstance(normalized['keywords'], str):
                normalized['keywords'] = [
                    k.strip() for k in normalized['keywords'].split(';')
                    if k.strip()
                ]
            elif not isinstance(normalized['keywords'], list):
                normalized['keywords'] = []
        
        # Normalizar num_pages a entero
        if 'num_pages' in normalized:
            try:
                normalized['num_pages'] = int(normalized['num_pages'])
            except (ValueError, TypeError):
                normalized['num_pages'] = None
        
        return normalized
    
    def load_documents(self, data_dir: str = "data/processed") -> List[Dict[str, Any]]:
        """
        Carga los documentos procesados y sus metadatos.
        
        Args:
            data_dir: Directorio con los documentos procesados
            
        Returns:
            Lista de documentos con su texto y metadatos
        """
        data_path = Path(data_dir)
        documents = []
        
        # Cargar metadatos
        metadata_path = Path("data/metadata/document_metadata.csv")
        if not metadata_path.exists():
            raise FileNotFoundError("No se encontró el archivo de metadatos")
        
        try:
            # Cargar metadatos desde CSV
            metadata_df = pd.read_csv(metadata_path)
            
            # Validar columnas requeridas
            missing_columns = [
                field for field in self.REQUIRED_METADATA_FIELDS 
                if field not in metadata_df.columns
            ]
            
            if missing_columns:
                raise ValueError(
                    f"Columnas requeridas faltantes en CSV: {', '.join(missing_columns)}"
                )
            
            # Convertir a diccionario usando filename como índice
            metadata_dict = metadata_df.set_index('filename').to_dict('index')
            
            self.logger.info(
                "Metadatos cargados exitosamente",
                total_documents=len(metadata_dict),
                columns=list(metadata_df.columns)
            )
            
            # Procesar cada archivo de texto
            for txt_file in data_path.glob("*.txt"):
                # Obtener el nombre base sin extensión
                base_name = txt_file.stem
                
                # Buscar el metadato correspondiente (reemplazando .pdf por .txt)
                metadata_key = f"{base_name}.pdf"
                
                if metadata_key not in metadata_dict:
                    self.logger.warning(
                        f"No se encontraron metadatos para {base_name}"
                    )
                    continue
                
                try:
                    # Leer el contenido del archivo
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    # Obtener y validar metadatos
                    metadata = metadata_dict[metadata_key]
                    metadata = self.validate_metadata(metadata, base_name)
                    
                    # Actualizar la ruta del archivo
                    metadata['file_path'] = str(txt_file)
                    
                    # Agregar documento a la lista
                    documents.append({
                        'text': text,
                        'metadata': metadata
                    })
                    
                except Exception as e:
                    self.logger.error(
                        f"Error procesando {base_name}",
                        error=str(e)
                    )
                    continue
            
            if not documents:
                raise ValueError("No se pudieron cargar documentos válidos")
            
            return documents
            
        except Exception as e:
            self.logger.error(
                "Error cargando metadatos",
                error=str(e)
            )
            raise
    
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
        Procesa los documentos para generar embeddings.
        """
        try:
            # Cargar documentos
            documents = self.load_documents()
            
            # Lista para almacenar todos los documentos procesados
            processed_documents = []
            
            # Procesar cada documento
            for doc in tqdm(documents, desc="Procesando documentos"):
                try:
                    # Dividir texto en chunks
                    chunks = self.chunk_text(doc['text'])
                    
                    # Generar embeddings
                    embeddings = self.generate_embeddings(chunks)
                    
                    # Guardar embeddings
                    output_file = Path("data/embeddings") / f"{doc['metadata']['filename']}.npy"
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Guardar embeddings como array de numpy
                    np.save(output_file, embeddings)
                    
                    # Guardar metadatos individuales
                    metadata_file = Path("data/embeddings") / f"{doc['metadata']['filename']}.json"
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "filename": doc['metadata']['filename'],
                            "num_chunks": len(chunks),
                            "embedding_dim": embeddings.shape[1],
                            "metadata": doc['metadata']
                        }, f, ensure_ascii=False, indent=2)
                    
                    # Agregar documento a la lista de procesados
                    processed_documents.append({
                        "filename": doc['metadata']['filename'],
                        "metadata": doc['metadata'],
                        "num_chunks": len(chunks),
                        "embedding_dim": embeddings.shape[1]
                    })
                        
                except Exception as e:
                    self.logger.error(
                        f"Error procesando documento {doc['metadata'].get('filename', 'desconocido')}",
                        error=str(e)
                    )
                    continue
            
            # Guardar archivo processed_documents.json
            if processed_documents:
                output_dir = Path("models")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                with open(output_dir / "processed_documents.json", 'w', encoding='utf-8') as f:
                    json.dump(processed_documents, f, ensure_ascii=False, indent=2)
                
                self.logger.info(
                    "Archivo processed_documents.json generado exitosamente",
                    total_documents=len(processed_documents)
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