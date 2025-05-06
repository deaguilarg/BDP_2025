"""
Script para ejecutar la aplicación principal de Streamlit.
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
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Función principal"""
    
    # Verificar que el índice existe
    index_dir = Path("models/faiss_index")
    if not index_dir.exists() or not list(index_dir.glob("faiss_index_*.bin")):
        logger.error("No se encontró el índice FAISS. Por favor, ejecute primero run_rag_system.py")
        return
    
    # Ejecutar aplicación Streamlit
    logger.info("Iniciando aplicación Streamlit...")
    try:
        subprocess.run(
            "python -m streamlit run app/streamlit_app.py",
            shell=True,
            check=True
        )
    except KeyboardInterrupt:
        logger.info("Aplicación detenida por el usuario")
    except Exception as e:
        logger.error(f"Error ejecutando Streamlit: {str(e)}")

if __name__ == "__main__":
    main() 