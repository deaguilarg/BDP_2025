from setuptools import setup, find_packages

setup(
    name="insurance_rag",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.3",
        "torch>=2.0.1",
        "transformers>=4.30.2",
        "sentence-transformers>=2.2.2",
        "huggingface-hub>=0.16.4",
        "faiss-cpu>=1.7.4",
        "pdfplumber>=0.11.6",
        "spacy>=3.7.2",
        "tqdm>=4.65.0",
        "loguru>=0.7.0",
        "psutil>=5.9.5"
    ],
    python_requires=">=3.9",
) 