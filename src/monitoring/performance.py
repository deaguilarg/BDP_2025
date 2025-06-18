"""
Sistema de monitoreo de rendimiento para el RAG de seguros.
"""

import time
import json
import psutil
import functools
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, List
from datetime import datetime

class PerformanceMonitor:
    """
    Monitor de rendimiento para el sistema RAG.
    """
    
    # Variable global para almacenar instancias de monitor
    _global_monitor = None
    
    def __init__(self, log_dir: str = "logs/performance"):
        """
        Inicializa el monitor de rendimiento.
        
        Args:
            log_dir: Directorio para almacenar logs de rendimiento
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging simple
        self.logger = logging.getLogger("PerformanceMonitor")
        self.logger.setLevel(logging.INFO)
        
        # Solo agregar handler si no existe
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_dir / "performance.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Inicializar contadores y métricas
        self.start_time = time.time()
        self.metrics: Dict[str, Any] = {
            "total_queries": 0,
            "total_processing_time": 0,
            "avg_response_time": 0,
            "memory_usage": [],
            "cpu_usage": [],
            "component_times": {},
            "error_rates": {},
            "query_latencies": []
        }
        
        # Establecer como monitor global si no existe
        if PerformanceMonitor._global_monitor is None:
            PerformanceMonitor._global_monitor = self
        
        # Registrar inicio
        self.logger.info(f"Monitor de rendimiento inicializado. Start time: {self.start_time}")
    
    @staticmethod
    def function_timer(component: str):
        """
        Decorador estático para monitorear el rendimiento de funciones.
        
        Args:
            component: Nombre del componente a monitorear
        
        Returns:
            Decorador que registra el tiempo de ejecución
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                error = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error = str(e)
                    raise
                finally:
                    duration = time.time() - start_time
                    
                    # Usar el monitor global si existe
                    if PerformanceMonitor._global_monitor:
                        try:
                            PerformanceMonitor._global_monitor.log_metrics(
                                component=component,
                                operation=func.__name__,
                                duration=duration,
                                error=error
                            )
                        except Exception as log_error:
                            # No fallar si hay problemas con el logging
                            print(f"Warning: Error logging metrics: {log_error}")
                            
            return wrapper
        return decorator
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """
        Obtiene métricas del sistema de forma segura.
        
        Returns:
            Diccionario con métricas del sistema
        """
        metrics = {
            "timestamp": time.time()
        }
        
        # Métricas de CPU y memoria de forma segura
        try:
            process = psutil.Process()
            metrics["memory_percent"] = process.memory_percent()
            metrics["cpu_percent"] = process.cpu_percent()
        except Exception as e:
            # Valores por defecto si hay problemas
            metrics["memory_percent"] = 0.0
            metrics["cpu_percent"] = 0.0
            print(f"Warning: Error getting system metrics: {e}")
        
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
        try:
            # Obtener métricas del sistema
            system_metrics = self._get_system_metrics()
            
            # Actualizar métricas globales
            self.metrics["total_processing_time"] += duration
            self.metrics["memory_usage"].append(system_metrics["memory_percent"])
            self.metrics["cpu_usage"].append(system_metrics["cpu_percent"])
            
            # Actualizar métricas por componente
            if component not in self.metrics["component_times"]:
                self.metrics["component_times"][component] = []
            self.metrics["component_times"][component].append(duration)
            
            # Calcular promedio de tiempo de respuesta
            if self.metrics["total_queries"] > 0:
                self.metrics["avg_response_time"] = (
                    self.metrics["total_processing_time"] / self.metrics["total_queries"]
                )
            
            # Log simple
            error_info = f" - ERROR: {kwargs.get('error')}" if kwargs.get('error') else ""
            self.logger.info(
                f"Component: {component} | Operation: {operation} | "
                f"Duration: {duration:.3f}s | Memory: {system_metrics['memory_percent']:.1f}% | "
                f"CPU: {system_metrics['cpu_percent']:.1f}%{error_info}"
            )
            
        except Exception as e:
            # No fallar el sistema principal si hay problemas con el monitoreo
            print(f"Warning: Error in log_metrics: {e}")
    
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
        try:
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
        except Exception as e:
            print(f"Warning: Error in log_query_metrics: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de rendimiento.
        
        Returns:
            Diccionario con estadísticas
        """
        try:
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
                    "avg_cpu": sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0
                }
            }
            
            return stats
        except Exception as e:
            print(f"Warning: Error getting statistics: {e}")
            return {}
    
    def save_statistics(self) -> None:
        """Guarda las estadísticas en un archivo JSON."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stats_file = self.log_dir / f"performance_stats_{timestamp}.json"
            
            stats = self.get_statistics()
            stats["timestamp"] = timestamp
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Estadísticas guardadas en: {stats_file}")
        except Exception as e:
            print(f"Warning: Error saving statistics: {e}")
    
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