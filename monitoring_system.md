# Sistema de Monitoreo y Logging para RAG de Seguros

Este documento detalla la implementación del sistema de monitoreo y logging para evaluar el rendimiento del RAG de documentos de seguros.

## Objetivos del Sistema de Monitoreo

1. **Evaluar rendimiento**: Medir tiempos de respuesta, precisión y relevancia
2. **Identificar áreas de mejora**: Detectar patrones en consultas problemáticas
3. **Generar insights**: Crear visualizaciones y reportes para análisis
4. **Facilitar la optimización**: Proporcionar datos para ajustar parámetros

## Componentes del Sistema

### 1. Logger Principal (`src/monitoring/logger.py`)

```python
from loguru import logger
import os
import json
import time
from datetime import datetime
import psutil
import torch

class RAGLogger:
    def __init__(self, log_dir="./logs"):
        # Configurar loguru para diferentes tipos de logs
        self.log_dir = log_dir
        os.makedirs(f"{log_dir}/queries", exist_ok=True)
        os.makedirs(f"{log_dir}/performance", exist_ok=True)
        os.makedirs(f"{log_dir}/errors", exist_ok=True)
        
        # Log de consultas
        logger.add(f"{log_dir}/queries/queries.log", 
                  format="{time:YYYY-MM-DD at HH:mm:ss} | {message}",
                  filter=lambda record: record["extra"].get("log_type") == "query",
                  rotation="1 day")
        
        # Log de rendimiento
        logger.add(f"{log_dir}/performance/performance.log",
                  format="{time:YYYY-MM-DD at HH:mm:ss} | {message}",
                  filter=lambda record: record["extra"].get("log_type") == "performance",
                  rotation="1 day")
        
        # Log de errores
        logger.add(f"{log_dir}/errors/errors.log",
                  format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
                  filter=lambda record: record["level"].name == "ERROR",
                  rotation="1 week")
    
    def log_query(self, query, retrieved_docs, response, response_time, feedback=None):
        """Registra una consulta completa con sus resultados"""
        query_data = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "retrieved_docs": [doc.to_dict() for doc in retrieved_docs] if retrieved_docs else [],
            "response": response,
            "response_time_seconds": response_time,
            "feedback": feedback
        }
        
        # Guardar json detallado
        query_id = int(time.time())
        with open(f"{self.log_dir}/queries/query_{query_id}.json", "w", encoding="utf-8") as f:
            json.dump(query_data, f, ensure_ascii=False, indent=2)
        
        # Log resumido para el archivo de log
        logger.bind(log_type="query").info(f"Query: '{query}' | Time: {response_time:.2f}s | Docs: {len(retrieved_docs)}")
        
        return query_id
    
    def log_performance(self, component, operation, execution_time, metadata=None):
        """Registra métricas de rendimiento de componentes específicos"""
        metadata = metadata or {}
        
        # Obtener métricas del sistema
        sys_metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "gpu_memory_used": self._get_gpu_memory() if torch.cuda.is_available() else "N/A"
        }
        
        perf_data = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "operation": operation,
            "execution_time_seconds": execution_time,
            "system_metrics": sys_metrics,
            **metadata
        }
        
        # Log en formato JSON para fácil procesamiento
        logger.bind(log_type="performance").info(json.dumps(perf_data))
        
        return perf_data
    
    def log_error(self, component, error_msg, context=None):
        """Registra errores con contexto para diagnóstico"""
        context = context or {}
        
        error_data = {
            "component": component,
            "error": str(error_msg),
            "context": context
        }
        
        logger.error(f"Error en {component}: {error_msg} | Contexto: {json.dumps(context)}")
        
        return error_data
    
    def _get_gpu_memory(self):
        """Obtiene información sobre el uso de memoria GPU"""
        if not torch.cuda.is_available():
            return None
            
        device = torch.cuda.current_device()
        gpu_properties = torch.cuda.get_device_properties(device)
        memory_allocated = torch.cuda.memory_allocated(device) / (1024 ** 2)  # MB
        memory_reserved = torch.cuda.memory_reserved(device) / (1024 ** 2)    # MB
        
        return {
            "device_name": gpu_properties.name,
            "memory_allocated_mb": round(memory_allocated, 2),
            "memory_reserved_mb": round(memory_reserved, 2),
            "total_memory_mb": round(gpu_properties.total_memory / (1024 ** 2), 2)
        }
```

