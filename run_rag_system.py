"""
Script principal para ejecutar el sistema RAG completo.
"""

import os
import sys
from pathlib import Path
import logging
import subprocess

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rag_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_command(command: str, description: str) -> bool:
    """
    Ejecuta un comando y maneja errores.
    
    Args:
        command: Comando a ejecutar
        description: Descripción del paso
        
    Returns:
        True si el comando se ejecutó exitosamente
    """
    try:
        logger.info(f"Ejecutando: {description}")
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Completado: {description}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en {description}: {str(e)}")
        logger.error(f"Salida de error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado en {description}: {str(e)}")
        return False

def main():
    """Función principal"""
    
    # Crear directorios necesarios
    Path("logs").mkdir(exist_ok=True)
    Path("models/faiss_index").mkdir(parents=True, exist_ok=True)
    
    # 1. Generar embeddings
    if not run_command(
        "python src/embeddings/embed_documents.py",
        "Generación de embeddings"
    ):
        logger.error("Error en la generación de embeddings. Abortando.")
        return
    
    # 2. Construir índice FAISS
    if not run_command(
        "python src/embeddings/index_builder.py",
        "Construcción del índice FAISS"
    ):
        logger.error("Error en la construcción del índice. Abortando.")
        return
    
    # 3. Ejecutar aplicación Streamlit
    logger.info("Iniciando aplicación Streamlit...")
    try:
        # Ejecutar Streamlit en modo debug
        subprocess.run(
            "python -m streamlit run app/debug_interface.py",
            shell=True,
            check=True
        )
    except KeyboardInterrupt:
        logger.info("Aplicación detenida por el usuario")
    except Exception as e:
        logger.error(f"Error ejecutando Streamlit: {str(e)}")

if __name__ == "__main__":
    main() 