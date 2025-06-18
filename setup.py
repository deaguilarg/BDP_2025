from setuptools import setup, find_packages

setup(
    name="insurance_rag",
    version="0.1.0",
    description="Sistema RAG para documentos de seguros Allianz",
    packages=find_packages(),
    install_requires=[
        # Core dependencies
        "numpy>=1.24.3",
        "sentence-transformers>=2.2.2",
        "faiss-cpu>=1.7.4",
        "transformers>=4.30.2",
        "huggingface-hub>=0.16.4",
        
        # PDF processing
        "pdfplumber>=0.11.6",
        
        # Web interface
        "streamlit>=1.28.0",
        "plotly>=5.15.0",
        
        # OpenAI
        "openai>=1.0.0",
        
        # Utilities
        "python-dotenv>=1.0.0",
        "tqdm>=4.65.0",
        "psutil>=5.9.5",
        "pandas>=2.0.0",
        
        # NLP
        "spacy>=3.7.2"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "insurance-rag=run_app:main",
            "setup-insurance-rag=scripts.setup:main"
        ]
    },
    python_requires=">=3.9",
    author="Equipo BDP",
    author_email="tu-email@empresa.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 