### 2. Monitor de Rendimiento (`src/monitoring/performance.py`)

```python
import time
import psutil
import numpy as np
import json
import os
from datetime import datetime, timedelta
from functools import wraps
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import torch
from loguru import logger

class PerformanceMonitor:
    def __init__(self, log_dir="./logs", visualizations_dir="./visualizations"):
        self.log_dir = log_dir
        self.visualizations_dir = visualizations_dir
        os.makedirs(visualizations_dir, exist_ok=True)
        
        # Inicializar métricas
        self.metrics = {
            "embedding_times": [],
            "retrieval_times": [],
            "llm_generation_times": [],
            "total_response_times": [],
            "num_chunks_retrieved": [],
            "relevance_scores": []
        }
    
    def function_timer(self, component_name):
        """Decorador para medir el tiempo de ejecución de funciones"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Registrar tiempo en el log
                logger.bind(log_type="performance").info(
                    f"{component_name} execution time: {execution_time:.4f}s"
                )
                
                # Almacenar la métrica según el componente
                if component_name == "embedding":
                    self.metrics["embedding_times"].append(execution_time)
                elif component_name == "retrieval":
                    self.metrics["retrieval_times"].append(execution_time)
                elif component_name == "llm_generation":
                    self.metrics["llm_generation_times"].append(execution_time)
                elif component_name == "total_response":
                    self.metrics["total_response_times"].append(execution_time)
                
                return result
            return wrapper
        return decorator
    
    def log_retrieval_metrics(self, num_chunks, relevance_scores):
        """Registra métricas relacionadas con la recuperación de documentos"""
        self.metrics["num_chunks_retrieved"].append(num_chunks)
        self.metrics["relevance_scores"].extend(relevance_scores)
        
        logger.bind(log_type="performance").info(
            f"Retrieval metrics: chunks={num_chunks}, avg_relevance={np.mean(relevance_scores):.4f}"
        )
    
    def generate_report(self, output_file=None):
        """Genera un informe detallado con estadísticas y visualizaciones"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{self.visualizations_dir}/performance_report_{timestamp}.html"
        
        # Generar visualizaciones
        self._create_time_distribution_chart()
        self._create_relevance_distribution_chart()
        self._create_system_usage_chart()
        
        # Calcular estadísticas
        stats = self._calculate_statistics()
        
        # Generar HTML con todos los componentes
        html_content = self._generate_html_report(stats)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return output_file
    
    def _calculate_statistics(self):
        """Calcula estadísticas descriptivas de las métricas recopiladas"""
        stats = {}
        
        for metric_name, values in self.metrics.items():
            if not values:
                stats[metric_name] = {"count": 0}
                continue
                
            stats[metric_name] = {
                "count": len(values),
                "mean": np.mean(values),
                "median": np.median(values),
                "min": np.min(values),
                "max": np.max(values),
                "p95": np.percentile(values, 95) if len(values) >= 20 else None
            }
        
        return stats
    
    def _create_time_distribution_chart(self):
        """Crea gráfico de distribución de tiempos por componente"""
        plt.figure(figsize=(10, 6))
        
        data = {
            "Embedding": self.metrics["embedding_times"],
            "Retrieval": self.metrics["retrieval_times"],
            "LLM Generation": self.metrics["llm_generation_times"],
            "Total Response": self.metrics["total_response_times"]
        }
        
        sns.boxplot(data=pd.DataFrame(data))
        plt.title("Distribución de Tiempos por Componente")
        plt.ylabel("Tiempo (segundos)")
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Guardar imagen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(f"{self.visualizations_dir}/time_distribution_{timestamp}.png")
        plt.close()
    
    def _create_relevance_distribution_chart(self):
        """Crea histograma de puntuaciones de relevancia"""
        if not self.metrics["relevance_scores"]:
            return
            
        plt.figure(figsize=(10, 6))
        sns.histplot(self.metrics["relevance_scores"], kde=True)
        plt.title("Distribución de Puntuaciones de Relevancia")
        plt.xlabel("Puntuación de Relevancia")
        plt.ylabel("Frecuencia")
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Guardar imagen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(f"{self.visualizations_dir}/relevance_distribution_{timestamp}.png")
        plt.close()
    
    def _create_system_usage_chart(self):
        """Crea gráfico de uso de recursos del sistema"""
        # Este método leería los logs de rendimiento y crearía visualizaciones
        # de uso de CPU, memoria y GPU a lo largo del tiempo
        pass
    
    def _generate_html_report(self, stats):
        """Genera reporte HTML con estadísticas y visualizaciones"""
        # Implementación básica de un informe HTML
        # En un sistema real, se usaría una plantilla más elaborada
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Informe de Rendimiento RAG - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .metric-section {{ margin: 30px 0; }}
                .visualization {{ margin: 30px 0; text-align: center; }}
                .visualization img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <h1>Informe de Rendimiento del Sistema RAG</h1>
            <p>Generado el: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="metric-section">
                <h2>Estadísticas de Tiempos de Ejecución</h2>
                <table>
                    <tr>
                        <th>Componente</th>
                        <th>Contador</th>
                        <th>Media (s)</th>
                        <th>Mediana (s)</th>
                        <th>Min (s)</th>
                        <th>Max (s)</th>
                        <th>P95 (s)</th>
                    </tr>
        """
        
        # Añadir filas para cada componente de tiempo
        for metric in ["embedding_times", "retrieval_times", "llm_generation_times", "total_response_times"]:
            component_name = metric.replace("_times", "").replace("_", " ").title()
            s = stats[metric]
            
            if s["count"] == 0:
                html += f"""
                    <tr>
                        <td>{component_name}</td>
                        <td colspan="6">No hay datos disponibles</td>
                    </tr>
                """
                continue
            
            html += f"""
                <tr>
                    <td>{component_name}</td>
                    <td>{s["count"]}</td>
                    <td>{s["mean"]:.4f}</td>
                    <td>{s["median"]:.4f}</td>
                    <td>{s["min"]:.4f}</td>
                    <td>{s["max"]:.4f}</td>
                    <td>{s["p95"]:.4f if s["p95"] is not None else "N/A"}</td>
                </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div class="metric-section">
                <h2>Estadísticas de Recuperación</h2>
                <table>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                    </tr>
        """
        
        # Añadir estadísticas de recuperación
        if stats["num_chunks_retrieved"]["count"] > 0:
            html += f"""
                <tr>
                    <td>Número promedio de chunks recuperados</td>
                    <td>{stats["num_chunks_retrieved"]["mean"]:.2f}</td>
                </tr>
            """
        
        if stats["relevance_scores"]["count"] > 0:
            html += f"""
                <tr>
                    <td>Puntuación media de relevancia</td>
                    <td>{stats["relevance_scores"]["mean"]:.4f}</td>
                </tr>
                <tr>
                    <td>Puntuación mínima de relevancia</td>
                    <td>{stats["relevance_scores"]["min"]:.4f}</td>
                </tr>
                <tr>
                    <td>Puntuación máxima de relevancia</td>
                    <td>{stats["relevance_scores"]["max"]:.4f}</td>
                </tr>
            """
        
        # Añadir las imágenes de las visualizaciones
        html += """
                </table>
            </div>
            
            <div class="visualization">
                <h2>Distribución de Tiempos por Componente</h2>
                <img src="time_distribution_{timestamp}.png" alt="Distribución de Tiempos">
            </div>
            
            <div class="visualization">
                <h2>Distribución de Puntuaciones de Relevancia</h2>
                <img src="relevance_distribution_{timestamp}.png" alt="Distribución de Relevancia">
            </div>
        </body>
        </html>
        """.format(timestamp=timestamp)
        
        return html
```

