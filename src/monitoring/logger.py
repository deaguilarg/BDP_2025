"""
Configuración y utilidades de logging para el sistema.
"""

import logging
import os
from pathlib import Path
from loguru import logger
from typing import Dict, Any

class RAGLogger:
    """
    Clase para manejar el logging del sistema RAG.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Inicializa el logger.
        
        Args:
            log_dir: Directorio donde se guardarán los logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar loguru
        logger.add(
            self.log_dir / "rag_system.log",
            rotation="500 MB",
            retention="10 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        
        self.logger = logger
    
    def info(self, message: str, **kwargs: Dict[str, Any]) -> None:
        """
        Registra un mensaje informativo.
        
        Args:
            message: Mensaje a registrar
            kwargs: Datos adicionales para el log
        """
        self.logger.info(f"{message} | {kwargs if kwargs else ''}")
    
    def error(self, message: str, **kwargs: Dict[str, Any]) -> None:
        """
        Registra un mensaje de error.
        
        Args:
            message: Mensaje a registrar
            kwargs: Datos adicionales para el log
        """
        self.logger.error(f"{message} | {kwargs if kwargs else ''}")
    
    def warning(self, message: str, **kwargs: Dict[str, Any]) -> None:
        """
        Registra un mensaje de advertencia.
        
        Args:
            message: Mensaje a registrar
            kwargs: Datos adicionales para el log
        """
        self.logger.warning(f"{message} | {kwargs if kwargs else ''}")
    
    def debug(self, message: str, **kwargs: Dict[str, Any]) -> None:
        """
        Registra un mensaje de depuración.
        
        Args:
            message: Mensaje a registrar
            kwargs: Datos adicionales para el log
        """
        self.logger.debug(f"{message} | {kwargs if kwargs else ''}") 