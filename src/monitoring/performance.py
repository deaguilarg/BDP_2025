"""
Utilidades para monitorear el rendimiento del sistema.
"""

import time
import functools
from typing import Any, Callable
import psutil
import torch
from loguru import logger

class PerformanceMonitor:
    """
    Clase para monitorear el rendimiento del sistema.
    """
    
    @staticmethod
    def function_timer(operation_name: str) -> Callable:
        """
        Decorador para medir el tiempo de ejecución de una función.
        
        Args:
            operation_name: Nombre de la operación que se está midiendo
            
        Returns:
            Función decorada
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                execution_time = end_time - start_time
                logger.info(f"Operación {operation_name} completada en {execution_time:.2f} segundos")
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def get_gpu_memory_info() -> dict:
        """
        Obtiene información sobre el uso de memoria GPU.
        
        Returns:
            Diccionario con información de memoria GPU
        """
        if torch.cuda.is_available():
            gpu_memory = {}
            for i in range(torch.cuda.device_count()):
                gpu_memory[f"gpu_{i}"] = {
                    "total": torch.cuda.get_device_properties(i).total_memory,
                    "allocated": torch.cuda.memory_allocated(i),
                    "cached": torch.cuda.memory_reserved(i)
                }
            return gpu_memory
        return {"gpu_available": False}
    
    @staticmethod
    def get_system_metrics() -> dict:
        """
        Obtiene métricas del sistema.
        
        Returns:
            Diccionario con métricas del sistema
        """
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "gpu_info": PerformanceMonitor.get_gpu_memory_info()
        }
    
    @staticmethod
    def log_system_metrics() -> None:
        """
        Registra las métricas del sistema en el log.
        """
        metrics = PerformanceMonitor.get_system_metrics()
        logger.info(f"Métricas del sistema: {metrics}") 