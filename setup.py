from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="insurance-rag",
    version="2.0.0",
    author="BDP Team",
    author_email="team@bdp.com",
    description="Sistema RAG para documentos de seguros Allianz",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bdp/insurance-rag",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
    },
    entry_points={
        "console_scripts": [
            "insurance-rag=app.streamlit_app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.json", "*.csv"],
    },
) 