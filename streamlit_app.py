"""
Archivo de entrada principal para Streamlit Cloud deployment.
Este archivo está en la raíz del proyecto para ser detectado automáticamente por Streamlit Cloud.
"""

import sys
import os
from pathlib import Path

# Configurar el path para imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Importar y ejecutar la aplicación principal
from app.streamlit_app import main

if __name__ == "__main__":
    main() 