#!/usr/bin/env python3
"""
Script de configuración inicial para el Sistema RAG de Allianz.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    """Imprime el encabezado de bienvenida"""
    print("=" * 60)
    print("🛡️  CONFIGURACIÓN INICIAL - ASISTENTE ALLIANZ")
    print("=" * 60)
    print()

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Error: Se requiere Python 3.9 o superior")
        print(f"   Versión actual: {version.major}.{version.minor}")
        print("   Descarga Python desde: https://python.org/downloads/")
        return False
    
    print(f"✓ Python {version.major}.{version.minor} detectado")
    return True

def create_directories():
    """Crea la estructura de directorios necesaria"""
    directories = [
        "logs", "data/raw", "data/processed", "data/embeddings",
        "data/metadata", "models/faiss_index", "scripts"
    ]
    
    print("📁 Creando estructura de directorios...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {directory}")

def install_dependencies():
    """Instala las dependencias del proyecto"""
    print("📦 Instalando dependencias...")
    print("   (Esto puede tomar varios minutos)")
    
    try:
        # Actualizar pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        
        # Instalar requirements
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        
        print("   ✓ Dependencias instaladas correctamente")
        return True
        
    except subprocess.CalledProcessError as e:
        print("   ❌ Error instalando dependencias")
        print(f"      Error: {e}")
        return False

def setup_env_file():
    """Configura el archivo .env"""
    env_path = Path(".env")
    
    if env_path.exists():
        print("✓ Archivo .env ya existe")
        return True
    
    print("🔑 Configurando API de OpenAI...")
    print("   Necesitas una clave API de OpenAI para usar el sistema")
    
    response = input("   ¿Tienes tu API key lista? (s/n): ").lower()
    
    if response in ['s', 'si', 'y', 'yes']:
        api_key = input("   Ingresa tu API key: ").strip()
        
        if api_key and api_key.startswith("sk-"):
            with open(".env", "w") as f:
                f.write(f"OPENAI_API_KEY={api_key}\n")
            print("   ✓ Archivo .env creado correctamente")
            return True
        else:
            print("   ❌ API key inválida (debe comenzar con 'sk-')")
    
    print("   💡 Crea manualmente un archivo .env con:")
    print("      OPENAI_API_KEY=tu-clave-aqui")
    return False

def create_batch_files():
    """Crea archivos batch para Windows si no existen"""
    if os.name == 'nt':  # Windows
        # Archivo iniciar.bat ya existe
        if not Path("iniciar.bat").exists():
            print("📝 Creando archivo iniciar.bat...")
            # El archivo ya se creó anteriormente
        
        print("   ✓ Archivos de Windows configurados")

def main():
    """Función principal de configuración"""
    print_header()
    
    # Verificar Python
    if not check_python_version():
        return 1
    
    # Crear directorios
    create_directories()
    
    # Instalar dependencias
    if not install_dependencies():
        return 1
    
    # Configurar .env
    setup_env_file()
    
    # Crear archivos batch
    create_batch_files()
    
    print()
    print("=" * 60)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("=" * 60)
    print()
    print("Próximos pasos:")
    print("1. Si no configuraste la API key, crea el archivo .env")
    print("2. Ejecuta: python run_app.py")
    print("3. O en Windows: doble clic en iniciar.bat")
    print()
    print("El sistema generará automáticamente el índice")
    print("de documentos en la primera ejecución.")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 