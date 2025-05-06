"""
Sistema de monitoreo de rendimiento para el RAG de seguros.
"""

import time
import json
import psutil
import functools
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from datetime import datetime

class PerformanceMonitor:
    """
    Monitor de rendimiento para el sistema RAG.
    """
    
    def __init__(self, log_dir: str = "logs/performance"):
        """
        Inicializa el monitor de rendimiento.
        
        Args:
            log_dir: Directorio para almacenar logs de rendimiento
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar contadores
        self.start_time = time.time()
        self.metrics: Dict[str, Any] = {
            "total_queries": 0,
            "total_processing_time": 0,
            "avg_response_time": 0,
            "memory_usage": [],
            "cpu_usage": []
        }
    
    def log_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Registra métricas de rendimiento.
        
        Args:
            metrics: Diccionario con métricas a registrar
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = self.log_dir / f"metrics_{timestamp}.json"
        
        # Agregar timestamp y métricas del sistema
        metrics.update({
            "timestamp": timestamp,
            "memory_percent": psutil.Process().memory_percent(),
            "cpu_percent": psutil.Process().cpu_percent()
        })
        
        # Guardar métricas
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        
        # Actualizar métricas globales
        self.metrics["memory_usage"].append(metrics["memory_percent"])
        self.metrics["cpu_usage"].append(metrics["cpu_percent"])
    
    @staticmethod
    def function_timer(operation_name: str) -> Callable:
        """
        Decorador para medir el tiempo de ejecución de funciones.
        
        Args:
            operation_name: Nombre de la operación para el log
            
        Returns:
            Función decorada
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Registrar métricas
                metrics = {
                    "operation": operation_name,
                    "execution_time": execution_time,
                    "success": True
                }
                
                # Si la instancia tiene un monitor, usar ese
                if hasattr(args[0], "performance_monitor"):
                    args[0].performance_monitor.log_metrics(metrics)
                
                return result
            return wrapper
        return decorator
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de las métricas de rendimiento.
        
        Returns:
            Diccionario con el resumen de métricas
        """
        total_time = time.time() - self.start_time
        
        return {
            "total_runtime": total_time,
            "total_queries": self.metrics["total_queries"],
            "avg_response_time": (
                self.metrics["total_processing_time"] / 
                self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 
                else 0
            ),
            "avg_memory_usage": (
                sum(self.metrics["memory_usage"]) / 
                len(self.metrics["memory_usage"])
                if self.metrics["memory_usage"] 
                else 0
            ),
            "avg_cpu_usage": (
                sum(self.metrics["cpu_usage"]) / 
                len(self.metrics["cpu_usage"])
                if self.metrics["cpu_usage"] 
                else 0
            )
        }
    
    def reset_metrics(self) -> None:
        """
        Reinicia los contadores de métricas.
        """
        self.start_time = time.time()
        self.metrics = {
            "total_queries": 0,
            "total_processing_time": 0,
            "avg_response_time": 0,
            "memory_usage": [],
            "cpu_usage": []
        } 