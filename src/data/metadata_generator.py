import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import spacy
from tqdm import tqdm

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/metadata_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MetadataGenerator:
    # Campos requeridos según el esquema
    REQUIRED_FIELDS = [
        'filename',
        'title',
        'insurer',
        'insurance_type',
        'file_path',
        'language'
    ]
    
    # Campos recomendados según el esquema
    RECOMMENDED_FIELDS = [
        'coverage_type',
        'document_date',
        'document_version',
        'num_pages',
        'keywords'
    ]
    
    def __init__(self, processed_dir: str = 'data/processed', metadata_dir: str = 'data/metadata'):
        """
        Inicializa el generador de metadatos.
        
        Args:
            processed_dir: Directorio con los textos procesados
            metadata_dir: Directorio donde se guardarán los metadatos
        """
        self.processed_dir = Path(processed_dir)
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar modelo de spaCy
        try:
            self.nlp = spacy.load('es_core_news_sm')
        except OSError:
            logger.error("No se pudo cargar el modelo de spaCy")
            raise
        
        # Patrones para identificar información
        self.patterns = {
            'insurer': r'(?i)(mapfre|axa|allianz|generali|zurich|liberty|reale|helvetia|pelayo|mutua\s+madrileña)',
            'insurance_type': r'(?i)(vida|hogar|auto(?:móvil)?|salud|decesos|responsabilidad\s+civil|multirriesgo)',
            'coverage_type': r'(?i)(básico|premium|todo\s+riesgo|completo|estándar)',
            'document_date': r'(?i)(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?\d{2,4})',
            'document_version': r'(?i)(?:v|versión|version)\s*(\d+(?:\.\d+)*|\d{4}/\d{2})'
        }
        
        # Palabras comunes que no deben ser consideradas como entidades
        self.stop_entities = {
            'ORG': {'además', 'subsidio', 'seguro', 'póliza', 'contrato', 'documento', 'cláusula', 
                   'condición', 'artículo', 'sección', 'apartado', 'inciso', 'literal', 'documento',
                   'comunicar', 'anticipación', 'convenio', 'complementario', 'inter-bureaux',
                   'espacio', 'económico', 'europeo', 'entidad', 'sanitarios', 'daños', 'intereses',
                   'carta', 'verde', 'civil', 'obligatoria', 'compañía', 'complementaria',
                   'condiciones', 'particulares', 'cristales', 'fondos', 'pensiones', 'física',
                   'permanente', 'indemnización', 'lunas', 'nacionales', 'naturaleza', 'reaseguros',
                   'reclamación', 'tomador', 'circulación', 'conducción', 'asegurado', 'incendio',
                   'responsabilidad', 'red', 'asesoramiento', 'convenio complementario'},
            'PER': {'asegurado', 'beneficiario', 'tomador', 'perjudicado', 'tercero', 'usuario',
                   'convenio', 'complementario', 'sanitarios', 'intereses', 'convenio complementario'},
            'LOC': {'domicilio', 'residencia', 'dirección', 'localidad', 'municipio', 'provincia',
                   'ciudad', 'vaticano', 'españa', 'gibraltar', 'mónaco', 'san marino',
                   'aseguradora', 'carta', 'verde', 'civil', 'obligatoria', 'complementaria',
                   'comunicar', 'condiciones', 'particulares', 'cristales', 'lunas', 'nacionales',
                   'naturaleza', 'reaseguros', 'tomador', 'incendio'}
        }
        
        # Patrones para validar entidades
        self.entity_patterns = {
            'ORG': r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Palabras con inicial mayúscula
            'PER': r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Nombres propios
            'LOC': r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$'   # Nombres de lugares
        }
        
        # Lista de organizaciones conocidas
        self.known_organizations = {
            'Mapfre', 'AXA', 'Allianz', 'Generali', 'Zurich', 'Liberty', 'Reale', 
            'Helvetia', 'Pelayo', 'Mutua Madrileña'
        }
        
        # Lista de ubicaciones conocidas
        self.known_locations = {
            'Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Zaragoza', 'Málaga',
            'Murcia', 'Palma', 'Las Palmas', 'Bilbao', 'Alicante', 'Córdoba',
            'Valladolid', 'Vigo', 'Gijón', 'Hospitalet', 'Vitoria', 'Elche',
            'Granada', 'Terrassa', 'A Coruña', 'Cartagena', 'Sabadell', 'Santa Cruz',
            'Oviedo', 'Móstoles', 'Pamplona', 'Santander', 'Castellón', 'Almería'
        }

    def is_valid_entity(self, entity: str, entity_type: str) -> bool:
        """
        Verifica si una entidad es válida según criterios específicos.
        
        Args:
            entity: Texto de la entidad
            entity_type: Tipo de entidad (ORG, PER, LOC)
            
        Returns:
            bool: True si la entidad es válida
        """
        # Convertir a minúsculas para comparación
        entity_lower = entity.lower()
        
        # Verificar si está en la lista de palabras a ignorar
        if entity_lower in self.stop_entities.get(entity_type, set()):
            return False
            
        # Verificar si es una combinación de palabras a ignorar
        words = entity_lower.split()
        if len(words) > 1:
            if all(word in self.stop_entities.get(entity_type, set()) for word in words):
                return False
        
        # Verificar longitud mínima
        if len(entity) < 3:
            return False
        
        # Verificar si es solo un número
        if entity.isdigit():
            return False
        
        # Verificar si es una palabra común en mayúsculas
        if entity.isupper() and len(entity) < 5:
            return False
        
        # Verificar si es una palabra con solo la primera letra en mayúscula
        if entity[0].isupper() and entity[1:].islower() and len(entity) < 5:
            return False
        
        # Verificar si contiene caracteres especiales
        if re.search(r'[^\w\s]', entity):
            return False
        
        # Verificar si coincide con el patrón esperado para el tipo de entidad
        if entity_type in self.entity_patterns:
            if not re.match(self.entity_patterns[entity_type], entity):
                return False
        
        # Verificaciones específicas por tipo de entidad
        if entity_type == 'ORG':
            # Para organizaciones, solo aceptar si es una organización conocida
            return entity in self.known_organizations
        
        elif entity_type == 'LOC':
            # Para ubicaciones, solo aceptar si es una ubicación conocida
            return entity in self.known_locations
        
        elif entity_type == 'PER':
            # Para personas, verificar que no sea una palabra común o combinación de ellas
            common_words = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'de', 'del',
                          'convenio', 'complementario', 'sanitarios', 'intereses'}
            words = entity_lower.split()
            return not any(word in common_words for word in words)
        
        return True

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extrae entidades nombradas del texto usando spaCy.
        
        Args:
            text: Texto del documento
            
        Returns:
            Dict con las entidades encontradas por tipo
        """
        doc = self.nlp(text)
        entities = {
            'ORG': [],
            'PER': [],
            'LOC': [],
            'MISC': []
        }
        
        for ent in doc.ents:
            if ent.label_ in entities and self.is_valid_entity(ent.text, ent.label_):
                # Limpiar la entidad
                cleaned_entity = ent.text.strip()
                if cleaned_entity and cleaned_entity not in entities[ent.label_]:
                    entities[ent.label_].append(cleaned_entity)
        
        return {k: sorted(list(set(v))) for k, v in entities.items()}

    def extract_title(self, text: str) -> str:
        """
        Extrae el título del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Título extraído
        """
        # Buscar patrones comunes de títulos en documentos de seguros
        title_patterns = [
            r'(?i)condiciones\s+(?:generales|particulares)\s+(?:del\s+)?seguro\s+(?:de\s+)?[^\n]+',
            r'(?i)póliza\s+(?:de\s+)?seguro\s+(?:de\s+)?[^\n]+',
            r'(?i)contrato\s+(?:de\s+)?seguro\s+(?:de\s+)?[^\n]+'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text[:1000])  # Buscar en los primeros 1000 caracteres
            if match:
                return match.group().strip()
        
        # Si no se encuentra un título específico, usar el nombre del archivo
        return "Documento de Seguro"

    def extract_insurer(self, text: str) -> str:
        """
        Extrae la aseguradora del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Nombre de la aseguradora
        """
        matches = self.find_pattern_matches(text, self.patterns['insurer'])
        return matches[0] if matches else "Desconocida"

    def extract_insurance_type(self, text: str) -> str:
        """
        Extrae el tipo de seguro del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Tipo de seguro
        """
        matches = self.find_pattern_matches(text, self.patterns['insurance_type'])
        return matches[0] if matches else "No especificado"

    def extract_coverage_type(self, text: str) -> str:
        """
        Extrae el tipo de cobertura del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Tipo de cobertura
        """
        matches = self.find_pattern_matches(text, self.patterns['coverage_type'])
        return matches[0] if matches else "No especificado"

    def extract_document_date(self, text: str) -> str:
        """
        Extrae la fecha del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Fecha en formato YYYY-MM-DD
        """
        matches = self.find_pattern_matches(text, self.patterns['document_date'])
        if matches:
            try:
                # Intentar convertir la fecha a formato estándar
                date_str = matches[0]
                if '/' in date_str or '-' in date_str:
                    day, month, year = re.split(r'[/-]', date_str)
                    if len(year) == 2:
                        year = '20' + year
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    # Manejar fechas en formato texto
                    months = {
                        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                    }
                    for month_name, month_num in months.items():
                        if month_name in date_str.lower():
                            day = re.search(r'\d{1,2}', date_str).group()
                            year = re.search(r'\d{4}', date_str).group()
                            return f"{year}-{month_num}-{day.zfill(2)}"
            except Exception as e:
                logger.warning(f"Error procesando fecha: {str(e)}")
        return None

    def extract_document_version(self, text: str) -> str:
        """
        Extrae la versión del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Versión del documento
        """
        matches = self.find_pattern_matches(text, self.patterns['document_version'])
        return matches[0] if matches else "No especificada"

    def extract_keywords(self, text: str, min_freq: int = 2) -> List[str]:
        """
        Extrae palabras clave del texto.
        
        Args:
            text: Texto del documento
            min_freq: Frecuencia mínima para considerar una palabra como clave
            
        Returns:
            Lista de palabras clave
        """
        doc = self.nlp(text.lower())
        word_freq = {}
        
        for token in doc:
            if not token.is_stop and not token.is_punct and token.is_alpha:
                word_freq[token.lemma_] = word_freq.get(token.lemma_, 0) + 1
        
        keywords = [word for word, freq in word_freq.items() if freq >= min_freq]
        return sorted(keywords)

    def find_pattern_matches(self, text: str, pattern: str) -> List[str]:
        """
        Encuentra coincidencias de un patrón en el texto.
        
        Args:
            text: Texto donde buscar
            pattern: Patrón regex a buscar
            
        Returns:
            Lista de coincidencias únicas
        """
        matches = re.finditer(pattern, text)
        return sorted(list(set(match.group() for match in matches)))

    def generate_metadata(self, text_path: Path) -> Dict:
        """
        Genera metadatos para un documento según el esquema especificado.
        
        Args:
            text_path: Ruta al archivo de texto
            
        Returns:
            Dict con los metadatos generados
        """
        try:
            text = text_path.read_text(encoding='utf-8')
            
            # Extraer información del nombre del archivo
            filename = text_path.stem
            parts = filename.split('-')
            
            # Determinar tipo de seguro y cobertura basado en el nombre del archivo
            insurance_type = None
            coverage_type = None
            
            if 'ipid' in filename:
                insurance_type = 'IPID'
                if 'basico' in filename:
                    coverage_type = 'Básico'
                elif 'ampliado' in filename:
                    coverage_type = 'Ampliado'
                elif 'optimo' in filename:
                    coverage_type = 'Óptimo'
                elif 'extra' in filename:
                    coverage_type = 'Extra'
            elif 'auto-plus' in filename:
                insurance_type = 'Auto'
                if 'basico' in filename:
                    coverage_type = 'Básico'
                elif 'terceros' in filename:
                    coverage_type = 'Terceros'
                elif 'robo-incendio' in filename:
                    coverage_type = 'Robo e Incendio'
            elif 'camion' in filename or 'furgoneta' in filename or 'remolque' in filename:
                insurance_type = 'Transporte'
                if 'basico' in filename:
                    coverage_type = 'Básico'
                elif 'todo-riesgo' in filename:
                    coverage_type = 'Todo Riesgo'
                elif 'perdida-total' in filename:
                    coverage_type = 'Pérdida Total'
            
            # Generar metadatos requeridos
            metadata = {
                'filename': filename + '.pdf',
                'title': self.extract_title(text),
                'insurer': 'IPID',  # Por defecto IPID
                'insurance_type': insurance_type or 'No especificado',
                'file_path': str(text_path),
                'language': 'es'  # Por defecto en español
            }
            
            # Generar metadatos recomendados
            metadata.update({
                'coverage_type': coverage_type or 'No especificado',
                'document_date': self.extract_document_date(text),
                'document_version': self.extract_document_version(text),
                'num_pages': None,  # Requeriría análisis del PDF original
                'keywords': ';'.join(self.extract_keywords(text))
            })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error generando metadatos para {text_path}: {str(e)}")
            return None

    def process_all_documents(self) -> pd.DataFrame:
        """
        Procesa todos los documentos y genera sus metadatos.
        
        Returns:
            DataFrame con los metadatos de todos los documentos
        """
        text_files = list(self.processed_dir.glob('*.txt'))
        all_metadata = []
        
        if not text_files:
            logger.warning(f"No se encontraron archivos de texto en {self.processed_dir}")
            return pd.DataFrame()
        
        for text_path in tqdm(text_files, desc="Generando metadatos"):
            metadata = self.generate_metadata(text_path)
            if metadata:
                all_metadata.append(metadata)
        
        # Crear DataFrame
        df_metadata = pd.DataFrame(all_metadata)
        
        # Guardar metadatos en CSV y JSON
        if not df_metadata.empty:
            # CSV para análisis
            df_metadata.to_csv(self.metadata_dir / 'document_metadata.csv', index=False)
            
            # JSON para mantener las estructuras de lista
            metadata_json = df_metadata.to_dict(orient='records')
            with open(self.metadata_dir / 'document_metadata.json', 'w', encoding='utf-8') as f:
                json.dump(metadata_json, f, ensure_ascii=False, indent=2)
            
            # Resumen del proceso
            logger.info(f"Proceso completado: {len(df_metadata)} documentos procesados")
            
        return df_metadata

def main():
    """Función principal para ejecutar la generación de metadatos"""
    try:
        generator = MetadataGenerator()
        metadata_df = generator.process_all_documents()
        
        if not metadata_df.empty:
            # Mostrar resumen
            print("\nResumen de la generación de metadatos:")
            print(f"Total de documentos procesados: {len(metadata_df)}")
            print("\nEstadísticas de campos encontrados:")
            print(f"Documentos con aseguradoras identificadas: {metadata_df['insurer'].notna().sum()}")
            print(f"Documentos con tipos de seguro identificados: {metadata_df['insurance_type'].notna().sum()}")
            print(f"Documentos con tipos de cobertura identificados: {metadata_df['coverage_type'].notna().sum()}")
            print(f"Documentos con fechas encontradas: {metadata_df['document_date'].notna().sum()}")
            
            # Mostrar ejemplos de palabras clave más comunes
            all_keywords = [kw for keywords in metadata_df['keywords'] for kw in keywords.split(';')]
            if all_keywords:
                keyword_freq = pd.Series(all_keywords).value_counts()
                print("\nPalabras clave más frecuentes:")
                print(keyword_freq.head())
    
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 