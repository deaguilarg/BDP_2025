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
import re
import unicodedata

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
        'producto',
        'insurance_type',
        'file_path',
        'coverage_type',
        'num_pages',
        'keywords'
    ]
    
    # Campos recomendados según el esquema
    RECOMMENDED_METADATA_FIELDS = [
        'title',
        'insurer',
        'document_date',
        'document_version',
        'language'
    ]
    
    # Secciones específicas para chunking
    SECTIONS = {
        'consiste': r'(?i)en\s+qué\s+consiste\s+este\s+tipo\s+de\s+seguro',
        'asegurado': r'(?i)qué\s+se\s+asegura',
        'no_asegurado': r'(?i)qué\s+no\s+está\s+asegurado',
        'sumas': r'(?i)sumas\s+aseguradas',
        'restricciones': r'(?i)existen\s+restricciones\s+en\s+lo\s+que\s+respecta\s+a\s+la\s+cobertura',
        'cobertura': r'(?i)dónde\s+estoy\s+cubierto',
        'obligaciones': r'(?i)cuáles\s+son\s+mis\s+obligaciones',
        'pagos': r'(?i)cuándo\s+y\s+cómo\s+tengo\s+que\s+efectuar\s+los\s+pagos',
        'vigencia': r'(?i)cuándo\s+comienza\s+y\s+finaliza\s+la\s+cobertura',
        'rescindir': r'(?i)cómo\s+puedo\s+rescindir\s+el\s+contrato'
    }
    
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
        
        if missing_fields:
            self.logger.warning(
                f"Campos requeridos faltantes para {filename}",
                missing_fields=missing_fields
            )
            
            # Manejar campos faltantes
            for field in missing_fields:
                if field == 'producto':
                    # Asignar un valor por defecto basado en insurance_type si está disponible
                    if metadata.get('insurance_type'):
                        metadata['producto'] = f"Seguro de {metadata['insurance_type']}"
                    else:
                        metadata['producto'] = "Seguro General"
                    missing_fields.remove('producto')
            
            # Si aún hay campos faltantes después del manejo especial, lanzar error
            if missing_fields:
                raise ValueError(f"Campos requeridos faltantes: {', '.join(missing_fields)}")
        
        # Normalizar campos
        normalized = metadata.copy()
        
        # Normalizar producto
        if 'producto' in normalized:
            producto = normalized['producto'].strip()
            if not producto.lower().startswith('seguro'):
                normalized['producto'] = f"Seguro de {producto}"
        
        # Normalizar tipo de seguro
        if 'insurance_type' in normalized:
            insurance_type = normalized['insurance_type'].lower()
            if 'auto' in insurance_type:
                normalized['insurance_type'] = 'Automóvil'
            elif 'responsabilidad' in insurance_type:
                normalized['insurance_type'] = 'Responsabilidad Civil'
            else:
                normalized['insurance_type'] = insurance_type.capitalize()
        
        # Normalizar tipo de cobertura
        if 'coverage_type' in normalized:
            coverage_type = normalized['coverage_type'].lower()
            if 'todo riesgo' in coverage_type:
                normalized['coverage_type'] = 'Todo Riesgo'
            elif 'básico con daños' in coverage_type:
                normalized['coverage_type'] = 'Básico con daños'
            elif 'pérdida total' in coverage_type:
                normalized['coverage_type'] = 'Pérdida total'
            elif 'todo riesgo con franquicia' in coverage_type:
                normalized['coverage_type'] = 'Todo riesgo con franquicia'
            else:
                normalized['coverage_type'] = coverage_type.capitalize()
        
        # Normalizar keywords
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
    
    def normalize_filename(self, filename: str) -> str:
        """Normaliza el nombre del archivo eliminando acentos y caracteres especiales."""
        # Normalizar caracteres Unicode
        normalized = unicodedata.normalize('NFKD', filename)
        # Eliminar caracteres no ASCII
        normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')
        return normalized

    def load_documents(self) -> List[Dict[str, Any]]:
        """Carga los documentos y sus metadatos."""
        # Cargar metadatos
        metadata_path = Path("data/metadata/metadata.csv")
        if not metadata_path.exists():
            raise FileNotFoundError("No se encontró el archivo de metadatos")
        
        # Cargar CSV con codificación UTF-8
        metadata_df = pd.read_csv(metadata_path, encoding='utf-8')
        
        # Convertir a diccionario usando filename como índice
        metadata_dict = {}
        for _, row in metadata_df.iterrows():
            filename = row['filename']
            # Eliminar la extensión .pdf del nombre del archivo
            base_filename = Path(filename).stem
            metadata = row.to_dict()
            metadata_dict[filename] = metadata
            
        self.logger.info(
            "Metadatos cargados exitosamente",
            total_documents=len(metadata_dict),
            columns=list(metadata_df.columns)
        )
        
        # Procesar cada archivo de texto
        documents = []
        data_path = Path("data/processed")
        
        for txt_file in data_path.glob("*.txt"):
            # Obtener el nombre base sin extensión
            base_name = txt_file.stem + '.pdf'
            
            # Normalizar el nombre del archivo
            normalized_base_name = self.normalize_filename(base_name)
            
            # Ignorar el archivo del glosario
            if base_name == "GLOSARIO DE TÉRMINOS DE SEGUROS.pdf":
                self.logger.info(f"Ignorando archivo de glosario: {txt_file.name}")
                continue
                
            # Buscar metadatos normalizando el nombre del archivo
            metadata = None
            for filename, meta in metadata_dict.items():
                if self.normalize_filename(filename) == normalized_base_name:
                    metadata = meta.copy()
                    # Usar solo el nombre base sin extensión
                    metadata['filename'] = Path(metadata['filename']).stem
                    break
            
            if not metadata:
                self.logger.warning(
                    f"No se encontraron metadatos para {base_name}"
                )
                continue
                
            # Leer contenido del archivo
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.error(
                    f"Error leyendo archivo {txt_file}",
                    error=str(e)
                )
                continue
                
            # Crear documento con contenido y metadatos
            document = {
                'content': content,
                'metadata': metadata
            }
            documents.append(document)
            
        if not documents:
            raise ValueError("No se pudieron cargar documentos válidos")
            
        return documents
    
    def chunk_text(self, text: str) -> List[Dict[str, str]]:
        """
        Divide el texto en chunks basados en secciones específicas.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de diccionarios con chunks y sus metadatos
        """
        chunks = []
        current_position = 0
        
        # Encontrar todas las secciones en el texto
        section_matches = []
        for section_name, pattern in self.SECTIONS.items():
            for match in re.finditer(pattern, text):
                section_matches.append((match.start(), section_name, match.group()))
        
        # Ordenar secciones por posición
        section_matches.sort(key=lambda x: x[0])
        
        # Crear chunks para cada sección
        for i, (start, section_name, section_title) in enumerate(section_matches):
            # Determinar el final del chunk
            if i < len(section_matches) - 1:
                end = section_matches[i + 1][0]
            else:
                end = len(text)
            
            # Extraer el contenido de la sección
            content = text[start:end].strip()
            
            # Crear chunk con metadatos
            chunk = {
                'text': content,
                'section': section_name,
                'section_title': section_title,
                'start_position': start,
                'end_position': end
            }
            
            chunks.append(chunk)
            
        # Si no se encontraron secciones, crear un chunk con todo el texto
        if not chunks:
            chunks.append({
                'text': text,
                'section': 'general',
                'section_title': 'Contenido General',
                'start_position': 0,
                'end_position': len(text)
            })
            
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
                    # Dividir texto en chunks por secciones
                    chunks = self.chunk_text(doc['content'])
                    
                    # Generar embeddings para cada chunk
                    chunk_texts = [chunk['text'] for chunk in chunks]
                    embeddings = self.generate_embeddings(chunk_texts)
                    
                    # Guardar embeddings
                    output_file = Path("data/embeddings") / f"{doc['metadata']['filename']}.npy"
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Guardar embeddings como array de numpy
                    np.save(output_file, embeddings)
                    
                    # Guardar metadatos individuales con información de chunks
                    metadata_file = Path("data/embeddings") / f"{doc['metadata']['filename']}.json"
                    
                    # Crear diccionario de metadatos sin el campo chunks original
                    clean_metadata = doc['metadata'].copy()
                    if 'chunks' in clean_metadata:
                        del clean_metadata['chunks']
                    
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "filename": doc['metadata']['filename'],
                            "num_chunks": len(chunks),
                            "embedding_dim": embeddings.shape[1],
                            "metadata": clean_metadata,
                            "chunks": chunks
                        }, f, ensure_ascii=False, indent=2)
                    
                    # Agregar documento a la lista de procesados
                    processed_documents.append({
                        "filename": doc['metadata']['filename'],
                        "metadata": clean_metadata,
                        "num_chunks": len(chunks),
                        "embedding_dim": embeddings.shape[1],
                        "sections": [chunk['section'] for chunk in chunks]
                    })
            
        except Exception as e:
            self.logger.error(
                        "Error procesando documento",
                        filename=doc['metadata'].get('filename', 'desconocido'),
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
    """Función principal para ejecutar la generación de embeddings"""
    try:
        # Inicializar el embedder
        embedder = DocumentEmbedder()
        
        # Procesar documentos
        embedder.process_documents()
        
        print("\nProceso de generación de embeddings completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 