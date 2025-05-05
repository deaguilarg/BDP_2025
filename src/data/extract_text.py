import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import PyPDF2
import pdfplumber
import spacy
from tqdm import tqdm

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pdf_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFExtractor:
    def __init__(self, raw_dir: str = 'data/raw', processed_dir: str = 'data/processed'):
        """
        Inicializa el extractor de PDFs.
        
        Args:
            raw_dir: Directorio que contiene los PDFs originales
            processed_dir: Directorio donde se guardarán los textos extraídos
        """
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar el modelo de spaCy para detección de idioma
        try:
            self.nlp = spacy.load('es_core_news_sm')
        except OSError:
            logger.error("No se pudo cargar el modelo de spaCy. Asegúrate de haberlo instalado.")
            raise

    def extract_text_from_pdf(self, pdf_path: Path) -> Tuple[str, Dict]:
        """
        Extrae el texto de un archivo PDF usando múltiples métodos.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Tuple[str, Dict]: Texto extraído y metadata del proceso
        """
        metadata = {
            'filename': pdf_path.name,
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': None,
            'num_pages': 0,
            'language': None,
            'success': False,
            'error': None
        }
        
        text = ""
        
        try:
            # Primer intento con PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata['num_pages'] = len(reader.pages)
                
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
            # Si el texto está vacío o tiene muy poco contenido, intentar con pdfplumber
            if len(text.strip()) < 100:
                with pdfplumber.open(pdf_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                    metadata['extraction_method'] = 'pdfplumber'
            else:
                metadata['extraction_method'] = 'PyPDF2'
            
            # Detectar idioma
            if text.strip():
                doc = self.nlp(text[:1000])  # Usar solo los primeros 1000 caracteres
                metadata['language'] = doc.lang_
                metadata['success'] = True
            else:
                metadata['error'] = "No se pudo extraer texto del PDF"
                
        except Exception as e:
            metadata['error'] = str(e)
            logger.error(f"Error procesando {pdf_path}: {str(e)}")
            return "", metadata
            
        return text.strip(), metadata

    def process_all_pdfs(self) -> pd.DataFrame:
        """
        Procesa todos los PDFs en el directorio raw y guarda los textos extraídos.
        
        Returns:
            pd.DataFrame: DataFrame con la metadata de todos los documentos procesados
        """
        all_metadata = []
        pdf_files = list(self.raw_dir.glob('*.pdf'))
        
        if not pdf_files:
            logger.warning(f"No se encontraron archivos PDF en {self.raw_dir}")
            return pd.DataFrame()
        
        for pdf_path in tqdm(pdf_files, desc="Procesando PDFs"):
            text, metadata = self.extract_text_from_pdf(pdf_path)
            
            if text:
                # Guardar el texto extraído
                output_path = self.processed_dir / f"{pdf_path.stem}.txt"
                output_path.write_text(text, encoding='utf-8')
                
                # Agregar rutas a la metadata
                metadata['input_path'] = str(pdf_path)
                metadata['output_path'] = str(output_path)
            
            all_metadata.append(metadata)
        
        # Crear DataFrame con la metadata
        df_metadata = pd.DataFrame(all_metadata)
        
        # Guardar metadata en CSV
        metadata_dir = Path('data/metadata')
        metadata_dir.mkdir(parents=True, exist_ok=True)
        df_metadata.to_csv(metadata_dir / 'pdf_extraction_metadata.csv', index=False)
        
        # Resumen del proceso
        successful = df_metadata['success'].sum()
        total = len(df_metadata)
        logger.info(f"Proceso completado: {successful}/{total} documentos procesados exitosamente")
        
        return df_metadata

def main():
    """Función principal para ejecutar la extracción de texto"""
    try:
        extractor = PDFExtractor()
        metadata_df = extractor.process_all_pdfs()
        
        if not metadata_df.empty:
            # Mostrar resumen
            print("\nResumen de la extracción:")
            print(f"Total de documentos procesados: {len(metadata_df)}")
            print(f"Documentos exitosos: {metadata_df['success'].sum()}")
            print(f"Documentos con errores: {len(metadata_df) - metadata_df['success'].sum()}")
            print("\nMétodos de extracción utilizados:")
            print(metadata_df['extraction_method'].value_counts())
            print("\nIdiomas detectados:")
            print(metadata_df['language'].value_counts())
    
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 