### 3. Integración en Componentes Principales

#### En `src/embeddings/embed_documents.py`:

```python
from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

# Inicializar logger y monitor
logger = RAGLogger()
performance_monitor = PerformanceMonitor()

@performance_monitor.function_timer("embedding")
def generate_embeddings(documents):
    # Código para generar embeddings
    # ...
    return embeddings
```

#### En `src/retrieval/search_engine.py`:

```python
from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

# Inicializar logger y monitor
logger = RAGLogger()
performance_monitor = PerformanceMonitor()

@performance_monitor.function_timer("retrieval")
def search_documents(query, top_k=5):
    # Código para buscar documentos
    # ...
    
    # Registrar métricas de la búsqueda
    relevance_scores = [doc.score for doc in retrieved_docs]
    performance_monitor.log_retrieval_metrics(
        num_chunks=len(retrieved_docs),
        relevance_scores=relevance_scores
    )
    
    return retrieved_docs
```

#### En `src/generation/answer_generator.py`:

```python
from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

# Inicializar logger y monitor
logger = RAGLogger()
performance_monitor = PerformanceMonitor()

@performance_monitor.function_timer("llm_generation")
def generate_answer(query, contexts):
    # Código para generar respuesta con LLM
    # ...
    return response
```

#### En la aplicación principal:

