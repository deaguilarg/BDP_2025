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
            'aseguradora': r'(?i)(mapfre|axa|allianz|generali|zurich|liberty|reale|helvetia|pelayo|mutua\s+madrileña)',
            'tipo_seguro': r'(?i)(vida|hogar|auto(?:móvil)?|salud|decesos|responsabilidad\s+civil|multirriesgo)',
            'coberturas': r'(?i)(robo|incendio|accidente|fallecimiento|invalidez|asistencia|daños|responsabilidad)',
            'fecha': r'(?i)(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?\d{2,4})'
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
        Genera metadatos para un documento.
        
        Args:
            text_path: Ruta al archivo de texto
            
        Returns:
            Dict con los metadatos generados
        """
        try:
            text = text_path.read_text(encoding='utf-8')
            
            # Metadatos básicos
            metadata = {
                'filename': text_path.stem + '.pdf',
                'file_path': str(text_path),
                'creation_date': datetime.fromtimestamp(text_path.stat().st_ctime).isoformat(),
                'last_modified': datetime.fromtimestamp(text_path.stat().st_mtime).isoformat(),
                'file_size': text_path.stat().st_size,
                'num_chars': len(text),
                'num_words': len(text.split()),
                'metadata_generation_date': datetime.now().isoformat()
            }
            
            # Extraer información usando patrones
            metadata.update({
                'aseguradoras': self.find_pattern_matches(text, self.patterns['aseguradora']),
                'tipos_seguro': self.find_pattern_matches(text, self.patterns['tipo_seguro']),
                'coberturas': self.find_pattern_matches(text, self.patterns['coberturas']),
                'fechas': self.find_pattern_matches(text, self.patterns['fecha'])
            })
            
            # Extraer entidades y palabras clave
            entities = self.extract_entities(text[:10000])  # Limitar a primeros 10000 caracteres
            metadata.update({
                'organizaciones': entities['ORG'],
                'personas': entities['PER'],
                'ubicaciones': entities['LOC'],
                'palabras_clave': self.extract_keywords(text[:10000])
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
            print(f"Documentos con aseguradoras identificadas: {metadata_df['aseguradoras'].apply(bool).sum()}")
            print(f"Documentos con tipos de seguro identificados: {metadata_df['tipos_seguro'].apply(bool).sum()}")
            print(f"Documentos con coberturas identificadas: {metadata_df['coberturas'].apply(bool).sum()}")
            print(f"Documentos con fechas encontradas: {metadata_df['fechas'].apply(bool).sum()}")
            
            # Mostrar ejemplos de palabras clave más comunes
            all_keywords = [kw for keywords in metadata_df['palabras_clave'] for kw in keywords]
            if all_keywords:
                keyword_freq = pd.Series(all_keywords).value_counts()
                print("\nPalabras clave más frecuentes:")
                print(keyword_freq.head())
            
            # Mostrar ejemplos de entidades encontradas
            print("\nEjemplos de entidades encontradas:")
            print("\nOrganizaciones (primeros 5 documentos):")
            for orgs in metadata_df['organizaciones'].head():
                if orgs:
                    print(f"- {', '.join(orgs)}")
            
            print("\nPersonas (primeros 5 documentos):")
            for pers in metadata_df['personas'].head():
                if pers:
                    print(f"- {', '.join(pers)}")
            
            print("\nUbicaciones (primeros 5 documentos):")
            for locs in metadata_df['ubicaciones'].head():
                if locs:
                    print(f"- {', '.join(locs)}")
    
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        raise

if __name__ == "__main__":
    main() 