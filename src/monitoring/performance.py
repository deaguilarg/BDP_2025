"""
Sistema de monitoreo de rendimiento para el RAG de seguros.
"""

import time
import json
import psutil
import functools
from pathlib import Path
from typing import Any, Callable, Dict, Optional, List
from datetime import datetime
import torch

from src.monitoring.logger import RAGLogger

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
        
        # Inicializar logger
        self.logger = RAGLogger()
        
        # Inicializar contadores y métricas
        self.start_time = time.time()
        self.metrics: Dict[str, Any] = {
            "total_queries": 0,
            "total_processing_time": 0,
            "avg_response_time": 0,
            "memory_usage": [],
            "cpu_usage": [],
            "gpu_usage": [] if torch.cuda.is_available() else None,
            "component_times": {},
            "error_rates": {},
            "query_latencies": []
        }
        
        # Registrar inicio
        self.logger.info(
            "Monitor de rendimiento inicializado",
            log_type="performance",
            start_time=self.start_time,
            has_gpu=torch.cuda.is_available()
        )
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """
        Obtiene métricas del sistema.
        
        Returns:
            Diccionario con métricas del sistema
        """
        metrics = {
            "memory_percent": psutil.Process().memory_percent(),
            "cpu_percent": psutil.Process().cpu_percent(),
            "timestamp": time.time()
        }
        
        if torch.cuda.is_available():
            metrics["gpu_percent"] = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() * 100
        
        return metrics
    
    def log_metrics(
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
        # Obtener métricas del sistema
        system_metrics = self._get_system_metrics()
        
        # Actualizar métricas globales
        self.metrics["total_processing_time"] += duration
        self.metrics["memory_usage"].append(system_metrics["memory_percent"])
        self.metrics["cpu_usage"].append(system_metrics["cpu_percent"])
        if "gpu_percent" in system_metrics:
            self.metrics["gpu_usage"].append(system_metrics["gpu_percent"])
        
        # Actualizar métricas por componente
        if component not in self.metrics["component_times"]:
            self.metrics["component_times"][component] = []
        self.metrics["component_times"][component].append(duration)
        
        # Calcular promedio de tiempo de respuesta
        if self.metrics["total_queries"] > 0:
            self.metrics["avg_response_time"] = (
                self.metrics["total_processing_time"] / self.metrics["total_queries"]
            )
        
        # Preparar métricas para logging
        metrics = {
            "component": component,
            "operation": operation,
            "duration": duration,
            "system_metrics": system_metrics,
            "global_metrics": {
                "avg_response_time": self.metrics["avg_response_time"],
                "total_queries": self.metrics["total_queries"],
                "total_processing_time": self.metrics["total_processing_time"]
            },
            **kwargs
        }
        
        # Registrar métricas
        self.logger.log_performance(
            component=component,
            operation=operation,
            duration=duration,
            **metrics
        )
    
    def log_query_metrics(
        self,
        query: str,
        duration: float,
        num_results: int,
        error: Optional[str] = None
    ) -> None:
        """
        Registra métricas específicas de consultas.
        
        Args:
            query: Consulta realizada
            duration: Duración de la consulta
            num_results: Número de resultados
            error: Error si ocurrió alguno
        """
        self.metrics["total_queries"] += 1
        self.metrics["query_latencies"].append(duration)
        
        if error:
            if "queries" not in self.metrics["error_rates"]:
                self.metrics["error_rates"]["queries"] = 0
            self.metrics["error_rates"]["queries"] += 1
        
        self.log_metrics(
            component="query",
            operation="search",
            duration=duration,
            query_length=len(query),
            num_results=num_results,
            error=error
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de rendimiento.
        
        Returns:
            Diccionario con estadísticas
        """
        uptime = time.time() - self.start_time
        
        stats = {
            "uptime": uptime,
            "total_queries": self.metrics["total_queries"],
            "avg_response_time": self.metrics["avg_response_time"],
            "total_processing_time": self.metrics["total_processing_time"],
            "queries_per_minute": (self.metrics["total_queries"] / uptime) * 60 if uptime > 0 else 0,
            "error_rate": (
                self.metrics["error_rates"].get("queries", 0) / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0
            ),
            "component_performance": {
                component: {
                    "avg_time": sum(times) / len(times) if times else 0,
                    "min_time": min(times) if times else 0,
                    "max_time": max(times) if times else 0,
                    "total_calls": len(times)
                }
                for component, times in self.metrics["component_times"].items()
            },
            "system_metrics": {
                "avg_memory": sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
                "avg_cpu": sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
                "avg_gpu": sum(self.metrics["gpu_usage"]) / len(self.metrics["gpu_usage"]) if self.metrics["gpu_usage"] else None
            }
        }
        
        return stats
    
    def save_statistics(self) -> None:
        """Guarda las estadísticas en un archivo JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stats_file = self.log_dir / f"performance_stats_{timestamp}.json"
        
        stats = self.get_statistics()
        stats["timestamp"] = timestamp
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        self.logger.info(
            "Estadísticas de rendimiento guardadas",
            log_type="performance",
            stats_file=str(stats_file)
        )
    
    def monitor(self, component: str):
        """
        Decorador para monitorear el rendimiento de funciones.
        
        Args:
            component: Nombre del componente a monitorear
        
        Returns:
            Decorador que registra el tiempo de ejecución
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.log_metrics(
                        component=component,
                        operation=func.__name__,
                        duration=duration
                    )
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.log_metrics(
                        component=component,
                        operation=func.__name__,
                        duration=duration,
                        error=str(e)
                    )
                    raise
            return wrapper
        return decorator 