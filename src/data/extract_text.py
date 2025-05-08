import os
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import PyPDF2
import pdfplumber
import spacy
from tqdm import tqdm
import fitz  # PyMuPDF

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

    def clean_text(self, text: str) -> str:
        """
        Limpia el texto extraído del PDF preservando los retornos de carro.
        
        Args:
            text: Texto a limpiar
            
        Returns:
            Texto limpio
        """
        # Normalizar retornos de carro
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Dividir el texto en líneas para procesarlas individualmente
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Reemplazar caracteres especiales manteniendo puntuación básica
            line = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ.,;:¿?¡!()\-]', ' ', line)
            
            # Corregir palabras separadas incorrectamente
            line = re.sub(r'([a-záéíóúñ])\s+([A-ZÁÉÍÓÚÑ])', r'\1\2', line)
            
            # Corregir palabras unidas incorrectamente
            line = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', line)
            
            # Corregir números y símbolos
            line = re.sub(r'(\d)([A-Za-záéíóúÁÉÍÓÚñÑ])', r'\1 \2', line)
            line = re.sub(r'([A-Za-záéíóúÁÉÍÓÚñÑ])(\d)', r'\1 \2', line)
            
            # Eliminar espacios múltiples
            line = re.sub(r'[ \t]+', ' ', line)
            
            # Corregir espacios alrededor de puntuación
            line = re.sub(r'\s+([.,;:¿?¡!])', r'\1', line)
            line = re.sub(r'([.,;:¿?¡!])\s+', r'\1 ', line)
            
            # Corregir espacios en paréntesis
            line = re.sub(r'\(\s+', '(', line)
            line = re.sub(r'\s+\)', ')', line)
            
            # Corregir espacios en guiones
            line = re.sub(r'\s+-\s+', '-', line)
            
            # Corregir espacios en números y símbolos de moneda
            line = re.sub(r'(\d+)\s*([€$])\s*(\d*)', r'\1\2\3', line)
            
            # Agregar la línea limpia
            cleaned_lines.append(line.strip())
        
        # Unir las líneas con retornos de carro
        text = '\n'.join(cleaned_lines)
        
        # Eliminar líneas vacías múltiples
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()

    def extract_text_from_pdf(self, pdf_path: Path) -> Tuple[str, Dict]:
        """
        Extrae el texto de un archivo PDF usando PyMuPDF (fitz) y lógica de bloques para separar columnas y eliminar pies de página.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Tuple[str, Dict]: Texto extraído y metadata del proceso
        """
        metadata = {
            'filename': pdf_path.name,
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'pymupdf_blocks',
            'num_pages': 0,
            'language': None,
            'success': False,
            'error': None
        }
        text = ""
        try:
            doc = fitz.open(str(pdf_path))
            metadata['num_pages'] = doc.page_count
            for page in doc:
                blocks = page.get_text("blocks")
                page_height = page.rect.height
                page_width = page.rect.width
                margin_bottom = 70
                clean_blocks = []
                for block in blocks:
                    if block[1] < page_height - margin_bottom:
                        block_text = block[4].strip()
                        if block_text and not block_text.lower().startswith("<image"):
                            clean_blocks.append(block)
                # Separar columnas
                left_col = [b for b in clean_blocks if b[0] < page_width / 2]
                right_col = [b for b in clean_blocks if b[0] >= page_width / 2]
                left_col_sorted = sorted(left_col, key=lambda b: (b[1], b[0]))
                right_col_sorted = sorted(right_col, key=lambda b: (b[1], b[0]))
                sorted_blocks = left_col_sorted + right_col_sorted
                page_text = "\n".join(block[4].strip() for block in sorted_blocks if block[4].strip())
                text += page_text + "\n"
            # Limpiar el texto extraído
            text = self.clean_text(text)
            # Detectar idioma
            if text.strip():
                doc_spacy = self.nlp(text[:1000])
                metadata['language'] = doc_spacy.lang_
                metadata['success'] = True
            else:
                metadata['error'] = "No se pudo extraer texto del PDF"
        except Exception as e:
            metadata['error'] = str(e)
            logger.error(f"Error procesando {pdf_path}: {str(e)}")
            return "", metadata
        return text, metadata

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