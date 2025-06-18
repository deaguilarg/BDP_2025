"""
Script para ejecutar la aplicación principal de Streamlit.
Sistema RAG para documentos de seguros Allianz.
"""

import os
import sys
from pathlib import Path
import logging
import subprocess
import time

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_directories():
    """Crea los directorios necesarios si no existen"""
    directories = [
        "logs", "data/raw", "data/processed", "data/embeddings", 
        "data/metadata", "models/faiss_index"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Directorio verificado: {directory}")

def check_api_key():
    """Verifica la configuración de la API key de OpenAI"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY no encontrada en variables de entorno")
            logger.info("💡 Cree un archivo .env en la raíz del proyecto con:")
            logger.info("   OPENAI_API_KEY=su-clave-aqui")
            return False
        
        if not api_key.startswith("sk-"):
            logger.error("❌ La API key no tiene el formato correcto")
            return False
            
        logger.info("✓ API key de OpenAI configurada correctamente")
        return True
        
    except ImportError:
        logger.error("❌ python-dotenv no instalado. Ejecute: pip install python-dotenv")
        return False

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    required_packages = [
        "streamlit", "sentence_transformers", "faiss", 
        "openai", "plotly", "pandas", "numpy"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == "faiss":
                import faiss
            elif package == "sentence_transformers":
                import sentence_transformers
            else:
                __import__(package)
            logger.info(f"✓ {package} instalado")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"❌ {package} no instalado")
    
    if missing_packages:
        logger.error(f"Instale las dependencias faltantes con:")
        logger.error(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_index():
    """Verifica que el índice FAISS existe"""
    index_dir = Path("models/faiss_index")
    
    if not index_dir.exists():
        logger.error("❌ Directorio de índice no encontrado")
        return False
    
    index_files = list(index_dir.glob("faiss_index_*.bin"))
    mapping_files = list(index_dir.glob("id_mapping_*.json"))
    
    if not index_files or not mapping_files:
        logger.error("❌ Índice FAISS no encontrado")
        logger.info("💡 Para generar el índice, ejecute:")
        logger.info("   python src/embeddings/embed_documents.py")
        logger.info("   python src/embeddings/index_builder.py")
        return False
    
    logger.info("✓ Índice FAISS encontrado")
    return True

def start_streamlit():
    """Inicia la aplicación Streamlit"""
    logger.info("🚀 Iniciando aplicación Streamlit...")
    logger.info("📱 La aplicación se abrirá en: http://localhost:8501")
    logger.info("⏹️  Para detener la aplicación, presione Ctrl+C")
    
    try:
        # Buscar un puerto disponible
        for port in [8501, 8502, 8503, 8504]:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py", 
                     "--server.port", str(port), "--server.headless", "true"],
                    check=True
                )
                break
            except subprocess.CalledProcessError:
                if port == 8504:  # Último puerto intentado
                    raise
                logger.info(f"Puerto {port} ocupado, intentando {port + 1}...")
                continue
                
    except KeyboardInterrupt:
        logger.info("\n🛑 Aplicación detenida por el usuario")
    except FileNotFoundError:
        logger.error("❌ Streamlit no está instalado. Ejecute: pip install streamlit")
    except Exception as e:
        logger.error(f"❌ Error ejecutando Streamlit: {str(e)}")

def main():
    """Función principal con verificaciones completas"""
    
    print("=" * 60)
    print("🛡️  SISTEMA RAG - SEGUROS ALLIANZ")
    print("=" * 60)
    
    # Crear directorios necesarios
    logger.info("📁 Verificando estructura de directorios...")
    create_directories()
    
    # Verificar dependencias
    logger.info("📦 Verificando dependencias...")
    if not check_dependencies():
        logger.error("❌ Faltan dependencias. Instale con: pip install -r requirements.txt")
        return 1
    
    # Verificar API key
    logger.info("🔑 Verificando configuración de API...")
    if not check_api_key():
        return 1
    
    # Verificar índice
    logger.info("🔍 Verificando índice FAISS...")
    if not check_index():
        response = input("\n¿Desea generar el índice ahora? (s/n): ").lower()
        if response in ['s', 'si', 'y', 'yes']:
            logger.info("🔄 Generando índice FAISS...")
            try:
                subprocess.run([sys.executable, "src/embeddings/embed_documents.py"], check=True)
                subprocess.run([sys.executable, "src/embeddings/index_builder.py"], check=True)
                logger.info("✓ Índice generado exitosamente")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Error generando índice: {e}")
                return 1
        else:
            logger.info("⏸️  Generación de índice cancelada")
            return 1
    
    # Todo verificado, iniciar aplicación
    logger.info("✅ Todas las verificaciones pasaron")
    time.sleep(1)
    start_streamlit()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 