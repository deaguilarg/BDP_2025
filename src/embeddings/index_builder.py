"""
Construcción y gestión del índice FAISS para embeddings de documentos.
"""

import json
import logging
import numpy as np
import faiss
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.monitoring.performance import PerformanceMonitor

class FAISSIndexBuilder:
    """
    Constructor y gestor del índice FAISS.
    """
    
    def __init__(
        self,
        embeddings_dir: str = "data/embeddings",
        index_dir: str = "models/faiss_index",
        dimension: int = 768,  # Dimensión por defecto para mpnet
        index_type: str = "flat"  # Tipo de índice: flat, ivf, hnsw
    ):
        """
        Inicializa el constructor del índice.
        
        Args:
            embeddings_dir: Directorio con los embeddings
            index_dir: Directorio para guardar el índice
            dimension: Dimensión de los embeddings
            index_type: Tipo de índice FAISS a construir
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.dimension = dimension
        self.index_type = index_type
        
        # Configurar logging simple
        self.logger = logging.getLogger("FAISSIndexBuilder")
        self.logger.setLevel(logging.INFO)
        
        # Inicializar monitor de rendimiento
        self.performance_monitor = PerformanceMonitor()
        
        # Mapeo de IDs a metadatos
        self.id_to_metadata: Dict[int, Dict] = {}
        self.current_id = 0
    
    def _create_index(self) -> faiss.Index:
        """
        Crea un índice FAISS según el tipo especificado.
        
        Returns:
            Índice FAISS inicializado
        """
        if self.index_type == "flat":
            # Índice plano (búsqueda exhaustiva)
            return faiss.IndexFlatIP(self.dimension)
        
        elif self.index_type == "ivf":
            # Índice IVF con cuantización
            nlist = max(4, self.current_id // 39)  # ~39 vectores por cluster
            quantizer = faiss.IndexFlatIP(self.dimension)
            return faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        
        elif self.index_type == "hnsw":
            # Índice HNSW para búsqueda aproximada rápida
            return faiss.IndexHNSWFlat(self.dimension, 32)  # 32 conexiones por nodo
        
        else:
            raise ValueError(f"Tipo de índice no soportado: {self.index_type}")
    
    @PerformanceMonitor.function_timer("load_embeddings")
    def load_embeddings(self) -> Tuple[np.ndarray, List[Dict]]:
        """
        Carga los embeddings y sus metadatos.
        
        Returns:
            Tupla con matriz de embeddings y lista de metadatos
        """
        all_embeddings = []
        all_metadata = []
        
        # Cargar cada archivo de embeddings
        for emb_file in self.embeddings_dir.glob("*.npy"):
            try:
                # Cargar embeddings
                embeddings = np.load(emb_file)
                
                # Cargar metadatos correspondientes
                metadata_file = emb_file.with_suffix(".json")
                if not metadata_file.exists():
                    self.logger.warning(
                        f"No se encontró archivo de metadatos para {emb_file}"
                    )
                    continue
                
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Agregar embeddings
                all_embeddings.append(embeddings)
                
                # Obtener chunks del metadata
                chunks = metadata.get("chunks", [])
                base_metadata = metadata.get("metadata", {})
                
                # Crear entrada de metadatos para cada embedding/chunk
                num_embeddings = len(embeddings)
                for i in range(num_embeddings):
                    # Combinar metadatos base con información del chunk específico
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata.update({
                        "filename": metadata.get("filename", ""),
                        "chunk_index": i,
                        "total_chunks": num_embeddings,
                        "embedding_dim": metadata.get("embedding_dim", embeddings.shape[1])
                    })
                    
                    # IMPORTANTE: Incluir el texto real del chunk
                    if i < len(chunks):
                        chunk_info = chunks[i]
                        chunk_metadata.update({
                            "text": chunk_info.get("text", ""),
                            "section": chunk_info.get("section", "general"),
                            "section_title": chunk_info.get("section_title", ""),
                            "start_position": chunk_info.get("start_position", 0),
                            "end_position": chunk_info.get("end_position", 0)
                        })
                    else:
                        # Fallback si no hay información de chunk
                        chunk_metadata["text"] = ""
                        chunk_metadata["section"] = "general"
                        
                    all_metadata.append(chunk_metadata)
                
                self.logger.info(f"Cargado: {emb_file.name} - {num_embeddings} chunks con texto")
                
            except Exception as e:
                self.logger.error(f"Error cargando embeddings de {emb_file}: {str(e)}")
                continue
        
        if not all_embeddings:
            raise ValueError("No se encontraron embeddings válidos")
        
        # Concatenar todos los embeddings
        embeddings_matrix = np.vstack(all_embeddings)
        
        # Verificar dimensiones
        if embeddings_matrix.shape[1] != self.dimension:
            raise ValueError(
                f"Dimensión de embeddings ({embeddings_matrix.shape[1]}) "
                f"no coincide con la esperada ({self.dimension})"
            )
        
        self.logger.info(
            f"Cargados {len(all_embeddings)} archivos, "
            f"{embeddings_matrix.shape[0]} chunks totales con texto incluido"
        )
        
        return embeddings_matrix, all_metadata
    
    @PerformanceMonitor.function_timer("build_index")
    def build_index(self) -> None:
        """
        Construye el índice FAISS con los embeddings disponibles.
        """
        try:
            # Cargar embeddings y metadatos
            embeddings, metadata = self.load_embeddings()
            
            # Crear índice
            index = self._create_index()
            
            # Entrenar si es necesario (IVF)
            if isinstance(index, faiss.IndexIVFFlat):
                index.train(embeddings)
            
            # Agregar vectores al índice
            index.add(embeddings)
            
            # Actualizar mapeo de IDs
            for i, meta in enumerate(metadata):
                self.id_to_metadata[i] = meta
            
            self.current_id = len(metadata)
            
            # Guardar índice
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            index_file = self.index_dir / f"faiss_index_{timestamp}.bin"
            faiss.write_index(index, str(index_file))
            
            # Guardar mapeo de IDs
            mapping_file = self.index_dir / f"id_mapping_{timestamp}.json"
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.id_to_metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.info(
                f"Índice FAISS construido exitosamente: {index_file}, "
                f"Mapping: {mapping_file}, Vectores: {self.current_id}, Tipo: {self.index_type}"
            )
            
        except Exception as e:
            self.logger.error(f"Error construyendo índice FAISS: {str(e)}")
            raise
    
    def load_index(
        self,
        index_file: Optional[str] = None,
        mapping_file: Optional[str] = None
    ) -> Tuple[faiss.Index, Dict[int, Dict]]:
        """
        Carga un índice FAISS existente y su mapeo de IDs.
        
        Args:
            index_file: Ruta al archivo del índice
            mapping_file: Ruta al archivo de mapeo
            
        Returns:
            Tupla con el índice y el mapeo de IDs
        """
        # Si no se especifican archivos, usar los más recientes
        if not index_file or not mapping_file:
            index_files = list(self.index_dir.glob("faiss_index_*.bin"))
            mapping_files = list(self.index_dir.glob("id_mapping_*.json"))
            
            if not index_files or not mapping_files:
                raise FileNotFoundError("No se encontraron archivos de índice")
            
            index_file = str(sorted(index_files)[-1])
            mapping_file = str(sorted(mapping_files)[-1])
        
        # Cargar índice
        index = faiss.read_index(index_file)
        
        # Cargar mapeo
        with open(mapping_file, 'r', encoding='utf-8') as f:
            id_mapping = json.load(f)
        
        self.logger.info(
            "Índice FAISS cargado exitosamente",
            index_file=index_file,
            mapping_file=mapping_file,
            num_vectors=len(id_mapping)
        )
        
        return index, id_mapping

def main():
    """Función principal para construir el índice"""
    try:
        # Inicializar constructor
        builder = FAISSIndexBuilder()
        
        # Construir índice
        builder.build_index()
        
    except Exception as e:
        logging.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 