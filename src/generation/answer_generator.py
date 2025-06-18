"""
Generación de respuestas usando el modelo de OpenAI.
"""

import json
import time
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
import openai
from openai import OpenAI

from src.monitoring.performance import PerformanceMonitor

class AnswerGenerator:
    """
    Generador de respuestas para consultas sobre seguros usando OpenAI.
    """
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-3.5-turbo",
        max_length: int = 512,
        temperature: float = 0.7
    ):
        """
        Inicializa el generador de respuestas.
        
        Args:
            api_key: Clave API de OpenAI
            model_name: Nombre del modelo de OpenAI (debe ser un modelo de chat)
            max_length: Longitud máxima de la respuesta
            temperature: Temperatura para la generación
        """
        # Configurar cliente de OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.max_length = max_length
        self.temperature = temperature
        
        # Configurar logging simple
        self.logger = logging.getLogger("AnswerGenerator")
        self.logger.setLevel(logging.INFO)
        
        # Inicializar monitor de rendimiento
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
            metadata = doc.get("metadata", {})
            context += f"Documento {i}:\n"
            context += f"Producto: {metadata.get('producto', 'No especificado')}\n"
            context += f"Tipo de seguro: {metadata.get('insurance_type', 'No especificado')}\n"
            context += f"Tipo de cobertura: {metadata.get('coverage_type', 'No especificado')}\n"
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
        prompt = f"""Eres un asistente de seguros impulsado por IA específicamente creado para apoyar a los asesores de Allianz.
        Tu rol es proporcionar información sobre seguros, claras, precisas, concisas y personalizadas 
        para ayudar a los asesores de Allianz a responder preguntas de los clientes.

Sigue estas instrucciones:

1. Declara claramente tu rol: "Como Asistente de Seguros de Allianz..."
2. Usa respuestas estructuradas, concisas y relevantes.
3. Basa tus respuestas exclusivamente en el contexto proporcionado; si es insuficiente, indícalo claramente.
4. Sugiere preguntas de seguimiento accionables que los asesores deberían hacer a los clientes para recomendaciones más precisas.
5. Mantén un tono profesional pero amigable apropiado para asesores de Allianz.
6. Reconoce claramente si careces de información para proporcionar una respuesta precisa.

{context}

Pregunta: {query}"""
        
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
        Genera una respuesta para la consulta usando OpenAI.
        
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
            
            # Medir tiempo de ejecución
            start_time = time.time()
            
            # Generar respuesta usando OpenAI
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en seguros que responde preguntas basándose únicamente en la información proporcionada."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length or self.max_length,
                temperature=temperature or self.temperature,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time
            
            # Extraer respuesta
            answer = response.choices[0].message.content.strip()
            
            # Log simple y seguro
            self.logger.info(
                f"Respuesta generada para consulta: '{query}' | "
                f"Tiempo: {execution_time:.3f}s | "
                f"Documentos: {len(context_docs)} | "
                f"Longitud respuesta: {len(answer)} chars"
            )
            
            return answer
            
        except Exception as e:
            # Log de error simple
            error_msg = f"Error en answer_generator: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
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
                "context_documents": context_docs,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
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
            # Registrar error usando el método info con nivel de error
            self.logger.info(
                f"Error al guardar conversación: {str(e)}",
                error=True,
                component="answer_generator",
                context={"query": query}
            )

def main():
    """
    Función principal para probar el generador de respuestas.
    """
    # Obtener clave API de OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Por favor, configura la variable de entorno OPENAI_API_KEY")
    
    # Crear instancia del generador
    generator = AnswerGenerator(api_key=api_key)
    
    # Datos de prueba
    query = "¿Qué cubre un seguro de motocicleta?"
    context_docs = [
        {
            "text": "El seguro de motocicleta cubre daños materiales y personales causados por accidentes de tránsito. Incluye cobertura de responsabilidad civil, daños a terceros, asistencia vial y robo total.",
            "metadata": {
                "producto": "Seguro de Motocicleta",
                "insurance_type": "Motocicleta",
                "coverage_type": "Completo"
            }
        }
    ]
    
    try:
        # Generar respuesta
        response = generator.generate_answer(query, context_docs)
        print("\nPregunta:", query)
        print("\nRespuesta:", response)
        
        # Guardar conversación
        generator.save_conversation(query, response, context_docs)
        
    except Exception as e:
        print("\nError al generar respuesta:", str(e))

if __name__ == "__main__":
    main() 