"""
Generación de respuestas usando el modelo de lenguaje.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.monitoring.logger import RAGLogger
from src.monitoring.performance import PerformanceMonitor

class AnswerGenerator:
    """
    Generador de respuestas para consultas sobre seguros.
    """
    
    def __init__(
        self,
        model_name: str = "AtlaAI/Selene-1-Mini-Llama-3.1-8B",
        max_length: int = 512,
        temperature: float = 0.7
    ):
        """
        Inicializa el generador de respuestas.
        
        Args:
            model_name: Nombre del modelo de lenguaje
            max_length: Longitud máxima de la respuesta
            temperature: Temperatura para la generación
        """
        # Cargar modelo y tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            load_in_8bit=True  # Optimización para memoria limitada
        )
        
        self.max_length = max_length
        self.temperature = temperature
        
        # Inicializar logger y monitor
        self.logger = RAGLogger()
        self.performance_monitor = PerformanceMonitor()
    
    def _format_context(self, context_docs: List[Dict]) -> str:
        """
        Formatea los documentos de contexto para el prompt.
        
        Args:
            context_docs: Lista de documentos con su texto y metadatos
            
        Returns:
            Contexto formateado
        """
        context = "Contexto relevante:\n\n"
        
        for i, doc in enumerate(context_docs, 1):
            metadata = doc["metadata"]
            context += f"Documento {i}:\n"
            context += f"Título: {metadata.get('title', 'No especificado')}\n"
            context += f"Aseguradora: {metadata.get('insurer', 'No especificada')}\n"
            context += f"Tipo de seguro: {metadata.get('insurance_type', 'No especificado')}\n"
            context += f"Texto: {doc.get('text', '')}\n\n"
        
        return context
    
    def _build_prompt(self, query: str, context_docs: List[Dict]) -> str:
        """
        Construye el prompt para el modelo.
        
        Args:
            query: Consulta del usuario
            context_docs: Documentos de contexto
            
        Returns:
            Prompt completo
        """
        # Formatear contexto
        context = self._format_context(context_docs)
        
        # Construir prompt
        prompt = f"""Por favor, responde la siguiente pregunta sobre seguros basándote únicamente en la información proporcionada en el contexto. Si la información no es suficiente para responder, indícalo claramente.

{context}

Pregunta: {query}

Respuesta:"""
        
        return prompt
    
    @PerformanceMonitor.function_timer("answer_generation")
    def generate_answer(
        self,
        query: str,
        context_docs: List[Dict],
        max_length: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Genera una respuesta para la consulta.
        
        Args:
            query: Consulta del usuario
            context_docs: Documentos de contexto
            max_length: Longitud máxima opcional
            temperature: Temperatura opcional
            
        Returns:
            Respuesta generada
        """
        try:
            # Construir prompt
            prompt = self._build_prompt(query, context_docs)
            
            # Tokenizar
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length
            ).to(self.model.device)
            
            # Generar respuesta
            outputs = self.model.generate(
                **inputs,
                max_length=max_length or self.max_length,
                temperature=temperature or self.temperature,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                num_return_sequences=1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Decodificar respuesta
            response = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )
            
            # Extraer solo la respuesta (después de "Respuesta:")
            response = response.split("Respuesta:")[-1].strip()
            
            self.logger.info(
                "Respuesta generada exitosamente",
                query_length=len(query),
                response_length=len(response),
                num_context_docs=len(context_docs)
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Error generando respuesta",
                query=query,
                error=str(e)
            )
            raise
    
    def save_conversation(
        self,
        query: str,
        response: str,
        context_docs: List[Dict],
        conversation_dir: str = "logs/conversations"
    ) -> None:
        """
        Guarda una conversación para análisis.
        
        Args:
            query: Consulta del usuario
            response: Respuesta generada
            context_docs: Documentos de contexto usados
            conversation_dir: Directorio para guardar conversaciones
        """
        try:
            # Crear directorio si no existe
            conversation_path = Path(conversation_dir)
            conversation_path.mkdir(parents=True, exist_ok=True)
            
            # Preparar datos
            conversation_data = {
                "query": query,
                "response": response,
                "context_documents": context_docs
            }
            
            # Guardar conversación
            timestamp = self.logger._get_timestamp()
            conversation_file = conversation_path / f"conversation_{timestamp}.json"
            
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(
                "Conversación guardada",
                file=str(conversation_file)
            )
            
        except Exception as e:
            self.logger.error(
                "Error guardando conversación",
                error=str(e)
            )
            # No levantar excepción para no interrumpir el flujo principal 