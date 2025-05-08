import os
from src.generation.answer_generator import AnswerGenerator

def test_answer_generator():
    # Obtener clave API de OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Por favor, configura la variable de entorno OPENAI_API_KEY")
    
    # Crear instancia del generador
    generator = AnswerGenerator(api_key=api_key)
    
    # Datos de prueba
    query = "¿Qué cubre un seguro de auto?"
    context_docs = [
        {
            "text": "El seguro de auto cubre daños materiales y personales causados por accidentes de tránsito. Incluye cobertura de responsabilidad civil, daños a terceros y asistencia vial.",
            "metadata": {
                "producto": "Seguro de Auto",
                "insurance_type": "Auto",
                "coverage_type": "Completo"
            }
        }
    ]
    
    try:
        # Generar respuesta
        response = generator.generate_answer(query, context_docs)
        print("\nPregunta:", query)
        print("\nRespuesta:", response)
        return True
    except Exception as e:
        print("\nError al generar respuesta:", str(e))
        return False

if __name__ == "__main__":
    test_answer_generator() 