```python
@performance_monitor.function_timer("total_response")
def process_query(query):
    # Proceso completo desde consulta hasta respuesta
    # ...
    
    # Registrar la consulta completa
    query_id = logger.log_query(
        query=query,
        retrieved_docs=retrieved_docs,
        response=response,
        response_time=execution_time
    )
    
    return response, query_id
```

## Visualizaciones en la Interfaz de Depuración

La interfaz de depuración (`app/debug_interface.py`) incluirá visualizaciones generadas a partir de los datos recopilados:

1. **Gráficos de tiempo de respuesta**: Evolución temporal y distribución
2. **Mapa de calor de relevancia**: Visualización de qué chunks son más relevantes
3. **Estadísticas de uso**: CPU, memoria y GPU
4. **Métricas de rendimiento por tipo de consulta**: Categorización de preguntas

## Obtención de Feedback del Usuario

La interfaz principal incluirá un mecanismo simple para que los usuarios califiquen la calidad de las respuestas:

```python
# En app/streamlit_app.py
if st.button("👍 Respuesta útil"):
    logger.log_query(
        query=query,
        retrieved_docs=retrieved_docs,
        response=response,
        response_time=response_time,
        feedback={"rating": "positive"}
    )
    st.success("¡Gracias por tu feedback!")

if st.button("👎 Respuesta no útil"):
    feedback_text = st.text_area("¿Puedes decirnos por qué?")
    logger.log_query(
        query=query,
        retrieved_docs=retrieved_docs,
        response=response,
        response_time=response_time,
        feedback={"rating": "negative", "comment": feedback_text}
    )
    st.success("¡Gracias por ayudarnos a mejorar!")
```

## Generación de Informes

El sistema puede generar informes periódicos o bajo demanda:

```python
# Generar informe bajo demanda en la interfaz de depuración
if st.button("Generar informe de rendimiento"):
    report_file = performance_monitor.generate_report()
    st.success(f"Informe generado exitosamente: {report_file}")
    # Proporcionar enlace para descargar
```

## Plan de Análisis de Datos

Los datos recopilados permitirán realizar análisis como:

1. Identificar patrones en consultas con tiempos de respuesta largos
2. Detectar tipos de preguntas donde el RAG tiene menor precisión
3. Optimizar parámetros de chunking y recuperación
4. Evaluar el impacto de cambios en el modelo o configuración

Este sistema proporcionará la base para crear un informe detallado sobre el rendimiento del RAG y áreas de mejora potencial.