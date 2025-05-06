"""
Sistema de logging personalizado para el RAG de seguros.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

class RAGLogger:
    """
    Logger personalizado para el sistema RAG.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Inicializa el logger.
        
        Args:
            log_dir: Directorio para almacenar logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logger principal
        self.logger = logging.getLogger("RAGLogger")
        self.logger.setLevel(logging.INFO)
        
        # Handler para archivo
        fh = logging.FileHandler(self.log_dir / "rag_system.log")
        fh.setLevel(logging.INFO)
        
        # Handler para consola
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Agregar handlers
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Crear subdirectorios
        (self.log_dir / "performance").mkdir(exist_ok=True)
        (self.log_dir / "user_queries").mkdir(exist_ok=True)
    
    def _format_message(
        self,
        message: str,
        **kwargs: Any
    ) -> str:
        """
        Formatea el mensaje con metadatos adicionales.
        """
        if kwargs:
            metadata = json.dumps(kwargs, ensure_ascii=False, indent=2)
            return f"{message}\nMetadata: {metadata}"
        return message
    
    def info(self, message: str, **kwargs: Any) -> None:
        """
        Registra un mensaje informativo.
        """
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """
        Registra una advertencia.
        """
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs: Any) -> None:
        """
        Registra un error.
        """
        self.logger.error(self._format_message(message, **kwargs))
    
    def log_query(
        self,
        query: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registra una consulta de usuario y su respuesta.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / "user_queries" / f"query_{timestamp}.json"
        
        log_data = {
            "timestamp": timestamp,
            "query": query,
            "response": response,
            "metadata": metadata or {}
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        self.info(
            "Consulta registrada",
            query_file=str(log_file),
            query_length=len(query),
            response_length=len(response)
        ) 