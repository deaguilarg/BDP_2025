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
        'producto',
        'insurance_type',
        'file_path',
        'coverage_type',
        'num_pages',
        'keywords'
    ]
    
    # Campos recomendados según el esquema
    RECOMMENDED_FIELDS = [
        'title',
        'insurer',
        'document_date',
        'document_version',
        'language'
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
        
        # Patrones para identificar información según el esquema
        self.patterns = {
            'producto': r'(?i)Producto:\s*([^\n]+)',
            'insurance_type': r'(?i)(hogar|vida|salud|auto(?:móvil)?|responsabilidad\s+civil|accidentes)',
            'coverage_type': r'(?i)(básico|premium|todo\s+riesgo|básico\s+con\s+daños|pérdida\s+total|todo\s+riesgo\s+con\s+franquicia)'
        }
        
        # Secciones específicas para chunking según las instrucciones
        self.sections = {
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
        matches = self.find_pattern_matches(text, self.patterns['insurance_type'])
        return matches[0] if matches else "Desconocida"

    def extract_insurance_type(self, text: str) -> str:
        """
        Extrae el tipo de seguro del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Tipo de seguro
        """
        matches = re.findall(self.patterns['insurance_type'], text)
        if matches:
            insurance_type = matches[0].lower()
            if 'auto' in insurance_type:
                return 'Automóvil'
            elif 'responsabilidad' in insurance_type:
                return 'Responsabilidad Civil'
            return insurance_type.capitalize()
        return "No especificado"

    def extract_coverage_type(self, text: str) -> str:
        """
        Extrae el tipo de cobertura del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Tipo de cobertura
        """
        matches = re.findall(self.patterns['coverage_type'], text)
        if matches:
            coverage_type = matches[0].lower()
            if 'todo riesgo' in coverage_type:
                return 'Todo Riesgo'
            elif 'básico con daños' in coverage_type:
                return 'Básico con daños'
            elif 'pérdida total' in coverage_type:
                return 'Pérdida total'
            elif 'todo riesgo con franquicia' in coverage_type:
                return 'Todo riesgo con franquicia'
            return coverage_type.capitalize()
        return "No especificado"

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

    def extract_keywords(self, text: str) -> List[str]:
        """
        Extrae palabras clave del texto.
        
        Args:
            text: Texto del documento
            
        Returns:
            Lista de palabras clave
        """
        doc = self.nlp(text.lower())
        keywords = []
        
        for token in doc:
            if (not token.is_stop and not token.is_punct and token.is_alpha and
                len(token.text) > 3):
                keywords.append(token.lemma_)
        
        return sorted(list(set(keywords)))

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

    def extract_producto(self, text: str) -> str:
        """
        Extrae el producto del documento.
        
        Args:
            text: Texto del documento
            
        Returns:
            Producto extraído
        """
        pattern = self.patterns['producto']
        matches = re.findall(pattern, text)
        if matches:
            return matches[0].strip()
        return "No especificado"

    def extract_chunks(self, text: str) -> Dict[str, str]:
        """
        Extrae las secciones específicas del documento según las instrucciones.
        
        Args:
            text: Texto del documento
            
        Returns:
            Dict con las secciones encontradas
        """
        chunks = {}
        current_section = None
        current_content = []
        
        # Dividir el texto en líneas
        lines = text.split('\n')
        
        for line in lines:
            # Verificar si la línea contiene el inicio de una nueva sección
            for section_name, pattern in self.sections.items():
                if re.search(pattern, line, re.IGNORECASE):
                    # Si ya teníamos una sección, guardarla
                    if current_section:
                        chunks[current_section] = '\n'.join(current_content).strip()
                    # Iniciar nueva sección
                    current_section = section_name
                    current_content = [line]
                    break
            else:
                # Si no es inicio de sección, agregar a la sección actual
                if current_section:
                    current_content.append(line)
        
        # Guardar la última sección
        if current_section:
            chunks[current_section] = '\n'.join(current_content).strip()
        
        return chunks

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
            filename = text_path.stem
            
            # Extraer chunks del documento
            chunks = self.extract_chunks(text)
            
            # Generar metadatos requeridos
            metadata = {
                'filename': filename + '.pdf',
                'producto': self.extract_producto(text),
                'insurance_type': self.extract_insurance_type(text),
                'file_path': str(text_path),
                'coverage_type': self.extract_coverage_type(text),
                'num_pages': None,  # Se obtendrá del PDF original
                'keywords': ';'.join(self.extract_keywords(text))
            }
            
            # Agregar chunks como metadatos adicionales
            metadata['chunks'] = chunks
            
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
            if text_path.stem + '.pdf' == "GLOSARIO DE TÉRMINOS DE SEGUROS.pdf":
                logger.info(f"Ignorando archivo de glosario: {text_path.name}")
                continue
                
            metadata = self.generate_metadata(text_path)
            if metadata:
                all_metadata.append(metadata)
        
        df_metadata = pd.DataFrame(all_metadata)
        
        if not df_metadata.empty:
            # Guardar metadatos en CSV
            df_metadata.to_csv(self.metadata_dir / 'metadata.csv', index=False)
            
            # Guardar chunks en JSON separado
            chunks_data = {row['filename']: row['chunks'] for _, row in df_metadata.iterrows()}
            with open(self.metadata_dir / 'chunks.json', 'w', encoding='utf-8') as f:
                json.dump(chunks_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Proceso completado: {len(df_metadata)} documentos procesados")
            
        return df_metadata

def main():
    """Función principal para ejecutar la generación de metadatos"""
    try:
        generator = MetadataGenerator()
        metadata_df = generator.process_all_documents()
        
        if not metadata_df.empty:
            print("\nResumen de la generación de metadatos:")
            print(f"Total de documentos procesados: {len(metadata_df)}")
            print("\nEstadísticas de campos encontrados:")
            print(f"Documentos con tipos de seguro identificados: {metadata_df['insurance_type'].notna().sum()}")
            print(f"Documentos con tipos de cobertura identificados: {metadata_df['coverage_type'].notna().sum()}")
    
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 