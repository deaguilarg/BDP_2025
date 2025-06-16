"""
Sistema de logging personalizado para el RAG de seguros.
"""

import logging
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
from loguru import logger

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
        
        # Crear subdirectorios para diferentes tipos de logs
        self._create_log_directories()
        
        # Configurar loguru para diferentes tipos de logs
        self._setup_loguru()
        
        # Configurar logger estándar para compatibilidad
        self._setup_standard_logger()
        
        # Inicializar contadores
        self.query_count = 0
        self.error_count = 0
        self.warning_count = 0
    
    def _create_log_directories(self) -> None:
        """Crea los subdirectorios necesarios para los logs."""
        directories = [
            "performance",  # Métricas de rendimiento
            "queries",      # Consultas de usuarios
            "errors",       # Errores del sistema
            "embeddings",   # Logs de generación de embeddings
            "index",        # Logs de construcción y carga de índices
            "generation",   # Logs de generación de respuestas
            "retrieval"     # Logs de recuperación de documentos
        ]
        
        for directory in directories:
            (self.log_dir / directory).mkdir(exist_ok=True)
    
    def _setup_loguru(self) -> None:
        """Configura los handlers de loguru para diferentes tipos de logs."""
        # Remover handlers por defecto
        logger.remove()
        
        # Configurar formato común
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        # Log general del sistema
        logger.add(
            self.log_dir / "rag_system.log",
            format=log_format,
            rotation="1 day",
            retention="7 days",
            compression="zip",
            level="INFO"
        )
        
        # Log de consultas
        logger.add(
            self.log_dir / "queries" / "queries_{time}.log",
            format=log_format,
            filter=lambda record: record["extra"].get("log_type") == "query",
            rotation="1 day",
            retention="30 days",
            compression="zip",
            level="INFO"
        )
        
        # Log de errores
        logger.add(
            self.log_dir / "errors" / "errors_{time}.log",
            format=log_format,
            filter=lambda record: record["level"].name == "ERROR",
            rotation="1 day",
            retention="30 days",
            compression="zip",
            level="ERROR"
        )
        
        # Log de rendimiento
        logger.add(
            self.log_dir / "performance" / "performance_{time}.log",
            format=log_format,
            filter=lambda record: record["extra"].get("log_type") == "performance",
            rotation="1 day",
            retention="7 days",
            compression="zip",
            level="INFO"
        )
    
    def _setup_standard_logger(self) -> None:
        """Configura el logger estándar de Python para compatibilidad."""
        self.logger = logging.getLogger("RAGLogger")
        self.logger.setLevel(logging.INFO)
        
        # Handler para archivo
        fh = logging.FileHandler(self.log_dir / "app.log")
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
    
    def _log_with_context(
        self,
        level: str,
        message: str,
        log_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Registra un mensaje con contexto adicional.
        
        Args:
            level: Nivel de log (info, warning, error)
            message: Mensaje a registrar
            log_type: Tipo de log (query, performance, etc.)
            **kwargs: Metadatos adicionales
        """
        # Actualizar contadores
        if level == "ERROR":
            self.error_count += 1
        elif level == "WARNING":
            self.warning_count += 1
        elif level == "INFO" and log_type == "query":
            self.query_count += 1
        
        # Agregar timestamp y contadores a los metadatos
        kwargs.update({
            "timestamp": datetime.now().isoformat(),
            "total_queries": self.query_count,
            "total_errors": self.error_count,
            "total_warnings": self.warning_count
        })
        
        # Registrar con loguru
        log_func = getattr(logger, level.lower())
        log_func(
            self._format_message(message, **kwargs),
            extra={"log_type": log_type}
        )
        
        # Registrar también con logger estándar
        log_func = getattr(self.logger, level.lower())
        log_func(self._format_message(message, **kwargs))
    
    def info(
        self,
        message: str,
        log_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Registra un mensaje informativo."""
        self._log_with_context("INFO", message, log_type, **kwargs)
    
    def warning(
        self,
        message: str,
        log_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Registra una advertencia."""
        self._log_with_context("WARNING", message, log_type, **kwargs)
    
    def error(
        self,
        message: str,
        log_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Registra un error."""
        self._log_with_context("ERROR", message, log_type, **kwargs)
    
    def log_query(
        self,
        query: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registra una consulta de usuario y su respuesta.
        
        Args:
            query: Consulta del usuario
            response: Respuesta generada
            metadata: Metadatos adicionales
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / "queries" / f"query_{timestamp}.json"
        
        log_data = {
            "timestamp": timestamp,
            "query": query,
            "response": response,
            "metadata": metadata or {},
            "query_id": self.query_count + 1
        }
        
        # Guardar en archivo JSON
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        # Registrar en logs
        self.info(
            "Consulta registrada",
            log_type="query",
            query_file=str(log_file),
            query_length=len(query),
            response_length=len(response),
            query_id=log_data["query_id"]
        )
    
    def log_performance(
        self,
        component: str,
        operation: str,
        duration: float,
        **kwargs: Any
    ) -> None:
        """
        Registra métricas de rendimiento.
        
        Args:
            component: Componente que se está midiendo
            operation: Operación realizada
            duration: Duración en segundos
            **kwargs: Métricas adicionales
        """
        metrics = {
            "component": component,
            "operation": operation,
            "duration": duration,
            **kwargs
        }
        
        self.info(
            f"Rendimiento: {component} - {operation}",
            log_type="performance",
            **metrics
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema.
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            "total_queries": self.query_count,
            "total_errors": self.error_count,
            "total_warnings": self.warning_count,
            "log_directory": str(self.log_dir),
            "timestamp": datetime.now().isoformat()
        }
    
    def cleanup_old_logs(self, days: int = 30) -> None:
        """
        Limpia logs antiguos.
        
        Args:
            days: Número de días a mantener
        """
        # Implementar limpieza de logs antiguos
        pass 