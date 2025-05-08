"""
Script de prueba para el generador de respuestas.
"""

import json
from pathlib import Path
from src.generation.answer_generator import AnswerGenerator

def load_test_context():
    """
    Carga un contexto de prueba desde los archivos de embeddings.
    """
    # Cargar chunks de prueba
    chunks_path = Path("data/embeddings/ipid-basico.json")
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    # Seleccionar algunos chunks relevantes
    test_chunks = [
        {
            "text": chunks[0]["text"],  # Chunk sobre qué consiste el seguro
            "metadata": {
                "producto": "IPID Básico",
                "insurance_type": "Accidentes",
                "coverage_type": "Básico"
            }
        },
        {
            "text": chunks[1]["text"],  # Chunk sobre qué está asegurado
            "metadata": {
                "producto": "IPID Básico",
                "insurance_type": "Accidentes",
                "coverage_type": "Básico"
            }
        }
    ]
    
    return test_chunks

def main():
    """
    Función principal para probar el generador de respuestas.
    """
    # Inicializar generador
    generator = AnswerGenerator()
    
    # Cargar contexto de prueba
    context_docs = load_test_context()
    
    # Pregunta de prueba
    query = "¿Qué cubre el seguro IPID Básico y cuáles son sus restricciones?"
    
    try:
        # Generar respuesta
        response = generator.generate_answer(query, context_docs)
        
        # Imprimir resultados
        print("\nPregunta:", query)
        print("\nRespuesta:", response)
        
        # Guardar conversación
        generator.save_conversation(query, response, context_docs)
        
    except Exception as e:
        print(f"Error durante la prueba: {str(e)}")

if __name__ == "__main__":
    main() 